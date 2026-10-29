import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.db.database import conectar_banco

from app.schemas.certidoes import CertidaoCreate
from app.services.receita_federal_service import consultar_federal
from app.services.automation_lock import AutomationBusyError, lock_automacao, status_automacao
from app.services.certidoes_service import (
    consultar_estadual,
    consultar_estadual_todas,
    consultar_narrativa_pyautogui,
    historico,
    listar,
    obter_pdf_path,
    registrar,
    tipos,
)

logger = logging.getLogger("omega.certidoes")

router = APIRouter(prefix="/api/v1/certidoes", tags=["Certidões"])

def _sanitizar_resultado_certidao(valor):
    """Remove caminhos locais, texto fiscal integral e exceções internas das respostas HTTP."""
    if isinstance(valor, list):
        return [_sanitizar_resultado_certidao(item) for item in valor]
    if not isinstance(valor, dict):
        return valor

    resultado = dict(valor)
    pdf_path = resultado.pop("pdf_path", None)
    if "pdf_disponivel" not in resultado and (
        "consulta_id" in resultado or "pdf_path" in valor or "documento_id" in resultado
    ):
        resultado["pdf_disponivel"] = bool(pdf_path)

    for campo in ("arquivo_pdf", "texto_extraido", "erro_tecnico", "situacao_detectada"):
        resultado.pop(campo, None)

    if isinstance(resultado.get("resultados"), list):
        resultado["resultados"] = _sanitizar_resultado_certidao(resultado["resultados"])

    situacao = str(resultado.get("situacao") or "").upper()
    status = str(resultado.get("status_processamento") or "").upper()
    if situacao == "ERRO" or status.startswith("ERRO"):
        mensagem = str(resultado.get("mensagem") or "")
        mensagens_seguras = (
            "Não foi possível concluir",
            "A consulta falhou",
            "O portal retornou um resultado, mas o PDF",
            "O PDF da certidão narrativa",
            "A automação não conseguiu",
            "A automação foi encerrada",
            "A consulta foi concluída, mas",
        )
        if not any(mensagem.startswith(prefixo) for prefixo in mensagens_seguras):
            resultado["mensagem"] = (
                "A consulta não foi concluída com segurança. "
                "Consulte o histórico e os logs do servidor antes de repetir a operação."
            )
    return resultado



@router.get("")
def listar_certidoes(empresa_id: int | None = Query(default=None)):
    itens = listar(empresa_id)
    return _sanitizar_resultado_certidao({"total": len(itens), "certidoes": itens})


@router.get("/tipos")
def listar_tipos():
    return {"total": len(tipos()), "tipos": tipos()}


@router.post("", status_code=201)
def registrar_certidao(dados: CertidaoCreate):
    try:
        return _sanitizar_resultado_certidao(registrar(dados.model_dump()))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/estadual/consultar/{empresa_id}")
async def consultar_certidao_estadual(empresa_id: int):
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
    finally:
        conexao.close()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    try:
        async with lock_automacao("CONSULTA_CERTIDAO_ESTADUAL", empresa_id, empresa["razao_social"]):
            return _sanitizar_resultado_certidao(await consultar_estadual(empresa_id))
    except AutomationBusyError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Não foi possível concluir a consulta na SEFAZ-PE.") from exc


@router.post("/federal/consultar/{empresa_id}")
async def consultar_certidao_federal(empresa_id: int):
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
    finally:
        conexao.close()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    try:
        async with lock_automacao("CONSULTA_CERTIDAO_FEDERAL", empresa_id, empresa["razao_social"]):
            return _sanitizar_resultado_certidao(await consultar_federal(empresa_id))
    except AutomationBusyError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Não foi possível concluir a consulta da Certidão Federal RFB/PGFN.") from exc


@router.post("/narrativa/consultar/{empresa_id}")
async def consultar_certidao_narrativa(empresa_id: int, certificado_nome: str | None = Query(default=None)):
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
    finally:
        conexao.close()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    try:
        async with lock_automacao("CONSULTA_CERTIDAO_NARRATIVA", empresa_id, empresa["razao_social"]):
            # PyAutoGUI é bloqueante e precisa da sessão gráfica do Windows;
            # executamos em thread para não travar o event loop do FastAPI.
            return _sanitizar_resultado_certidao(await asyncio.to_thread(consultar_narrativa_pyautogui, empresa_id, certificado_nome))
    except AutomationBusyError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Não foi possível concluir a Certidão Narrativa de Débito Fiscal na SEFAZ-PE.") from exc


@router.post("/estadual/consultar-todas")
async def consultar_todas_certidoes_estaduais():
    try:
        async with lock_automacao("CONSULTA_CERTIDOES_ESTADUAIS_LOTE", None, "Todas as empresas ativas"):
            return _sanitizar_resultado_certidao(await consultar_estadual_todas())
    except AutomationBusyError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except Exception:
        logger.exception("Falha inesperada na consulta em lote de certidões estaduais.")
        raise HTTPException(
            status_code=500,
            detail="Não foi possível concluir o processamento em lote. Consulte os logs do servidor.",
        )


@router.get("/estadual/empresa/{empresa_id}")
def certidao_estadual_atual(empresa_id: int):
    itens = listar(empresa_id)
    item = next((x for x in itens if x.get("tipo_certidao") == "Estadual - SEFAZ"), None)
    if not item:
        raise HTTPException(status_code=404, detail="Certidão Estadual não encontrada.")
    return _sanitizar_resultado_certidao(item)


@router.get("/estadual/empresa/{empresa_id}/historico")
def historico_estadual(empresa_id: int):
    conexao_itens = historico(empresa_id)
    itens = [x for x in conexao_itens if x.get("tipo_certidao") == "Estadual - SEFAZ"]
    return _sanitizar_resultado_certidao({"total": len(itens), "historico": itens})


@router.get("/automacao/status")
async def status_automacao_certidoes():
    return await status_automacao()


@router.get("/pdf")
def visualizar_pdf(path: str, download: bool = False):
    try:
        arquivo = obter_pdf_path(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not arquivo.is_file() or arquivo.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF não encontrado.")
    headers = {"Content-Disposition": f'attachment; filename="{arquivo.name}"'} if download else None
    return FileResponse(arquivo, media_type="application/pdf", filename=arquivo.name, headers=headers)


@router.get("/pdf/consulta/{consulta_id}")
def visualizar_pdf_consulta(consulta_id: int, download: bool = False):
    conexao = conectar_banco()
    try:
        linha = conexao.execute(
            "SELECT pdf_path FROM consultas_certidoes WHERE id=?",
            (consulta_id,),
        ).fetchone()
    finally:
        conexao.close()
    if not linha or not linha["pdf_path"]:
        raise HTTPException(status_code=404, detail="PDF não encontrado para esta consulta.")
    try:
        arquivo = obter_pdf_path(linha["pdf_path"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="O PDF não está em um diretório de certidões permitido.") from exc
    if not arquivo.is_file() or arquivo.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF não encontrado no armazenamento.")
    headers = {"Content-Disposition": f'attachment; filename="{arquivo.name}"'} if download else None
    return FileResponse(arquivo, media_type="application/pdf", filename=arquivo.name, headers=headers)


@router.get("/{certidao_id}")
def consultar_certidao(certidao_id: int):
    itens = listar()
    for item in itens:
        if item["id"] == certidao_id:
            return _sanitizar_resultado_certidao(item)
    raise HTTPException(status_code=404, detail="Certidão não encontrada.")


@router.get("/empresa/{empresa_id}/historico")
def historico_certidoes(empresa_id: int, tipo_certidao_id: int | None = Query(default=None)):
    itens = historico(empresa_id, tipo_certidao_id)
    return _sanitizar_resultado_certidao({"total": len(itens), "historico": itens})
