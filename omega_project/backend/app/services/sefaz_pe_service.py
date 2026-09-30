import asyncio
import logging
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, async_playwright
from pypdf import PdfReader

logger = logging.getLogger("omega.sefaz_pe")

URL_SISTEMA = "https://efisco.sefaz.pe.gov.br/sfi_trb_gcc/PREmitirCertidaoRegularidadeFiscalMovel"
TIMEOUT_NAVEGACAO = 60_000
TIMEOUT_ELEMENTO = 30_000
TIMEOUT_NOVA_ABA_MS = 10_000
TIMEOUT_DOWNLOAD_MS = 30_000
TIPO_CERTIDAO_NOME = "Estadual - SEFAZ"
ORIGEM = "SEFAZ-PE"
HEADLESS = os.getenv("SEFAZ_HEADLESS", "false").strip().lower() in {"1", "true", "sim", "yes"}


def limpar_cnpj(cnpj: str) -> str:
    return "".join(c for c in str(cnpj) if c.isdigit())


def formatar_cnpj(cnpj: str) -> str:
    cnpj = limpar_cnpj(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def validar_cnpj(cnpj: str) -> bool:
    cnpj = limpar_cnpj(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    d1 = 0 if soma % 11 < 2 else 11 - soma % 11
    if int(cnpj[12]) != d1:
        return False
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    d2 = 0 if soma % 11 < 2 else 11 - soma % 11
    return int(cnpj[13]) == d2


def normalizar_texto(texto: str) -> str:
    import unicodedata
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto.upper()).strip()


def extrair_texto_pdf(caminho: str) -> str:
    reader = PdfReader(caminho)
    return "\n".join((pagina.extract_text() or "") for pagina in reader.pages)


def _extrair_datas(texto: str) -> tuple[Optional[str], Optional[str]]:
    normalizado = normalizar_texto(texto)
    padrao = r"(\d{2}/\d{2}/\d{4})"
    emissao = None
    validade = None

    for trecho in normalizado.splitlines():
        datas = re.findall(padrao, trecho)
        if not datas:
            continue
        if any(x in trecho for x in ("EMISSAO", "EMITIDA", "EMITIDO")) and not emissao:
            emissao = datas[0]
        if any(x in trecho for x in ("VALIDADE", "VALIDA ATE", "VALIDO ATE", "VIGENCIA")) and not validade:
            validade = datas[-1]

    todas = re.findall(padrao, normalizado)
    if not emissao and todas:
        # Só usar fallback quando houver contexto temporal claro próximo às datas.
        for m in re.finditer(padrao, normalizado):
            inicio = max(0, m.start() - 70)
            contexto = normalizado[inicio:m.end() + 70]
            if "EMISSAO" in contexto or "EMITIDA" in contexto:
                emissao = m.group(1)
                break
    if not validade and todas:
        for m in re.finditer(padrao, normalizado):
            inicio = max(0, m.start() - 70)
            contexto = normalizado[inicio:m.end() + 70]
            if any(x in contexto for x in ("VALIDADE", "VALIDA ATE", "VALIDO ATE")):
                validade = m.group(1)
                break

    def iso(valor: Optional[str]) -> Optional[str]:
        if not valor:
            return None
        try:
            return datetime.strptime(valor, "%d/%m/%Y").date().isoformat()
        except ValueError:
            return None

    return iso(emissao), iso(validade)


def analisar_certidao(texto_pdf: str, nome_arquivo: str = "") -> dict:
    texto = normalizar_texto(texto_pdf)
    arquivo = normalizar_texto(nome_arquivo).replace(" ", "")

    # A ordem é deliberada: a expressão mais específica vem primeiro.
    if "CERTIDAO POSITIVA COM EFEITOS DE NEGATIVA" in texto or "POSITIVA COM EFEITOS DE NEGATIVA" in texto:
        situacao = "POSITIVA COM EFEITOS DE NEGATIVA"
        tipo = "POSITIVA COM EFEITOS DE NEGATIVA"
    elif "CERTIDAO NEGATIVA DE DEBITOS" in texto or "CERTIDAO NEGATIVA DE DEBITO" in texto or "CERTIDAO NEGATIVA" in texto or "NADA CONSTA" in texto:
        situacao = "REGULAR"
        tipo = "NEGATIVA"
    elif "CERTIDAO POSITIVA DE DEBITOS" in texto or "CERTIDAO POSITIVA DE DEBITO" in texto or "CERTIDAO POSITIVA" in texto:
        situacao = "IRREGULAR"
        tipo = "POSITIVA"
    elif any(p in texto for p in ("INSCRITO REGULAR", "CONTRIBUINTE REGULAR", "SITUACAO FISCAL REGULAR", "SITUACAO REGULAR")):
        situacao = "REGULAR"
        tipo = "REGULAR"
    elif any(p in texto for p in ("INSCRITO IRREGULAR", "CONTRIBUINTE IRREGULAR", "SITUACAO IRREGULAR", "DEBITOS PENDENTES", "DEBITO PENDENTE", "EXISTENCIA DE DEBITO", "EXISTEM DEBITOS")):
        situacao = "IRREGULAR"
        tipo = "IRREGULARIDADE"
    elif "INSCRITOREGULAR" in arquivo:
        situacao = "REGULAR"
        tipo = "NEGATIVA"
    elif "INSCRITOIRREGULAR" in arquivo:
        situacao = "IRREGULAR"
        tipo = "POSITIVA"
    else:
        situacao = "NAO IDENTIFICADO"
        tipo = "NAO IDENTIFICADO"

    pendencia = situacao == "IRREGULAR"
    detalhes = None
    if pendencia:
        linhas = [l.strip() for l in texto_pdf.splitlines() if l.strip()]
        relevantes = []
        chaves = ("DEBIT", "PEND", "TRIBUT", "ICMS", "AUTO", "NOTIFIC", "DIVIDA")
        for linha in linhas:
            n = normalizar_texto(linha)
            if any(k in n for k in chaves):
                relevantes.append(linha.strip())
        if relevantes:
            detalhes = "\n".join(dict.fromkeys(relevantes))[:5000]

    data_emissao, data_validade = _extrair_datas(texto_pdf)
    return {
        "situacao": situacao,
        "tipo_certidao": tipo,
        "pendencia": pendencia,
        "pendencia_detalhes": detalhes,
        "data_emissao": data_emissao,
        "data_validade": data_validade,
        "motivo": f"Classificação obtida por análise do PDF e, quando necessário, do nome original do arquivo.",
    }


async def obter_razao_social(page: Page) -> Optional[str]:
    try:
        texto_body = await page.locator("body").inner_text(timeout=10_000)
        linhas = [l.strip() for l in texto_body.splitlines() if l.strip()]
        for i, linha in enumerate(linhas):
            n = normalizar_texto(linha)
            if "NOME/RAZAO SOCIAL" in n or "NOME/RAZAO" in n:
                # Caso o valor esteja na mesma linha.
                partes = re.split(r"Nome/Razão Social\s*: ?", linha, flags=re.I)
                if len(partes) > 1 and partes[1].strip():
                    candidato = partes[1].strip()
                    if normalizar_texto(candidato) not in {"RESULTADO DA CONSULTA", "IDENTIFICACAO DO CONTRIBUINTE"}:
                        return candidato
                # Caso esteja na linha seguinte.
                for candidato in linhas[i + 1:i + 5]:
                    cn = normalizar_texto(candidato)
                    if cn in {"RESULTADO DA CONSULTA", "IDENTIFICACAO DO CONTRIBUINTE", "DOCUMENTO DE IDENTIFICACAO"}:
                        continue
                    if "TIPO DE DOCUMENTO" in cn or len(limpar_cnpj(candidato)) == 14:
                        continue
                    return candidato
    except Exception as exc:
        logger.warning("Falha na captura da razão social: %s", exc)
    return None


async def preencher_cnpj(page: Page, cnpj: str) -> None:
    cnpj_formatado = formatar_cnpj(cnpj)
    try:
        campo_tipo = page.get_by_label(re.compile(r"Tipo de Documento de Identificação", re.I)).first
        await campo_tipo.select_option(label="CNPJ", timeout=TIMEOUT_ELEMENTO)
    except Exception:
        selects = page.locator("select")
        encontrado = False
        for i in range(await selects.count()):
            select = selects.nth(i)
            try:
                opcoes = await select.locator("option").all_text_contents()
                if any("CNPJ" in o.upper() for o in opcoes):
                    await select.select_option(label="CNPJ")
                    encontrado = True
                    break
            except Exception:
                continue
        if not encontrado:
            raise RuntimeError("Campo Tipo de Documento não localizado no e-Fisco.")

    try:
        campo = page.get_by_label(re.compile(r"Número do Documento de Identificação", re.I)).first
        await campo.fill(cnpj_formatado, timeout=TIMEOUT_ELEMENTO)
        return
    except Exception:
        pass

    inputs = page.locator("input")
    for i in range(await inputs.count()):
        campo = inputs.nth(i)
        try:
            tipo = await campo.get_attribute("type")
            if tipo not in (None, "", "text"):
                continue
            if not await campo.input_value():
                await campo.fill(cnpj_formatado)
                return
        except Exception:
            continue
    raise RuntimeError("Campo do CNPJ não localizado no e-Fisco.")


async def localizar_contribuinte(page: Page) -> None:
    botao = page.get_by_role("button", name=re.compile(r"Localizar", re.I)).first
    await botao.wait_for(state="visible", timeout=TIMEOUT_ELEMENTO)
    await botao.click(timeout=TIMEOUT_ELEMENTO)
    await page.wait_for_timeout(2_000)


async def emitir_certidao(page: Page, context: BrowserContext) -> Page:
    botao = page.get_by_role("button", name=re.compile(r"Emitir", re.I)).first
    await botao.wait_for(state="visible", timeout=TIMEOUT_ELEMENTO)
    paginas_antes = list(context.pages)
    await botao.click(timeout=TIMEOUT_ELEMENTO)

    limite = TIMEOUT_NOVA_ABA_MS / 1000
    decorrido = 0.0
    while decorrido < limite:
        await asyncio.sleep(0.25)
        novas = [p for p in context.pages if p not in paginas_antes]
        if novas:
            nova = novas[-1]
            try:
                await nova.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_NAVEGACAO)
            except Exception:
                pass
            await nova.bring_to_front()
            return nova
        decorrido += 0.25

    # Fluxo real testado: pode continuar na mesma página.
    try:
        await page.get_by_text(re.compile(r"Operação concluída com sucesso", re.I)).first.wait_for(state="visible", timeout=TIMEOUT_ELEMENTO)
    except Exception:
        pass
    return page


async def baixar_pdf(page: Page, pasta_destino: str, cnpj: str) -> tuple[str, str]:
    destino = os.path.join(pasta_destino, f"certidao_{limpar_cnpj(cnpj)}.pdf")
    botao = page.get_by_role("button", name=re.compile(r"Salvar documento", re.I)).first
    await botao.wait_for(state="visible", timeout=TIMEOUT_ELEMENTO)
    try:
        async with page.expect_download(timeout=TIMEOUT_DOWNLOAD_MS) as info:
            await botao.click(timeout=TIMEOUT_ELEMENTO)
        download = await info.value
        original = download.suggested_filename
        await download.save_as(destino)
        return destino, original
    except PlaywrightTimeoutError:
        await page.wait_for_timeout(2_000)
        candidatos = []
        try:
            candidatos = [p for p in Path(pasta_destino).glob("*.pdf") if p.is_file()]
        except Exception:
            pass
        # Alguns fluxos baixam no diretório de downloads do contexto.
        if candidatos:
            candidato = candidatos[-1]
            shutil.copyfile(candidato, destino)
            return destino, candidato.name
        raise RuntimeError("O botão 'Salvar documento' foi acionado, mas o PDF não foi capturado.")


async def executar_consulta_playwright(cnpj: str, browser: Optional[Browser] = None) -> dict:
    original = str(cnpj).strip()
    limpo = limpar_cnpj(original)
    base = {
        "cnpj": original,
        "cnpj_formatado": formatar_cnpj(limpo),
        "empresa": None,
        "situacao": "ERRO",
        "tipo_certidao": None,
        "status_processamento": "Erro",
        "mensagem": None,
        "arquivo_pdf": None,
        "texto_pdf": None,
        "data_emissao": None,
        "data_validade": None,
        "pendencia": False,
        "pendencia_detalhes": None,
    }
    if not validar_cnpj(limpo):
        base["mensagem"] = "CNPJ inválido."
        return base

    temp = tempfile.mkdtemp(prefix="sefaz_pe_")
    pw = None
    context = None
    page = None
    sucesso = None
    try:
        if browser is None:
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        logger.info("Consultando SEFAZ-PE | CNPJ=%s", formatar_cnpj(limpo))
        await page.goto(URL_SISTEMA, wait_until="domcontentloaded", timeout=TIMEOUT_NAVEGACAO)
        await page.wait_for_timeout(1_500)
        await preencher_cnpj(page, limpo)
        await localizar_contribuinte(page)
        base["empresa"] = await obter_razao_social(page)
        botao = page.get_by_role("button", name=re.compile(r"Emitir", re.I)).first
        if await botao.count() == 0:
            raise RuntimeError("O layout do e-Fisco não apresentou o botão Emitir.")
        sucesso = await emitir_certidao(page, context)
        caminho, nome_original = await baixar_pdf(sucesso, temp, limpo)
        if not os.path.exists(caminho) or os.path.getsize(caminho) < 100:
            raise RuntimeError("PDF inválido ou não encontrado após o download.")
        texto = extrair_texto_pdf(caminho)
        analise = analisar_certidao(texto, nome_original)
        base.update(analise)
        base["arquivo_pdf"] = caminho
        base["nome_original_arquivo"] = nome_original
        base["texto_pdf"] = texto
        base["status_processamento"] = "Sucesso"
        base["mensagem"] = "Consulta concluída com sucesso."
        return base
    except PlaywrightTimeoutError:
        base["mensagem"] = "Tempo limite excedido durante a automação do e-Fisco."
        return base
    except Exception as exc:
        base["mensagem"] = str(exc)
        return base
    finally:
        try:
            if sucesso and sucesso != page and not sucesso.is_closed():
                await sucesso.close()
        except Exception:
            pass
        try:
            if page and not page.is_closed():
                await page.close()
        except Exception:
            pass
        try:
            if context:
                await context.close()
        except Exception:
            pass
        shutil.rmtree(temp, ignore_errors=True)
        if pw:
            try:
                await pw.stop()
            except Exception:
                pass
