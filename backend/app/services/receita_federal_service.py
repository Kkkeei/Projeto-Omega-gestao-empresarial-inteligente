import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from app.db.database import conectar_banco, backup_banco_permanente
from app.services.sefaz_pe_service import limpar_cnpj, formatar_cnpj

PORTAL_URL = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"
BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_ROOT = BASE_DIR.parent / "storage" / "certidoes" / "federal"


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

    # Ordem intencional: termos específicos antes dos genéricos.
    if "POSITIVA COM EFEITOS DE NEGATIVA" in t or "POSITIVA COM EFEITO DE NEGATIVA" in t:
        return "POSITIVA COM EFEITOS DE NEGATIVA", True, "A certidão indica existência de débitos com efeitos de negativa."
    if "NÃO CONSTA" in t and "DÉBITO" in t:
        return "REGULAR", False, None
    if "REGULAR" in t and "FISCAL" in t and "PEND" not in t:
        return "REGULAR", False, None
    if "NEGATIVA" in t and "DÉBITOS" in t:
        return "NEGATIVA", False, None
    if "POSITIVA" in t:
        return "IRREGULAR", True, "A certidão indica situação positiva/irregular."
    if "DÉBITO" in t and any(x in t for x in ("PENDÊNCIA", "PENDENCIA", "IRREGULAR")):
        return "IRREGULAR", True, "Foram identificados indícios de pendência fiscal no documento/resultado."
    return "NAO DISPONIVEL", False, "Não foi possível classificar com segurança o resultado da Receita Federal."


def _parse_date(texto: str, label: str) -> str | None:
    padroes = [
        rf"{label}\s*[:\-]?\s*(\d{{2}}[/-]\d{{2}}[/-]\d{{4}})",
        rf"{label}\s*[:\-]?\s*(\d{{4}}[/-]\d{{2}}[/-]\d{{2}})",
    ]
    for p in padroes:
        m = re.search(p, texto, flags=re.IGNORECASE)
        if not m:
            continue
        valor = m.group(1).replace("/", "-")
        partes = valor.split("-")
        try:
            if len(partes[0]) == 4:
                return f"{partes[0]}-{partes[1]}-{partes[2]}"
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        except Exception:
            return None
    return None


def _numero_certidao(texto: str) -> str | None:
    padroes = [
        r"(?:N[ÚU]MERO|N[º°O]|Nº)\s*(?:DA\s+CERTID[ÃA]O)?\s*[:\-]?\s*([A-Z0-9./-]{8,})",
        r"CERTID[ÃA]O\s+N[ÚU]MERO\s*[:\-]?\s*([A-Z0-9./-]{8,})",
    ]
    for p in padroes:
        m = re.search(p, texto, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip(" .;,")
    return None


def _extract_texto(page) -> str:
    return page.locator("body").inner_text(timeout=15000)


async def _fill_cnpj(page, cnpj: str):
    candidatos = [
        "input[placeholder*='CNPJ' i]",
        "input[name*='cnpj' i]",
        "input[id*='cnpj' i]",
        "input[aria-label*='CNPJ' i]",
        "input[inputmode='numeric']",
        "input[type='text']",
    ]
    for seletor in candidatos:
        loc = page.locator(seletor).first
        try:
            if await loc.is_visible(timeout=1200):
                await loc.fill(cnpj)
                return True
        except Exception:
            continue
    return False


async def _click_consultar(page):
    # Não depender de um único seletor: portal Angular pode mudar texto/atributo.
    candidatos = [
        page.get_by_role("button", name=re.compile(r"consultar|pesquisar|emitir", re.I)).first,
        page.get_by_text(re.compile(r"consultar|pesquisar", re.I)).first,
        page.locator("button[type='submit']").first,
        page.locator("input[type='submit']").first,
    ]
    for loc in candidatos:
        try:
            if await loc.is_visible(timeout=1200):
                await loc.click()
                return True
        except Exception:
            continue
    return False


async def _download_documento(page) -> tuple[str | None, str | None]:
    # Tenta capturar download a partir de botão/link de emissão/baixar/visualizar.
    candidatos = [
        page.get_by_role("link", name=re.compile(r"baixar|download|visualizar|certid", re.I)).first,
        page.get_by_role("button", name=re.compile(r"baixar|download|visualizar|certid", re.I)).first,
        page.get_by_text(re.compile(r"baixar|download|visualizar", re.I)).first,
    ]
    for loc in candidatos:
        try:
            if not await loc.is_visible(timeout=1200):
                continue
            try:
                async with page.expect_download(timeout=8000) as info:
                    await loc.click()
                download = await info.value
                tmp = await download.path()
                if tmp:
                    nome = download.suggested_filename or "certidao_federal.pdf"
                    return str(tmp), nome
            except Exception:
                await loc.click()
                await page.wait_for_timeout(1500)
                # Se abrir PDF em nova aba, procura pelo contexto atual.
                if page.url.lower().endswith(".pdf") or "pdf" in page.url.lower():
                    return None, Path(page.url.split("?")[0]).name or "certidao_federal.pdf"
        except Exception:
            continue
    return None, None


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
    tamanho = destino.stat().st_size
    digest = hashlib.sha256(destino.read_bytes()).hexdigest()

    doc = conexao.execute(
        "SELECT id FROM documentos WHERE empresa_id=? AND tipo=? ORDER BY id DESC LIMIT 1",
        (empresa_id, "CERTIDAO_FEDERAL_RFB_PGFN"),
    ).fetchone()
    if doc:
        doc_id = doc["id"]
        versao = conexao.execute(
            "SELECT COALESCE(MAX(versao),0)+1 AS v FROM documento_versoes WHERE documento_id=?",
            (doc_id,),
        ).fetchone()["v"]
    else:
        cur = conexao.execute(
            "INSERT INTO documentos (empresa_id,tipo,nome,descricao,categoria,origem) VALUES (?,?,?,?,?,?)",
            (empresa_id, "CERTIDAO_FEDERAL_RFB_PGFN", "Certidão Federal RFB/PGFN", "Certidão de Débitos Relativos a Créditos Tributários Federais e à Dívida Ativa da União", "CERTIDOES", "RFB/PGFN"),
        )
        doc_id = cur.lastrowid
        versao = 1
    conexao.execute(
        """INSERT INTO documento_versoes
        (documento_id,versao,nome_arquivo,caminho_arquivo,extensao,tamanho,hash_arquivo,origem)
        VALUES (?,?,?,?,?,?,?,?)""",
        (doc_id, versao, nome_original, rel, ".pdf", tamanho, digest, "RFB/PGFN"),
    )
    return doc_id, rel, digest


def _persistir(empresa_id: int, resultado: dict) -> dict:
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
                doc_id, pdf_path, _ = _salvar_pdf(
                    conexao, empresa_id, resultado["arquivo_pdf"], resultado.get("nome_original_arquivo") or "certidao_federal.pdf"
                )
            except Exception as exc:
                resultado["erro_tecnico"] = f"Falha ao armazenar PDF: {exc}"

        situacao = resultado.get("situacao") or "ERRO"
        pendencia = situacao == "IRREGULAR"
        observacao = resultado.get("pendencia_detalhes") or resultado.get("mensagem")

        atual = conexao.execute(
            "SELECT id FROM certidoes WHERE empresa_id=? AND tipo_certidao_id=?",
            (empresa_id, tipo_id),
        ).fetchone()
        if atual:
            cert_id = atual["id"]
            conexao.execute(
                """UPDATE certidoes SET situacao=?,numero_certidao=?,data_emissao=?,data_validade=?,documento_id=COALESCE(?,documento_id),origem=?,observacao=?,atualizada_em=CURRENT_TIMESTAMP WHERE id=?""",
                (situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), doc_id, "RFB/PGFN", observacao, cert_id),
            )
        else:
            cur = conexao.execute(
                """INSERT INTO certidoes (empresa_id,tipo_certidao_id,situacao,numero_certidao,data_emissao,data_validade,documento_id,origem,observacao) VALUES (?,?,?,?,?,?,?,?,?)""",
                (empresa_id, tipo_id, situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), doc_id, "RFB/PGFN", observacao),
            )
            cert_id = cur.lastrowid

        cur = conexao.execute(
            """INSERT INTO consultas_certidoes
            (empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,data_emissao,data_validade,pdf_path,origem,mensagem,pendencia,pendencia_detalhes,nome_arquivo_original,status_processamento,erro_tecnico,texto_extraido)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id, tipo_id, cert_id, situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), pdf_path, "RFB/PGFN", resultado.get("mensagem"), 1 if pendencia else 0, resultado.get("pendencia_detalhes"), resultado.get("nome_original_arquivo"), resultado.get("status_processamento"), resultado.get("erro_tecnico"), resultado.get("texto_extraido")),
        )
        consulta_id = cur.lastrowid

        # O banco atual tem trigger/apêndice de histórico. Inserimos o snapshot diretamente.
        conexao.execute(
            """INSERT INTO certidoes_historico
            (consulta_id,empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,data_emissao,data_validade,pdf_path,documento_id,hash_arquivo,nome_arquivo_original,status_processamento,erro_tecnico,mensagem,texto_extraido,consultado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (consulta_id, empresa_id, tipo_id, cert_id, situacao, resultado.get("numero_certidao"), resultado.get("data_emissao"), resultado.get("data_validade"), pdf_path, doc_id, resultado.get("hash_arquivo"), resultado.get("nome_original_arquivo"), resultado.get("status_processamento"), resultado.get("erro_tecnico"), resultado.get("mensagem"), resultado.get("texto_extraido")),
        )

        automacao = conexao.execute(
            "SELECT id FROM automacoes WHERE tipo='CONSULTA_CERTIDAO_FEDERAL' AND ativo=1 ORDER BY id LIMIT 1"
        ).fetchone()
        conexao.execute(
            """INSERT INTO execucoes_automacao
            (automacao_id,empresa_id,tipo,status,fim,mensagem,erro_tecnico,resultado,origem)
            VALUES (?,?,?,?,CURRENT_TIMESTAMP,?,?,?,?)""",
            (automacao["id"] if automacao else None, empresa_id, "CONSULTA_CERTIDAO_FEDERAL", resultado.get("status_processamento") or "ERRO", resultado.get("mensagem"), resultado.get("erro_tecnico"), json.dumps({"situacao": situacao, "pdf_path": pdf_path, "consulta_id": consulta_id}, ensure_ascii=False), "RFB/PGFN"),
        )

        if pendencia:
            aberta = conexao.execute(
                "SELECT id FROM pendencias WHERE empresa_id=? AND tipo='CERTIDAO_FEDERAL' AND status <> 'RESOLVIDA' ORDER BY id DESC LIMIT 1",
                (empresa_id,),
            ).fetchone()
            descricao = resultado.get("pendencia_detalhes") or "A Certidão Federal indica situação positiva/irregular."
            if aberta:
                conexao.execute("UPDATE pendencias SET descricao=?,prioridade='ALTA',atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (descricao, aberta["id"]))
            else:
                conexao.execute("""INSERT INTO pendencias (empresa_id,tipo,origem,titulo,descricao,status,prioridade,data_identificacao) VALUES (?,?,?,?,?,?,?,DATE('now'))""", (empresa_id, "CERTIDAO_FEDERAL", "RFB/PGFN", "Pendência na Certidão Federal", descricao, "ABERTA", "ALTA"))
        else:
            conexao.execute("UPDATE pendencias SET status='RESOLVIDA',data_resolucao=DATE('now'),atualizado_em=CURRENT_TIMESTAMP WHERE empresa_id=? AND tipo='CERTIDAO_FEDERAL' AND status <> 'RESOLVIDA'", (empresa_id,))

        conexao.commit()
        backup_banco_permanente()
        resultado["consulta_id"] = consulta_id
        resultado["certidao_id"] = cert_id
        resultado["documento_id"] = doc_id
        resultado["pdf_path"] = pdf_path
        resultado["empresa_id"] = empresa_id
        resultado["empresa"] = empresa["razao_social"]
        resultado["cnpj"] = formatar_cnpj(empresa["cnpj"])
        resultado["pendencia"] = pendencia
        return resultado
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


async def _executar_browser(cnpj: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2500)

            preenchido = await _fill_cnpj(page, cnpj)
            if not preenchido:
                # Não finge sucesso: devolve diagnóstico para intervenção.
                texto = await _extract_texto(page)
                return {"situacao": "AGUARDANDO_INTERVENCAO", "status_processamento": "Aguardando intervenção", "mensagem": "O campo CNPJ da Receita Federal não foi localizado automaticamente.", "texto_extraido": texto[:20000]}

            if not await _click_consultar(page):
                texto = await _extract_texto(page)
                return {"situacao": "AGUARDANDO_INTERVENCAO", "status_processamento": "Aguardando intervenção", "mensagem": "O botão de consulta da Receita Federal não foi localizado automaticamente.", "texto_extraido": texto[:20000]}

            await page.wait_for_timeout(2500)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            texto = await _extract_texto(page)

            # Dá alguns segundos para conteúdo Angular ser atualizado.
            for _ in range(4):
                situacao, _, _ = _classificar(texto)
                if situacao != "NAO DISPONIVEL":
                    break
                await page.wait_for_timeout(1500)
                texto = await _extract_texto(page)

            situacao, pendencia, detalhes = _classificar(texto)
            data_emissao = _parse_date(texto, r"data\s+de\s+emiss[aã]o")
            data_validade = _parse_date(texto, r"validade|data\s+de\s+validade")
            numero = _numero_certidao(texto)
            arquivo, nome = await _download_documento(page)

            if arquivo and os.path.isfile(arquivo):
                return {
                    "situacao": situacao if situacao != "NAO DISPONIVEL" else "AGUARDANDO_INTERVENCAO",
                    "status_processamento": "Sucesso",
                    "mensagem": None,
                    "pendencia": pendencia,
                    "pendencia_detalhes": detalhes,
                    "numero_certidao": numero,
                    "data_emissao": data_emissao,
                    "data_validade": data_validade,
                    "arquivo_pdf": arquivo,
                    "nome_original_arquivo": nome,
                    "texto_extraido": texto[:30000],
                }

            # Sem PDF: ainda preservamos o resultado textual e pedimos intervenção.
            return {
                "situacao": situacao if situacao != "NAO DISPONIVEL" else "AGUARDANDO_INTERVENCAO",
                "status_processamento": "Aguardando intervenção",
                "mensagem": "Resultado localizado, mas o documento PDF não foi capturado automaticamente.",
                "pendencia": pendencia,
                "pendencia_detalhes": detalhes,
                "numero_certidao": numero,
                "data_emissao": data_emissao,
                "data_validade": data_validade,
                "texto_extraido": texto[:30000],
            }
        except PlaywrightTimeoutError as exc:
            return {"situacao": "ERRO", "status_processamento": "Erro", "mensagem": f"Tempo limite na Receita Federal: {exc}", "erro_tecnico": str(exc)}
        except Exception as exc:
            return {"situacao": "ERRO", "status_processamento": "Erro", "mensagem": str(exc), "erro_tecnico": str(exc)}
        finally:
            await context.close()
            await browser.close()


async def consultar_federal(empresa_id: int) -> dict:
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT cnpj,razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        cnpj = limpar_cnpj(empresa["cnpj"])
        if len(cnpj) != 14:
            raise ValueError("CNPJ inválido ou não cadastrado corretamente.")
    finally:
        conexao.close()

    resultado = await _executar_browser(cnpj)
    return _persistir(empresa_id, resultado)
