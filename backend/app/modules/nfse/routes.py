from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.auth.routes import current_user
from app.modules.nfse import service

router = APIRouter(prefix="/api/v1/nfse", tags=["NFS-e"])


class ConsultarRequest(BaseModel):
    origem: str = Field(min_length=2, max_length=2)
    entidade_id: int = Field(gt=0)


class ImportarA3Request(BaseModel):
    origem: str = Field(min_length=2, max_length=2)
    entidade_id: int = Field(gt=0)
    thumbprint_sha256: str = Field(min_length=16, max_length=128)
    content_type: str = "application/json"
    body_b64: str = Field(min_length=1)


@router.get("/contexto")
def contexto(origem: str, entidade_id: int, _user=Depends(current_user)):
    try:
        return service.contexto(origem, entidade_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("")
def listar(origem: str | None = None, entidade_id: int | None = None, limit: int = 100, offset: int = 0, _user=Depends(current_user)):
    documents = service.listar(origem, entidade_id, limit, offset)
    return {"total": len(documents), "nfse": documents}


@router.get("/{nfse_id}")
def detalhe(nfse_id: int, _user=Depends(current_user)):
    try:
        return service.detalhe(nfse_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/consultar")
def consultar(body: ConsultarRequest, _user=Depends(current_user)):
    try:
        return service.consultar_a1(body.origem, body.entidade_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/a3/importar")
def importar_a3(body: ImportarA3Request, _user=Depends(current_user)):
    try:
        return service.importar_resposta_a3(body.origem, body.entidade_id, body.thumbprint_sha256, body.content_type, body.body_b64)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
