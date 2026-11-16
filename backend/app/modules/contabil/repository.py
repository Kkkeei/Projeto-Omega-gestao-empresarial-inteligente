from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.db.database import conectar_banco
from .models import CATEGORIAS_PADRAO, competencia_anterior


def _row(row) -> dict[str, Any] | None:
    return dict(row) if row else None


def _rows(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def registrar_historico(conn, empresa_id: int, usuario_id: int | None, entidade: str,
                        entidade_id: int | None, acao: str, novos: Any = None,
                        anteriores: Any = None, observacao: str | None = None) -> None:
    dump = lambda value: json.dumps(value, ensure_ascii=False, default=str) if value is not None else None
    conn.execute(
        """INSERT INTO contabil_historico
           (empresa_id, usuario_id, entidade, entidade_id, acao,
            dados_anteriores, dados_novos, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (empresa_id, usuario_id, entidade, entidade_id, acao, dump(anteriores), dump(novos), observacao),
    )
    conn.execute(
        "INSERT INTO auditorias (entidade, entidade_id, acao, dados_anteriores, dados_novos, origem) VALUES (?, ?, ?, ?, ?, ?)",
        (f"CONTABIL_{entidade}", entidade_id, acao, dump(anteriores), dump(novos), "CONTABIL"),
    )


def empresa_existe(empresa_id: int) -> bool:
    conn = conectar_banco()
    try:
        return conn.execute("SELECT 1 FROM empresas WHERE id=?", (empresa_id,)).fetchone() is not None
    finally:
        conn.close()


def obter_empresa(empresa_id: int) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        return _row(conn.execute(
            "SELECT id, razao_social, nome_fantasia, cnpj, regime_tributario, ativo FROM empresas WHERE id=?",
            (empresa_id,),
        ).fetchone())
    finally:
        conn.close()


def garantir_categorias(conn, empresa_id: int, usuario_id: int | None = None) -> None:
    for ordem, nome in enumerate(CATEGORIAS_PADRAO, 1):
        conn.execute(
            """INSERT INTO contabil_categorias (empresa_id, nome, ordem, padrao, criado_por)
               SELECT ?, ?, ?, 1, ? WHERE NOT EXISTS
               (SELECT 1 FROM contabil_categorias WHERE empresa_id=? AND nome=? COLLATE NOCASE AND ativo=1)""",
            (empresa_id, nome, ordem, usuario_id, empresa_id, nome),
        )


def listar_responsaveis() -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        return _rows(conn.execute(
            """SELECT u.id, u.nome, u.email, u.perfil, u.ativo,
                      COUNT(a.id) AS empresas_atribuidas
                 FROM usuarios u LEFT JOIN contabil_atribuicoes a
                   ON a.usuario_id=u.id AND a.encerrado_em IS NULL
                WHERE u.ativo=1 GROUP BY u.id ORDER BY UPPER(u.nome)""").fetchall())
    finally:
        conn.close()


def _empresa_select(where: str = "", params: list[Any] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        query = f"""SELECT e.id, e.razao_social, e.nome_fantasia, e.cnpj,
                           e.regime_tributario, e.ativo, a.usuario_id responsavel_id,
                           u.nome responsavel_nome
                      FROM empresas e
                 LEFT JOIN contabil_atribuicoes a ON a.empresa_id=e.id AND a.encerrado_em IS NULL
                 LEFT JOIN usuarios u ON u.id=a.usuario_id {where}
                  ORDER BY UPPER(e.razao_social)"""
        if limit:
            query += " LIMIT ?"
            params = (params or []) + [limit]
        return _rows(conn.execute(query, params or []).fetchall())
    finally:
        conn.close()


def listar_empresas(busca: str | None, regime: str | None, incluir_inativas: bool) -> list[dict[str, Any]]:
    filters, params = [], []
    if not incluir_inativas:
        filters.append("e.ativo=1")
    if busca:
        term = f"%{busca.strip()}%"
        filters.append("(e.razao_social LIKE ? OR COALESCE(e.nome_fantasia,'') LIKE ? OR e.cnpj LIKE ?)")
        params.extend([term, term, term])
    if regime:
        filters.append("UPPER(COALESCE(e.regime_tributario,''))=UPPER(?)")
        params.append(regime)
    return _empresa_select("WHERE " + " AND ".join(filters) if filters else "", params)


def listar_dashboard(competencia: int, busca: str | None, regime: str | None,
                     responsavel_id: int | None, sem_responsavel: bool,
                     pagina: int, por_pagina: int, user: dict | None = None) -> dict[str, Any]:
    empresas = listar_empresas(busca, regime, False)
    if user and user.get("perfil") != "ADMIN":
        # Empresas ainda sem responsável pertencem à carteira compartilhada.
        # Assim que uma empresa recebe atribuição ativa, fica restrita ao responsável.
        empresas = [
            empresa for empresa in empresas
            if empresa["responsavel_id"] in (None, user.get("id"))
        ]
    if responsavel_id is not None:
        empresas = [e for e in empresas if e["responsavel_id"] == responsavel_id]
    if sem_responsavel:
        empresas = [e for e in empresas if e["responsavel_id"] is None]
    conn = conectar_banco()
    try:
        for empresa in empresas:
            conn.execute(
                """INSERT OR IGNORE INTO contabil_obrigacoes (documento_id, empresa_id, competencia)
                   SELECT id, empresa_id, ? FROM contabil_documentos
                    WHERE empresa_id=? AND competencia_inicio<=?
                      AND (competencia_fim IS NULL OR competencia_fim>=?)""",
                (competencia, empresa["id"], competencia, competencia),
            )
            rows = conn.execute(
                """SELECT o.id, c.empresa_id,
                    (SELECT COUNT(*) FROM contabil_arquivos a WHERE a.obrigacao_id=o.id AND a.excluido_em IS NULL) qtd
                   FROM contabil_obrigacoes o JOIN contabil_documentos c ON c.id=o.documento_id
                  WHERE o.empresa_id=? AND o.competencia=? AND o.cancelada_em IS NULL""",
                (empresa["id"], competencia),
            ).fetchall()
            total = len(rows)
            received = sum(1 for r in rows if r["qtd"])
            empresa["documentos_total"] = total
            empresa["documentos_recebidos"] = received
            empresa["status_documentacao"] = "COMPLETA" if total and received == total else "PARCIAL" if received else "SEM_RECEBIMENTO"
        counts = {"total_empresas": len(empresas), "simples_nacional": 0, "lucro_presumido": 0,
                  "lucro_real": 0, "documentacao_completa": 0, "documentacao_parcial": 0, "sem_recebimento": 0}
        for e in empresas:
            regime_key = (e["regime_tributario"] or "").lower().replace(" ", "_")
            if "simples" in regime_key: counts["simples_nacional"] += 1
            elif "presumido" in regime_key: counts["lucro_presumido"] += 1
            elif "real" in regime_key: counts["lucro_real"] += 1
            counts[{"COMPLETA": "documentacao_completa", "PARCIAL": "documentacao_parcial",
                    "SEM_RECEBIMENTO": "sem_recebimento"}[e["status_documentacao"]]] += 1
        start = (pagina - 1) * por_pagina
        return {"competencia": competencia, "resumo": counts, "empresas": empresas[start:start + por_pagina],
                "total": len(empresas), "pagina": pagina, "por_pagina": por_pagina}
    finally:
        conn.close()


def listar_painel_lancamentos_conferencias(
    competencia: int,
    busca: str | None,
    regime: str | None,
    responsavel_id: int | None,
    sem_responsavel: bool,
    pagina: int,
    por_pagina: int,
    user: dict[str, Any],
) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        scope_where = "e.ativo=1"
        scope_params: list[Any] = []
        if user["perfil"] != "ADMIN":
            # Disponibiliza empresas sem responsável como carteira compartilhada.
            # Empresas atribuídas continuam visíveis apenas ao responsável.
            scope_where += " AND (a.usuario_id=? OR a.usuario_id IS NULL)"
            scope_params.append(user["id"])

        scope_query = f"""
            SELECT e.id, e.razao_social, e.nome_fantasia, e.cnpj,
                   e.regime_tributario, a.usuario_id responsavel_id,
                   u.nome responsavel_nome
              FROM empresas e
              LEFT JOIN contabil_atribuicoes a
                ON a.empresa_id=e.id AND a.encerrado_em IS NULL
              LEFT JOIN usuarios u ON u.id=a.usuario_id
             WHERE {scope_where}
             ORDER BY UPPER(e.razao_social)
        """
        all_visible = _rows(conn.execute(scope_query, scope_params).fetchall())

        counts = {
            "total_empresas": len(all_visible),
            "simples_nacional": 0,
            "lucro_presumido": 0,
            "lucro_real": 0,
        }
        for empresa in all_visible:
            regime_key = (empresa["regime_tributario"] or "").upper()
            if "SIMPLES" in regime_key:
                counts["simples_nacional"] += 1
            elif "PRESUMIDO" in regime_key:
                counts["lucro_presumido"] += 1
            elif "REAL" in regime_key:
                counts["lucro_real"] += 1

        filters = [scope_where]
        params = list(scope_params)
        if busca and busca.strip():
            term = f"%{busca.strip()}%"
            digits = "".join(char for char in busca if char.isdigit())
            if digits:
                filters.append(
                    "(e.razao_social LIKE ? OR COALESCE(e.nome_fantasia,'') LIKE ? "
                    "OR e.cnpj LIKE ? OR REPLACE(REPLACE(REPLACE(REPLACE(e.cnpj,'.',''),'/',''),'-',''),' ','') LIKE ?)"
                )
                params.extend([term, term, term, f"%{digits}%"])
            else:
                filters.append("(e.razao_social LIKE ? OR COALESCE(e.nome_fantasia,'') LIKE ?)")
                params.extend([term, term])
        if regime and regime.upper() != "TODOS":
            filters.append("UPPER(COALESCE(e.regime_tributario,''))=UPPER(?)")
            params.append(regime)
        if responsavel_id is not None:
            filters.append("a.usuario_id=?")
            params.append(responsavel_id)
        elif sem_responsavel:
            filters.append("a.usuario_id IS NULL")

        where = " AND ".join(filters)
        total = conn.execute(
            f"""SELECT COUNT(*) total
                  FROM empresas e
                  LEFT JOIN contabil_atribuicoes a
                    ON a.empresa_id=e.id AND a.encerrado_em IS NULL
                 WHERE {where}""",
            params,
        ).fetchone()["total"]
        start = (pagina - 1) * por_pagina
        empresas = _rows(conn.execute(
            f"""SELECT e.id, e.razao_social, e.nome_fantasia, e.cnpj,
                       e.regime_tributario, a.usuario_id responsavel_id,
                       u.nome responsavel_nome
                  FROM empresas e
                  LEFT JOIN contabil_atribuicoes a
                    ON a.empresa_id=e.id AND a.encerrado_em IS NULL
                  LEFT JOIN usuarios u ON u.id=a.usuario_id
                 WHERE {where}
                 ORDER BY UPPER(e.razao_social)
                 LIMIT ? OFFSET ?""",
            params + [por_pagina, start],
        ).fetchall())

        empresa_ids = [empresa["id"] for empresa in empresas]
        if empresa_ids:
            # Compatibilidade com registros antigos: não aplicável só é válido
            # quando existe justificativa explícita. Sem justificativa, volta a
            # ser aplicável para que painel e detalhe usem a mesma regra.
            placeholders = ",".join("?" for _ in empresa_ids)
            conn.execute(
                f"""UPDATE contabil_movimentacoes_competencias
                       SET aplicavel=1, atualizado_em=CURRENT_TIMESTAMP
                     WHERE empresa_id IN ({placeholders}) AND aplicavel=0
                       AND (justificativa_nao_aplicavel IS NULL OR TRIM(justificativa_nao_aplicavel)='')
                       AND lancado=0 AND conferido=0""",
                empresa_ids,
            )
            placeholders = ",".join("?" for _ in empresa_ids)
            period_params = [competencia, competencia]
            conn.execute(
                f"""INSERT OR IGNORE INTO contabil_movimentacoes
                    (empresa_id, nome, categoria_id, origem, documento_origem_id)
                    SELECT d.empresa_id, d.nome, d.categoria_id, 'DOCUMENTACAO', d.id
                      FROM contabil_documentos d
                     WHERE d.empresa_id IN ({placeholders})
                       AND d.competencia_inicio<=?
                       AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)""",
                empresa_ids + period_params,
            )
            conn.execute(
                f"""INSERT OR IGNORE INTO contabil_obrigacoes
                    (documento_id, empresa_id, competencia)
                    SELECT d.id, d.empresa_id, ?
                      FROM contabil_documentos d
                     WHERE d.empresa_id IN ({placeholders})
                       AND d.competencia_inicio<=?
                       AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)""",
                [competencia] + empresa_ids + period_params,
            )
            conn.execute(
                f"""INSERT OR IGNORE INTO contabil_movimentacoes_competencias
                    (movimentacao_id, empresa_id, competencia, aplicavel)
                    SELECT m.id, m.empresa_id, ?, 1
                      FROM contabil_movimentacoes m
                      JOIN contabil_documentos d ON d.id=m.documento_origem_id
                     WHERE m.empresa_id IN ({placeholders})
                       AND d.competencia_inicio<=?
                       AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)
                    UNION ALL
                    SELECT m.id, m.empresa_id, ?, 1
                      FROM contabil_movimentacoes m
                     WHERE m.empresa_id IN ({placeholders})
                       AND m.origem='LANCAMENTOS_CONFERENCIAS'
                       AND m.ativa=1 AND m.competencia_inicio<=?
                       AND (m.competencia_fim IS NULL OR m.competencia_fim>=?)""",
                [competencia] + empresa_ids + period_params
                + [competencia] + empresa_ids + [competencia, competencia],
            )
            conn.commit()
            rows = _rows(conn.execute(
                f"""SELECT mc.empresa_id, mc.id competencia_id, mc.data_limite,
                           mc.aplicavel, mc.lancado, mc.conferido,
                           m.id movimentacao_id, m.nome, m.origem,
                           EXISTS(
                               SELECT 1
                                 FROM contabil_obrigacoes o
                                 JOIN contabil_arquivos ar
                                   ON ar.obrigacao_id=o.id AND ar.excluido_em IS NULL
                                WHERE o.documento_id=m.documento_origem_id
                                  AND o.competencia=mc.competencia
                                  AND o.cancelada_em IS NULL
                           ) documento_disponivel
                      FROM contabil_movimentacoes_competencias mc
                      JOIN contabil_movimentacoes m ON m.id=mc.movimentacao_id
                      LEFT JOIN contabil_documentos d ON d.id=m.documento_origem_id
                     WHERE mc.empresa_id IN ({placeholders})
                       AND mc.competencia=?
                       AND (m.origem<>'DOCUMENTACAO' OR NOT EXISTS (
                           SELECT 1 FROM contabil_movimentacoes duplicada
                            WHERE duplicada.documento_origem_id=m.documento_origem_id
                              AND duplicada.ativa=1 AND duplicada.id<m.id
                       ))
                       AND ((m.origem='DOCUMENTACAO' AND d.competencia_inicio<=?
                             AND (d.competencia_fim IS NULL OR d.competencia_fim>=?))
                         OR (m.origem='LANCAMENTOS_CONFERENCIAS' AND m.competencia_inicio<=?
                             AND (m.competencia_fim IS NULL OR m.competencia_fim>=?)))
                     ORDER BY mc.empresa_id, UPPER(m.nome)""",
                empresa_ids + [competencia, competencia, competencia, competencia, competencia],
            ).fetchall())
        else:
            rows = []

        por_empresa: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            por_empresa.setdefault(row["empresa_id"], []).append(row)

        hoje = datetime.now().date().isoformat()
        for empresa in empresas:
            aplicaveis = [
                item for item in por_empresa.get(empresa["id"], [])
                if item["aplicavel"]
            ]
            total_movimentacoes = len(aplicaveis)
            concluidas = sum(bool(item["lancado"] and item["conferido"]) for item in aplicaveis)
            pendentes = total_movimentacoes - concluidas
            atrasadas = sum(
                bool(item["data_limite"] and item["data_limite"] < hoje
                     and not (item["lancado"] and item["conferido"]))
                for item in aplicaveis
            )
            aguardando_documento = sum(
                item["origem"] == "DOCUMENTACAO" and not item["documento_disponivel"]
                for item in aplicaveis
            )
            lancadas_aguardando_conferencia = sum(
                bool(item["lancado"] and not item["conferido"])
                for item in aplicaveis
            )

            if total_movimentacoes == 0:
                situacao = "SEM_MOVIMENTACOES"
                indicador = "CINZA"
                descricao = "Sem movimentações aplicáveis."
            elif atrasadas:
                situacao = "ATRASADO"
                indicador = "VERMELHO"
                descricao = f"{atrasadas} movimentações em aberto."
            elif concluidas == total_movimentacoes:
                situacao = "CONCLUIDO"
                indicador = "VERDE"
                descricao = "Todas as movimentações lançadas e conferidas."
            elif any(item["lancado"] or item["conferido"] for item in aplicaveis):
                situacao = "EM_ANDAMENTO"
                indicador = "AZUL" if lancadas_aguardando_conferencia else "LARANJA"
                descricao = f"{pendentes} movimentações pendentes."
            else:
                situacao = "PENDENTE"
                indicador = "LARANJA"
                descricao = f"{total_movimentacoes} movimentações não iniciadas."

            empresa.update({
                "movimentacoes_total": total_movimentacoes,
                "movimentacoes_concluidas": concluidas,
                "progresso_percentual": round(concluidas / total_movimentacoes * 100) if total_movimentacoes else 0,
                "movimentacoes_atrasadas": atrasadas,
                "aguardando_documento": aguardando_documento,
                "situacao": situacao,
                "indicador": indicador,
                "descricao_situacao": descricao,
            })

        return {
            "competencia": competencia,
            "resumo": counts,
            "empresas": empresas,
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
        }
    finally:
        conn.close()


def atribuicao_lote(alteracoes: list[dict[str, Any]], usuario_id: int) -> list[dict[str, Any]]:
    conn = conectar_banco()
    result = []
    try:
        conn.execute("BEGIN")
        for item in alteracoes:
            empresa_id, novo_id = item["empresa_id"], item.get("responsavel_id")
            if not conn.execute("SELECT 1 FROM empresas WHERE id=?", (empresa_id,)).fetchone():
                raise LookupError("Empresa não encontrada.")
            atual = conn.execute("SELECT * FROM contabil_atribuicoes WHERE empresa_id=? AND encerrado_em IS NULL", (empresa_id,)).fetchone()
            if atual and atual["usuario_id"] != novo_id and not item.get("confirmar_transferencia"):
                raise ConflictError("A empresa já possui responsável. Confirme a transferência.")
            if novo_id is not None and not conn.execute("SELECT 1 FROM usuarios WHERE id=? AND ativo=1", (novo_id,)).fetchone():
                raise LookupError("Responsável ativo não encontrado.")
            if atual:
                conn.execute("UPDATE contabil_atribuicoes SET encerrado_em=CURRENT_TIMESTAMP, motivo_encerramento=? WHERE id=?",
                             (item.get("motivo"), atual["id"]))
            new_id = None
            if novo_id is not None:
                new_id = conn.execute(
                    "INSERT INTO contabil_atribuicoes (empresa_id, usuario_id, atribuido_por) VALUES (?, ?, ?)",
                    (empresa_id, novo_id, usuario_id)).lastrowid
            registrar_historico(conn, empresa_id, usuario_id, "ATRIBUICAO", new_id, "TRANSFERIR",
                                {"responsavel_id": novo_id}, {"responsavel_id": atual["usuario_id"] if atual else None}, item.get("motivo"))
            result.append({"empresa_id": empresa_id, "responsavel_id": novo_id,
                           "responsavel_nome": conn.execute("SELECT nome FROM usuarios WHERE id=?", (novo_id,)).fetchone()["nome"] if novo_id else None})
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class ConflictError(ValueError):
    pass


def documentacao(empresa_id: int, competencia: int, ano: int, usuario_id: int | None = None) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        empresa = _row(conn.execute("SELECT id, razao_social, nome_fantasia, cnpj, regime_tributario FROM empresas WHERE id=?", (empresa_id,)).fetchone())
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        garantir_categorias(conn, empresa_id, usuario_id)
        conn.execute(
            """INSERT OR IGNORE INTO contabil_obrigacoes (documento_id, empresa_id, competencia, criada_por)
               SELECT id, empresa_id, ?, ? FROM contabil_documentos
                WHERE empresa_id=? AND competencia_inicio<=?
                  AND (competencia_fim IS NULL OR competencia_fim>=?)""",
            (competencia, usuario_id, empresa_id, competencia, competencia))
        conn.commit()
        docs = _rows(conn.execute(
            """SELECT d.*, c.nome categoria_nome, o.id obrigacao_id,
                      COUNT(a.id) quantidade_arquivos, MAX(a.enviado_em) ultimo_upload
                 FROM contabil_documentos d JOIN contabil_categorias c ON c.id=d.categoria_id
                 LEFT JOIN contabil_obrigacoes o ON o.documento_id=d.id AND o.competencia=? AND o.cancelada_em IS NULL
                 LEFT JOIN contabil_arquivos a ON a.obrigacao_id=o.id AND a.excluido_em IS NULL
                WHERE d.empresa_id=? AND d.competencia_inicio<=?
                  AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)
                GROUP BY d.id ORDER BY c.ordem, UPPER(d.nome)""",
            (competencia, empresa_id, competencia, competencia)).fetchall())
        atual = competencia_anterior()
        for d in docs:
            d["ativo"] = bool(d["ativo"])
            d["status"] = "RECEBIDO" if d["quantidade_arquivos"] else "FUTURO" if competencia > atual else "PENDENTE" if competencia == atual else "NAO_RECEBIDO"
        categorias = _rows(conn.execute(
            """SELECT c.*, COUNT(DISTINCT d.id) documentos_count,
                SUM(CASE WHEN o.id IS NOT NULL AND NOT EXISTS
                  (SELECT 1 FROM contabil_arquivos a WHERE a.obrigacao_id=o.id AND a.excluido_em IS NULL) THEN 1 ELSE 0 END) obrigacoes_pendentes,
                SUM(CASE WHEN o.id IS NOT NULL AND EXISTS
                  (SELECT 1 FROM contabil_arquivos a WHERE a.obrigacao_id=o.id AND a.excluido_em IS NULL) THEN 1 ELSE 0 END) obrigacoes_recebidas
              FROM contabil_categorias c
              LEFT JOIN contabil_documentos d ON d.categoria_id=c.id
                AND d.competencia_inicio<=?
                AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)
              LEFT JOIN contabil_obrigacoes o ON o.documento_id=d.id AND o.competencia=?
             WHERE c.empresa_id=? AND c.ativo=1 GROUP BY c.id ORDER BY c.ordem, c.nome""",
            (competencia, competencia, competencia, empresa_id)).fetchall())
        for c in categorias: c["ativo"] = bool(c["ativo"])
        statuses = []
        for mes in range(1, 13):
            comp = ano * 100 + mes
            applicable = documentacao_status(conn, empresa_id, comp)
            statuses.append({"mes": mes, "status": applicable})
        return {"empresa": empresa, "competencia": competencia, "categorias": categorias, "documentos": docs,
                "competencias_ano": statuses,
                "resumo": {"total": len(docs), "recebidos": sum(d["status"] == "RECEBIDO" for d in docs),
                           "pendentes": sum(d["status"] == "PENDENTE" for d in docs),
                           "nao_recebidos": sum(d["status"] == "NAO_RECEBIDO" for d in docs)}}
    finally:
        conn.close()


def documentacao_status(conn, empresa_id: int, competencia: int) -> str:
    rows = conn.execute("""SELECT d.id,
      EXISTS(SELECT 1 FROM contabil_obrigacoes o JOIN contabil_arquivos a ON a.obrigacao_id=o.id AND a.excluido_em IS NULL
             WHERE o.documento_id=d.id AND o.competencia=?) recebido
      FROM contabil_documentos d WHERE d.empresa_id=? AND d.competencia_inicio<=?
      AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)""", (competencia, empresa_id, competencia, competencia)).fetchall()
    # Sem um cadastro aplicável, a competência não é pendente: ela ainda não
    # faz parte do fluxo da empresa e deve aparecer neutra na timeline.
    if not rows: return "SEM_DOCUMENTACAO"
    received = sum(bool(r["recebido"]) for r in rows)
    return "COMPLETA" if received == len(rows) else "PARCIAL" if received or competencia == competencia_anterior() else "SEM_RECEBIMENTO"


def listar_historico(empresa_id: int, limite: int = 200) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        return _rows(conn.execute(
            """SELECT h.*, u.nome usuario_nome
                 FROM contabil_historico h LEFT JOIN usuarios u ON u.id=h.usuario_id
                WHERE h.empresa_id=? ORDER BY h.criado_em DESC, h.id DESC LIMIT ?""",
            (empresa_id, limite),
        ).fetchall())
    finally:
        conn.close()


def obter_painel_empresa_lancamentos(empresa_id: int, competencia: int, user: dict) -> dict[str, Any]:
    """Retorna as movimentações da empresa na competência, respeitando a carteira."""
    conn = conectar_banco()
    try:
        empresa = _row(conn.execute(
            """SELECT e.id,e.razao_social,e.nome_fantasia,e.cnpj,e.regime_tributario,
                      a.usuario_id responsavel_id,u.nome responsavel_nome
                 FROM empresas e
                 LEFT JOIN contabil_atribuicoes a ON a.empresa_id=e.id AND a.encerrado_em IS NULL
                 LEFT JOIN usuarios u ON u.id=a.usuario_id
                WHERE e.id=? AND e.ativo=1""", (empresa_id,)
        ).fetchone())
        if not empresa:
            raise LookupError("Empresa não encontrada ou inativa.")
        if (user["perfil"] != "ADMIN"
                and empresa["responsavel_id"] not in (None, user["id"])):
            raise PermissionError("A empresa está atribuída a outro responsável.")

        garantir_categorias(conn, empresa_id, user["id"])
        # Corrige registros legados sem justificativa de não aplicabilidade.
        conn.execute(
            """UPDATE contabil_movimentacoes_competencias
                   SET aplicavel=1, atualizado_em=CURRENT_TIMESTAMP
                 WHERE empresa_id=? AND competencia=? AND aplicavel=0
                   AND (justificativa_nao_aplicavel IS NULL OR TRIM(justificativa_nao_aplicavel)='')
                   AND lancado=0 AND conferido=0""",
            (empresa_id, competencia),
        )
        # Gera movimentação e obrigação para documentos recorrentes da competência.
        conn.execute(
            """INSERT OR IGNORE INTO contabil_movimentacoes
                (empresa_id,nome,categoria_id,origem,documento_origem_id,ativa)
                SELECT d.empresa_id,d.nome,d.categoria_id,'DOCUMENTACAO',d.id,1
                  FROM contabil_documentos d
                 WHERE d.empresa_id=? AND d.competencia_inicio<=?
                   AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)""",
            (empresa_id, competencia, competencia),
        )
        conn.execute(
            """INSERT OR IGNORE INTO contabil_obrigacoes (documento_id,empresa_id,competencia)
                SELECT d.id,d.empresa_id,? FROM contabil_documentos d
                 WHERE d.empresa_id=? AND d.competencia_inicio<=?
                   AND (d.competencia_fim IS NULL OR d.competencia_fim>=?)""",
            (competencia, empresa_id, competencia, competencia),
        )
        conn.execute(
            """INSERT OR IGNORE INTO contabil_movimentacoes_competencias
                (movimentacao_id,empresa_id,competencia,aplicavel)
                SELECT m.id,m.empresa_id,?,1 FROM contabil_movimentacoes m
                 WHERE m.empresa_id=? AND m.ativa=1 AND m.competencia_inicio<=?
                   AND (m.competencia_fim IS NULL OR m.competencia_fim>=?)""",
            (competencia, empresa_id, competencia, competencia),
        )
        conn.commit()
        rows = _rows(conn.execute(
            """SELECT mc.id competencia_id,mc.movimentacao_id,mc.empresa_id,mc.competencia,
                      mc.data_limite,mc.aplicavel,mc.justificativa_nao_aplicavel,
                      mc.lancado,mc.conferido,mc.lancado_por,mc.lancado_em,
                      mc.conferido_por,mc.conferido_em,m.nome,m.origem,m.categoria_id,
                      c.nome categoria_nome,d.id documento_origem_id,o.id obrigacao_id,
                      CASE WHEN m.origem='DOCUMENTACAO' THEN EXISTS(
                        SELECT 1 FROM contabil_arquivos ar
                         WHERE ar.obrigacao_id=o.id AND ar.excluido_em IS NULL
                      ) ELSE 1 END documento_disponivel,
                      (SELECT COUNT(*) FROM contabil_arquivos ar
                        WHERE ar.obrigacao_id=o.id AND ar.excluido_em IS NULL) quantidade_arquivos
                 FROM contabil_movimentacoes_competencias mc
                 JOIN contabil_movimentacoes m ON m.id=mc.movimentacao_id
                 LEFT JOIN contabil_categorias c ON c.id=m.categoria_id
                 LEFT JOIN contabil_documentos d ON d.id=m.documento_origem_id
                 LEFT JOIN contabil_obrigacoes o ON o.documento_id=d.id
                      AND o.competencia=mc.competencia AND o.cancelada_em IS NULL
                WHERE mc.empresa_id=? AND mc.competencia=?
                  AND (m.origem<>'DOCUMENTACAO' OR NOT EXISTS (
                      SELECT 1 FROM contabil_movimentacoes duplicada
                       WHERE duplicada.documento_origem_id=m.documento_origem_id
                         AND duplicada.ativa=1 AND duplicada.id<m.id
                  ))
                  AND ((m.origem='DOCUMENTACAO' AND d.competencia_inicio<=?
                        AND (d.competencia_fim IS NULL OR d.competencia_fim>=?))
                    OR (m.origem='LANCAMENTOS_CONFERENCIAS' AND m.competencia_inicio<=?
                        AND (m.competencia_fim IS NULL OR m.competencia_fim>=?)))
                ORDER BY COALESCE(c.ordem,999),UPPER(m.nome)""",
            (empresa_id, competencia, competencia, competencia, competencia, competencia),
        ).fetchall())
        for row in rows:
            for key in ("aplicavel", "lancado", "conferido", "documento_disponivel"):
                row[key] = bool(row[key])
            row["status_documento"] = (
                "AGUARDANDO_DOCUMENTO" if row["origem"] == "DOCUMENTACAO" and not row["documento_disponivel"]
                else "RECEBIDO" if row["origem"] == "DOCUMENTACAO" else "NAO_SE_APLICA"
            )
            row["concluida"] = bool(row["lancado"] and row["conferido"])
        aplicaveis = [row for row in rows if row["aplicavel"]]
        concluidas = sum(row["concluida"] for row in aplicaveis)
        return {
            "empresa": empresa,
            "competencia": competencia,
            "movimentacoes": rows,
            "resumo": {
                "total": len(aplicaveis),
                "concluidas": concluidas,
                "pendentes": len(aplicaveis) - concluidas,
                "aguardando_documento": sum(row["status_documento"] == "AGUARDANDO_DOCUMENTO" for row in aplicaveis),
                "progresso_percentual": round(concluidas / len(aplicaveis) * 100) if aplicaveis else 0,
            },
            "categorias": _rows(conn.execute(
                "SELECT id,nome,ordem FROM contabil_categorias WHERE empresa_id=? AND ativo=1 ORDER BY ordem,nome",
                (empresa_id,),
            ).fetchall()),
        }
    finally:
        conn.close()
