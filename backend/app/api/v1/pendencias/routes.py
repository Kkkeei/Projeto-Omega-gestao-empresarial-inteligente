from fastapi import APIRouter, HTTPException, Query
from app.schemas.pendencias import PendenciaCreate, PendenciaUpdate
from app.services.pendencias_service import listar, criar, atualizar

router = APIRouter(prefix="/api/v1/pendencias", tags=["Pendências"])


@router.get("")
def listar_pendencias(empresa_id: int | None = Query(default=None), status: str | None = Query(default=None)):
    itens = listar(empresa_id, status)
    return {"total": len(itens), "pendencias": itens}


@router.post("", status_code=201)
def criar_pendencia(dados: PendenciaCreate):
    try:
        return criar(dados.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{pendencia_id}")
def atualizar_pendencia(pendencia_id: int, dados: PendenciaUpdate):
    try:
        return atualizar(pendencia_id, dados.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
