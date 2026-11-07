from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.v1.auth.routes import current_user
from . import repository, service
from .storage import resolver_caminho_armazenado
from .schemas import (
    ArquivoDelete, ArquivoRename, AtribuicaoLote, CategoriaCreate,
    DocumentoCreate, DocumentoInativar, DocumentoUpdate,
)

router = APIRouter(prefix="/api/v1/contabil", tags=["Contábil"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, repository.ConflictError):
        return HTTPException(409, str(exc))
    if isinstance(exc, LookupError):
        return HTTPException(404, str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(400, str(exc))
    raise exc


@router.get("/status")
def status():
    return service.obter_status_modulo()


@router.get("/dashboard")
def dashboard(competencia: int = Query(...), busca: str | None = None, regime: str | None = None,
              responsavel_id: int | None = Query(None, gt=0), sem_responsavel: bool = False,
              pagina: int = Query(1, ge=1), por_pagina: int = Query(100, ge=1, le=200),
              user=Depends(current_user)):
    try:
        service.validar_competencia(competencia)
        return repository.listar_dashboard(competencia, busca, regime, responsavel_id, sem_responsavel, pagina, por_pagina)
    except Exception as exc: raise _error(exc)


@router.get("/responsaveis")
def responsaveis(user=Depends(current_user)):
    return {"responsaveis": repository.listar_responsaveis()}


@router.get("/empresas")
def empresas(busca: str | None = None, regime: str | None = None, incluir_inativas: bool = False,
             user=Depends(current_user)):
    return {"empresas": repository.listar_empresas(busca, regime, incluir_inativas)}


@router.post("/atribuicoes/lote")
def atribuicoes(data: AtribuicaoLote, user=Depends(current_user)):
    try:
        return {"alteradas": len(data.alteracoes),
                "atribuicoes": repository.atribuicao_lote([item.model_dump() for item in data.alteracoes], user["id"])}
    except Exception as exc: raise _error(exc)


@router.get("/empresas/{empresa_id}/documentacao")
def documentacao(empresa_id: int, competencia: int = Query(...), ano: int = Query(...),
                 user=Depends(current_user)):
    try:
        service.validar_competencia(competencia)
        return repository.documentacao(empresa_id, competencia, ano, user["id"])
    except Exception as exc: raise _error(exc)


@router.get("/empresas/{empresa_id}/historico")
def historico(empresa_id: int, user=Depends(current_user)):
    if not repository.empresa_existe(empresa_id):
        raise HTTPException(404, "Empresa não encontrada.")
    return {"eventos": repository.listar_historico(empresa_id)}


@router.post("/empresas/{empresa_id}/categorias", status_code=201)
def criar_categoria(empresa_id: int, data: CategoriaCreate, user=Depends(current_user)):
    try: return service.criar_categoria(empresa_id, data.nome, data.descricao, user["id"])
    except Exception as exc: raise _error(exc)


@router.patch("/categorias/{categoria_id}")
def atualizar_categoria(categoria_id: int, data: CategoriaCreate, user=Depends(current_user)):
    try: return service.atualizar_categoria(categoria_id, data.nome, data.descricao, user["id"])
    except Exception as exc: raise _error(exc)


@router.delete("/categorias/{categoria_id}")
def arquivar_categoria(categoria_id: int, user=Depends(current_user)):
    try: return service.arquivar_categoria(categoria_id, user["id"])
    except Exception as exc: raise _error(exc)


@router.post("/empresas/{empresa_id}/documentos", status_code=201)
def criar_documento(empresa_id: int, data: DocumentoCreate, user=Depends(current_user)):
    try: return service.criar_documento(empresa_id, data, user["id"])
    except Exception as exc: raise _error(exc)


@router.patch("/documentos/{documento_id}")
def atualizar_documento(documento_id: int, data: DocumentoUpdate, user=Depends(current_user)):
    try: return service.atualizar_documento(documento_id, data, user["id"])
    except Exception as exc: raise _error(exc)


@router.post("/documentos/{documento_id}/inativar")
def inativar_documento(documento_id: int, data: DocumentoInativar, user=Depends(current_user)):
    try: return service.inativar_documento(documento_id, data, user["id"])
    except Exception as exc: raise _error(exc)


@router.get("/obrigacoes/{obrigacao_id}/arquivos")
def arquivos(obrigacao_id: int, user=Depends(current_user)):
    return service.listar_arquivos(obrigacao_id)


@router.post("/obrigacoes/{obrigacao_id}/arquivos")
def upload(obrigacao_id: int, arquivos: list[UploadFile] = File(...), user=Depends(current_user)):
    try: return service.upload_arquivos(obrigacao_id, arquivos, user["id"])
    except Exception as exc: raise _error(exc)


@router.patch("/arquivos/{arquivo_id}")
def renomear(arquivo_id: int, data: ArquivoRename, user=Depends(current_user)):
    try: return service.renomear_arquivo(arquivo_id, data.nome, user["id"])
    except Exception as exc: raise _error(exc)


@router.delete("/arquivos/{arquivo_id}")
def excluir(arquivo_id: int, data: ArquivoDelete | None = None, user=Depends(current_user)):
    try: return service.excluir_arquivo(arquivo_id, data.motivo if data else None, user["id"])
    except Exception as exc: raise _error(exc)


@router.get("/arquivos/{arquivo_id}/download")
def download(arquivo_id: int, user=Depends(current_user)):
    row = service.obter_arquivo(arquivo_id)
    if not row: raise HTTPException(404, "Arquivo não encontrado.")
    try:
        path = resolver_caminho_armazenado(row["caminho_storage"])
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    if not path.is_file(): raise HTTPException(404, "Arquivo físico não encontrado.")
    return FileResponse(path, media_type=row["mime_type"] or "application/octet-stream", filename=row["nome_original"])
