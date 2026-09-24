from __future__ import annotations

from datetime import date
from pathlib import Path
import io

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth

from app.db.database import BASE_DIR, STORAGE_BASE
from .repository import (
    criar_declaracao,
    listar_faturamentos_empresa,
    listar_faturamentos_periodo,
    obter_empresa,
    obter_ultima_competencia_faturamento,
)


MESES_PT = [
    "", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]
MESES_PT_MIN = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

DECLARACOES_DIR = STORAGE_BASE / "declaracoes_faturamento"
TEMPLATE_PDF = BASE_DIR / "assets" / "templates" / "faturamento_declaracao_template.pdf"
LOCAL_DOCUMENTO_PADRAO = "Afogados da Ingazeira - PE"
PAGE_WIDTH, PAGE_HEIGHT = A4


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


def periodo_12_meses_por_empresa(empresa_id: int) -> tuple[int, int, int, int, bool]:
    """Calcula os 12 meses a partir do último faturamento informado.

    Regra: o último mês com lançamento é o mês final da janela. A partir dele,
    o sistema volta 11 meses. Competências sem lançamento continuam na janela e
    recebem R$ 0,00 no detalhamento, sem bloquear a geração da declaração.

    Se ainda não existir nenhum lançamento, usa como referência o mês anterior
    ao mês civil atual e retorna os 12 meses correspondentes, todos podendo ficar
    zerados. O booleano de retorno informa se foi encontrado algum lançamento.
    """
    hoje = date.today()
    limite_ano, limite_mes = hoje.year, hoje.month

    # Consulta somente a última competência informada. O banco já possui índice
    # composto por empresa + competência; não carregamos o histórico inteiro.
    ultimo = obter_ultima_competencia_faturamento(empresa_id, limite_ano, limite_mes)
    if ultimo:
        fim_ano, fim_mes = ultimo
        controle_informado = True
    else:
        fim_ano, fim_mes = _mes_anterior(hoje.year, hoje.month)
        controle_informado = False

    inicio_ano, inicio_mes = _adicionar_meses(fim_ano, fim_mes, -11)
    return inicio_ano, inicio_mes, fim_ano, fim_mes, controle_informado


def _periodo_label(ano_inicio: int, mes_inicio: int, ano_fim: int, mes_fim: int) -> str:
    return f"{MESES_PT[mes_inicio].title()}/{ano_inicio} a {MESES_PT[mes_fim].title()}/{ano_fim}"


def _formatar_cnpj(cnpj: str | None) -> str:
    digits = "".join(ch for ch in (cnpj or "") if ch.isdigit())
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return cnpj or ""


def _formatar_moeda(valor: float) -> str:
    texto = f"{float(valor or 0):,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _formatar_mes_ano(ano: int, mes: int) -> str:
    return f"{MESES_PT[mes]}/{ano}"


def _formatar_local_documento(empresa: dict | None) -> str:
    """Monta o local da declaração a partir do município/UF da empresa."""
    municipio = str((empresa or {}).get("municipio") or "").strip()
    uf = str((empresa or {}).get("uf") or "").strip().upper()

    if municipio:
        # Mantém acentos já cadastrados e melhora apenas a capitalização.
        municipio = municipio.title()
        palavras_minusculas = {"da", "de", "do", "das", "dos", "e"}
        municipio = " ".join(
            palavra.lower() if palavra.lower() in palavras_minusculas and indice > 0 else palavra
            for indice, palavra in enumerate(municipio.split())
        )
        if uf:
            return f"{municipio} - {uf}"
        return municipio

    return LOCAL_DOCUMENTO_PADRAO


def _formatar_data_extenso(
    data: date | None = None,
    empresa: dict | None = None,
) -> str:
    data = data or date.today()
    local = _formatar_local_documento(empresa)
    return f"{local}, {data.day} de {MESES_PT_MIN[data.month]} de {data.year}."


def _ajustar_font_size(
    texto: str,
    fonte: str,
    largura_maxima: float,
    tamanho_inicial: float,
    tamanho_minimo: float = 7.0,
) -> float:
    tamanho = tamanho_inicial
    while tamanho > tamanho_minimo and stringWidth(texto, fonte, tamanho) > largura_maxima:
        tamanho -= 0.25
    return max(tamanho, tamanho_minimo)


def _y_from_top(bottom_of_text: float) -> float:
    return PAGE_HEIGHT - bottom_of_text + 1.0


def _whiteout(c: canvas.Canvas, x: float, top: float, width: float, height: float) -> None:
    c.setFillColor(white)
    c.rect(x, PAGE_HEIGHT - top - height, width, height, fill=1, stroke=0)


def _whiteout_bottom(c: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    c.setFillColor(white)
    c.rect(x, y, width, height, fill=1, stroke=0)


def _draw_center(
    c: canvas.Canvas,
    texto: str,
    centro_x: float,
    y: float,
    fonte: str = "Times-Roman",
    tamanho: float = 10,
) -> None:
    c.setFillColor(black)
    c.setFont(fonte, tamanho)
    c.drawCentredString(centro_x, y, texto)


def _iterar_periodos(
    ano_inicio: int,
    mes_inicio: int,
    ano_fim: int,
    mes_fim: int,
) -> list[tuple[int, int]]:
    atual = (ano_inicio, mes_inicio)
    fim = (ano_fim, mes_fim)
    periodos: list[tuple[int, int]] = []
    while atual <= fim:
        periodos.append(atual)
        atual = (atual[0] + 1, 1) if atual[1] == 12 else (atual[0], atual[1] + 1)
    return periodos


def _descricao_declaracao(tipo: str, periodos: list[tuple[int, int]]) -> tuple[str, str, str]:
    inicio = periodos[0]
    fim = periodos[-1]

    if tipo == "Anual":
        if not (inicio[1] == 1 and fim[1] == 12 and inicio[0] == fim[0]):
            raise ValueError("Uma declaração anual precisa conter janeiro a dezembro do mesmo ano.")
        ano = inicio[0]
        return (
            f"Relação de Faturamento do ano de {ano}",
            f"no ano de {ano}",
            f"anual_{ano}",
        )

    if tipo == "Últimos 12 meses":
        if len(periodos) != 12:
            raise ValueError("A declaração dos últimos 12 meses precisa conter exatamente 12 competências.")
        return (
            "Relação de Faturamento dos últimos 12 meses",
            "nos últimos 12 meses",
            f"12_meses_{inicio[0]}_{inicio[1]:02d}_{fim[0]}_{fim[1]:02d}",
        )

    if tipo == "Personalizada":
        if len(periodos) != 12:
            raise ValueError(
                "O modelo visual da declaração possui 12 linhas. O período personalizado deve conter exatamente 12 competências."
            )
        periodo_texto = f"{inicio[1]:02d}/{inicio[0]} a {fim[1]:02d}/{fim[0]}"
        return (
            f"Relação de Faturamento do período de {periodo_texto}",
            f"no período de {periodo_texto}",
            f"personalizada_{inicio[0]}_{inicio[1]:02d}_{fim[0]}_{fim[1]:02d}",
        )

    raise ValueError(f"Tipo de declaração inválido: {tipo}")


def _draw_center_parts(c: canvas.Canvas, parts: list[tuple[str, str, float]], center_x: float, y: float, size: float) -> None:
    total_width = sum(stringWidth(texto, fonte, size) for texto, fonte, _ in parts)
    x = center_x - total_width / 2
    for texto, fonte, _ in parts:
        c.setFillColor(black)
        c.setFont(fonte, size)
        c.drawString(x, y, texto)
        x += stringWidth(texto, fonte, size)


def _fit_center_parts(parts_factory, center_x: float, y: float, width_max: float, size_start: float = 10.0) -> tuple[float, list[tuple[str, str, float]]]:
    size = size_start
    while size >= 8.0:
        parts = parts_factory(size)
        total = sum(stringWidth(texto, fonte, size) for texto, fonte, _ in parts)
        if total <= width_max:
            return size, parts
        size -= 0.25
    size = 8.0
    return size, parts_factory(size)


def _desenhar_corpo(
    c: canvas.Canvas,
    razao_social: str,
    cnpj: str,
    qualificador: str,
    subtitulo: str,
) -> None:
    # Coordenadas do template oficial de 12 meses. Apagamos apenas o texto dinâmico.
    _whiteout_bottom(c, 70, 567, 455, 49)

    centro = PAGE_WIDTH / 2
    line1_factory = lambda sz: [
        ("Declaramos que a empresa ", "Times-Roman", 0),
        (razao_social, "Times-Bold", 0),
        (", devidamente", "Times-Roman", 0),
    ]
    line2_factory = lambda sz: [
        ("cadastrada no CNPJ sob número ", "Times-Roman", 0),
        (cnpj, "Times-Bold", 0),
        (f" , obteve {qualificador} o", "Times-Roman", 0),
    ]
    line3 = "faturamento conforme abaixo discriminado:"

    size1, parts1 = _fit_center_parts(line1_factory, centro, 600.15, 470)
    size2, parts2 = _fit_center_parts(line2_factory, centro, 587.15, 470)
    size3 = 10.0 if stringWidth(line3, "Times-Roman", 10.0) <= 470 else 9.25

    _draw_center_parts(c, parts1, centro, 600.15, size1)
    _draw_center_parts(c, parts2, centro, 587.15, size2)
    c.setFillColor(black)
    c.setFont("Times-Roman", size3)
    c.drawCentredString(centro, 574.35, line3)

    _whiteout_bottom(c, 120, 524, 355, 19)
    tamanho_subtitulo = _ajustar_font_size(subtitulo, "Times-Roman", 345, 11.0, 8.5)
    _draw_center(c, subtitulo, centro, 533.13, "Times-Roman", tamanho_subtitulo)


def _desenhar_tabela(
    c: canvas.Canvas,
    periodos: list[tuple[int, int]],
    valores: dict[tuple[int, int], float],
) -> float:
    """Substitui somente os textos das 12 linhas e do total, preservando as bordas originais."""
    if len(periodos) != 12:
        raise ValueError("O template possui exatamente 12 linhas de competências.")

    # Baselines medidos no PDF-modelo entregue pelo escritório.
    row_baselines = [
        488.72, 473.52, 458.30, 443.10,
        427.90, 412.70, 397.50, 382.30,
        367.07, 351.88, 336.67, 321.47,
    ]

    # Bordas exatas aproximadas do template: x=197.5, 296.75 e 395.5.
    # O texto é apagado somente dentro das células, sem tocar nas linhas.
    for (ano, mes), y in zip(periodos, row_baselines):
        _whiteout_bottom(c, 199.0, y - 4.0, 96.0, 12.0)
        _whiteout_bottom(c, 298.5, y - 4.0, 95.0, 12.0)
        _draw_center(c, _formatar_mes_ano(ano, mes), 247.1, y, "Times-Roman", 10.0)
        _draw_center(c, _formatar_moeda(valores.get((ano, mes), 0.0)), 346.1, y, "Times-Roman", 11.0)

    # Linha TOTAL. O retângulo de limpeza fica somente dentro das células,
    # preservando as linhas da tabela. O código anterior invadia a borda
    # inferior e deixava parte do conteúdo original do template visível.
    _whiteout_bottom(c, 199.0, 301.0, 96.0, 13.5)
    _whiteout_bottom(c, 298.5, 301.0, 95.0, 13.5)
    total = sum(valores.get(periodo, 0.0) for periodo in periodos)
    _draw_center(c, "TOTAL", 247.1, 304.08, "Times-Bold", 12.0)
    _draw_center(c, _formatar_moeda(total), 346.1, 304.08, "Times-Bold", 12.0)
    return total


def _desenhar_data(
    c: canvas.Canvas,
    data_emissao: date | None,
    empresa: dict | None = None,
) -> None:
    # Data do template fica abaixo da tabela, alinhada ao centro.
    _whiteout_bottom(c, 100, 247, 400, 26)
    _draw_center(
        c,
        _formatar_data_extenso(data_emissao, empresa),
        PAGE_WIDTH / 2,
        259.85,
        "Times-Roman",
        10.0,
    )


def _desenhar_assinatura(c: canvas.Canvas) -> None:
    # A assinatura, o nome do contador e o CRC já fazem parte do PDF-template oficial.
    # Não desenhamos novamente para preservar exatamente o visual do documento original.
    return


def _gerar_pdf_visual(
    *,
    empresa: dict,
    valores: dict[tuple[int, int], float],
    periodos: list[tuple[int, int]],
    tipo: str,
    data_emissao: date | None = None,
) -> tuple[str, Path, float]:
    if not TEMPLATE_PDF.exists():
        raise FileNotFoundError(f"Template de faturamento não encontrado: {TEMPLATE_PDF}")

    DECLARACOES_DIR.mkdir(parents=True, exist_ok=True)

    razao_social = (empresa.get("razao_social") or "").strip()
    if not razao_social:
        raise ValueError("A empresa não possui razão social cadastrada.")
    cnpj = _formatar_cnpj(empresa.get("cnpj"))

    subtitulo, qualificador, sufixo = _descricao_declaracao(tipo, periodos)

    nome_seguro = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in razao_social).strip("_")
    destino = DECLARACOES_DIR / f"Declaracao_Faturamento_{nome_seguro}_{sufixo}.pdf"

    camada_bytes = io.BytesIO()
    camada = canvas.Canvas(camada_bytes, pagesize=A4)
    _desenhar_corpo(camada, razao_social, cnpj, qualificador, subtitulo)
    total = _desenhar_tabela(camada, periodos, valores)
    _desenhar_data(camada, data_emissao, empresa)
    _desenhar_assinatura(camada)
    camada.save()
    camada_bytes.seek(0)

    base_pdf = PdfReader(str(TEMPLATE_PDF))
    camada_pdf = PdfReader(camada_bytes)
    pagina = base_pdf.pages[0]
    pagina.merge_page(camada_pdf.pages[0])

    writer = PdfWriter()
    writer.add_page(pagina)
    with destino.open("wb") as arquivo:
        writer.write(arquivo)

    return destino.name, destino.resolve(), total


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

    periodos = _iterar_periodos(ano_inicio, mes_inicio, ano_fim, mes_fim)
    if len(periodos) != 12:
        raise ValueError("A declaração deve conter exatamente 12 competências para usar o modelo visual oficial.")

    registros = listar_faturamentos_periodo(empresa_id, ano_inicio, mes_inicio, ano_fim, mes_fim)
    valores = {
        (int(item["competencia_ano"]), int(item["competencia_mes"])): float(item["valor"] or 0)
        for item in registros
    }

    nome_arquivo, caminho_obj, valor_total = _gerar_pdf_visual(
        empresa=empresa,
        valores=valores,
        periodos=periodos,
        tipo=tipo,
        data_emissao=date.today(),
    )

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


# Mantidos como utilitários públicos para o módulo, caso sejam necessários em outros pontos.
def gerar_declaracao_anual(empresa_id: int, ano: int, usuario_id: int) -> dict:
    return gerar_declaracao_periodo(
        empresa_id=empresa_id,
        tipo="Anual",
        ano_inicio=ano,
        mes_inicio=1,
        ano_fim=ano,
        mes_fim=12,
        usuario_id=usuario_id,
    )


def gerar_declaracao_12_meses(empresa_id: int, usuario_id: int) -> dict:
    ano_inicio, mes_inicio, ano_fim, mes_fim, _ = periodo_12_meses_por_empresa(empresa_id)
    return gerar_declaracao_periodo(
        empresa_id=empresa_id,
        tipo="Últimos 12 meses",
        ano_inicio=ano_inicio,
        mes_inicio=mes_inicio,
        ano_fim=ano_fim,
        mes_fim=mes_fim,
        usuario_id=usuario_id,
    )


def gerar_declaracao_personalizada(
    empresa_id: int,
    ano_inicio: int,
    mes_inicio: int,
    ano_fim: int,
    mes_fim: int,
    usuario_id: int,
) -> dict:
    return gerar_declaracao_periodo(
        empresa_id=empresa_id,
        tipo="Personalizada",
        ano_inicio=ano_inicio,
        mes_inicio=mes_inicio,
        ano_fim=ano_fim,
        mes_fim=mes_fim,
        usuario_id=usuario_id,
    )
