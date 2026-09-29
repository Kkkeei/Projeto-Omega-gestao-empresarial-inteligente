from __future__ import annotations

from app.db.database import conectar_banco


def resumo_periodo(ano: int, mes: int) -> dict:
    conn = conectar_banco()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS quantidade,
                   SUM(CASE WHEN status='PENDENTE' THEN 1 ELSE 0 END) AS pendentes,
                   SUM(CASE WHEN status='PAGO' THEN 1 ELSE 0 END) AS pagos,
                   COALESCE(SUM(CASE WHEN status='PENDENTE' THEN valor ELSE 0 END),0) AS valor_a_pagar
              FROM impostos_mensais
             WHERE competencia_ano=? AND competencia_mes=?
            """,
            (ano, mes),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()
