from __future__ import annotations

from datetime import date
from typing import Any

from app.db.database import conectar_banco
from app.modules.impostos.repository import competencia_iso, competencia_label

REGIMES_DCTFWEB = {"LUCRO PRESUMIDO", "LUCRO REAL"}
STATUS_FINALIZADOS = {
    "A_PAGAR", "A_VENCER", "EM_ATRASO", "PAGO", "CREDOR",
    "SEM_MOVIMENTACAO", "SEM_MOVIMENTO", "GUIA_REGISTRADA",
}
STATUS_SEM_MOVIMENTACAO = {"SEM_MOVIMENTACAO", "SEM_MOVIMENTO"}


def _normalizar_regime(valor: Any) -> str:
    return " ".join(str(valor or "").strip().upper().split())


def _status_obrigacao(status: Any, registro_existe: bool) -> tuple[str, bool]:
    """Retorna status sem confundir ausência de registro com ausência de movimento."""
    chave = str(status or "").strip().upper()
    if not registro_existe or not chave or chave == "PENDENTE":
        return "PENDENTE", False
    if chave in {"SEM_MOVIMENTACAO", "SEM_MOVIMENTO"}:
        return "SEM_MOVIMENTACAO", True
    if chave == "CREDOR":
        return "CREDOR", True
    if chave in STATUS_FINALIZADOS:
        return ("PAGO" if chave == "PAGO" else "VALOR_INFORMADO"), True
    # Estados desconhecidos não liberam o fechamento silenciosamente.
    return "PENDENTE", False


def dashboard(ano: int | None = None, mes: int | None = None) -> dict[str, Any]:
    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or hoje.month
    if not 2000 <= ano <= 2100 or not 1 <= mes <= 12:
        raise ValueError("Competência inválida.")

    competencia = competencia_iso(ano, mes)
    conn = conectar_banco()
    try:
        rows = conn.execute(
            """
            SELECT e.id AS empresa_id, e.razao_social, e.nome_fantasia, e.cnpj,
                   e.regime_tributario, ei.tributo_id, ei.obrigatorio,
                   t.nome AS tributo_nome, t.sigla AS tributo_sigla, t.esfera,
                   im.id AS mensal_id, im.status AS status_mensal, im.valor,
                   im.numero_documento
              FROM empresas e
              JOIN empresa_impostos ei ON ei.empresa_id = e.id
              JOIN tributos t ON t.id = ei.tributo_id
              LEFT JOIN impostos_mensais im
                ON im.empresa_id = e.id
               AND im.tributo_id = ei.tributo_id
               AND im.competencia_ano = ?
               AND im.competencia_mes = ?
             WHERE e.ativo = 1
               AND UPPER(COALESCE(t.esfera, '')) = 'FEDERAL'
               AND UPPER(COALESCE(e.regime_tributario, '')) IN ('LUCRO PRESUMIDO', 'LUCRO REAL')
               AND (ei.vigencia_inicio IS NULL OR substr(ei.vigencia_inicio, 1, 7) <= substr(?, 1, 7))
               AND (ei.vigencia_fim IS NULL OR substr(ei.vigencia_fim, 1, 7) >= substr(?, 1, 7))
               AND (ei.status = 'ATIVO' OR ei.vigencia_fim IS NOT NULL)
             ORDER BY e.razao_social COLLATE NOCASE, t.nome COLLATE NOCASE
            """,
            (ano, mes, competencia, competencia),
        ).fetchall()

        empresas: dict[int, dict[str, Any]] = {}
        tributos: dict[int, dict[str, Any]] = {}
        for row in rows:
            item = dict(row)
            regime = _normalizar_regime(item.get("regime_tributario"))
            if regime not in REGIMES_DCTFWEB:
                continue
            # A esfera Federal é a fonte da seleção; cada vínculo vigente é uma obrigação esperada.
            tributo_id = int(item["tributo_id"])
            tributos[tributo_id] = {
                "id": tributo_id,
                "nome": item["tributo_nome"],
                "sigla": item.get("tributo_sigla"),
                "esfera": item["esfera"],
            }
            empresa = empresas.setdefault(
                int(item["empresa_id"]),
                {
                    "id": int(item["empresa_id"]),
                    "razao_social": item["razao_social"],
                    "nome_fantasia": item.get("nome_fantasia"),
                    "cnpj": item["cnpj"],
                    "regime_tributario": item["regime_tributario"],
                    "obrigacoes": [],
                },
            )
            status, finalizada = _status_obrigacao(item.get("status_mensal"), item.get("mensal_id") is not None)
            empresa["obrigacoes"].append({
                "tributo_id": tributo_id,
                "nome": item["tributo_nome"],
                "sigla": item.get("tributo_sigla"),
                "status": status,
                "valor": float(item["valor"]) if item.get("valor") is not None else None,
                "numero_documento": item.get("numero_documento"),
                "finalizada": finalizada,
            })

        total_obrigacoes = finalizadas = empresas_com_pendencias = 0
        for empresa in empresas.values():
            obrigacoes = empresa["obrigacoes"]
            empresa["total_obrigacoes"] = len(obrigacoes)
            empresa["finalizadas"] = sum(1 for x in obrigacoes if x["finalizada"])
            empresa["pendentes"] = len(obrigacoes) - empresa["finalizadas"]
            empresa["status_geral"] = "COMPLETA" if obrigacoes and empresa["pendentes"] == 0 else "PENDENTE"
            total_obrigacoes += len(obrigacoes)
            finalizadas += empresa["finalizadas"]
            if empresa["pendentes"]:
                empresas_com_pendencias += 1

        pendentes = total_obrigacoes - finalizadas
        percentual = round(finalizadas / total_obrigacoes * 100, 1) if total_obrigacoes else 0
        # Zero obrigações é estado vazio, nunca uma liberação automática.
        liberada = total_obrigacoes > 0 and pendentes == 0
        return {
            "competencia": {"ano": ano, "mes": mes, "label": competencia_label(ano, mes)},
            "tributos": sorted(tributos.values(), key=lambda x: (x["nome"] or "").casefold()),
            "empresas": list(empresas.values()),
            "indicadores": {
                "total_empresas": len(empresas),
                "total_obrigacoes": total_obrigacoes,
                "finalizadas": finalizadas,
                "pendentes": pendentes,
                "empresas_com_pendencias": empresas_com_pendencias,
                "percentual": percentual,
                "liberada": liberada,
            },
        }
    finally:
        conn.close()
