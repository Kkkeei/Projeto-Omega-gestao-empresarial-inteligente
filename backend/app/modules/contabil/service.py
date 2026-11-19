from datetime import date, datetime
import hashlib
import mimetypes
import os
import secrets
from pathlib import Path
from fastapi import UploadFile

from . import repository
from .models import competencia_anterior
from .storage import garantir_diretorio_obrigacao, nome_seguro, STORAGE_ROOT


def validar_competencia(competencia: int) -> None:
    ano, mes = divmod(competencia, 100)
    if ano < 1900 or ano > 2999 or mes not in range(1, 13):
        raise ValueError("A competência deve estar no formato YYYYMM.")


def obter_status_modulo() -> dict[str, str | int]:
    """Retorna informações de disponibilidade sem criar tabelas implicitamente."""
    return {
        "modulo": "contabil",
        "status": "disponivel",
        "competencia_atual": competencia_anterior(),
    }


def exigir_empresa(empresa_id: int) -> dict:
    empresa = repository.obter_empresa(empresa_id)
    if empresa is None:
        raise LookupError("Empresa não encontrada.")
    return empresa


def validar_acesso_empresa(empresa_id: int, user: dict) -> None:
    """Impede acesso a dados contábeis fora da carteira do usuário."""
    empresa = repository.obter_empresa(empresa_id)
    if not empresa or not empresa.get("ativo"):
        raise LookupError("Empresa não encontrada ou inativa.")
    if user.get("perfil") == "ADMIN":
        return
    conn = repository.conectar_banco()
    try:
        atribuicao = conn.execute(
            """SELECT usuario_id FROM contabil_atribuicoes
                WHERE empresa_id=? AND encerrado_em IS NULL""",
            (empresa_id,),
        ).fetchone()
        # Sem responsável, a empresa fica disponível na carteira compartilhada.
        if atribuicao and atribuicao["usuario_id"] != user.get("id"):
            raise PermissionError("A empresa está atribuída a outro responsável.")
    finally:
        conn.close()


def _atualizar_recebimento_movimentacao_interna(
    movimentacao_id: int, competencia: int, recebido: bool, user: dict,
) -> dict:
    """Atualiza somente o recebimento de uma movimentação interna.

    Esse fluxo é intencionalmente separado das validações de lançamento e
    conferência: marcar um item como recebido não deve depender de documento,
    arquivo ou obrigação contábil cadastrada.
    """
    conn = repository.conectar_banco()
    try:
        repository._garantir_coluna_recebido(conn)
        conn.execute("BEGIN IMMEDIATE")

        movimento = conn.execute(
            "SELECT * FROM contabil_movimentacoes WHERE id=?",
            (movimentacao_id,),
        ).fetchone()
        if not movimento:
            raise LookupError("Movimentação não encontrada.")
        if movimento["origem"] != "LANCAMENTOS_CONFERENCIAS":
            raise ValueError("O recebimento manual está disponível somente para movimentações internas.")

        if user.get("perfil") != "ADMIN":
            atribuicao = conn.execute(
                """SELECT usuario_id FROM contabil_atribuicoes
                    WHERE empresa_id=? AND encerrado_em IS NULL""",
                (movimento["empresa_id"],),
            ).fetchone()
            if atribuicao and atribuicao["usuario_id"] != user.get("id"):
                raise PermissionError("A empresa está atribuída a outro responsável.")

        dentro_periodo = (
            movimento["competencia_inicio"] is not None
            and movimento["competencia_inicio"] <= competencia
            and (movimento["competencia_fim"] is None or movimento["competencia_fim"] >= competencia)
        )
        if not dentro_periodo:
            raise LookupError("A movimentação não existe para esta competência.")

        atual = conn.execute(
            """SELECT * FROM contabil_movimentacoes_competencias
                WHERE movimentacao_id=? AND competencia=?""",
            (movimentacao_id, competencia),
        ).fetchone()
        if not atual and not movimento["ativa"]:
            raise LookupError("A movimentação não está ativa nesta competência.")

        if not atual:
            conn.execute(
                """INSERT OR IGNORE INTO contabil_movimentacoes_competencias
                    (movimentacao_id, empresa_id, competencia, aplicavel)
                    VALUES (?, ?, ?, 1)""",
                (movimentacao_id, movimento["empresa_id"], competencia),
            )
            atual = conn.execute(
                """SELECT * FROM contabil_movimentacoes_competencias
                    WHERE movimentacao_id=? AND competencia=?""",
                (movimentacao_id, competencia),
            ).fetchone()
        if not atual:
            raise RuntimeError("Não foi possível preparar o recebimento desta competência.")
        if not bool(atual["aplicavel"]):
            raise ValueError("Reative a movimentação nesta competência antes de alterar o recebimento.")

        anteriores = dict(atual)
        novo_recebido = int(bool(recebido))
        if not novo_recebido and (bool(atual["lancado"]) or bool(atual["conferido"])):
            raise ValueError("Desfaça o lançamento e a conferência antes de marcar como não recebido.")

        agora = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """UPDATE contabil_movimentacoes_competencias
                  SET recebido=?, atualizado_em=?
                WHERE id=?""",
            (novo_recebido, agora, atual["id"]),
        )
        novos = {**anteriores, "recebido": novo_recebido, "atualizado_em": agora,
                 "competencia": competencia, "movimentacao_id": movimentacao_id}
        repository.registrar_historico(
            conn, movimento["empresa_id"], user.get("id"),
            "MOVIMENTACAO_COMPETENCIA", atual["id"], "ATUALIZAR",
            novos, {**anteriores, "competencia": competencia, "movimentacao_id": movimentacao_id},
            "Atualização do recebimento da movimentação interna.",
        )
        conn.commit()
        resultado = dict(conn.execute(
            "SELECT * FROM contabil_movimentacoes_competencias WHERE id=?",
            (atual["id"],),
        ).fetchone())
        resultado["competencia"] = competencia
        resultado["movimentacao_id"] = movimentacao_id
        return resultado
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def atualizar_movimentacao_competencia(
    movimentacao_id: int,
    competencia: int,
    alteracoes: dict,
    user: dict,
) -> dict:
    validar_competencia(competencia)
    if "recebido" in alteracoes and set(alteracoes).issubset({"recebido"}):
        if alteracoes["recebido"] is None:
            raise ValueError("Informe se a movimentação foi recebida.")
        return _atualizar_recebimento_movimentacao_interna(
            movimentacao_id, competencia, bool(alteracoes["recebido"]), user,
        )
    if not alteracoes:
        raise ValueError("Informe ao menos uma alteração.")
    if "justificativa" in alteracoes:
        justificativa = alteracoes["justificativa"]
        alteracoes["justificativa"] = justificativa.strip() if justificativa else None
    if alteracoes.get("aplicavel") is False and not alteracoes.get("justificativa"):
        raise ValueError("Informe uma justificativa para marcar como não aplicável.")

    conn = repository.conectar_banco()
    try:
        colunas_mc = {row["name"] for row in conn.execute("PRAGMA table_info(contabil_movimentacoes_competencias)").fetchall()}
        if "recebido" not in colunas_mc:
            conn.execute("ALTER TABLE contabil_movimentacoes_competencias ADD COLUMN recebido INTEGER NOT NULL DEFAULT 0")
        conn.execute("BEGIN")
        movimento = conn.execute(
            """SELECT m.*, d.competencia_inicio doc_competencia_inicio,
                      d.competencia_fim doc_competencia_fim
                 FROM contabil_movimentacoes m
                 LEFT JOIN contabil_documentos d ON d.id=m.documento_origem_id
                WHERE m.id=?""",
            (movimentacao_id,),
        ).fetchone()
        if not movimento:
            raise LookupError("Movimentação não encontrada.")

        if user["perfil"] != "ADMIN":
            atribuicao = conn.execute(
                """SELECT usuario_id FROM contabil_atribuicoes
                    WHERE empresa_id=? AND encerrado_em IS NULL""",
                (movimento["empresa_id"],),
            ).fetchone()
            if atribuicao and atribuicao["usuario_id"] != user["id"]:
                raise PermissionError("A empresa está atribuída a outro responsável.")

        dentro_periodo = (
            movimento["origem"] == "DOCUMENTACAO"
            and movimento["doc_competencia_inicio"] <= competencia
            and (
                movimento["doc_competencia_fim"] is None
                or movimento["doc_competencia_fim"] >= competencia
            )
        ) or (
            movimento["origem"] == "LANCAMENTOS_CONFERENCIAS"
            and movimento["competencia_inicio"] <= competencia
            and (
                movimento["ativa"]
                or conn.execute(
                    """SELECT 1 FROM contabil_movimentacoes_competencias
                        WHERE movimentacao_id=? AND competencia=?""",
                    (movimentacao_id, competencia),
                ).fetchone()
            )
            and (
                movimento["competencia_fim"] is None
                or movimento["competencia_fim"] >= competencia
            )
        )
        if not dentro_periodo:
            raise LookupError("A movimentação não existe para esta competência.")

        if movimento["origem"] == "DOCUMENTACAO":
            conn.execute(
                """INSERT OR IGNORE INTO contabil_obrigacoes
                    (documento_id, empresa_id, competencia)
                    VALUES (?, ?, ?)""",
                (movimento["documento_origem_id"], movimento["empresa_id"], competencia),
            )
        conn.execute(
            """INSERT OR IGNORE INTO contabil_movimentacoes_competencias
                (movimentacao_id, empresa_id, competencia, aplicavel)
                VALUES (?, ?, ?, 1)""",
            (movimentacao_id, movimento["empresa_id"], competencia),
        )
        atual = conn.execute(
            """SELECT * FROM contabil_movimentacoes_competencias
                WHERE movimentacao_id=? AND competencia=?""",
            (movimentacao_id, competencia),
        ).fetchone()
        anteriores = dict(atual)
        novos = dict(anteriores)
        for campo in ("data_limite", "lancado", "conferido", "aplicavel", "recebido"):
            if campo in alteracoes:
                valor = alteracoes[campo]
                novos[campo] = valor.isoformat() if campo == "data_limite" and valor else valor

        if "lancado" in alteracoes and not novos["lancado"] and novos["conferido"]:
            novos["conferido"] = 0
            novos["conferido_por"] = None
            novos["conferido_em"] = None
        if novos["conferido"] and not novos["lancado"]:
            raise ValueError("A movimentação precisa estar lançada antes de ser conferida.")
        if not bool(novos["aplicavel"]):
            if novos["lancado"] or novos["conferido"]:
                raise ValueError("Desmarque lançamento e conferência antes de tornar a movimentação não aplicável.")
            novos["justificativa_nao_aplicavel"] = alteracoes["justificativa"]
        elif novos["aplicavel"]:
            novos["justificativa_nao_aplicavel"] = None

        documento_disponivel = True
        if movimento["origem"] == "DOCUMENTACAO":
            documento_disponivel = conn.execute(
                """SELECT EXISTS(
                       SELECT 1 FROM contabil_obrigacoes o
                       JOIN contabil_arquivos a
                         ON a.obrigacao_id=o.id AND a.excluido_em IS NULL
                      WHERE o.documento_id=? AND o.competencia=?
                        AND o.cancelada_em IS NULL
                   ) disponivel""",
                (movimento["documento_origem_id"], competencia),
            ).fetchone()["disponivel"]
        recebido_ok = bool(novos.get("recebido", anteriores.get("recebido", 0)))
        if movimento["origem"] == "LANCAMENTOS_CONFERENCIAS" and not recebido_ok and (
            ("lancado" in alteracoes and alteracoes["lancado"])
            or ("conferido" in alteracoes and alteracoes["conferido"])
        ):
            raise ValueError("Marque a movimentação como recebida antes de lançar ou conferir.")
        if movimento["origem"] == "DOCUMENTACAO" and not documento_disponivel and (
            ("lancado" in alteracoes and alteracoes["lancado"])
            or ("conferido" in alteracoes and alteracoes["conferido"])
        ):
            raise ValueError("Receba o documento antes de lançar ou conferir a movimentação.")

        agora = datetime.now().isoformat(timespec="seconds")
        if "lancado" in alteracoes:
            if bool(novos["lancado"]) != bool(anteriores["lancado"]):
                novos["lancado_por"] = user["id"] if novos["lancado"] else None
                novos["lancado_em"] = agora if novos["lancado"] else None
        if "conferido" in alteracoes:
            if bool(novos["conferido"]) != bool(anteriores["conferido"]):
                novos["conferido_por"] = user["id"] if novos["conferido"] else None
                novos["conferido_em"] = agora if novos["conferido"] else None
        novos["aplicavel"] = int(bool(novos["aplicavel"]))
        novos["lancado"] = int(bool(novos["lancado"]))
        novos["conferido"] = int(bool(novos["conferido"]))
        novos["recebido"] = int(bool(novos.get("recebido", 0)))
        novos["atualizado_em"] = agora

        conn.execute(
            """UPDATE contabil_movimentacoes_competencias
                  SET data_limite=?, aplicavel=?, justificativa_nao_aplicavel=?,
                      lancado=?, conferido=?, recebido=?, lancado_por=?, lancado_em=?,
                      conferido_por=?, conferido_em=?, atualizado_em=?
                WHERE id=?""",
            (
                novos["data_limite"], int(bool(novos["aplicavel"])),
                novos["justificativa_nao_aplicavel"], int(bool(novos["lancado"])),
                int(bool(novos["conferido"])), int(bool(novos["recebido"])), novos["lancado_por"], novos["lancado_em"],
                novos["conferido_por"], novos["conferido_em"], agora, atual["id"],
            ),
        )
        novos["competencia"] = competencia
        novos["movimentacao_id"] = movimentacao_id
        repository.registrar_historico(
            conn, movimento["empresa_id"], user["id"],
            "MOVIMENTACAO_COMPETENCIA", atual["id"], "ATUALIZAR",
            novos, {**anteriores, "competencia": competencia, "movimentacao_id": movimentacao_id},
            alteracoes.get("justificativa"),
        )
        conn.commit()
        result = dict(conn.execute(
            "SELECT * FROM contabil_movimentacoes_competencias WHERE id=?",
            (atual["id"],),
        ).fetchone())
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx"}
MAX_UPLOAD_BYTES = int(os.getenv("OMEGA_CONTABIL_MAX_MB", "25")) * 1024 * 1024


def _require_competencia(value: int) -> None:
    validar_competencia(value)


def criar_categoria(empresa_id: int, nome: str, descricao: str | None, user_id: int):
    conn = repository.conectar_banco()
    try:
        if not repository.empresa_existe(empresa_id): raise LookupError("Empresa não encontrada.")
        nome = nome.strip()
        if not nome: raise ValueError("O nome da categoria é obrigatório.")
        repository.garantir_escopos_categorias(conn)
        ordem = conn.execute("SELECT COALESCE(MAX(ordem),0)+1 n FROM contabil_categorias WHERE empresa_id=? AND escopo='DOCUMENTACAO'", (empresa_id,)).fetchone()["n"]
        cur = conn.execute("INSERT INTO contabil_categorias (empresa_id,nome,descricao,ordem,criado_por,escopo) VALUES (?,?,?,?,?,'DOCUMENTACAO')", (empresa_id,nome,descricao,ordem,user_id))
        repository.registrar_historico(conn, empresa_id, user_id, "CATEGORIA", cur.lastrowid, "CRIAR", {"nome": nome})
        conn.commit()
        return dict(conn.execute("SELECT *, CAST(ativo AS BOOLEAN) ativo FROM contabil_categorias WHERE id=?", (cur.lastrowid,)).fetchone())
    except Exception: conn.rollback(); raise
    finally: conn.close()


def atualizar_categoria(categoria_id: int, nome: str, descricao: str | None, user_id: int):
    conn = repository.conectar_banco()
    try:
        repository.garantir_escopos_categorias(conn)
        row = conn.execute("SELECT * FROM contabil_categorias WHERE id=? AND ativo=1 AND escopo='DOCUMENTACAO'", (categoria_id,)).fetchone()
        if not row: raise LookupError("Categoria não encontrada na Documentação.")
        anterior = dict(row)
        conn.execute("UPDATE contabil_categorias SET nome=?, descricao=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (nome.strip(), descricao, categoria_id))
        repository.registrar_historico(conn, row["empresa_id"], user_id, "CATEGORIA", categoria_id, "EDITAR", {"nome": nome, "descricao": descricao}, anterior)
        conn.commit()
        return dict(conn.execute("SELECT * FROM contabil_categorias WHERE id=?", (categoria_id,)).fetchone())
    finally: conn.close()


def arquivar_categoria(categoria_id: int, user_id: int):
    conn = repository.conectar_banco()
    try:
        repository.garantir_escopos_categorias(conn)
        row = conn.execute("SELECT * FROM contabil_categorias WHERE id=? AND ativo=1 AND escopo='DOCUMENTACAO'", (categoria_id,)).fetchone()
        if not row: raise LookupError("Categoria não encontrada na Documentação.")
        if conn.execute("SELECT 1 FROM contabil_documentos WHERE categoria_id=? LIMIT 1", (categoria_id,)).fetchone():
            raise ValueError("Não é possível arquivar uma categoria com documentos vinculados.")
        conn.execute("UPDATE contabil_categorias SET ativo=0, arquivado_em=CURRENT_TIMESTAMP WHERE id=?", (categoria_id,))
        repository.registrar_historico(conn, row["empresa_id"], user_id, "CATEGORIA", categoria_id, "ARQUIVAR")
        conn.commit()
        return {"ok": True}
    finally: conn.close()


def criar_documento(empresa_id: int, data, user_id: int):
    _require_competencia(data.competencia_inicio)
    exigir_empresa(empresa_id)
    conn = repository.conectar_banco()
    try:
        repository.garantir_escopos_categorias(conn)
        cat = conn.execute("SELECT 1 FROM contabil_categorias WHERE id=? AND empresa_id=? AND ativo=1 AND escopo='DOCUMENTACAO'", (data.categoria_id, empresa_id)).fetchone()
        if not cat: raise LookupError("Categoria não encontrada.")
        cur = conn.execute("INSERT INTO contabil_documentos (empresa_id,categoria_id,nome,observacao,competencia_inicio,criado_por,atualizado_por) VALUES (?,?,?,?,?,?,?)",
                           (empresa_id,data.categoria_id,data.nome.strip(),data.observacao,data.competencia_inicio,user_id,user_id))
        conn.execute("INSERT INTO contabil_obrigacoes (documento_id,empresa_id,competencia,criada_por) VALUES (?,?,?,?)", (cur.lastrowid,empresa_id,data.competencia_inicio,user_id))
        repository.registrar_historico(conn, empresa_id, user_id, "DOCUMENTO", cur.lastrowid, "CRIAR", {"nome": data.nome})
        conn.commit()
        painel = repository.documentacao(empresa_id, data.competencia_inicio, data.competencia_inicio // 100, user_id)
        return next(item for item in painel["documentos"] if item["id"] == cur.lastrowid)
    except Exception: conn.rollback(); raise
    finally: conn.close()


def atualizar_documento(documento_id: int, data, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT * FROM contabil_documentos WHERE id=? AND ativo=1", (documento_id,)).fetchone()
        if not row: raise LookupError("Documento não encontrado.")
        repository.garantir_escopos_categorias(conn)
        if not conn.execute("SELECT 1 FROM contabil_categorias WHERE id=? AND empresa_id=? AND ativo=1 AND escopo='DOCUMENTACAO'", (data.categoria_id,row["empresa_id"])).fetchone():
            raise LookupError("Categoria não encontrada.")
        nome = data.nome.strip()
        if not nome:
            raise ValueError("O nome da documentação é obrigatório.")
        conn.execute("UPDATE contabil_documentos SET nome=?, categoria_id=?, observacao=?, atualizado_por=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                     (nome,data.categoria_id,data.observacao,user_id,documento_id))
        # Mantém a movimentação derivada alinhada ao documento de origem.
        conn.execute(
            "UPDATE contabil_movimentacoes SET nome=?, categoria_id=? WHERE documento_origem_id=?",
            (nome, data.categoria_id, documento_id),
        )
        repository.registrar_historico(conn,row["empresa_id"],user_id,"DOCUMENTO",documento_id,"EDITAR",
            {"nome":nome,"categoria_id":data.categoria_id,"observacao":data.observacao},dict(row))
        conn.commit()
        painel = repository.documentacao(row["empresa_id"], row["competencia_inicio"], row["competencia_inicio"] // 100, user_id)
        return next(item for item in painel["documentos"] if item["id"] == documento_id)
    finally: conn.close()


def inativar_documento(documento_id: int, data, user_id: int):
    _require_competencia(data.competencia_fim)
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT * FROM contabil_documentos WHERE id=? AND ativo=1", (documento_id,)).fetchone()
        if not row: raise LookupError("Documento não encontrado.")
        if data.competencia_fim < row["competencia_inicio"]: raise ValueError("A competência final é inválida.")
        conn.execute("UPDATE contabil_documentos SET competencia_fim=?, ativo=0, inativado_em=CURRENT_TIMESTAMP, motivo_inativacao=?, observacao_inativacao=?, atualizado_por=? WHERE id=?",
                     (data.competencia_fim,data.motivo,data.observacao,user_id,documento_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"DOCUMENTO",documento_id,"INATIVAR",{"competencia_fim":data.competencia_fim,"motivo":data.motivo})
        conn.commit()
        return {"id": documento_id, "ativo": False, "competencia_fim": data.competencia_fim}
    finally: conn.close()


def reativar_documento(documento_id: int, user_id: int):
    """Reativa um cadastro de documentação, preservando obrigações e arquivos históricos."""
    conn = repository.conectar_banco()
    try:
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT * FROM contabil_documentos WHERE id=? AND ativo=0",
            (documento_id,),
        ).fetchone()
        if not row:
            raise LookupError("Documento inativo não encontrado.")
        anterior = dict(row)
        conn.execute(
            """UPDATE contabil_documentos
                  SET ativo=1, competencia_inicio=?, competencia_fim=NULL, inativado_em=NULL,
                      motivo_inativacao=NULL, observacao_inativacao=NULL,
                      atualizado_por=?, atualizado_em=CURRENT_TIMESTAMP
                WHERE id=?""",
            (competencia_anterior(), user_id, documento_id),
        )
        repository.registrar_historico(
            conn, row["empresa_id"], user_id, "DOCUMENTO", documento_id,
            "REATIVAR", {"competencia_inicio_nova": competencia_anterior()},
            anterior, "Reativação do cadastro de documentação",
        )
        conn.commit()
        return {"id": documento_id, "ativo": True, "competencia_inicio": competencia_anterior(), "competencia_fim": None}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reativar_movimentacao_interna(movimentacao_id: int, user: dict) -> dict:
    """Reativa uma movimentação interna sem apagar o histórico anterior."""
    conn = repository.conectar_banco()
    try:
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT * FROM contabil_movimentacoes WHERE id=? AND origem='LANCAMENTOS_CONFERENCIAS' AND ativa=0",
            (movimentacao_id,),
        ).fetchone()
        if not row:
            raise LookupError("Movimentação interna inativa não encontrada.")
        validar_acesso_empresa(row["empresa_id"], user)
        anterior = dict(row)
        inicio = competencia_anterior()
        conn.execute(
            """UPDATE contabil_movimentacoes
                  SET ativa=1, competencia_inicio=?, competencia_fim=NULL, inativada_em=NULL
                WHERE id=?""",
            (inicio, movimentacao_id),
        )
        repository.registrar_historico(
            conn, row["empresa_id"], user["id"], "MOVIMENTACAO", movimentacao_id,
            "REATIVAR", {"competencia_inicio_nova": inicio}, anterior,
            "Reativação do cadastro de movimentação",
        )
        conn.commit()
        return {"id": movimentacao_id, "ativa": True, "competencia_inicio": inicio, "competencia_fim": None}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def marcar_documento_nao_recebido(obrigacao_id: int, confirmado: bool, user: dict) -> dict:
    """Registra a confirmação somente na obrigação/mês selecionado."""
    conn = repository.conectar_banco()
    try:
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT * FROM contabil_obrigacoes WHERE id=? AND cancelada_em IS NULL",
            (obrigacao_id,),
        ).fetchone()
        if not row:
            raise LookupError("Obrigação não encontrada.")
        if user.get("perfil") != "ADMIN":
            atribuicao = conn.execute(
                "SELECT usuario_id FROM contabil_atribuicoes WHERE empresa_id=? AND encerrado_em IS NULL",
                (row["empresa_id"],),
            ).fetchone()
            if atribuicao and atribuicao["usuario_id"] != user.get("id"):
                raise PermissionError("A empresa está atribuída a outro responsável.")
        possui_arquivo = conn.execute(
            "SELECT EXISTS(SELECT 1 FROM contabil_arquivos WHERE obrigacao_id=? AND excluido_em IS NULL)",
            (obrigacao_id,),
        ).fetchone()[0]
        if confirmado and possui_arquivo:
            raise ValueError("Esta obrigação possui arquivo recebido. Remova ou arquive o arquivo antes de confirmar o não recebimento.")
        anterior = dict(row)
        agora = datetime.now().isoformat(timespec="seconds") if confirmado else None
        conn.execute(
            "UPDATE contabil_obrigacoes SET nao_recebido_confirmado=?, nao_recebido_por=?, nao_recebido_em=? WHERE id=?",
            (int(confirmado), user.get("id") if confirmado else None, agora, obrigacao_id),
        )
        novo = dict(conn.execute("SELECT * FROM contabil_obrigacoes WHERE id=?", (obrigacao_id,)).fetchone())
        repository.registrar_historico(
            conn, row["empresa_id"], user.get("id"), "OBRIGACAO", obrigacao_id,
            "CONFIRMAR_NAO_RECEBIDO" if confirmado else "REABRIR_PENDENCIA", novo, anterior,
        )
        conn.commit()
        return {"id": obrigacao_id, "nao_recebido_confirmado": bool(confirmado)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_arquivos(obrigacao_id: int):
    conn = repository.conectar_banco()
    try: return {"arquivos": [dict(r) for r in conn.execute("""SELECT a.*, u.nome enviado_por_nome FROM contabil_arquivos a LEFT JOIN usuarios u ON u.id=a.enviado_por WHERE a.obrigacao_id=? AND a.excluido_em IS NULL ORDER BY a.enviado_em DESC""",(obrigacao_id,)).fetchall()]}
    finally: conn.close()


def upload_arquivos(obrigacao_id: int, uploads: list[UploadFile], user_id: int):
    conn = repository.conectar_banco()
    written: list[Path] = []
    try:
        obligation = conn.execute("SELECT * FROM contabil_obrigacoes WHERE id=? AND cancelada_em IS NULL", (obrigacao_id,)).fetchone()
        if not obligation: raise LookupError("Obrigação não encontrada.")
        for upload in uploads:
            ext = Path(upload.filename or "").suffix.lower()
            if ext not in ALLOWED_EXTENSIONS: raise ValueError("Tipo de arquivo não permitido.")
            data = upload.file.read()
            if len(data) > MAX_UPLOAD_BYTES: raise ValueError("O arquivo excede o limite permitido.")
            if not data: raise ValueError("O arquivo está vazio.")
            if not _conteudo_compativel(ext, data):
                raise ValueError("O conteúdo do arquivo não corresponde ao tipo informado.")
            directory = garantir_diretorio_obrigacao(obligation["empresa_id"], obligation["competencia"], obrigacao_id)
            physical = directory / f"{secrets.token_hex(16)}{ext}"
            physical.write_bytes(data); written.append(physical)
            cur = conn.execute("""INSERT INTO contabil_arquivos
              (obrigacao_id,nome_original,nome_armazenado,caminho_storage,extensao,mime_type,tamanho,hash_sha256,enviado_por)
              VALUES (?,?,?,?,?,?,?,?,?)""",
              (obrigacao_id,nome_seguro(upload.filename or "arquivo"),physical.name,str(physical.relative_to(STORAGE_ROOT)),ext,upload.content_type or mimetypes.guess_type(upload.filename or "")[0],len(data),hashlib.sha256(data).hexdigest(),user_id))
            repository.registrar_historico(conn,obligation["empresa_id"],user_id,"ARQUIVO",cur.lastrowid,"UPLOAD",{"nome": upload.filename})
        conn.commit()
        return listar_arquivos(obrigacao_id)
    except Exception:
        conn.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise
    finally: conn.close()


def renomear_arquivo(arquivo_id: int, nome: str, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT a.*,o.empresa_id FROM contabil_arquivos a JOIN contabil_obrigacoes o ON o.id=a.obrigacao_id WHERE a.id=? AND a.excluido_em IS NULL",(arquivo_id,)).fetchone()
        if not row: raise LookupError("Arquivo não encontrado.")
        safe = nome_seguro(nome)
        conn.execute("UPDATE contabil_arquivos SET nome_original=? WHERE id=?",(safe,arquivo_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"ARQUIVO",arquivo_id,"RENOMEAR",{"nome":safe},{"nome":row["nome_original"]})
        conn.commit()
        return dict(conn.execute("SELECT * FROM contabil_arquivos WHERE id=?",(arquivo_id,)).fetchone())
    finally: conn.close()


def excluir_arquivo(arquivo_id: int, motivo: str | None, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT a.*,o.empresa_id FROM contabil_arquivos a JOIN contabil_obrigacoes o ON o.id=a.obrigacao_id WHERE a.id=? AND a.excluido_em IS NULL",(arquivo_id,)).fetchone()
        if not row: raise LookupError("Arquivo não encontrado.")
        conn.execute("UPDATE contabil_arquivos SET excluido_em=CURRENT_TIMESTAMP, excluido_por=?, motivo_exclusao=? WHERE id=?",(user_id,motivo,arquivo_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"ARQUIVO",arquivo_id,"EXCLUIR",{"motivo":motivo})
        conn.commit(); return {"ok": True}
    finally: conn.close()


def obter_arquivo(arquivo_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT a.*,o.empresa_id,o.competencia FROM contabil_arquivos a JOIN contabil_obrigacoes o ON o.id=a.obrigacao_id WHERE a.id=? AND a.excluido_em IS NULL",(arquivo_id,)).fetchone()
        return dict(row) if row else None
    finally: conn.close()


def _conteudo_compativel(ext: str, data: bytes) -> bool:
    if ext == ".pdf":
        return data.startswith(b"%PDF-")
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".xlsx":
        return data.startswith(b"PK\x03\x04")
    return False


def criar_movimentacao_interna(empresa_id: int, data, user: dict) -> dict:
    validar_competencia(data.competencia_inicio)
    nome = data.nome.strip()
    if not nome:
        raise ValueError("Informe o nome da movimentação.")
    conn = repository.conectar_banco()
    try:
        conn.execute("BEGIN")
        empresa = conn.execute("SELECT id FROM empresas WHERE id=? AND ativo=1", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada ou inativa.")
        if user["perfil"] != "ADMIN":
            atribuicao = conn.execute(
                "SELECT usuario_id FROM contabil_atribuicoes WHERE empresa_id=? AND encerrado_em IS NULL",
                (empresa_id,),
            ).fetchone()
            if atribuicao and atribuicao["usuario_id"] != user["id"]:
                raise PermissionError("A empresa está atribuída a outro responsável.")
        repository.garantir_escopos_categorias(conn)
        if data.categoria_id is not None and not conn.execute(
            "SELECT 1 FROM contabil_categorias WHERE id=? AND empresa_id=? AND ativo=1 AND escopo IN ('DOCUMENTACAO','LANCAMENTOS')",
            (data.categoria_id, empresa_id),
        ).fetchone():
            raise LookupError("Categoria não encontrada para esta empresa.")
        cursor = conn.execute(
            """INSERT INTO contabil_movimentacoes
                (empresa_id,nome,categoria_id,origem,documento_origem_id,competencia_inicio,ativa,criada_por)
                VALUES (?,?,?,'LANCAMENTOS_CONFERENCIAS',NULL,?,1,?)""",
            (empresa_id, nome, data.categoria_id, data.competencia_inicio, user["id"]),
        )
        movimento_id = cursor.lastrowid
        conn.execute(
            """INSERT INTO contabil_movimentacoes_competencias
                (movimentacao_id,empresa_id,competencia,data_limite,aplicavel,justificativa_nao_aplicavel)
                VALUES (?,?,?,?,1,NULL)""",
            (movimento_id, empresa_id, data.competencia_inicio, data.data_limite.isoformat() if data.data_limite else None),
        )
        repository.registrar_historico(
            conn, empresa_id, user["id"], "MOVIMENTACAO", movimento_id, "CRIAR",
            {"nome": nome, "categoria_id": data.categoria_id, "competencia_inicio": data.competencia_inicio, "origem": "LANCAMENTOS_CONFERENCIAS"},
        )
        conn.commit()
        return {"id": movimento_id, "empresa_id": empresa_id, "nome": nome, "categoria_id": data.categoria_id,
                "competencia_inicio": data.competencia_inicio, "data_limite": data.data_limite.isoformat() if data.data_limite else None,
                "origem": "LANCAMENTOS_CONFERENCIAS"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def atualizar_movimentacao_interna(movimentacao_id: int, nome: str, categoria_id: int | None, user: dict) -> dict:
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da movimentação.")
    conn = repository.conectar_banco()
    try:
        conn.execute("BEGIN")
        row = conn.execute("SELECT * FROM contabil_movimentacoes WHERE id=?", (movimentacao_id,)).fetchone()
        if not row:
            raise LookupError("Movimentação não encontrada.")
        if row["origem"] != "LANCAMENTOS_CONFERENCIAS":
            raise ValueError("Somente movimentações internas podem ser editadas aqui.")
        validar_acesso_empresa(row["empresa_id"], user)
        if categoria_id is not None:
            repository.garantir_escopos_categorias(conn)
            categoria = conn.execute(
                "SELECT id FROM contabil_categorias WHERE id=? AND empresa_id=? AND ativo=1 AND escopo IN ('DOCUMENTACAO','LANCAMENTOS')",
                (categoria_id, row["empresa_id"]),
            ).fetchone()
            if not categoria:
                raise ValueError("Categoria não encontrada para esta empresa.")
        anterior = dict(row)
        conn.execute(
            "UPDATE contabil_movimentacoes SET nome=?, categoria_id=? WHERE id=?",
            (nome, categoria_id, movimentacao_id),
        )
        repository.registrar_historico(
            conn, row["empresa_id"], user["id"], "MOVIMENTACAO", movimentacao_id, "EDITAR",
            {"nome": nome, "categoria_id": categoria_id}, anterior,
        )
        conn.commit()
        return {"id": movimentacao_id, "empresa_id": row["empresa_id"], "nome": nome, "categoria_id": categoria_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inativar_movimentacao_interna(movimentacao_id: int, competencia_fim: int, motivo: str | None, user: dict) -> dict:
    validar_competencia(competencia_fim)
    motivo = (motivo or "").strip() or None
    conn = repository.conectar_banco()
    try:
        conn.execute("BEGIN")
        row = conn.execute("SELECT * FROM contabil_movimentacoes WHERE id=?", (movimentacao_id,)).fetchone()
        if not row:
            raise LookupError("Movimentação não encontrada.")
        if row["origem"] != "LANCAMENTOS_CONFERENCIAS":
            raise ValueError("Movimentações originadas da Documentação devem ser inativadas na própria Documentação.")
        if user["perfil"] != "ADMIN":
            atribuicao = conn.execute(
                "SELECT usuario_id FROM contabil_atribuicoes WHERE empresa_id=? AND encerrado_em IS NULL",
                (row["empresa_id"],),
            ).fetchone()
            if atribuicao and atribuicao["usuario_id"] != user["id"]:
                raise PermissionError("A empresa está atribuída a outro responsável.")
        if competencia_fim < row["competencia_inicio"]:
            raise ValueError("A competência final não pode ser anterior à competência inicial.")
        anterior = dict(row)
        conn.execute(
            "UPDATE contabil_movimentacoes SET ativa=0,competencia_fim=?,inativada_em=CURRENT_TIMESTAMP WHERE id=?",
            (competencia_fim, movimentacao_id),
        )
        repository.registrar_historico(
            conn, row["empresa_id"], user["id"], "MOVIMENTACAO", movimentacao_id, "INATIVAR",
            {"competencia_fim": competencia_fim}, anterior, motivo,
        )
        conn.commit()
        return {"id": movimentacao_id, "ativa": False, "competencia_fim": competencia_fim}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
