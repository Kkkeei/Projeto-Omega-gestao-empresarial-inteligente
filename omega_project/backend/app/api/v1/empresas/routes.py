from fastapi import APIRouter, HTTPException, Query
from app.schemas.empresas import EmpresaCreate, EmpresaUpdate, InativarEmpresa, AlterarRegime
from app.services.empresas_service import *
import asyncio
import os
from app.services.certidoes_service import listar as listar_certidoes
from app.services.pendencias_service import listar as listar_pendencias

router=APIRouter(prefix="/api/v1/empresas",tags=["Empresas"])

@router.get("")
def listar(q:str|None=Query(default=None),ativo:bool|None=Query(default=None)):
    itens=listar_empresas(q,ativo); return {"total":len(itens),"empresas":itens}

@router.get("/cnpj/{cnpj}/consulta")
async def consulta_cnpj(cnpj:str):
    try:return await consultar_cnpj_externo(cnpj)
    except ValueError as e: raise HTTPException(400,str(e))
    except Exception as e: raise HTTPException(502,f"Não foi possível consultar o CNPJ: {e}")

@router.post("",status_code=201)
def cadastrar(dados:EmpresaCreate):
    try:return criar_empresa(dados.model_dump(exclude_none=True))
    except ValueError as e: raise HTTPException(400,str(e))

@router.get("/{empresa_id}")
def consultar(empresa_id:int):
    e=empresa_por_id(empresa_id)
    if not e: raise HTTPException(404,"Empresa não encontrada.")
    return e

@router.put("/{empresa_id}")
def atualizar(empresa_id:int,dados:EmpresaUpdate):
    try:return atualizar_empresa(empresa_id,dados.model_dump(exclude_unset=True))
    except LookupError as e: raise HTTPException(404,str(e))

@router.post("/{empresa_id}/inativar")
def inativar(empresa_id:int,dados:InativarEmpresa):
    try:return inativar_empresa(empresa_id,dados.data_saida,dados.observacao)
    except (LookupError,ValueError) as e: raise HTTPException(400,str(e))

@router.post("/{empresa_id}/regime")
def regime(empresa_id:int,dados:AlterarRegime):
    try:return alterar_regime(empresa_id,dados.regime_tributario,dados.mes_inicio,dados.ano_inicio,dados.observacao)
    except (LookupError,ValueError) as e: raise HTTPException(400,str(e))

@router.get("/{empresa_id}/historico")
def historico(empresa_id:int):
    try:
        h=historico_empresa(empresa_id); return {"total":len(h),"historico":h}
    except LookupError as e: raise HTTPException(404,str(e))

@router.get("/{empresa_id}/certidoes")
def certidoes_empresa(empresa_id:int):
    if not empresa_por_id(empresa_id): raise HTTPException(404,"Empresa não encontrada.")
    itens=listar_certidoes(empresa_id); return {"total":len(itens),"certidoes":itens}

@router.get("/{empresa_id}/pendencias")
def pendencias_empresa(empresa_id:int):
    if not empresa_por_id(empresa_id): raise HTTPException(404,"Empresa não encontrada.")
    itens=listar_pendencias(empresa_id,None); return {"total":len(itens),"pendencias":itens}

@router.post("/{empresa_id}/sync")
async def sincronizar(empresa_id:int):
    try:
        e,a=await sincronizar_empresa(empresa_id); return {"empresa":e,"alteracoes":a,"origem":"BRASILAPI"}
    except LookupError as e: raise HTTPException(404,str(e))
    except Exception as e: raise HTTPException(502,f"Falha na sincronização: {e}")

@router.post("/sync-todas")
async def sincronizar_todas():
    """Sincroniza uma empresa por vez, com intervalo, para reduzir 429 de provedores externos."""
    itens = listar_empresas(ativo=True)
    resultados = []
    intervalo = float(os.getenv("BRASILAPI_INTERVAL_SECONDS", "2.0"))
    for indice, e in enumerate(itens):
        try:
            atualizado, alteracoes = await sincronizar_empresa(e['id'])
            resultados.append({'empresa_id':e['id'],'status':'OK','alteracoes':len(alteracoes),'empresa':atualizado})
        except Exception as ex:
            resultados.append({'empresa_id':e['id'],'status':'ERRO','mensagem':str(ex)})
        if indice < len(itens) - 1 and intervalo > 0:
            await asyncio.sleep(intervalo)
    return {'total':len(resultados),'resultados':resultados}
