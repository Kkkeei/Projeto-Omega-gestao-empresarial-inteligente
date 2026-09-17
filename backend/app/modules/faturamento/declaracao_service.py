from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.db.database import BASE_DIR, STORAGE_BASE
from .repository import (
    criar_declaracao,
    listar_faturamentos_periodo,
    obter_empresa,
)


MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

DECLARACOES_DIR = STORAGE_BASE / "declaracoes_faturamento"
CONTADOR_NOME = "HORACIO DATIVO TAVARES FILHO"


def _mes_anterior(ano: int, mes: int) -> tuple[int, int]:
    if mes == 1:
        return ano - 1, 12
    return ano, mes - 1


def _adicionar_meses(ano: int, mes: int, quantidade: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + quantidade
    return total // 12, (total % 12) + 1


def ultimo_periodo_completo_12_meses() -> tuple[int, int, int, int]:
    fim_ano, fim_mes = _mes_anterior(date.today().year, date.today().month)
    inicio_ano, inicio_mes = _adicionar_meses(fim_ano, fim_mes, -11)
    return inicio_ano, inicio_mes, fim_ano, fim_mes


def _periodo_label(ano_inicio: int, mes_inicio: int, ano_fim: int, mes_fim: int) -> str:
    return f"{MESES[mes_inicio]}/{ano_inicio} a {MESES[mes_fim]}/{ano_fim}"


def _brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _gerar_pdf(
    *,
    empresa: dict,
    faturamentos: list[dict],
    tipo: str,
    ano_inicio: int,
    mes_inicio: int,
    ano_fim: int,
    mes_fim: int,
    valor_total: float,
) -> tuple[str, str]:
    DECLARACOES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    nome_arquivo = (
        f"declaracao_faturamento_{empresa['id']}_"
        f"{ano_inicio}{mes_inicio:02d}_{ano_fim}{mes_fim:02d}_{stamp}.pdf"
    )
    caminho = DECLARACOES_DIR / nome_arquivo

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "OmegaTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=16, leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#172033"),
        spaceAfter=8,
    )
    subtitle = ParagraphStyle(
        "OmegaSub", parent=styles["Normal"], fontSize=9, leading=13,
        alignment=TA_CENTER, textColor=colors.HexColor("#667085"), spaceAfter=18,
    )
    normal = ParagraphStyle(
        "OmegaNormal", parent=styles["Normal"], fontSize=10, leading=16,
        textColor=colors.HexColor("#344054"),
    )
    small = ParagraphStyle(
        "OmegaSmall", parent=styles["Normal"], fontSize=8, leading=11,
        textColor=colors.HexColor("#667085"),
    )
    right = ParagraphStyle(
        "OmegaRight", parent=small, alignment=TA_RIGHT,
    )
    center = ParagraphStyle(
        "OmegaCenter", parent=small, alignment=TA_CENTER,
    )

    doc = SimpleDocTemplate(
        str(caminho), pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Declaração de Faturamento",
        author=CONTADOR_NOME,
    )

    elementos = []
    cabecalho = Table(
        [[
            Paragraph("ÔMEGA", ParagraphStyle("Brand", parent=title, alignment=TA_LEFT, fontSize=17)),
            Paragraph("CONTABILIDADE · GESTÃO EMPRESARIAL", right),
        ]],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#D9E1EA")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos += [cabecalho, Spacer(1, 16)]
    elementos += [
        Paragraph("DECLARAÇÃO DE FATURAMENTO", title),
        Paragraph(tipo.upper(), subtitle),
        Paragraph(f"<b>Razão Social:</b> {empresa['razao_social']}", normal),
        Paragraph(f"<b>CNPJ:</b> {empresa['cnpj']}", normal),
        Paragraph(f"<b>Regime Tributário:</b> {empresa.get('regime_tributario') or 'Não informado'}", normal),
        Spacer(1, 12),
        Paragraph(
            "Declaramos, para os devidos fins, que a empresa acima identificada apresentou "
            f"faturamento total de <b>{_brl(valor_total)}</b> no período de "
            f"<b>{_periodo_label(ano_inicio, mes_inicio, ano_fim, mes_fim)}</b>, "
            "conforme os registros de faturamento mantidos pela empresa.",
            normal,
        ),
        Spacer(1, 16),
    ]

    tabela_data = [[
        Paragraph("COMPETÊNCIA", small),
        Paragraph("FATURAMENTO", right),
    ]]
    for item in faturamentos:
        competencia = f"{MESES[item['competencia_mes']]}/{item['competencia_ano']}"
        tabela_data.append([
            Paragraph(competencia, small),
            Paragraph(_brl(float(item["valor"])), right),
        ])
    tabela_data.append([
        Paragraph("TOTAL", ParagraphStyle("TotalL", parent=small, fontName="Helvetica-Bold", textColor=colors.HexColor("#172033"))),
        Paragraph(_brl(valor_total), ParagraphStyle("TotalR", parent=right, fontName="Helvetica-Bold", textColor=colors.HexColor("#172033"))),
    ])

    tabela = Table(tabela_data, colWidths=[8.5 * cm, 8.5 * cm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#DDE3EA")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FAFBFC")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elementos += [tabela, Spacer(1, 42)]
    elementos.append(Paragraph(f"Garanhuns/PE, {date.today().strftime('%d/%m/%Y')}.", normal))
    elementos.append(Spacer(1, 48))
    assinatura = Table([
        [Paragraph("____________________________________________", center)],
        [Paragraph(f"<b>{CONTADOR_NOME}</b>", center)],
        [Paragraph("Contador", center)],
    ], colWidths=[8 * cm], hAlign="CENTER")
    assinatura.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elementos.append(assinatura)
    doc.build(elementos)
    return nome_arquivo, str(caminho.resolve())


def gerar_declaracao_periodo(
    *,
    empresa_id: int,
    tipo: str,
    ano_inicio: int,
    mes_inicio: int,
    ano_fim: int,
    mes_fim: int,
    usuario_id: int,
) -> dict:
    empresa = obter_empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")

    inicio = ano_inicio * 12 + mes_inicio
    fim = ano_fim * 12 + mes_fim
    if inicio > fim:
        raise ValueError("O período inicial não pode ser maior que o período final.")

    faturamentos = listar_faturamentos_periodo(
        empresa_id, ano_inicio, mes_inicio, ano_fim, mes_fim
    )
    valor_total = sum(float(item["valor"]) for item in faturamentos)
    nome_arquivo, caminho = _gerar_pdf(
        empresa=empresa,
        faturamentos=faturamentos,
        tipo=tipo,
        ano_inicio=ano_inicio,
        mes_inicio=mes_inicio,
        ano_fim=ano_fim,
        mes_fim=mes_fim,
        valor_total=valor_total,
    )
    caminho_obj = Path(caminho).resolve()
    try:
        caminho_armazenado = str(caminho_obj.relative_to(BASE_DIR.parent.resolve()))
    except ValueError:
        caminho_armazenado = str(caminho_obj)
    return criar_declaracao(
        empresa_id=empresa_id,
        tipo=tipo,
        periodo_inicio=f"{ano_inicio:04d}-{mes_inicio:02d}",
        periodo_fim=f"{ano_fim:04d}-{mes_fim:02d}",
        valor_total=valor_total,
        nome_arquivo=nome_arquivo,
        caminho_arquivo=caminho_armazenado,
        usuario_id=usuario_id,
    )
