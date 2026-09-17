import sqlite3
from typing import Any

from app.db.database import conectar_banco
from .schemas import FaturamentoCreate, FaturamentoUpdate


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
            SELECT id, cnpj, razao_social, nome_fantasia, regime_tributario, ativo
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
                (empresa_id, competencia_ano, competencia_mes, valor, observacao)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                dados.empresa_id,
                dados.competencia_ano,
                dados.competencia_mes,
                dados.valor,
                dados.observacao,
            ),
        )
        conn.commit()
        return obter_faturamento(cursor.lastrowid)  # type: ignore[arg-type]
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "UNIQUE" in str(exc).upper():
            raise ValueError("Já existe faturamento informado para esta empresa e competência.") from exc
        raise
    finally:
        conn.close()


def obter_faturamento(faturamento_id: int) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        row = conn.execute(
            """
            SELECT id, empresa_id, competencia_ano, competencia_mes, valor,
                   observacao, criado_em, atualizado_em
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
               SET valor=?, observacao=?, atualizado_em=CURRENT_TIMESTAMP
             WHERE id=?
            """,
            (dados.valor, dados.observacao, faturamento_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            return None
        conn.commit()
        return obter_faturamento(faturamento_id)
    finally:
        conn.close()


def listar_faturamentos_empresa(empresa_id: int) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        rows = conn.execute(
            """
            SELECT id, empresa_id, competencia_ano, competencia_mes, valor,
                   observacao, criado_em, atualizado_em
              FROM faturamentos
             WHERE empresa_id=?
             ORDER BY competencia_ano DESC, competencia_mes DESC
            """,
            (empresa_id,),
        ).fetchall()
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
            SELECT competencia_ano, competencia_mes, valor, observacao
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


def resumo_faturamento(empresa_id: int) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        total = conn.execute(
            """
            SELECT COUNT(*) AS quantidade_lancamentos,
                   COALESCE(SUM(valor), 0) AS valor_total
              FROM faturamentos
             WHERE empresa_id=?
            """,
            (empresa_id,),
        ).fetchone()
        ultimo = conn.execute(
            """
            SELECT competencia_ano, competencia_mes, valor
              FROM faturamentos
             WHERE empresa_id=?
             ORDER BY competencia_ano DESC, competencia_mes DESC
             LIMIT 1
            """,
            (empresa_id,),
        ).fetchone()
        return {
            "quantidade_lancamentos": total["quantidade_lancamentos"],
            "valor_total": total["valor_total"],
            "ultimo_faturamento": dict(ultimo) if ultimo else None,
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
                fp.valor AS valor_competencia,
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
              )
            """
            params.extend([termo, termo, termo])
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
