from __future__ import annotations

from app.db.database import conectar_banco


def listar_notificacoes(empresa_id: int | None = None) -> list[dict]:
    conn = conectar_banco()
    try:
        sql = "SELECT * FROM notificacoes_impostos"
        params: list = []
        if empresa_id is not None:
            sql += " WHERE empresa_id=?"
            params.append(empresa_id)
        sql += " ORDER BY criado_em DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
