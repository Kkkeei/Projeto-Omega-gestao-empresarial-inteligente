from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.db.database import conectar_banco
from app.modules.contabil import repository, service
from app.services.auth_service import ensure_admin_user


def _criar_empresa(regime: str | None = None) -> int:
    cnpj = uuid4().int % 10**14
    with conectar_banco() as conn:
        cursor = conn.execute(
            """INSERT INTO empresas (cnpj, razao_social, nome_fantasia, regime_tributario, ativo)
               VALUES (?, ?, ?, ?, 1)""",
            (f"{cnpj:014d}", f"EMPRESA TESTE {cnpj}", "Empresa Teste", regime),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _criar_documento(empresa_id: int, competencia: int, nome: str) -> int:
    with conectar_banco() as conn:
        cursor = conn.execute(
            """INSERT INTO contabil_categorias (empresa_id, nome, ordem)
               VALUES (?, ?, 1)""",
            (empresa_id, f"Categoria {uuid4().hex[:8]}"),
        )
        categoria_id = int(cursor.lastrowid)
        cursor = conn.execute(
            """INSERT INTO contabil_documentos
                (empresa_id, categoria_id, nome, competencia_inicio, criado_por)
               VALUES (?, ?, ?, ?, 1)""",
            (empresa_id, categoria_id, nome, competencia),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _admin():
    ensure_admin_user()
    with conectar_banco() as conn:
        user = conn.execute("SELECT * FROM usuarios WHERE perfil='ADMIN' ORDER BY id LIMIT 1").fetchone()
        assert user is not None
        return dict(user)


def test_painel_calcula_situacoes_bloqueia_sem_documento_e_registra_nao_aplicavel():
    admin = _admin()
    empresa_id = _criar_empresa("LUCRO REAL")
    competencia = date.today().year * 100 + date.today().month
    primeiro_documento = _criar_documento(empresa_id, competencia, "Extrato recebido")
    segundo_documento = _criar_documento(empresa_id, competencia, "Extrato pendente")

    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "LUCRO REAL", None, False, 1, 200, admin,
    )
    empresa = next(item for item in painel["empresas"] if item["id"] == empresa_id)
    assert empresa["movimentacoes_total"] == 2
    assert empresa["movimentacoes_concluidas"] == 0
    assert empresa["situacao"] == "PENDENTE"
    assert empresa["aguardando_documento"] == 2

    with conectar_banco() as conn:
        primeira = conn.execute(
            "SELECT id FROM contabil_movimentacoes WHERE documento_origem_id=?",
            (primeiro_documento,),
        ).fetchone()
        segunda = conn.execute(
            "SELECT id FROM contabil_movimentacoes WHERE documento_origem_id=?",
            (segundo_documento,),
        ).fetchone()
        obrigacao = conn.execute(
            "SELECT id FROM contabil_obrigacoes WHERE documento_id=? AND competencia=?",
            (primeiro_documento, competencia),
        ).fetchone()
        assert primeira is not None and segunda is not None and obrigacao is not None
        obrigacao_id = obrigacao["id"]

    with pytest.raises(ValueError, match="Receba o documento"):
        service.atualizar_movimentacao_competencia(
            primeira["id"], competencia, {"lancado": True}, admin,
        )

    with conectar_banco() as conn:
        conn.execute(
            """INSERT INTO contabil_arquivos
                (obrigacao_id, nome_original, nome_armazenado, caminho_storage,
                 extensao, tamanho, hash_sha256)
               VALUES (?, 'extrato.pdf', 'extrato.pdf', 'teste/extrato.pdf',
                       '.pdf', 1, 'hash-teste')""",
            (obrigacao_id,),
        )
        conn.commit()

    service.atualizar_movimentacao_competencia(
        primeira["id"], competencia, {"lancado": True}, admin,
    )
    service.atualizar_movimentacao_competencia(
        primeira["id"], competencia, {"conferido": True}, admin,
    )
    service.atualizar_movimentacao_competencia(
        segunda["id"], competencia,
        {"data_limite": date.today() - timedelta(days=1)}, admin,
    )

    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "LUCRO REAL", None, False, 1, 200, admin,
    )
    empresa = next(item for item in painel["empresas"] if item["id"] == empresa_id)
    assert empresa["movimentacoes_concluidas"] == 1
    assert empresa["situacao"] == "ATRASADO"
    assert empresa["indicador"] == "VERMELHO"

    service.atualizar_movimentacao_competencia(
        segunda["id"], competencia,
        {"aplicavel": False, "justificativa": "Sem movimentação nesta competência."},
        admin,
    )
    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "LUCRO REAL", None, False, 1, 200, admin,
    )
    empresa = next(item for item in painel["empresas"] if item["id"] == empresa_id)
    assert empresa["movimentacoes_total"] == 1
    assert empresa["movimentacoes_concluidas"] == 1
    assert empresa["situacao"] == "CONCLUIDO"

    with conectar_banco() as conn:
        history = conn.execute(
            """SELECT dados_novos, observacao FROM contabil_historico
                WHERE entidade='MOVIMENTACAO_COMPETENCIA'
                  AND entidade_id=(
                    SELECT id FROM contabil_movimentacoes_competencias
                     WHERE movimentacao_id=? AND competencia=?
                  )
                ORDER BY id DESC LIMIT 1""",
            (segunda["id"], competencia),
        ).fetchone()
        assert history is not None
        assert "Sem movimentação nesta competência." in history["observacao"]
        assert '"aplicavel": 0' in history["dados_novos"]


def test_painel_respeita_empresa_atribuida_e_contagens_de_regime():
    admin = _admin()
    assigned_id = _criar_empresa("SIMPLES NACIONAL")
    unassigned_id = _criar_empresa("LUCRO REAL")
    with conectar_banco() as conn:
        cursor = conn.execute(
            """INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo)
               VALUES (?, ?, ?, 'USUARIO', 1)""",
            ("Responsável Teste", f"{uuid4().hex}@example.test", "hash-teste"),
        )
        user_id = int(cursor.lastrowid)
        conn.execute(
            """INSERT INTO contabil_atribuicoes (empresa_id, usuario_id)
               VALUES (?, ?)""",
            (assigned_id, user_id),
        )
        conn.commit()
        user = dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone())

    competencia = date.today().year * 100 + date.today().month
    user_panel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "TODOS", None, False, 1, 200, user,
    )
    visible_user_ids = {item["id"] for item in user_panel["empresas"]}
    assert assigned_id in visible_user_ids
    assert unassigned_id in visible_user_ids

    admin_panel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "TODOS", None, False, 1, 200, admin,
    )
    visible_ids = {item["id"] for item in admin_panel["empresas"]}
    assert assigned_id in visible_ids
    assert unassigned_id in visible_ids
    assert admin_panel["resumo"]["simples_nacional"] >= 1
    assert admin_panel["resumo"]["lucro_real"] >= 1


def test_detalhe_e_criacao_de_movimentacao_interna_respeitam_competencia():
    admin = _admin()
    empresa_id = _criar_empresa("SIMPLES NACIONAL")
    competencia = date.today().year * 100 + date.today().month
    from app.modules.contabil.schemas import MovimentacaoCreate

    created = service.criar_movimentacao_interna(
        empresa_id,
        MovimentacaoCreate(nome="Folha de pagamento", competencia_inicio=competencia),
        admin,
    )
    assert created["origem"] == "LANCAMENTOS_CONFERENCIAS"

    detalhe = repository.obter_painel_empresa_lancamentos(empresa_id, competencia, admin)
    assert detalhe["resumo"]["total"] == 1
    assert detalhe["movimentacoes"][0]["nome"] == "Folha de pagamento"
    assert detalhe["movimentacoes"][0]["documento_disponivel"] is True
    assert detalhe["movimentacoes"][0]["aplicavel"] is True
    assert detalhe["resumo"]["pendentes"] == 1

    anterior = competencia - 1 if competencia % 100 > 1 else (competencia // 100 - 1) * 100 + 12
    detalhe_anterior = repository.obter_painel_empresa_lancamentos(empresa_id, anterior, admin)
    assert detalhe_anterior["resumo"]["total"] == 0


def test_detalhe_bloqueia_empresa_fora_da_carteira():
    admin = _admin()
    empresa_id = _criar_empresa("LUCRO REAL")
    with conectar_banco() as conn:
        cursor = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
            ("Usuário sem carteira", f"{uuid4().hex}@example.test", "hash", "USUARIO"),
        )
        user = dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (cursor.lastrowid,)).fetchone())
        other = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
            ("Outro responsável", f"{uuid4().hex}@example.test", "hash", "USUARIO"),
        ).lastrowid
        conn.execute(
            "INSERT INTO contabil_atribuicoes (empresa_id,usuario_id) VALUES (?,?)",
            (empresa_id, other),
        )
        conn.commit()
    competencia = date.today().year * 100 + date.today().month
    with pytest.raises(PermissionError, match="outro responsável"):
        repository.obter_painel_empresa_lancamentos(empresa_id, competencia, user)


def test_inativacao_interna_preserva_competencia_final_e_bloqueia_futuras():
    admin = _admin()
    empresa_id = _criar_empresa("LUCRO PRESUMIDO")
    competencia = date.today().year * 100 + date.today().month
    from app.modules.contabil.schemas import MovimentacaoCreate

    created = service.criar_movimentacao_interna(
        empresa_id,
        MovimentacaoCreate(nome="Parcelamento", competencia_inicio=competencia),
        admin,
    )
    result = service.inativar_movimentacao_interna(
        created["id"], competencia, "Encerramento da obrigação", admin,
    )
    assert result["ativa"] is False
    atual = repository.obter_painel_empresa_lancamentos(empresa_id, competencia, admin)
    assert any(item["movimentacao_id"] == created["id"] for item in atual["movimentacoes"])
    futura = competencia + 1 if competencia % 100 < 12 else (competencia // 100 + 1) * 100 + 1
    futuro = repository.obter_painel_empresa_lancamentos(empresa_id, futura, admin)
    assert all(item["movimentacao_id"] != created["id"] for item in futuro["movimentacoes"])


def test_documento_inativado_preserva_visualizacao_das_competencias_anteriores():
    from app.modules.contabil.schemas import DocumentoCreate, DocumentoInativar

    admin = _admin()
    empresa_id = _criar_empresa("LUCRO REAL")
    categoria = service.criar_categoria(empresa_id, "Extratos", None, admin["id"])
    documento = service.criar_documento(
        empresa_id,
        DocumentoCreate(
            categoria_id=categoria["id"],
            nome="Extrato histórico",
            competencia_inicio=202609,
        ),
        admin["id"],
    )
    service.inativar_documento(
        documento["id"],
        DocumentoInativar(competencia_fim=202610, motivo="Conta encerrada"),
        admin["id"],
    )

    historico = repository.documentacao(empresa_id, 202609, 2026, admin["id"])
    posterior = repository.documentacao(empresa_id, 202611, 2026, admin["id"])

    assert any(item["id"] == documento["id"] for item in historico["documentos"])
    item_historico = next(item for item in historico["documentos"] if item["id"] == documento["id"])
    assert item_historico["ativo"] is False
    assert all(item["id"] != documento["id"] for item in posterior["documentos"])


def test_edicao_documento_atualiza_movimentacao_derivada_e_retorna_registro_correto():
    from app.modules.contabil.schemas import DocumentoCreate, DocumentoUpdate

    admin = _admin()
    empresa_id = _criar_empresa("SIMPLES NACIONAL")
    categoria_a = service.criar_categoria(empresa_id, "Bancos", None, admin["id"])
    categoria_b = service.criar_categoria(empresa_id, "Aplicações", None, admin["id"])
    documento = service.criar_documento(
        empresa_id,
        DocumentoCreate(
            categoria_id=categoria_a["id"],
            nome="Banco Alfa",
            competencia_inicio=202610,
        ),
        admin["id"],
    )
    # Materializa a movimentação derivada da documentação.
    repository.obter_painel_empresa_lancamentos(empresa_id, 202610, admin)
    atualizado = service.atualizar_documento(
        documento["id"],
        DocumentoUpdate(nome="Banco Beta", categoria_id=categoria_b["id"], observacao="Atualizado"),
        admin["id"],
    )

    with conectar_banco() as conn:
        movimento = conn.execute(
            "SELECT nome, categoria_id FROM contabil_movimentacoes WHERE documento_origem_id=?",
            (documento["id"],),
        ).fetchone()
    assert atualizado["id"] == documento["id"]
    assert atualizado["nome"] == "Banco Beta"
    assert movimento["nome"] == "Banco Beta"
    assert movimento["categoria_id"] == categoria_b["id"]


def test_empresa_sem_movimentacoes_fica_com_indicador_neutro():
    admin = _admin()
    empresa_id = _criar_empresa("LUCRO REAL")
    competencia = date.today().year * 100 + date.today().month
    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "TODOS", None, False, 1, 500, admin,
    )
    empresa = next(item for item in painel["empresas"] if item["id"] == empresa_id)
    assert empresa["movimentacoes_total"] == 0
    assert empresa["movimentacoes_concluidas"] == 0
    assert empresa["situacao"] == "SEM_MOVIMENTACOES"
    assert empresa["indicador"] == "CINZA"


def test_empresa_com_9_de_10_concluidas_mas_uma_vencida_fica_atrasada():
    admin = _admin()
    empresa_id = _criar_empresa("LUCRO PRESUMIDO")
    competencia = date.today().year * 100 + date.today().month
    from app.modules.contabil.schemas import MovimentacaoCreate

    movements = []
    for index in range(10):
        movements.append(service.criar_movimentacao_interna(
            empresa_id,
            MovimentacaoCreate(nome=f"Movimentação {index + 1}", competencia_inicio=competencia),
            admin,
        ))
    for movement in movements[:9]:
        service.atualizar_movimentacao_competencia(
            movement["id"], competencia, {"lancado": True}, admin,
        )
        service.atualizar_movimentacao_competencia(
            movement["id"], competencia, {"conferido": True}, admin,
        )
    service.atualizar_movimentacao_competencia(
        movements[9]["id"], competencia,
        {"data_limite": date.today() - timedelta(days=1)}, admin,
    )
    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "TODOS", None, False, 1, 500, admin,
    )
    empresa = next(item for item in painel["empresas"] if item["id"] == empresa_id)
    assert empresa["movimentacoes_concluidas"] == 9
    assert empresa["movimentacoes_total"] == 10
    assert empresa["progresso_percentual"] == 90
    assert empresa["situacao"] == "ATRASADO"
    assert empresa["indicador"] == "VERMELHO"


def test_dashboard_contabil_exibe_empresa_sem_responsavel_e_respeita_carteira():
    _admin()
    assigned_id = _criar_empresa("SIMPLES NACIONAL")
    shared_id = _criar_empresa("LUCRO REAL")
    assigned_to_other_id = _criar_empresa("LUCRO PRESUMIDO")
    with conectar_banco() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
            ("Responsável Dashboard", f"{uuid4().hex}@example.test", "hash", "USUARIO"),
        )
        user = dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (cur.lastrowid,)).fetchone())
        other = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
            ("Outro Responsável", f"{uuid4().hex}@example.test", "hash", "USUARIO"),
        ).lastrowid
        conn.execute("INSERT INTO contabil_atribuicoes (empresa_id,usuario_id) VALUES (?,?)", (assigned_id,user["id"]))
        conn.execute("INSERT INTO contabil_atribuicoes (empresa_id,usuario_id) VALUES (?,?)", (assigned_to_other_id,other))
        conn.commit()
    competencia = date.today().year * 100 + date.today().month
    dashboard = repository.listar_dashboard(competencia, None, None, None, False, 1, 200, user)
    visible_ids = {item["id"] for item in dashboard["empresas"]}
    assert assigned_id in visible_ids
    assert shared_id in visible_ids
    assert assigned_to_other_id not in visible_ids


def test_usuario_acessa_empresa_sem_responsavel_mas_nao_empresa_de_outro_responsavel():
    _admin()
    shared_id = _criar_empresa("LUCRO REAL")
    assigned_to_other_id = _criar_empresa("LUCRO PRESUMIDO")
    with conectar_banco() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
            ("Usuário de teste", f"{uuid4().hex}@example.test", "hash", "USUARIO"),
        )
        user = dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (cur.lastrowid,)).fetchone())
        other = conn.execute(
            "INSERT INTO usuarios (nome,email,senha_hash,perfil,ativo) VALUES (?,?,?,?,1)",
            ("Outro Responsável", f"{uuid4().hex}@example.test", "hash", "USUARIO"),
        ).lastrowid
        conn.execute("INSERT INTO contabil_atribuicoes (empresa_id,usuario_id) VALUES (?,?)", (assigned_to_other_id,other))
        conn.commit()
    service.validar_acesso_empresa(shared_id, user)
    with pytest.raises(PermissionError, match="outro responsável"):
        service.validar_acesso_empresa(assigned_to_other_id, user)


def test_movimentacao_lancada_sem_conferencia_gera_indicador_azul_e_em_andamento():
    admin = _admin()
    empresa_id = _criar_empresa("LUCRO PRESUMIDO")
    competencia = date.today().year * 100 + date.today().month
    from app.modules.contabil.schemas import MovimentacaoCreate

    primeira = service.criar_movimentacao_interna(
        empresa_id, MovimentacaoCreate(nome="Movimento parcial", competencia_inicio=competencia), admin,
    )
    service.criar_movimentacao_interna(
        empresa_id, MovimentacaoCreate(nome="Movimento pendente", competencia_inicio=competencia), admin,
    )
    service.atualizar_movimentacao_competencia(primeira["id"], competencia, {"lancado": True}, admin)
    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "TODOS", None, False, 1, 500, admin,
    )
    empresa = next(item for item in painel["empresas"] if item["id"] == empresa_id)
    assert empresa["situacao"] == "EM_ANDAMENTO"
    assert empresa["indicador"] == "AZUL"
    assert empresa["movimentacoes_concluidas"] == 0
    assert empresa["movimentacoes_total"] == 2


def test_pesquisa_do_painel_encontra_empresa_por_cnpj_sem_mascara():
    admin = _admin()
    empresa_id = _criar_empresa("SIMPLES NACIONAL")
    with conectar_banco() as conn:
        cnpj = conn.execute("SELECT cnpj FROM empresas WHERE id=?", (empresa_id,)).fetchone()["cnpj"]
    painel = repository.listar_painel_lancamentos_conferencias(
        date.today().year * 100 + date.today().month, cnpj, "TODOS", None, False, 1, 500, admin,
    )
    assert [item["id"] for item in painel["empresas"]] == [empresa_id]


def test_conta_configurada_como_admin_e_promovida_e_visualiza_empresa_sem_atribuicao(monkeypatch):
    email = f"admin-bootstrap-{uuid4().hex}@example.test"
    monkeypatch.setenv("OMEGA_ADMIN_EMAIL", email)
    monkeypatch.setenv("OMEGA_ADMIN_PASSWORD", "Senha-Temporaria-123")
    with conectar_banco() as conn:
        cursor = conn.execute(
            """INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo)
               VALUES (?, ?, ?, 'USUARIO', 0)""",
            ("Conta antiga", email, "hash-preservado"),
        )
        user_id = int(cursor.lastrowid)
        conn.commit()

    ensure_admin_user()
    with conectar_banco() as conn:
        user = dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone())

    assert user["perfil"] == "ADMIN"
    assert user["ativo"] == 1
    assert user["senha_hash"] == "hash-preservado"

    empresa_id = _criar_empresa("LUCRO REAL")
    competencia = date.today().year * 100 + date.today().month
    painel = repository.listar_painel_lancamentos_conferencias(
        competencia, None, "TODOS", None, False, 1, 500, user,
    )
    assert any(empresa["id"] == empresa_id for empresa in painel["empresas"])


def test_nao_aplicavel_pode_ser_reativado_e_legados_sem_justificativa_sao_corrigidos():
    admin = _admin()
    empresa_id = _criar_empresa("SIMPLES NACIONAL")
    competencia = date.today().year * 100 + date.today().month
    from app.modules.contabil.schemas import MovimentacaoCreate

    created = service.criar_movimentacao_interna(
        empresa_id,
        MovimentacaoCreate(nome="Movimento reversível", competencia_inicio=competencia),
        admin,
    )
    service.atualizar_movimentacao_competencia(
        created["id"], competencia,
        {"aplicavel": False, "justificativa": "Não houve movimento no mês."},
        admin,
    )
    detalhe = repository.obter_painel_empresa_lancamentos(empresa_id, competencia, admin)
    item = next(x for x in detalhe["movimentacoes"] if x["movimentacao_id"] == created["id"])
    assert item["aplicavel"] is False
    assert detalhe["resumo"]["total"] == 0

    service.atualizar_movimentacao_competencia(
        created["id"], competencia, {"aplicavel": True}, admin,
    )
    detalhe = repository.obter_painel_empresa_lancamentos(empresa_id, competencia, admin)
    item = next(x for x in detalhe["movimentacoes"] if x["movimentacao_id"] == created["id"])
    assert item["aplicavel"] is True
    assert item["justificativa_nao_aplicavel"] is None
    assert detalhe["resumo"]["total"] == 1
    assert detalhe["resumo"]["pendentes"] == 1

    # Simula registro legado com aplicavel=0 sem justificativa: a leitura deve
    # normalizar para aplicável, mantendo o painel e o detalhe coerentes.
    with conectar_banco() as conn:
        conn.execute(
            """UPDATE contabil_movimentacoes_competencias
                  SET aplicavel=0, justificativa_nao_aplicavel=NULL
                WHERE movimentacao_id=? AND competencia=?""",
            (created["id"], competencia),
        )
        conn.commit()
    detalhe = repository.obter_painel_empresa_lancamentos(empresa_id, competencia, admin)
    item = next(x for x in detalhe["movimentacoes"] if x["movimentacao_id"] == created["id"])
    assert item["aplicavel"] is True
    assert detalhe["resumo"]["total"] == 1
