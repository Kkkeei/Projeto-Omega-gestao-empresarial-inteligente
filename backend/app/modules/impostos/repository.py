from __future__ import annotations

from typing import Any

from app.db.database import conectar_banco


MESES = [
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]


def listar_tributos(ativos_apenas: bool = True) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        sql = "SELECT id, nome, sigla, esfera, categoria, periodicidade, descricao, ativo, criado_em, atualizado_em FROM tributos"
        if ativos_apenas:
            sql += " WHERE ativo=1"
        sql += " ORDER BY nome"
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def criar_tributo(data: dict[str, Any]) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        cur = conn.execute(
            """
            INSERT INTO tributos (nome, sigla, esfera, categoria, periodicidade, descricao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (data["nome"].strip(), data.get("sigla"), data.get("esfera"), data.get("categoria"), data.get("periodicidade"), data.get("descricao")),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tributos WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def empresa_existe(empresa_id: int) -> bool:
    conn = conectar_banco()
    try:
        return conn.execute("SELECT 1 FROM empresas WHERE id=? AND ativo=1 LIMIT 1", (empresa_id,)).fetchone() is not None
    finally:
        conn.close()


def listar_empresas_impostos(q: str | None, regime: str | None, ano: int, mes: int) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        where = ["e.ativo=1"]
        params: list[Any] = []
        if q:
            where.append("(LOWER(e.razao_social) LIKE ? OR LOWER(COALESCE(e.nome_fantasia,'')) LIKE ? OR e.cnpj LIKE ?)")
            termo = f"%{q.strip().lower()}%"
            params.extend([termo, termo, f"%{q.strip()}%"])
        if regime and regime.upper() != "TODOS":
            where.append("UPPER(COALESCE(e.regime_tributario,''))=?")
            params.append(regime.upper())

        sql = f"""
            SELECT
                e.id, e.razao_social, e.nome_fantasia, e.cnpj, e.regime_tributario,
                COUNT(DISTINCT CASE WHEN ei.status='ATIVO' THEN ei.tributo_id END) AS tributos_vinculados,
                SUM(CASE WHEN im.status='PENDENTE' THEN 1 ELSE 0 END) AS impostos_pendentes,
                SUM(CASE WHEN im.status='PAGO' THEN 1 ELSE 0 END) AS impostos_pagos,
                COALESCE(SUM(CASE WHEN im.status='PENDENTE' THEN COALESCE(im.valor,0) ELSE 0 END),0) AS valor_a_pagar
            FROM empresas e
            LEFT JOIN empresa_impostos ei ON ei.empresa_id=e.id
            LEFT JOIN impostos_mensais im
              ON im.empresa_id=e.id
             AND im.tributo_id=ei.tributo_id
             AND im.competencia_ano=?
             AND im.competencia_mes=?
            WHERE {' AND '.join(where)}
            GROUP BY e.id
            ORDER BY e.razao_social
        """
        rows = [dict(r) for r in conn.execute(sql, [ano, mes, *params]).fetchall()]
        for row in rows:
            row["impostos_pendentes"] = int(row["impostos_pendentes"] or 0)
            row["impostos_pagos"] = int(row["impostos_pagos"] or 0)
            row["tributos_vinculados"] = int(row["tributos_vinculados"] or 0)
            row["valor_a_pagar"] = float(row["valor_a_pagar"] or 0)

        indicadores = {
            "total_empresas": len(rows),
            "empresas_configuradas": sum(1 for r in rows if r["tributos_vinculados"] > 0),
            "impostos_pendentes": sum(r["impostos_pendentes"] for r in rows),
            "impostos_pagos": sum(r["impostos_pagos"] for r in rows),
            "valor_a_pagar": round(sum(r["valor_a_pagar"] for r in rows), 2),
            "competencia": {"ano": ano, "mes": mes, "label": f"{MESES[mes]}/{ano}"},
        }
        return {"empresas": rows, "indicadores": indicadores, "competencia": indicadores["competencia"]}
    finally:
        conn.close()


def obter_empresa_impostos(empresa_id: int, ano: int, mes: int) -> dict[str, Any] | None:
    conn = conectar_banco()
    try:
        empresa = conn.execute(
            "SELECT id, cnpj, razao_social, nome_fantasia, regime_tributario, municipio, uf, ativo, observacoes FROM empresas WHERE id=?",
            (empresa_id,),
        ).fetchone()
        if not empresa:
            return None

        tributos = conn.execute(
            """
            SELECT
                ei.id AS vinculo_id,
                t.id AS tributo_id,
                t.nome,
                t.sigla,
                t.esfera,
                t.categoria,
                t.periodicidade,
                ei.obrigatorio,
                ei.vigencia_inicio,
                ei.vigencia_fim,
                ei.status AS vinculo_status,
                ei.observacao AS vinculo_observacao,
                im.id AS imposto_mensal_id,
                im.status AS status_mensal,
                im.valor,
                im.data_vencimento,
                im.data_pagamento,
                im.numero_documento,
                im.observacao AS mensal_observacao
            FROM empresa_impostos ei
            JOIN tributos t ON t.id=ei.tributo_id
            LEFT JOIN impostos_mensais im
              ON im.empresa_id=ei.empresa_id
             AND im.tributo_id=ei.tributo_id
             AND im.competencia_ano=?
             AND im.competencia_mes=?
            WHERE ei.empresa_id=? AND ei.status='ATIVO'
              AND t.ativo=1
            ORDER BY t.nome
            """,
            (ano, mes, empresa_id),
        ).fetchall()

        resumo = {
            "tributos_vinculados": len(tributos),
            "informados": sum(1 for r in tributos if r["status_mensal"]),
            "pendentes": sum(1 for r in tributos if (r["status_mensal"] or "PENDENTE") == "PENDENTE"),
            "pagos": sum(1 for r in tributos if r["status_mensal"] == "PAGO"),
            "valor_a_pagar": round(sum(float(r["valor"] or 0) for r in tributos if (r["status_mensal"] or "PENDENTE") == "PENDENTE"), 2),
        }
        return {
            "empresa": dict(empresa),
            "competencia": {"ano": ano, "mes": mes, "label": f"{MESES[mes]}/{ano}"},
            "resumo": resumo,
            "tributos": [dict(r) for r in tributos],
        }
    finally:
        conn.close()


def vincular_tributo(empresa_id: int, data: dict[str, Any]) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        empresa = conn.execute("SELECT regime_tributario FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        tributo = conn.execute("SELECT id, nome FROM tributos WHERE id=? AND ativo=1", (data["tributo_id"],)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        if not tributo:
            raise LookupError("Tributo não encontrado.")
        inicio = data.get("vigencia_inicio")
        fim = data.get("vigencia_fim")
        conn.execute(
            """
            INSERT INTO empresa_impostos (empresa_id, tributo_id, regime_tributario, obrigatorio, vigencia_inicio, vigencia_fim, status, observacao)
            VALUES (?, ?, ?, ?, ?, ?, 'ATIVO', ?)
            ON CONFLICT(empresa_id, tributo_id, vigencia_inicio) DO UPDATE SET
                obrigatorio=excluded.obrigatorio,
                vigencia_fim=excluded.vigencia_fim,
                status='ATIVO',
                observacao=excluded.observacao,
                atualizado_em=CURRENT_TIMESTAMP
            """,
            (empresa_id, data["tributo_id"], empresa["regime_tributario"], int(bool(data.get("obrigatorio", True))), inicio, fim, data.get("observacao")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM empresa_impostos WHERE empresa_id=? AND tributo_id=? AND vigencia_inicio IS ? LIMIT 1",
            (empresa_id, data["tributo_id"], inicio),
        ).fetchone()
        return {"vinculo": dict(row), "tributo": dict(tributo)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def registrar_imposto_mensal(empresa_id: int, data: dict[str, Any]) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        vinculo = conn.execute(
            "SELECT 1 FROM empresa_impostos WHERE empresa_id=? AND tributo_id=? AND status='ATIVO' LIMIT 1",
            (empresa_id, data["tributo_id"]),
        ).fetchone()
        if not vinculo:
            raise LookupError("O tributo ainda não está vinculado à empresa.")
        conn.execute(
            """
            INSERT INTO impostos_mensais
                (empresa_id, tributo_id, competencia_ano, competencia_mes, status, valor, data_vencimento, data_pagamento, numero_documento, observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(empresa_id, tributo_id, competencia_ano, competencia_mes) DO UPDATE SET
                status=excluded.status,
                valor=excluded.valor,
                data_vencimento=excluded.data_vencimento,
                data_pagamento=excluded.data_pagamento,
                numero_documento=excluded.numero_documento,
                observacao=excluded.observacao,
                atualizado_em=CURRENT_TIMESTAMP
            """,
            (
                empresa_id,
                data["tributo_id"],
                data["competencia_ano"],
                data["competencia_mes"],
                data["status"].upper(),
                data.get("valor"),
                data.get("data_vencimento"),
                data.get("data_pagamento"),
                data.get("numero_documento"),
                data.get("observacao"),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM impostos_mensais WHERE empresa_id=? AND tributo_id=? AND competencia_ano=? AND competencia_mes=?",
            (empresa_id, data["tributo_id"], data["competencia_ano"], data["competencia_mes"]),
        ).fetchone()
        return dict(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
