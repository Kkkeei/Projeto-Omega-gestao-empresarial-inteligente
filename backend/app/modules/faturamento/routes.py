from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.v1.auth.routes import current_user
from app.db.database import BASE_DIR
from .declaracao_service import gerar_declaracao_periodo, ultimo_periodo_completo_12_meses, periodo_12_meses_por_empresa
from .banco_brasil_service import gerar_declaracao_banco_brasil, obter_periodo_banco_brasil
from .schemas import (
    DeclaracaoAnualCreate,
    DeclaracaoPersonalizadaCreate,
    FaturamentoCreate,
    FaturamentoLoteCreate,
    FaturamentoUpdate,
    ObservacaoEmpresaFaturamento,
    BancoBrasilConfig,
)
from .service import (
    editar_faturamento,
    obter_dashboard_faturamento,
    obter_empresa_faturamento,
    registrar_faturamento,
    registrar_faturamentos_lote,
    salvar_observacao_empresa,
)
from .repository import listar_declaracoes_empresa, obter_declaracao, obter_empresa


router = APIRouter(prefix="/api/v1", tags=["Faturamento"])


@router.get("/faturamento/empresas")
def listar_empresas_faturamento(
    regime: str | None = Query(default=None),
    busca: str | None = Query(default=None),
    ano: int | None = Query(default=None, ge=2000, le=2100),
    mes: int | None = Query(default=None, ge=1, le=12),
):
    if (ano is None) != (mes is None):
        raise HTTPException(status_code=400, detail="Informe ano e mês juntos para a competência de controle.")
    return obter_dashboard_faturamento(regime=regime, busca=busca, ano=ano, mes=mes)


@router.get("/empresas/{empresa_id}/faturamento")
def detalhe_faturamento(
    empresa_id: int,
    ano: int | None = Query(default=None, ge=2000, le=2100),
):
    try:
        return obter_empresa_faturamento(empresa_id, ano=ano)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/empresas/{empresa_id}/faturamento", status_code=201)
def cadastrar_faturamento(
    empresa_id: int,
    dados: FaturamentoCreate,
):
    if dados.empresa_id != empresa_id:
        raise HTTPException(status_code=400, detail="O empresa_id informado deve corresponder à empresa da URL.")
    try:
        return registrar_faturamento(dados)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/empresas/{empresa_id}/faturamento/lote", status_code=201)
def cadastrar_faturamento_lote(
    empresa_id: int,
    dados: FaturamentoLoteCreate,
):
    try:
        return registrar_faturamentos_lote(empresa_id, dados)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/empresas/{empresa_id}/faturamento/observacao")
def alterar_observacao_empresa(
    empresa_id: int,
    dados: ObservacaoEmpresaFaturamento,
):
    try:
        return salvar_observacao_empresa(empresa_id, dados.observacao)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/faturamentos/{faturamento_id}")
def alterar_faturamento(faturamento_id: int, dados: FaturamentoUpdate):
    try:
        return editar_faturamento(faturamento_id, dados)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/empresas/{empresa_id}/declaracoes-faturamento/12-meses")
def declaracao_12_meses(empresa_id: int, user=Depends(current_user)):
    ano_inicio, mes_inicio, ano_fim, mes_fim, _ = periodo_12_meses_por_empresa(empresa_id)
    try:
        return gerar_declaracao_periodo(
            empresa_id=empresa_id,
            tipo="Últimos 12 meses",
            ano_inicio=ano_inicio,
            mes_inicio=mes_inicio,
            ano_fim=ano_fim,
            mes_fim=mes_fim,
            usuario_id=user["id"],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/empresas/{empresa_id}/declaracoes-faturamento/banco-brasil/periodo")
def periodo_declaracao_banco_brasil(empresa_id: int, user=Depends(current_user)):
    try:
        return obter_periodo_banco_brasil(empresa_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/empresas/{empresa_id}/declaracoes-faturamento/banco-brasil/config")
def config_banco_brasil(empresa_id: int, user=Depends(current_user)):
    from .repository import obter_config_banco_brasil
    empresa = None
    try:
        empresa = obter_empresa(empresa_id)
    except Exception:
        pass
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return obter_config_banco_brasil(empresa_id) or {
        "empresa_id": empresa_id,
        "percentual_a_vista": 20,
        "percentual_a_prazo": 80,
        "percentual_cartao": None,
        "percentual_cheque": None,
        "percentual_boleto": None,
        "prazo_medio_dias": None,
    }


@router.put("/empresas/{empresa_id}/declaracoes-faturamento/banco-brasil/config")
def salvar_configuracao_banco_brasil(empresa_id: int, dados: BancoBrasilConfig, user=Depends(current_user)):
    from .repository import empresa_existe, salvar_config_banco_brasil
    if not empresa_existe(empresa_id):
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return salvar_config_banco_brasil(empresa_id, dados.model_dump())


@router.post("/empresas/{empresa_id}/declaracoes-faturamento/banco-brasil")
async def declaracao_banco_brasil(empresa_id: int, dados: BancoBrasilConfig | None = None, user=Depends(current_user)):
    try:
        return await gerar_declaracao_banco_brasil(
            empresa_id=empresa_id,
            usuario_id=user["id"],
            config=(dados.model_dump() if dados else BancoBrasilConfig().model_dump()),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/empresas/{empresa_id}/declaracoes-faturamento/anual")
def declaracao_anual(empresa_id: int, dados: DeclaracaoAnualCreate, user=Depends(current_user)):
    try:
        return gerar_declaracao_periodo(
            empresa_id=empresa_id,
            tipo="Anual",
            ano_inicio=dados.ano,
            mes_inicio=1,
            ano_fim=dados.ano,
            mes_fim=12,
            usuario_id=user["id"],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/empresas/{empresa_id}/declaracoes-faturamento/personalizada")
def declaracao_personalizada(
    empresa_id: int,
    dados: DeclaracaoPersonalizadaCreate,
    user=Depends(current_user),
):
    try:
        return gerar_declaracao_periodo(
            empresa_id=empresa_id,
            tipo="Personalizada",
            ano_inicio=dados.ano_inicio,
            mes_inicio=dados.mes_inicio,
            ano_fim=dados.ano_fim,
            mes_fim=dados.mes_fim,
            usuario_id=user["id"],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/empresas/{empresa_id}/declaracoes-faturamento")
def listar_declaracoes(empresa_id: int):
    return {"declaracoes": listar_declaracoes_empresa(empresa_id)}


@router.get("/declaracoes-faturamento/{declaracao_id}")
def detalhes_declaracao(declaracao_id: int):
    result = obter_declaracao(declaracao_id)
    if not result:
        raise HTTPException(status_code=404, detail="Declaração não encontrada.")
    return result


def _arquivo_declaracao(declaracao_id: int) -> tuple[dict, Path]:
    declaracao = obter_declaracao(declaracao_id)
    if not declaracao:
        raise HTTPException(status_code=404, detail="Declaração não encontrada.")
    stored = Path(declaracao["caminho_arquivo"])
    caminho = (stored if stored.is_absolute() else BASE_DIR.parent / stored).resolve()
    base = BASE_DIR.parent.resolve()
    try:
        caminho.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Caminho de arquivo inválido.") from exc
    if not caminho.exists():
        raise HTTPException(status_code=404, detail="Arquivo da declaração não encontrado no armazenamento.")
    return declaracao, caminho


@router.get("/declaracoes-faturamento/{declaracao_id}/visualizar")
def visualizar_declaracao(declaracao_id: int):
    declaracao, caminho = _arquivo_declaracao(declaracao_id)
    return FileResponse(
        path=str(caminho),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{declaracao["nome_arquivo"]}"'},
    )


@router.get("/declaracoes-faturamento/{declaracao_id}/download")
def baixar_declaracao(declaracao_id: int):
    declaracao, caminho = _arquivo_declaracao(declaracao_id)
    return FileResponse(
        path=str(caminho),
        media_type="application/pdf",
        filename=declaracao["nome_arquivo"],
    )
