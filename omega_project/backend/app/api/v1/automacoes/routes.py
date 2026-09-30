from fastapi import APIRouter, HTTPException, Query
from app.schemas.automacoes import AutomacaoExecutar
from app.services.automacoes_service import executar, historico

router = APIRouter(prefix="/api/v1/automacoes", tags=["Automações"])


@router.post("/executar")
def executar_automacao(dados: AutomacaoExecutar):
    try:
        return executar(dados.model_dump())
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/executar/{tipo}")
def executar_tipo(tipo: str, empresa_id: int | None = Query(default=None)):
    try:
        return executar({"tipo": tipo, "empresa_id": empresa_id})
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/execucoes")
def execucoes(empresa_id: int | None = Query(default=None)):
    itens = historico(empresa_id)
    return {"total": len(itens), "execucoes": itens}
