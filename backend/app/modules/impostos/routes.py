from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.api.v1.auth.routes import current_user
from app.db.database import STORAGE_BASE

from . import notificacoes_service, relatorio_service, repository, service
from .schemas import GuiaConfirmacao, ImpostoMensalCreate, NotificacaoConfigUpdate, RegistroSituacaoCreate, RelatorioFiltros, TributoCreate, TributoUpdate, VinculoTributoCreate, VinculoTributoUpdate

router = APIRouter(prefix="/api/v1/impostos", tags=["Impostos"], dependencies=[Depends(current_user)])


@router.get("/dashboard")
def dashboard(q: str | None = Query(None), regime: str | None = Query(None), situacao: str | None = Query(None), ano: int | None = Query(None, ge=2000, le=2100), mes: int | None = Query(None, ge=1, le=12)):
    return service.dashboard(q, regime, situacao, ano, mes)


@router.get("/tributos")
def listar_tributos(ativos: bool = Query(False), q: str | None = None, esfera: str | None = None):
    return {"tributos": repository.listar_tributos(ativos_apenas=ativos, q=q, esfera=esfera)}


@router.post("/tributos", status_code=201)
def criar_tributo(data: TributoCreate):
    try: return repository.criar_tributo(data.model_dump())
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc
    except Exception as exc: raise HTTPException(400, "Não foi possível cadastrar o tributo.") from exc


@router.put("/tributos/{tributo_id}")
def atualizar_tributo(tributo_id: int, data: TributoUpdate):
    try: return repository.atualizar_tributo(tributo_id, data.model_dump())
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/empresas/{empresa_id}")
def detalhe_empresa(empresa_id:int, ano:int|None=Query(None,ge=2000,le=2100), mes:int|None=Query(None,ge=1,le=12)):
    try: return service.detalhe_empresa(empresa_id,ano,mes)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc


@router.get("/empresas/{empresa_id}/configuracao")
def configuracao_empresa(empresa_id:int):
    if not repository.empresa_existe(empresa_id): raise HTTPException(404,"Empresa não encontrada.")
    return {"configuracoes":repository.listar_configuracoes_empresa(empresa_id)}


@router.post("/empresas/{empresa_id}/tributos", status_code=201)
def vincular_tributo(empresa_id:int,data:VinculoTributoCreate):
    try: return repository.vincular_tributo(empresa_id,data.model_dump())
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(409,str(exc)) from exc


@router.put("/vinculos/{vinculo_id}")
def editar_vinculo(vinculo_id:int,data:VinculoTributoUpdate):
    try: return repository.atualizar_vinculo(vinculo_id,data.model_dump())
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(409,str(exc)) from exc


@router.post("/empresas/{empresa_id}/mensais", status_code=201)
def registrar_mensal(empresa_id:int,data:ImpostoMensalCreate):
    try: return repository.salvar_mensal(empresa_id,data.model_dump(mode="json"),"REGISTRO_MANUAL")
    except LookupError as exc: raise HTTPException(400,str(exc)) from exc


@router.post("/empresas/{empresa_id}/mensais/situacao", status_code=201)
def registrar_situacao(empresa_id:int,data:RegistroSituacaoCreate, tipo:str=Query(...,pattern="^(CREDOR|SEM_MOVIMENTACAO)$")):
    try:
        return repository.salvar_mensal(empresa_id,{"tributo_id":data.tributo_id,"competencia_ano":data.competencia_ano,"competencia_mes":data.competencia_mes,"status":tipo,"valor":0,"observacao":data.observacao},tipo)
    except LookupError as exc: raise HTTPException(400,str(exc)) from exc


@router.post("/empresas/{empresa_id}/mensais/{tributo_id}/pago")
def marcar_pago(empresa_id:int,tributo_id:int,ano:int=Query(...),mes:int=Query(...)):
    try:
        mensal=repository.obter_mensal(empresa_id,tributo_id,ano,mes)
        if not mensal: raise LookupError("Registro mensal não encontrado.")
        return repository.salvar_mensal(empresa_id,{"tributo_id":tributo_id,"competencia_ano":ano,"competencia_mes":mes,"status":"PAGO","valor":mensal.get("valor"),"data_vencimento":mensal.get("data_vencimento"),"data_pagamento":__import__('datetime').date.today().isoformat(),"numero_documento":mensal.get("numero_documento"),"observacao":mensal.get("observacao")},"MARCAR_PAGO")
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc


@router.get("/empresas/{empresa_id}/tributos/{tributo_id}")
def detalhe_imposto(empresa_id:int,tributo_id:int,ano:int|None=Query(None,ge=2000,le=2100),mes:int|None=Query(None,ge=1,le=12)):
    try: return service.detalhe_imposto(empresa_id,tributo_id,ano,mes)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc


@router.post("/empresas/{empresa_id}/tributos/{tributo_id}/preparar-guia")
async def preparar_guia(empresa_id:int,tributo_id:int,ano:int=Query(...),mes:int=Query(...),arquivo:UploadFile=File(...)):
    try: return await _preparar_guia(empresa_id,tributo_id,ano,mes,arquivo)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc


async def _preparar_guia(empresa_id:int,tributo_id:int,ano:int,mes:int,arquivo:UploadFile):
    return service.preparar_guia(empresa_id,tributo_id,ano,mes,arquivo,STORAGE_BASE)


@router.post("/empresas/{empresa_id}/tributos/{tributo_id}/confirmar-guia")
def confirmar_guia(empresa_id:int,tributo_id:int,data:GuiaConfirmacao):
    try: return service.confirmar_guia(empresa_id,tributo_id,data.model_dump())
    except (LookupError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc


@router.put("/documentos/{documento_id}")
def editar_documento(documento_id:int,data:dict):
    try: return repository.atualizar_documento(documento_id,data)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc


@router.get("/documentos/{documento_id}/download")
def download_documento(documento_id:int):
    from app.db.database import conectar_banco
    conn=conectar_banco()
    try: row=conn.execute("SELECT nome_arquivo,caminho_arquivo,mime_type FROM documentos_impostos WHERE id=?",(documento_id,)).fetchone()
    finally: conn.close()
    if not row: raise HTTPException(404,"Documento não encontrado.")
    path=Path(row["caminho_arquivo"]).resolve(); base=STORAGE_BASE.resolve()
    try: path.relative_to(base)
    except ValueError: raise HTTPException(500,"Caminho de documento inválido.")
    if not path.exists(): raise HTTPException(404,"Arquivo não encontrado no armazenamento.")
    return FileResponse(str(path),media_type=row["mime_type"] or "application/octet-stream",filename=row["nome_arquivo"])


@router.get("/notificacoes/config")
def notificacoes_config(): return {"configuracoes":notificacoes_service.listar_configuracoes()}


@router.put("/notificacoes/config")
def salvar_notificacoes_config(data:NotificacaoConfigUpdate): return notificacoes_service.salvar_configuracao(data.model_dump())


@router.get("/notificacoes/eventos")
def notificacoes_eventos(empresa_id:int|None=None,imposto_mensal_id:int|None=None): return {"eventos":notificacoes_service.listar_eventos(empresa_id,imposto_mensal_id)}


@router.post("/notificacoes/eventos/{evento_id}/reenviar")
def reenviar_notificacao(evento_id:int):
    try: return notificacoes_service.reenviar(evento_id)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc


@router.post("/relatorios/preview")
def relatorio_preview(data:RelatorioFiltros,empresa_id:int=Query(...)):
    try: return relatorio_service.gerar_previa(empresa_id,data.ano_inicio,data.mes_inicio,data.ano_fim,data.mes_fim)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc


@router.get("/relatorios/pdf")
def relatorio_pdf(empresa_id:int,ano_inicio:int,mes_inicio:int,ano_fim:int,mes_fim:int):
    try:
        dados=relatorio_service.gerar_previa(empresa_id,ano_inicio,mes_inicio,ano_fim,mes_fim); pdf=relatorio_service.gerar_pdf(dados)
        nome=f"relatorio_impostos_{empresa_id}_{ano_inicio}{mes_inicio:02d}_{ano_fim}{mes_fim:02d}.pdf"
        return Response(content=pdf,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{nome}"'})
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
