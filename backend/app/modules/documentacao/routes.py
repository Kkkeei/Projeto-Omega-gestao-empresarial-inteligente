from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.v1.auth.routes import current_user
from app.modules.documentacao.schemas import CategoriaCreate
from app.modules.documentacao import service

router = APIRouter(prefix="/api/v1/documentacao", tags=["Documentação"])


def _user(user=Depends(current_user)):
    return user


@router.get("/empresas")
def empresas(q: str | None = Query(default=None), regime: str | None = Query(default=None), ativo: bool | None = Query(default=None), page: int = Query(default=1, ge=1), page_size: int = Query(default=200, ge=1, le=200), _user=Depends(_user)):
    return service.listar_empresas_documentacao(q, regime, ativo, page, page_size)


@router.get("/empresas/{empresa_id}/categorias")
def categorias(empresa_id: int, _user=Depends(_user)):
    try:
        return {"categorias": service.listar_categorias(empresa_id)}
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/empresas/{empresa_id}/categorias", status_code=201)
def categoria_criar(empresa_id: int, data: CategoriaCreate, _user=Depends(_user)):
    try:
        return service.criar_categoria(empresa_id, data.nome, data.descricao, data.categoria_pai_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.delete("/categorias/{categoria_id}")
def categoria_arquivar(categoria_id: int, _user=Depends(_user)):
    try:
        return service.arquivar_categoria(categoria_id, _user["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.get("/empresas/{empresa_id}/documentos")
def documentos(empresa_id: int, categoria_id: int | None = Query(default=None), _user=Depends(_user)):
    try:
        return {"documentos": service.listar_documentos(empresa_id, categoria_id)}
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/empresas/{empresa_id}/documentos/upload", status_code=201)
async def upload_documento(
    empresa_id: int,
    categoria_id: int = Form(...),
    nome_documento: str = Form(...),
    observacao: str | None = Form(default=None),
    arquivo: UploadFile = File(...),
    user=Depends(_user),
):
    try:
        return service.upload_documento(empresa_id, categoria_id, nome_documento, arquivo, user["id"], observacao)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.delete("/documentos/{documento_id}")
def documento_arquivar(documento_id: int, _user=Depends(_user)):
    try:
        return service.arquivar_documento(documento_id, _user["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.get("/documentos/{documento_id}")
def documento(documento_id: int, _user=Depends(_user)):
    try:
        return service.documento_por_id(documento_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.get("/documentos/{documento_id}/versoes")
def versoes(documento_id: int, _user=Depends(_user)):
    try:
        return {"versoes": service.listar_versoes(documento_id)}
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/documentos/{documento_id}/versoes", status_code=201)
async def nova_versao(documento_id: int, observacao: str | None = Form(default=None), arquivo: UploadFile = File(...), user=Depends(_user)):
    try:
        return service.nova_versao(documento_id, arquivo, user["id"], observacao)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _file_response(versao_id: int, inline: bool):
    try:
        row = service.arquivo_versao(versao_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    root = Path(service.BASE_DIR.parent).resolve()
    path = (root / row["caminho_arquivo"]).resolve()
    if root not in path.parents or not path.exists():
        raise HTTPException(404, "Arquivo físico não encontrado.")
    media = row.get("mime_type") or "application/octet-stream"
    disposition = "inline" if inline else "attachment"
    return FileResponse(path, media_type=media, filename=row.get("nome_arquivo") or path.name, content_disposition_type=disposition)


@router.get("/versoes/{versao_id}/visualizar")
def visualizar(versao_id: int, _user=Depends(_user)):
    return _file_response(versao_id, True)


@router.get("/versoes/{versao_id}/download")
def baixar(versao_id: int, _user=Depends(_user)):
    return _file_response(versao_id, False)
