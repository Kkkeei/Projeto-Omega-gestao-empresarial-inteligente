from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
import asyncio

from app.api.v1.auth.routes import current_user
from app.db.database import BASE_DIR, STORAGE_BASE
from app.modules.documentacao.schemas import CategoriaCreate, CategoriaUpdate
from app.modules.documentacao import service

router = APIRouter(prefix="/api/v1/documentacao", tags=["Documentação"])


def _user(user=Depends(current_user)):
    return user


@router.get("/empresas")
def empresas(q: str | None = Query(default=None), regime: str | None = Query(default=None), ativo: bool | None = Query(default=None), page: int = Query(default=1, ge=1), page_size: int = Query(default=500, ge=1, le=500), _user=Depends(_user)):
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


@router.put("/categorias/{categoria_id}")
def categoria_atualizar(categoria_id: int, data: CategoriaUpdate, _user=Depends(_user)):
    try:
        return service.atualizar_categoria(categoria_id, data.nome, data.descricao, _user["id"])
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
        return await asyncio.to_thread(service.upload_documento, empresa_id, categoria_id, nome_documento, arquivo, user["id"], observacao)
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
        return await asyncio.to_thread(service.nova_versao, documento_id, arquivo, user["id"], observacao)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _file_response(versao_id: int, inline: bool, user_id: int | None = None):
    try:
        row = service.arquivo_versao(versao_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    storage_root = STORAGE_BASE.resolve()
    project_root = BASE_DIR.parent.resolve()
    raw_path = Path(str(row.get("caminho_arquivo") or ""))
    if raw_path.is_absolute():
        path = raw_path.resolve()
    else:
        candidates = [(project_root / raw_path).resolve(), (storage_root / raw_path).resolve()]
        path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    if not path.exists():
        raise HTTPException(404, "Arquivo físico não encontrado.")
    try:
        path.relative_to(storage_root)
    except ValueError:
        raise HTTPException(404, "Arquivo fora do armazenamento permitido.")
    media = row.get("mime_type") or "application/octet-stream"
    safe_inline = inline and media in {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"}
    disposition = "inline" if safe_inline else "attachment"
    service.registrar_acesso_arquivo(versao_id, user_id, "VISUALIZAR" if inline else "DOWNLOAD")
    return FileResponse(path, media_type=media, filename=row.get("nome_arquivo") or path.name, content_disposition_type=disposition)


@router.get("/versoes/{versao_id}/visualizar")
def visualizar(versao_id: int, _user=Depends(_user)):
    return _file_response(versao_id, True, _user["id"])


@router.get("/versoes/{versao_id}/download")
def baixar(versao_id: int, _user=Depends(_user)):
    return _file_response(versao_id, False, _user["id"])
