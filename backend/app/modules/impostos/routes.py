from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.auth.routes import current_user
from . import repository, service
from .schemas import ImpostoMensalCreate, TributoCreate, TributoUpdate, VinculoTributoCreate

router = APIRouter(prefix="/api/v1/impostos", tags=["Impostos"], dependencies=[Depends(current_user)])


@router.get("/dashboard")
def dashboard(
    q: str | None = Query(default=None),
    regime: str | None = Query(default=None),
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
):
    return service.dashboard(q, regime, ano, mes)


@router.get("/tributos")
def listar_tributos():
    return {"tributos": repository.listar_tributos()}


@router.post("/tributos", status_code=201)
def criar_tributo(data: TributoCreate):
    try:
        return repository.criar_tributo(data.model_dump())
    except Exception as exc:
        msg = str(exc)
        if "UNIQUE" in msg or "unique" in msg:
            raise HTTPException(409, "Já existe um tributo com esse nome.") from exc
        raise HTTPException(400, "Não foi possível cadastrar o tributo.") from exc


@router.put("/tributos/{tributo_id}")
def atualizar_tributo(tributo_id: int, data: TributoUpdate):
    from app.db.database import conectar_banco

    conn = conectar_banco()
    try:
        cur = conn.execute(
            "UPDATE tributos SET nome=?, sigla=?, esfera=?, categoria=?, periodicidade=?, descricao=?, ativo=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (data.nome.strip(), data.sigla, data.esfera, data.categoria, data.periodicidade, data.descricao, int(data.ativo), tributo_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Tributo não encontrado.")
        conn.commit()
        row = conn.execute("SELECT * FROM tributos WHERE id=?", (tributo_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()


@router.get("/empresas/{empresa_id}")
def detalhe_empresa(
    empresa_id: int,
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
):
    try:
        return service.detalhe_empresa(empresa_id, ano, mes)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/empresas/{empresa_id}/tributos", status_code=201)
def vincular_tributo(empresa_id: int, data: VinculoTributoCreate):
    try:
        return repository.vincular_tributo(empresa_id, data.model_dump(mode="json"))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, "Não foi possível vincular o tributo.") from exc


@router.post("/empresas/{empresa_id}/mensais", status_code=201)
def registrar_mensal(empresa_id: int, data: ImpostoMensalCreate):
    try:
        return repository.registrar_imposto_mensal(empresa_id, data.model_dump(mode="json"))
    except LookupError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, "Não foi possível registrar o imposto da competência.") from exc
