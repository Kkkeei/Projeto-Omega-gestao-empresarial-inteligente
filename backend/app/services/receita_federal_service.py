import hashlib
import os
import re
import shutil
import time
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.db.database import conectar_banco
from app.services.sefaz_pe_service import limpar_cnpj, formatar_cnpj

PORTAL_URL = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"
BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_ROOT = BASE_DIR.parent / "storage" / "certidoes" / "federal"


def _gui():
    import pyautogui
    import pyperclip
    pyautogui.FAILSAFE = True
    return pyautogui, pyperclip




def _fechar_chrome_completo() -> None:
    """Fecha o Chrome ao final da automação no Windows.

    O fluxo federal usa PyAutoGUI e pode reutilizar uma instância existente do
    Chrome. Para impedir que a sessão gráfica fique presa, encerramos o processo
    ao final. O comportamento é controlado por OMEGA_CLOSE_CHROME_HARD (default=true).
    """
    if os.getenv("OMEGA_CLOSE_CHROME_HARD", "true").strip().lower() not in {"1", "true", "sim", "yes"}:
        return
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True, text=True, timeout=15)
    except Exception:
        pass

def _tipo_federal_id(conexao):
    row = conexao.execute(
        "SELECT id FROM tipos_certidao WHERE nome=? AND ativo=1",
        ("Federal - RFB/PGFN",),
    ).fetchone()
    if not row:
        raise LookupError("Tipo de certidão Federal - RFB/PGFN não cadastrado.")
    return row["id"]


def _classificar(texto: str) -> tuple[str, bool, str | None]:
    t = re.sub(r"\s+", " ", (texto or "").upper()).strip()
    if not t:
        return "NAO DISPONIVEL", False, None
    if "POSITIVA COM EFEITOS DE NEGATIVA" in t or "POSITIVA COM EFEITO DE NEGATIVA" in t:
        return "POSITIVA COM EFEITOS DE NEGATIVA", True, "A certidão indica débitos com efeitos de negativa."
    if "NÃO CONSTA" in t and "DÉBITO" in t:
        return "REGULAR", False, None
    if "REGULARIDADE FISCAL" in t or ("REGULAR" in t and "FISCAL" in t):
        return "REGULAR", False, None
    if "NEGATIVA" in t and "DÉBIT" in t:
        return "NEGATIVA", False, None
    if "POSITIVA" in t or "IRREGULAR" in t or "PENDÊNCIA" in t or "PENDENCIA" in t:
        return "IRREGULAR", True, "O resultado apresentado indica situação fiscal positiva/pendente."
    return "NAO DISPONIVEL", False, "Não foi possível classificar com segurança o resultado da Receita Federal."


def _parse_date(texto: str, label: str) -> str | None:
    padroes = [
        rf"{label}\s*[:\-]?\s*(\d{{2}}[/-]\d{{2}}[/-]\d{{4}})",
        rf"{label}\s*[:\-]?\s*(\d{{4}}[/-]\d{{2}}[/-]\d{{2}})",
    ]
    for p in padroes:
        m = re.search(p, texto or "", flags=re.IGNORECASE)
        if not m:
            continue
        valor = m.group(1).replace("/", "-")
        partes = valor.split("-")
        if len(partes) != 3:
            continue
        return f"{partes[0]}-{partes[1]}-{partes[2]}" if len(partes[0]) == 4 else f"{partes[2]}-{partes[1]}-{partes[0]}"
    return None


def _numero_certidao(texto: str) -> str | None:
    for p in (
        r"(?:N[ÚU]MERO|N[º°O])\s*(?:DA\s+CERTID[ÃA]O)?\s*[:\-]?\s*([A-Z0-9./-]{8,})",
        r"CERTID[ÃA]O\s+N[ÚU]MERO\s*[:\-]?\s*([A-Z0-9./-]{8,})",
    ):
        m = re.search(p, texto or "", flags=re.IGNORECASE)
        if m:
            return m.group(1).strip(" .;,")
    return None


def _copiar_clipboard() -> str:
    pyautogui, pyperclip = _gui()
    pyperclip.copy("")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.5)
    return pyperclip.paste() or ""


def _abrir_chrome() -> None:
    pyautogui, _ = _gui()
    pyautogui.press("win")
    time.sleep(0.8)
    pyautogui.write("chrome", interval=0.06)
    pyautogui.press("enter")
    time.sleep(float(os.getenv("RFB_CHROME_START_WAIT", "4")))


def _abrir_portal() -> None:
    pyautogui, pyperclip = _gui()
    pyautogui.hotkey("ctrl", "l")
    pyperclip.copy(PORTAL_URL)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")
    time.sleep(float(os.getenv("RFB_PAGE_WAIT", "7")))
    _aceitar_cookies()


def _aceitar_cookies() -> None:
    """Tenta dispensar o banner de cookies sem depender de posições de tela.

    A Receita utiliza uma interface web que pode alterar a posição dos controles.
    Na abertura, o banner de consentimento normalmente recebe foco; Enter aceita
    a ação principal. O fluxo é configurável e repetido somente quando solicitado.
    """
    if os.getenv("RFB_ACCEPT_COOKIES", "true").strip().lower() not in {"1", "true", "sim", "yes"}:
        return
    pyautogui, _ = _gui()
    tentativas = int(os.getenv("RFB_COOKIE_ENTER_TRIES", "2"))
    atraso = float(os.getenv("RFB_COOKIE_DELAY", "0.7"))
    for _ in range(max(1, tentativas)):
        pyautogui.press("enter")
        time.sleep(atraso)


def _tab_enter(count: int, delay: float = 0.25) -> None:
    pyautogui, _ = _gui()
    for _ in range(max(0, count)):
        pyautogui.press("tab")
        time.sleep(delay)
    pyautogui.press("enter")


def _digitar_cnpj(cnpj: str) -> None:
    pyautogui, _ = _gui()
    # A navegação 100% PyAutoGUI é configurável por ambiente porque a Receita usa uma SPA e pode alterar a ordem de foco.
    tabs = int(os.getenv("RFB_TABS_TO_CNPJ", "6"))
    _tab_enter(tabs, float(os.getenv("RFB_TAB_DELAY", "0.25")))
    time.sleep(0.5)
    pyautogui.write(cnpj, interval=0.03)
    pyautogui.press("enter")


def _consultar() -> None:
    tabs = int(os.getenv("RFB_TABS_TO_CONSULTAR", "2"))
    _tab_enter(tabs, float(os.getenv("RFB_TAB_DELAY", "0.25")))
    time.sleep(float(os.getenv("RFB_RESULT_WAIT", "6")))


def _texto_tela() -> str:
    """Copia o texto atualmente visível no Chrome."""
    try:
        return _copiar_clipboard()
    except Exception:
        return ""


def _certidao_valida_encontrada(texto: str) -> bool:
    t = re.sub(r"\s+", " ", (texto or "").upper())
    return (
        "CERTIDÃO VÁLIDA ENCONTRADA" in t
        or "CERTIDAO VALIDA ENCONTRADA" in t
        or ("CERTIDÃO" in t and "VÁLIDA" in t and "ENCONTRADA" in t)
        or ("CERTIDAO" in t and "VALIDA" in t and "ENCONTRADA" in t)
    )


def _novos_pdfs(diretorio: Path, desde: float) -> list[Path]:
    if not diretorio.exists():
        return []
    return sorted(
        [p for p in diretorio.glob("*.pdf") if p.is_file() and p.stat().st_mtime >= desde],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _clicar_emitir_nova_certidao() -> bool:
    """Trata o modal 'Certidão válida encontrada'.

    A Receita pode exibir uma certidão ainda válida e bloquear o fluxo com um
    modal. Nesse caso não basta copiar o texto da tela: é necessário escolher
    explicitamente a opção de emissão de uma nova certidão.

    Como o fluxo é PyAutoGUI, evitamos coordenadas fixas. O modal recebe foco e
    a função percorre os controles por TAB, confirmando cada candidato e
    verificando se o modal desapareceu. O número de tentativas é configurável.
    """
    pyautogui, _ = _gui()
    max_tabs = int(os.getenv("RFB_NOVA_CERTIDAO_MAX_TABS", "10"))
    atraso = float(os.getenv("RFB_TAB_DELAY", "0.30"))
    espera = float(os.getenv("RFB_NOVA_CERTIDAO_WAIT", "1.2"))

    # Primeiro posiciona o foco no início do modal. Esc pode fechar alguns
    # overlays, por isso só usamos se explicitamente habilitado.
    if os.getenv("RFB_NOVA_CERTIDAO_ESC", "false").strip().lower() in {"1", "true", "sim", "yes"}:
        pyautogui.press("esc")
        time.sleep(0.4)

    # Em muitas versões o foco já está no primeiro botão do modal.
    for i in range(max_tabs):
        if i:
            pyautogui.press("tab")
            time.sleep(atraso)
        pyautogui.press("enter")
        time.sleep(espera)
        texto = _texto_tela()
        if not _certidao_valida_encontrada(texto):
            return True
    return False


def _salvar_pdf_do_navegador(destino_dir: Path, inicio: float) -> Path | None:
    """Captura PDF baixado automaticamente ou salva o PDF aberto no Chrome."""
    pyautogui, pyperclip = _gui()
    destino_dir.mkdir(parents=True, exist_ok=True)
    downloads = Path.home() / "Downloads"

    # 1) O portal normalmente dispara um download. Não usamos Ctrl+S como
    # primeira opção, pois isso pode salvar HTML da SPA em vez da certidão.
    for _ in range(int(os.getenv("RFB_PDF_DOWNLOAD_POLLS", "20"))):
        encontrados = _novos_pdfs(downloads, inicio)
        if encontrados:
            origem = encontrados[0]
            destino = destino_dir / f"certidao_federal_tmp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
            shutil.copy2(origem, destino)
            return destino
        time.sleep(float(os.getenv("RFB_PDF_DOWNLOAD_POLL", "0.75")))

    # 2) Se a Receita abriu o PDF no próprio navegador, salvamos a visualização
    # em PDF usando Ctrl+S.
    nome = f"certidao_federal_tmp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    destino = destino_dir / nome
    pyautogui.hotkey("ctrl", "s")
    time.sleep(2)
    pyperclip.copy(str(destino))
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")
    time.sleep(float(os.getenv("RFB_SAVE_WAIT", "4")))
    if destino.is_file() and destino.stat().st_size > 0:
        return destino
    return None


def _obter_documento() -> Path | None:
    """Emite uma nova certidão, inclusive quando existe uma certidão válida.

    Fluxo:
      1. detecta o modal 'Certidão válida encontrada';
      2. aciona 'Emissão de nova certidão' por navegação de teclado;
      3. aguarda o PDF real ser baixado;
      4. se o PDF abrir no Chrome, salva a visualização.
    """
    pyautogui, _ = _gui()
    destino_dir = STORAGE_ROOT / "_tmp"
    destino_dir.mkdir(parents=True, exist_ok=True)
    inicio = time.time()

    texto = _texto_tela()
    if _certidao_valida_encontrada(texto):
        if not _clicar_emitir_nova_certidao():
            return None
        time.sleep(float(os.getenv("RFB_AFTER_NOVA_CERTIDAO_WAIT", "2")))

    # Caso o modal não tenha sido capturado pelo clipboard, ainda tentamos o
    # fluxo configurável de tabs para chegar à emissão.
    waits = os.getenv("RFB_DOCUMENT_TAB_TRIES", "3,4,5").split(",")
    for raw in waits:
        try:
            tabs = int(raw.strip())
        except ValueError:
            continue
        pyautogui.press("esc")
        _tab_enter(tabs, float(os.getenv("RFB_TAB_DELAY", "0.25")))
        time.sleep(float(os.getenv("RFB_DOCUMENT_WAIT", "4")))

        # Depois de cada tentativa, se o modal reaparecer, trate-o novamente.
        texto = _texto_tela()
        if _certidao_valida_encontrada(texto):
            if not _clicar_emitir_nova_certidao():
                continue
            time.sleep(float(os.getenv("RFB_AFTER_NOVA_CERTIDAO_WAIT", "2")))

        arquivo = _salvar_pdf_do_navegador(destino_dir, inicio)
        if arquivo:
            return arquivo

    return None


def _executar_pyautogui(cnpj: str) -> dict[str, Any]:
    try:
        _abrir_chrome()
        _abrir_portal()
        _digitar_cnpj(cnpj)
        _consultar()
        # A consulta pode abrir o resultado e deixar o foco em um controle de
        # emissão. Garantimos uma pequena janela para a página estabilizar antes
        # de tentar emitir e capturar o PDF.
        time.sleep(float(os.getenv("RFB_BEFORE_EMIT_WAIT", "1.5")))

        texto = _copiar_clipboard()
        situacao, pendencia, detalhes = _classificar(texto)
        data_emissao = _parse_date(texto, r"data\s+de\s+emiss[aã]o")
        data_validade = _parse_date(texto, r"data\s+de\s+validade|validade")
        numero = _numero_certidao(texto)

        if situacao == "NAO DISPONIVEL":
            return {
                "situacao": "ERRO",
                "status_processamento": "Erro técnico",
                "mensagem": "Não foi possível identificar com segurança o resultado exibido pela Receita Federal.",
                "erro_tecnico": "Resultado não identificável após consulta visual.",
                "pendencia": False,
                "pendencia_detalhes": None,
                "numero_certidao": numero,
                "data_emissao": data_emissao,
                "data_validade": data_validade,
                "arquivo_pdf": None,
                "nome_original_arquivo": None,
                "texto_extraido": texto[:30000],
                "origem": "Consulta Automatizada / PyAutoGUI",
            }

        arquivo = None
        try:
            arquivo = _obter_documento()
        except Exception as exc:
            return {
                "situacao": "ERRO",
                "status_processamento": "Erro técnico",
                "mensagem": "A consulta foi concluída, mas não foi possível capturar o PDF automaticamente.",
                "erro_tecnico": f"Falha ao capturar PDF: {type(exc).__name__}: {exc}",
                "pendencia": False,
                "pendencia_detalhes": None,
                "numero_certidao": numero,
                "data_emissao": data_emissao,
                "data_validade": data_validade,
                "arquivo_pdf": None,
                "nome_original_arquivo": None,
                "texto_extraido": texto[:30000],
                "origem": "Consulta Automatizada / PyAutoGUI",
            }

        if arquivo is None:
            return {
                "situacao": "ERRO",
                "status_processamento": "Erro técnico",
                "mensagem": "A consulta foi concluída, mas o PDF não foi localizado no computador.",
                "erro_tecnico": "Arquivo PDF não encontrado após o comando de salvamento.",
                "pendencia": False,
                "pendencia_detalhes": None,
                "numero_certidao": numero,
                "data_emissao": data_emissao,
                "data_validade": data_validade,
                "arquivo_pdf": None,
                "nome_original_arquivo": None,
                "texto_extraido": texto[:30000],
                "origem": "Consulta Automatizada / PyAutoGUI",
            }

        return {
            "situacao": situacao,
            "status_processamento": "Sucesso",
            "mensagem": None,
            "pendencia": pendencia,
            "pendencia_detalhes": detalhes,
            "numero_certidao": numero,
            "data_emissao": data_emissao,
            "data_validade": data_validade,
            "arquivo_pdf": str(arquivo),
            "nome_original_arquivo": arquivo.name,
            "texto_extraido": texto[:30000],
            "origem": "Consulta Automatizada / PyAutoGUI",
        }
    except Exception as exc:
        return {
            "situacao": "ERRO",
            "status_processamento": "Erro técnico",
            "mensagem": "A automação federal não conseguiu concluir o fluxo.",
            "erro_tecnico": f"{type(exc).__name__}: {exc}",
            "pendencia": False,
            "pendencia_detalhes": None,
            "origem": "Consulta Automatizada / PyAutoGUI",
        }
    finally:
        _fechar_chrome_completo()


def _salvar_pdf(conexao, empresa_id: int, origem: str, nome_original: str) -> tuple[int, str, str]:
    empresa = conexao.execute("SELECT cnpj FROM empresas WHERE id=?", (empresa_id,)).fetchone()
    if not empresa:
        raise LookupError("Empresa não encontrada ao armazenar certidão federal.")
    cnpj = limpar_cnpj(empresa["cnpj"])
    agora = datetime.now()
    pasta = STORAGE_ROOT / cnpj / str(agora.year)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"certidao_{agora.strftime('%Y-%m-%d_%H%M%S_%f')}.pdf"
    shutil.copyfile(origem, destino)
    rel = str(destino.resolve().relative_to(BASE_DIR.parent.resolve()))
    digest = hashlib.sha256(destino.read_bytes()).hexdigest()
    tamanho = destino.stat().st_size

    doc = conexao.execute("SELECT id FROM documentos WHERE empresa_id=? AND tipo=? ORDER BY id DESC LIMIT 1", (empresa_id, "CERTIDAO_FEDERAL_RFB_PGFN")).fetchone()
    if doc:
        doc_id = doc["id"]
        versao = conexao.execute("SELECT COALESCE(MAX(versao),0)+1 AS v FROM documento_versoes WHERE documento_id=?", (doc_id,)).fetchone()["v"]
    else:
        cur = conexao.execute(
            "INSERT INTO documentos (empresa_id,tipo,nome,descricao,categoria,origem) VALUES (?,?,?,?,?,?)",
            (empresa_id, "CERTIDAO_FEDERAL_RFB_PGFN", "Certidão Federal RFB/PGFN", "Certidão de Débitos Relativos a Créditos Tributários Federais e à Dívida Ativa da União", "CERTIDOES", "RFB/PGFN"),
        )
        doc_id = cur.lastrowid
        versao = 1
    conexao.execute(
        "INSERT INTO documento_versoes (documento_id,versao,nome_arquivo,caminho_arquivo,extensao,tamanho,hash_arquivo,origem) VALUES (?,?,?,?,?,?,?,?)",
        (doc_id, versao, nome_original, rel, ".pdf", tamanho, digest, "RFB/PGFN"),
    )
    return doc_id, rel, digest


def _persistir(empresa_id: int, resultado: dict[str, Any]) -> dict[str, Any]:
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT cnpj,razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        tipo_id = _tipo_federal_id(conexao)

        doc_id = None
        pdf_path = None
        if resultado.get("arquivo_pdf"):
            try:
                doc_id, pdf_path, _ = _salvar_pdf(conexao, empresa_id, resultado["arquivo_pdf"], resultado.get("nome_original_arquivo") or "certidao_federal.pdf")
            except Exception as exc:
                resultado["erro_tecnico"] = f"Falha ao armazenar PDF: {exc}"

        situacao = resultado.get("situacao") or "ERRO"
        pendencia = situacao == "IRREGULAR"
        observacao = resultado.get("pendencia_detalhes") or resultado.get("mensagem")

        atual = conexao.execute("SELECT id FROM certidoes WHERE empresa_id=? AND tipo_certidao_id=?", (empresa_id, tipo_id)).fetchone()
        if atual:
            cert_id = atual["id"]
            conexao.execute(
                "UPDATE certidoes SET situacao=?,numero_certidao=?,data_emissao=?,data_validade=?,documento_id=COALESCE(?,documento_id),origem=?,observacao=?,atualizada_em=CURRENT_TIMESTAMP WHERE id=?",
                (situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), doc_id, resultado.get("origem", "RFB/PGFN"), observacao, cert_id),
            )
        else:
            cur = conexao.execute(
                "INSERT INTO certidoes (empresa_id,tipo_certidao_id,situacao,numero_certidao,data_emissao,data_validade,documento_id,origem,observacao) VALUES (?,?,?,?,?,?,?,?,?)",
                (empresa_id, tipo_id, situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), doc_id, resultado.get("origem", "RFB/PGFN"), observacao),
            )
            cert_id = cur.lastrowid

        cur = conexao.execute(
            "INSERT INTO consultas_certidoes (empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,data_emissao,data_validade,pdf_path,origem,mensagem,pendencia,pendencia_detalhes,nome_arquivo_original,status_processamento,erro_tecnico,texto_extraido) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (empresa_id, tipo_id, cert_id, situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), pdf_path, resultado.get("origem", "RFB/PGFN"), resultado.get("mensagem"), 1 if pendencia else 0, resultado.get("pendencia_detalhes"), resultado.get("nome_original_arquivo"), resultado.get("status_processamento"), resultado.get("erro_tecnico"), resultado.get("texto_extraido")),
        )
        consulta_id = cur.lastrowid
        hash_arquivo = None
        if doc_id:
            row_hash = conexao.execute(
                "SELECT hash_arquivo FROM documento_versoes WHERE documento_id=? ORDER BY versao DESC LIMIT 1",
                (doc_id,),
            ).fetchone()
            hash_arquivo = row_hash["hash_arquivo"] if row_hash else None
        conexao.execute(
            "INSERT OR IGNORE INTO certidoes_historico (empresa_id,tipo_certidao_id,certidao_id,consulta_id,situacao,numero_certidao,data_emissao,data_validade,pdf_path,documento_id,hash_arquivo,nome_arquivo_original,status_processamento,erro_tecnico,mensagem,texto_extraido,consultado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (empresa_id, tipo_id, cert_id, consulta_id, situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), pdf_path, doc_id, hash_arquivo, resultado.get("nome_original_arquivo"), resultado.get("status_processamento"), resultado.get("erro_tecnico"), resultado.get("mensagem"), resultado.get("texto_extraido")),
        )

        automacao = conexao.execute(
            "SELECT id FROM automacoes WHERE tipo=? AND ativo=1 ORDER BY id LIMIT 1",
            ("CONSULTA_CERTIDAO_FEDERAL",),
        ).fetchone()
        conexao.execute(
            "INSERT INTO execucoes_automacao (automacao_id,empresa_id,tipo,status,fim,mensagem,erro_tecnico,resultado,origem) VALUES (?,?,?,?,CURRENT_TIMESTAMP,?,?,?,?)",
            (
                automacao["id"] if automacao else None,
                empresa_id,
                "CONSULTA_CERTIDAO_FEDERAL",
                resultado.get("status_processamento") or "Erro",
                resultado.get("mensagem"),
                resultado.get("erro_tecnico"),
                __import__("json").dumps({"situacao": situacao, "pdf_path": pdf_path, "pendencia": pendencia}, ensure_ascii=False),
                resultado.get("origem", "RFB/PGFN / PyAutoGUI"),
            ),
        )
        conexao.commit()

        resultado.update({"empresa": empresa["razao_social"], "cnpj": formatar_cnpj(empresa["cnpj"]), "pendencia": pendencia, "pdf_path": pdf_path, "documento_id": doc_id, "consulta_id": consulta_id})
        return resultado
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


async def _executar_browser(cnpj: str) -> dict[str, Any]:
    return await asyncio.to_thread(_executar_pyautogui, cnpj)


async def consultar_federal(empresa_id: int) -> dict[str, Any]:
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT cnpj FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        cnpj = limpar_cnpj(empresa["cnpj"])
        if len(cnpj) != 14:
            raise ValueError("CNPJ inválido ou não cadastrado corretamente.")
    finally:
        conexao.close()
    try:
        resultado = await _executar_browser(cnpj)
    except Exception as exc:
        resultado = {"situacao": "ERRO", "status_processamento": "Erro", "mensagem": str(exc), "erro_tecnico": str(exc), "origem": "Consulta Automatizada / PyAutoGUI"}
    return _persistir(empresa_id, resultado)
