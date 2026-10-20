from __future__ import annotations

from io import BytesIO

from app.db.database import conectar_banco
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .repository import MESES, chave_competencia, competencia_iso


def _meses(ano_inicio: int, mes_inicio: int, ano_fim: int, mes_fim: int):
    cur = chave_competencia(ano_inicio, mes_inicio)
    end = chave_competencia(ano_fim, mes_fim)
    out = []
    while cur <= end:
        y = (cur - 1) // 12
        m = cur - y * 12
        out.append((y, m))
        cur += 1
    return out


def _format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_previa(empresa_id: int, ano_inicio: int, mes_inicio: int, ano_fim: int, mes_fim: int) -> dict:
    if chave_competencia(ano_inicio, mes_inicio) > chave_competencia(ano_fim, mes_fim):
        raise ValueError("A competência inicial não pode ser posterior à competência final.")

    conn = conectar_banco()
    try:
        empresa = conn.execute(
            "SELECT id,razao_social,nome_fantasia,cnpj FROM empresas WHERE id=?",
            (empresa_id,),
        ).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")

        inicio = competencia_iso(ano_inicio, mes_inicio)
        fim = competencia_iso(ano_fim, mes_fim)

        # O relatório deve trazer qualquer tributo que tenha sido relevante em
        # pelo menos uma competência do período, mesmo se a vigência terminou
        # antes do fim do relatório.
        tributos = conn.execute(
            """
            SELECT DISTINCT t.id,t.nome,t.sigla,t.esfera
              FROM empresa_impostos ei
              JOIN tributos t ON t.id=ei.tributo_id
             WHERE ei.empresa_id=?
               AND (ei.vigencia_inicio IS NULL OR substr(ei.vigencia_inicio,1,7) <= substr(?,1,7))
               AND (ei.vigencia_fim IS NULL OR substr(ei.vigencia_fim,1,7) >= substr(?,1,7))
             ORDER BY CASE t.esfera WHEN 'Federal' THEN 1 WHEN 'Estadual' THEN 2 WHEN 'Municipal' THEN 3 ELSE 4 END,
                      t.nome COLLATE NOCASE
            """,
            (empresa_id, fim, inicio),
        ).fetchall()
        taxes = [dict(t) for t in tributos]

        configs: dict[int, list[dict]] = {}
        for tax in taxes:
            rows = conn.execute(
                """
                SELECT vigencia_inicio,vigencia_fim,status
                  FROM empresa_impostos
                 WHERE empresa_id=? AND tributo_id=?
                   AND (vigencia_inicio IS NULL OR substr(vigencia_inicio,1,7) <= substr(?,1,7))
                   AND (vigencia_fim IS NULL OR substr(vigencia_fim,1,7) >= substr(?,1,7))
                 ORDER BY id DESC
                """,
                (empresa_id, tax["id"], fim, inicio),
            ).fetchall()
            configs[tax["id"]] = [dict(row) for row in rows]

        def ativo_na_comp(tax_id: int, ano: int, mes: int) -> bool:
            comp = competencia_iso(ano, mes)[:7]
            return any(
                (not row.get("vigencia_inicio") or row["vigencia_inicio"][:7] <= comp)
                and (not row.get("vigencia_fim") or row["vigencia_fim"][:7] >= comp)
                for row in configs.get(tax_id, [])
            )

        rows = []
        totals = {str(t["id"]): 0.0 for t in taxes}
        total_geral = 0.0

        for ano, mes in _meses(ano_inicio, mes_inicio, ano_fim, mes_fim):
            cells = []
            status = []
            row_total = 0.0
            for tax in taxes:
                if not ativo_na_comp(tax["id"], ano, mes):
                    cells.append("—")
                    status.append({"tributo_id": tax["id"], "situacao": "Não aplicável"})
                    continue

                record = conn.execute(
                    "SELECT * FROM impostos_mensais WHERE empresa_id=? AND tributo_id=? AND competencia_ano=? AND competencia_mes=?",
                    (empresa_id, tax["id"], ano, mes),
                ).fetchone()

                if not record:
                    cells.append("Pendente")
                    status.append({"tributo_id": tax["id"], "situacao": "Pendente"})
                    continue

                data = dict(record)
                st = (data.get("status") or "PENDENTE").upper()
                if st == "PENDENTE":
                    cell = "Pendente"
                    situacao = "Pendente"
                elif st == "CREDOR":
                    cell = "R$ 0,00 (Credor)"
                    situacao = "Credor"
                elif st in {"SEM_MOVIMENTO", "SEM_MOVIMENTACAO"}:
                    cell = "R$ 0,00 (Sem movimentação)"
                    situacao = "Sem movimentação"
                elif st == "SEM_APURACAO":
                    cell = "R$ 0,00 (Sem apuração)"
                    situacao = "Sem apuração"
                else:
                    value = float(data.get("valor") or 0)
                    cell = value
                    row_total += value
                    totals[str(tax["id"])] += value
                    total_geral += value
                    situacao = st

                cells.append(cell)
                status.append({"tributo_id": tax["id"], "situacao": situacao})

            rows.append({
                "competencia": f"{mes:02d}/{ano}",
                "valores": cells,
                "total": row_total,
                "situacoes": status,
            })

        return {
            "empresa": dict(empresa),
            "periodo": {
                "ano_inicio": ano_inicio,
                "mes_inicio": mes_inicio,
                "ano_fim": ano_fim,
                "mes_fim": mes_fim,
                "label": f"{mes_inicio:02d}/{ano_inicio} a {mes_fim:02d}/{ano_fim}",
            },
            "tributos": taxes,
            "linhas": rows,
            "totais": totals,
            "total_geral": total_geral,
        }
    finally:
        conn.close()


def gerar_pdf(dados: dict) -> bytes:
    buf = BytesIO()
    page_width, _page_height = landscape(A4)
    margin = 8 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#10204a"),
        spaceAfter=4,
    )
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=7, leading=9)

    story = [
        Paragraph("RELATÓRIO DE IMPOSTOS", title),
        Paragraph(f"{dados['empresa']['razao_social']} — CNPJ: {dados['empresa']['cnpj']}", small),
        Paragraph(f"Período: {dados['periodo']['label']}", small),
        Spacer(1, 5 * mm),
    ]

    headers = ["Competência"] + [t["nome"] for t in dados["tributos"]] + ["Total"]
    table = [headers]
    for row in dados["linhas"]:
        values = [row["competencia"]]
        for value in row["valores"]:
            values.append(value if isinstance(value, str) else _format_brl(value))
        values.append(_format_brl(row["total"]))
        table.append(values)

    total = ["TOTAL"]
    for tax in dados["tributos"]:
        total.append(_format_brl(float(dados["totais"].get(str(tax["id"]), 0))))
    total.append(_format_brl(float(dados["total_geral"])))
    table.append(total)

    available_width = page_width - (2 * margin)
    fixed_width = 25 * mm
    tax_count = len(dados["tributos"])
    tax_width = max(11 * mm, (available_width - (2 * fixed_width)) / max(1, tax_count))
    widths = [fixed_width] + [tax_width for _ in dados["tributos"]] + [fixed_width]

    tbl = Table(table, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf4ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1d5fa8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dce3ec")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#fafbfd")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Pendente = competência configurada ainda sem registro; "
        "Credor = apuração com valor a recolher igual a zero; "
        "Sem movimentação = não houve fato gerador informado; — = tributo fora da vigência da competência.",
        small,
    ))
    story.append(Paragraph(
        "Relatório consolidado dos registros existentes no módulo Impostos.",
        small,
    ))
    doc.build(story)
    return buf.getvalue()
