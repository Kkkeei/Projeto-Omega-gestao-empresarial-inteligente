"""Automação da Certidão Negativa/Narrativa de Débito Fiscal da SEFAZ-PE.

O fluxo visual abaixo preserva deliberadamente a sequência original que já foi
homologada pelo usuário. A etapa nova fica somente depois do comentário marcado
no código original: leitura do conteúdo que está sendo exibido no Chrome.
"""
from __future__ import annotations

import os
import subprocess
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pyperclip

pyautogui = None

def _get_pyautogui():
    global pyautogui
    if pyautogui is None:
        import pyautogui as _pyautogui
        _pyautogui.FAILSAFE = True
        pyautogui = _pyautogui
    return pyautogui

URL_SEFAZ_NARRATIVA = (
    "https://sso.sefaz.pe.gov.br/auth/realms/sefazpe/protocol/openid-connect/auth?"
    "client_id=efisco-cli&response_type=code&redirect_uri="
    "https://efisco.sefaz.pe.gov.br/sfi_trb_gpf/PREmitirCertidaoNegativaNarrativaDebitoFiscal"
)
CERTIFICADO_PADRAO = os.getenv("SEFAZ_CERTIFICADO_NOME", "OMEGA CONTABILIDADE")

def _fechar_chrome_completo() -> None:
    if os.getenv("OMEGA_CLOSE_CHROME_HARD", "true").strip().lower() not in {"1", "true", "sim", "yes"}:
        return
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True, text=True, timeout=15)
    except Exception:
        pass

STORAGE_BASE = Path(__file__).resolve().parents[3] / "storage" / "automacoes" / "sefaz_narrativa"


def _data_iso(texto: str | None) -> str | None:
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _extrair_data(texto: str, palavras: tuple[str, ...]) -> str | None:
    padrao = r"(?:" + "|".join(re.escape(p) for p in palavras) + r").{0,100}?(\d{2}/\d{2}/\d{4})"
    match = re.search(padrao, texto, flags=re.IGNORECASE | re.DOTALL)
    return _data_iso(match.group(1)) if match else None


def _classificar_documento(texto: str) -> str:
    """Classificação conservadora: só usa frases explícitas do documento."""
    normalizado = " ".join((texto or "").upper().split())
    if "CERTIDÃO POSITIVA COM EFEITOS DE NEGATIVA" in normalizado:
        return "POSITIVA COM EFEITOS DE NEGATIVA"
    if "CERTIDÃO NEGATIVA" in normalizado or "NÃO HÁ DÉBITO" in normalizado or "NAO HA DEBITO" in normalizado:
        return "REGULAR"
    if "CERTIDÃO POSITIVA" in normalizado:
        return "IRREGULAR"
    return "ERRO"


def _ler_texto_visivel_no_chrome() -> str:
    """Copia o conteúdo textual atualmente exibido na janela ativa do Chrome."""
    pg = _get_pyautogui()
    pg.press("esc")
    time.sleep(0.4)
    pyperclip.copy("")
    pg.hotkey("ctrl", "a")
    time.sleep(0.4)
    pg.hotkey("ctrl", "c")
    time.sleep(0.8)
    texto = pyperclip.paste() or ""
    pg.press("esc")
    return texto.strip()


def _salvar_texto_debug(texto: str, cnpj: str) -> str | None:
    if not texto:
        return None
    agora = datetime.now()
    pasta = STORAGE_BASE / "leituras" / agora.strftime("%Y") / agora.strftime("%m")
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{cnpj}_{agora.strftime('%Y%m%d_%H%M%S_%f')}.txt"
    caminho.write_text(texto, encoding="utf-8")
    return str(caminho.resolve().relative_to(STORAGE_BASE.parent.parent.resolve()))


def _executar_automacao_interna(cnpj: str, certificado_nome: str | None = None) -> dict[str, Any]:
    """Executa o fluxo original e sempre fecha o Chrome ao final."""
    cnpj = re.sub(r"\D", "", cnpj or "")
    certificado_nome = certificado_nome or CERTIFICADO_PADRAO

    if len(cnpj) != 14:
        raise ValueError("CNPJ inválido para a automação SEFAZ-PE.")

    print("Iniciando automação no Google Chrome...")

    pg = _get_pyautogui()

    # --- FLUXO ORIGINAL: PRESERVADO ---
    pg.press('win')
    time.sleep(1)

    pg.write('chrome', interval=0.1)
    time.sleep(1)
    pg.press('enter')

    time.sleep(4)

    pg.hotkey('ctrl', 'l')
    time.sleep(0.5)

    # SOLUÇÃO: URL usando escape de caracteres unicode (mantida do código original)
    url_sefaz = URL_SEFAZ_NARRATIVA

    pyperclip.copy(url_sefaz)
    time.sleep(0.5)

    pg.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pg.press('enter')

    print("Aguardando carregamento da Sefaz-PE...")
    time.sleep(7)

    print("Executando exatamente os 4 tabs solicitados...")
    for _ in range(3):
        pg.press('tab')
        time.sleep(0.3)

    print("Pressionando Enter no botão do Gov.br...")
    pg.press('enter')

    print("Aguardando redirecionamento para o Gov.br...")
    time.sleep(7)

    print("Navegando até a opção de Certificado Digital...")
    for _ in range(3):
        pg.press('tab')
        time.sleep(0.3)
    pg.press('enter')

    time.sleep(3)

    print(f"Selecionando o certificado {certificado_nome}...")
    pg.write(certificado_nome, interval=0.1)
    time.sleep(1)

    pg.press('enter')
    time.sleep(3)
    print("Verificando se há mensagens de erro na tela...")
    time.sleep(2)

    for i in range(7):
        pg.press('tab')
        time.sleep(0.2)
    pg.press("enter")
    for i in range(2):
        pg.press('down')
        time.sleep(0.2)
    pg.press('enter')
    # Primeiro move o cursor
    pg.moveTo(x=1465, y=451, duration=1)

    # Depois executa o clique na posição atual
    pg.click()
    pg.write(cnpj)
    time.sleep(0.2)
    pg.press('enter')

    # O layout da SEFAZ pode deslocar o botão alguns pixels conforme DPI/zoom.
    # Mantemos o clique visual configurável e usamos a posição ajustada como
    # padrão para a tela do servidor: o ponto antigo (961, 494) ficava acima
    # do botão Emitir.
    emitir_x = int(os.getenv("SEFAZ_NARRATIVA_EMITIR_X", "961"))
    emitir_y = int(os.getenv("SEFAZ_NARRATIVA_EMITIR_Y", "520"))
    print(f"Clicando no botão Emitir em ({emitir_x}, {emitir_y})...")
    pg.moveTo(x=emitir_x, y=emitir_y, duration=0.5)
    pg.click()
    time.sleep(2)

    for i in range(9):
        pg.press('tab')
        time.sleep(0.2)
    pg.press('enter')
    time.sleep(12)
    # --- FIM DO FLUXO ORIGINAL ---

    print("Lendo o documento exibido no navegador...")
    texto = _ler_texto_visivel_no_chrome()
    texto_path = _salvar_texto_debug(texto, cnpj)

    situacao = _classificar_documento(texto)
    data_emissao = _extrair_data(texto, ("emissão", "emissao", "emitida em", "emitido em"))
    data_validade = _extrair_data(texto, ("validade", "válida até", "valida ate", "vencimento"))

    numero = None
    m_num = re.search(r"(?:N[º°o]?\s*|NÚMERO\s*:?\s*)([A-Z0-9./-]{4,})", texto or "", flags=re.IGNORECASE)
    if m_num:
        numero = m_num.group(1).strip()

    mensagem = "Documento lido no navegador."
    if not texto:
        situacao = "ERRO"
        mensagem = "A página final foi alcançada, mas não foi possível copiar o texto do documento no navegador."

    return {
        "cnpj": cnpj,
        "cnpj_formatado": f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}",
        "tipo_certidao": "Narrativa de Débito Fiscal - SEFAZ",
        "situacao": situacao,
        "status_processamento": "Sucesso" if texto else "Erro técnico",
        "mensagem": mensagem,
        "numero_certidao": numero,
        "data_emissao": data_emissao,
        "data_validade": data_validade,
        "pendencia": situacao == "IRREGULAR",
        "pendencia_detalhes": "Documento indica Certidão Positiva." if situacao == "IRREGULAR" else None,
        "texto_extraido": texto,
        "texto_path": texto_path,
        "nome_original_arquivo": "CertidaoNarrativaDebitoFiscal.txt",
        "arquivo_pdf": None,
        "pdf_path": None,
    }


def executar_automacao_pyautogui(cnpj: str, certificado_nome: str | None = None) -> dict[str, Any]:
    try:
        return _executar_automacao_interna(cnpj, certificado_nome)
    except Exception as exc:
        return {
            "cnpj": re.sub(r"\D", "", cnpj or ""),
            "tipo_certidao": "Narrativa de Débito Fiscal - SEFAZ",
            "situacao": "ERRO",
            "status_processamento": "Erro técnico",
            "mensagem": "A automação Narrativa não conseguiu concluir o fluxo.",
            "erro_tecnico": f"{type(exc).__name__}: {exc}",
            "pendencia": False,
            "origem": "SEFAZ-PE / PyAutoGUI",
        }
    finally:
        _fechar_chrome_completo()
