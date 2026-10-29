from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.auth.routes import current_user
from . import service

router = APIRouter(
    prefix="/api/v1/dctfweb",
    tags=["DCTFWeb"],
    dependencies=[Depends(current_user)],
)


@router.get("/dashboard")
def dashboard(
    ano: int | None = Query(None, ge=2000, le=2100),
    mes: int | None = Query(None, ge=1, le=12),
):
    try:
        return service.dashboard(ano, mes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Falha de consulta nunca deve virar uma falsa liberação do fechamento.
        raise HTTPException(status_code=500, detail="Não foi possível consultar o fechamento da competência.") from exc
