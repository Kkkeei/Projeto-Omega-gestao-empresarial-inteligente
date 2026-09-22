import sqlite3
from typing import Any

from app.db.database import conectar_banco
from .schemas import FaturamentoCreate, FaturamentoUpdate, FaturamentoLoteCreate


MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def empresa_existe(empresa_id: int) -> bool:
    conn = conectar_banco()
    try:
        row = conn.execute("SELECT id FROM empresas WHERE id=? LIMIT 1", (empresa_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def obter_empresa(empresa_id: int) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        row = conn.execute(
            """
            SELECT id, cnpj, razao_social, nome_fantasia, regime_tributario,
                   municipio, uf, ativo, observacoes
              FROM empresas
             WHERE id=?
            """,
            (empresa_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def criar_faturamento(dados: FaturamentoCreate) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        cursor = conn.execute(
            """
            INSERT INTO faturamentos
                (empresa_id, competencia_ano, competencia_mes, valor, observacao, data_faturamento, periodicidade)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(empresa_id, competencia_ano, competencia_mes)
            DO UPDATE SET
                valor=excluded.valor,
                observacao=excluded.observacao,
                data_faturamento=excluded.data_faturamento,
                periodicidade=excluded.periodicidade,
                atualizado_em=CURRENT_TIMESTAMP
            """,
            (
                dados.empresa_id,
                dados.competencia_ano,
                dados.competencia_mes,
                dados.valor,
                dados.observacao,
                dados.data_faturamento.isoformat() if dados.data_faturamento else f"{dados.competencia_ano:04d}-{dados.competencia_mes:02d}-01",
                dados.periodicidade,
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, empresa_id, competencia_ano, competencia_mes, valor,
                   observacao, data_faturamento, periodicidade, criado_em, atualizado_em
              FROM faturamentos
             WHERE empresa_id=? AND competencia_ano=? AND competencia_mes=?
             LIMIT 1
            """,
            (dados.empresa_id, dados.competencia_ano, dados.competencia_mes),
        ).fetchone()
        if not row:
            raise LookupError("Faturamento não encontrado após o salvamento.")
        return dict(row)
    finally:
        conn.close()


def salvar_faturamentos_lote(empresa_id: int, dados: FaturamentoLoteCreate) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        for item in dados.itens:
            conn.execute(
                """
                INSERT INTO faturamentos
                    (empresa_id, competencia_ano, competencia_mes, valor, observacao, data_faturamento, periodicidade)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(empresa_id, competencia_ano, competencia_mes)
                DO UPDATE SET
                    valor=excluded.valor,
                    observacao=excluded.observacao,
                    data_faturamento=excluded.data_faturamento,
                    periodicidade=excluded.periodicidade,
                    atualizado_em=CURRENT_TIMESTAMP
                """,
                (
                    empresa_id,
                    item.competencia_ano,
                    item.competencia_mes,
                    item.valor,
                    item.observacao,
                    item.data_faturamento.isoformat() if item.data_faturamento else None,
                    item.periodicidade,
                ),
            )
        conn.commit()
        return {
            "meses_atualizados": len(dados.itens),
            "valor_total": sum(float(item.valor) for item in dados.itens),
            "itens": listar_faturamentos_periodo(
                empresa_id,
                min((i.competencia_ano, i.competencia_mes) for i in dados.itens)[0],
                min((i.competencia_ano, i.competencia_mes) for i in dados.itens)[1],
                max((i.competencia_ano, i.competencia_mes) for i in dados.itens)[0],
                max((i.competencia_ano, i.competencia_mes) for i in dados.itens)[1],
            ),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obter_faturamento(faturamento_id: int) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        row = conn.execute(
            """
            SELECT id, empresa_id, competencia_ano, competencia_mes, valor,
                   observacao, data_faturamento, periodicidade, criado_em, atualizado_em
              FROM faturamentos
             WHERE id=?
            """,
            (faturamento_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def atualizar_faturamento(faturamento_id: int, dados: FaturamentoUpdate) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        cur = conn.execute(
            """
            UPDATE faturamentos
               SET valor=?, observacao=?, data_faturamento=?, periodicidade=?, atualizado_em=CURRENT_TIMESTAMP
             WHERE id=?
            """,
            (dados.valor, dados.observacao, dados.data_faturamento.isoformat() if dados.data_faturamento else None, dados.periodicidade, faturamento_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            return None
        conn.commit()
        return obter_faturamento(faturamento_id)
    finally:
        conn.close()


def listar_faturamentos_empresa(empresa_id: int, ano: int | None = None) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        sql = """
            SELECT id, empresa_id, competencia_ano, competencia_mes, valor,
                   observacao, data_faturamento, periodicidade, criado_em, atualizado_em
              FROM faturamentos
             WHERE empresa_id=?
        """
        params: list[Any] = [empresa_id]
        if ano is not None:
            sql += " AND competencia_ano=?"
            params.append(ano)
        sql += " ORDER BY competencia_ano DESC, competencia_mes DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def listar_faturamentos_periodo(
    empresa_id: int,
    ano_inicio: int,
    mes_inicio: int,
    ano_fim: int,
    mes_fim: int,
) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        rows = conn.execute(
            """
            SELECT competencia_ano, competencia_mes, valor, observacao, data_faturamento, periodicidade
              FROM faturamentos
             WHERE empresa_id=?
               AND (competencia_ano > ? OR (competencia_ano=? AND competencia_mes>=?))
               AND (competencia_ano < ? OR (competencia_ano=? AND competencia_mes<=?))
             ORDER BY competencia_ano, competencia_mes
            """,
            (
                empresa_id,
                ano_inicio, ano_inicio, mes_inicio,
                ano_fim, ano_fim, mes_fim,
            ),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def resumo_faturamento(empresa_id: int, ano: int) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        total = conn.execute(
            """
            SELECT COUNT(*) AS quantidade_lancamentos,
                   COALESCE(SUM(valor), 0) AS valor_total
              FROM faturamentos
             WHERE empresa_id=? AND competencia_ano=?
            """,
            (empresa_id, ano),
        ).fetchone()
        primeiro = conn.execute(
            """
            SELECT competencia_ano, competencia_mes, valor
              FROM faturamentos
             WHERE empresa_id=? AND competencia_ano=?
             ORDER BY competencia_mes ASC
             LIMIT 1
            """,
            (empresa_id, ano),
        ).fetchone()
        ultimo = conn.execute(
            """
            SELECT competencia_ano, competencia_mes, valor
              FROM faturamentos
             WHERE empresa_id=? AND competencia_ano=?
             ORDER BY competencia_mes DESC
             LIMIT 1
            """,
            (empresa_id, ano),
        ).fetchone()
        return {
            "ano": ano,
            "quantidade_lancamentos": total["quantidade_lancamentos"],
            "meses_informados": total["quantidade_lancamentos"],
            "percentual_informado": round((total["quantidade_lancamentos"] / 12) * 100, 2),
            "valor_total": total["valor_total"],
            "media_mensal": float(total["valor_total"] or 0) / 12,
            "primeiro_faturamento": dict(primeiro) if primeiro else None,
            "ultimo_faturamento": dict(ultimo) if ultimo else None,
        }
    finally:
        conn.close()


def listar_meses_ano(empresa_id: int, ano: int) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        rows = conn.execute(
            """
            SELECT id, competencia_ano, competencia_mes, valor, observacao, data_faturamento, periodicidade, atualizado_em
              FROM faturamentos
             WHERE empresa_id=? AND competencia_ano=?
             ORDER BY competencia_mes
            """,
            (empresa_id, ano),
        ).fetchall()
        index = {(row["competencia_ano"], row["competencia_mes"]): dict(row) for row in rows}
        return [
            {
                "competencia_ano": ano,
                "competencia_mes": mes,
                "valor": index.get((ano, mes), {}).get("valor"),
                "observacao": index.get((ano, mes), {}).get("observacao"),
                "data_faturamento": index.get((ano, mes), {}).get("data_faturamento"),
                "periodicidade": index.get((ano, mes), {}).get("periodicidade") or "Mensal",
                "id": index.get((ano, mes), {}).get("id"),
                "atualizado_em": index.get((ano, mes), {}).get("atualizado_em"),
                "informado": (ano, mes) in index,
            }
            for mes in range(1, 13)
        ]
    finally:
        conn.close()


def atualizar_observacao_empresa(empresa_id: int, observacao: str | None) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        cur = conn.execute(
            "UPDATE empresas SET observacoes=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (observacao, empresa_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            return None
        conn.commit()
        row = conn.execute("SELECT id, observacoes FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def pendencias_faturamento_por_empresa(ano: int, mes_limite: int) -> dict[int, list[int]]:
    """Retorna os meses ainda sem faturamento por empresa.

    mes_limite representa o último mês já encerrado para fins de cobrança
    do faturamento (ex.: em setembro, agosto é o último mês pendente).
    """
    if mes_limite < 1:
        return {}

    conn = conectar_banco()
    try:
        rows = conn.execute(
            """
            SELECT e.id AS empresa_id, f.competencia_mes
              FROM empresas e
              LEFT JOIN faturamentos f
                ON f.empresa_id=e.id
               AND f.competencia_ano=?
             WHERE e.ativo=1
             ORDER BY e.id, f.competencia_mes
            """,
            (ano,),
        ).fetchall()

        informados: dict[int, set[int]] = {}
        for row in rows:
            empresa_id = int(row["empresa_id"])
            informados.setdefault(empresa_id, set())
            if row["competencia_mes"] is not None:
                informados[empresa_id].add(int(row["competencia_mes"]))

        return {
            empresa_id: [m for m in range(1, mes_limite + 1) if m not in meses]
            for empresa_id, meses in informados.items()
        }
    finally:
        conn.close()


def listar_empresas_faturamento(
    ano_competencia: int,
    mes_competencia: int,
    regime: str | None = None,
    busca: str | None = None,
) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        sql = """
            SELECT
                e.id,
                e.cnpj,
                e.razao_social,
                e.nome_fantasia,
                e.regime_tributario,
                e.ativo,
                CASE WHEN fp.id IS NULL THEN 'pendente' ELSE 'informado' END AS status_competencia,
                fp.id AS faturamento_competencia_id,
                fp.valor AS valor_competencia,
                fp.data_faturamento AS data_faturamento_competencia,
                COALESCE(fp.periodicidade, 'Mensal') AS periodicidade_competencia,
                fp.observacao AS observacao_competencia,
                (
                    SELECT f2.competencia_ano
                      FROM faturamentos f2
                     WHERE f2.empresa_id=e.id
                     ORDER BY f2.competencia_ano DESC, f2.competencia_mes DESC
                     LIMIT 1
                ) AS ultima_competencia_ano,
                (
                    SELECT f2.competencia_mes
                      FROM faturamentos f2
                     WHERE f2.empresa_id=e.id
                     ORDER BY f2.competencia_ano DESC, f2.competencia_mes DESC
                     LIMIT 1
                ) AS ultima_competencia_mes,
                (
                    SELECT f2.valor
                      FROM faturamentos f2
                     WHERE f2.empresa_id=e.id
                     ORDER BY f2.competencia_ano DESC, f2.competencia_mes DESC
                     LIMIT 1
                ) AS ultimo_valor
              FROM empresas e
              LEFT JOIN faturamentos fp
                ON fp.empresa_id=e.id
               AND fp.competencia_ano=?
               AND fp.competencia_mes=?
             WHERE e.ativo=1
        """
        params: list[Any] = [ano_competencia, mes_competencia]
        if regime:
            sql += " AND UPPER(COALESCE(e.regime_tributario,'')) = UPPER(?)"
            params.append(regime)
        if busca and busca.strip():
            termo = f"%{busca.strip().lower()}%"
            sql += """
              AND (
                    LOWER(COALESCE(e.razao_social,'')) LIKE ?
                 OR LOWER(COALESCE(e.nome_fantasia,'')) LIKE ?
                 OR LOWER(COALESCE(e.cnpj,'')) LIKE ?
                 OR LOWER(COALESCE(e.nire,'')) LIKE ?
              )
            """
            params.extend([termo, termo, termo, termo])
        sql += " ORDER BY UPPER(COALESCE(e.razao_social,e.nome_fantasia))"
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def criar_declaracao(
    *,
    empresa_id: int,
    tipo: str,
    periodo_inicio: str,
    periodo_fim: str,
    valor_total: float,
    nome_arquivo: str,
    caminho_arquivo: str,
    usuario_id: int,
) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        cur = conn.execute(
            """
            INSERT INTO declaracoes_faturamento
                (empresa_id,tipo,periodo_inicio,periodo_fim,valor_total,
                 nome_arquivo,caminho_arquivo,usuario_id)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id,
                tipo,
                periodo_inicio,
                periodo_fim,
                valor_total,
                nome_arquivo,
                caminho_arquivo,
                usuario_id,
            ),
        )
        conn.commit()
        return obter_declaracao(cur.lastrowid)  # type: ignore[arg-type]
    finally:
        conn.close()


def obter_declaracao(declaracao_id: int) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        row = conn.execute(
            """
            SELECT d.id,d.empresa_id,d.tipo,d.periodo_inicio,d.periodo_fim,d.valor_total,
                   d.nome_arquivo,d.caminho_arquivo,d.usuario_id,d.data_geracao,
                   u.nome AS usuario_nome
              FROM declaracoes_faturamento d
              LEFT JOIN usuarios u ON u.id=d.usuario_id
             WHERE d.id=?
            """,
            (declaracao_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def listar_declaracoes_empresa(empresa_id: int) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        rows = conn.execute(
            """
            SELECT d.id,d.empresa_id,d.tipo,d.periodo_inicio,d.periodo_fim,d.valor_total,
                   d.nome_arquivo,d.caminho_arquivo,d.usuario_id,d.data_geracao,
                   u.nome AS usuario_nome
              FROM declaracoes_faturamento d
              LEFT JOIN usuarios u ON u.id=d.usuario_id
             WHERE d.empresa_id=?
             ORDER BY d.data_geracao DESC, d.id DESC
            """,
            (empresa_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
