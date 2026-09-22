from datetime import date
from typing import Any

from .repository import (
    atualizar_faturamento,
    atualizar_observacao_empresa,
    criar_faturamento,
    empresa_existe,
    listar_empresas_faturamento,
    listar_faturamentos_empresa,
    listar_meses_ano,
    obter_empresa,
    obter_faturamento,
    resumo_faturamento,
    listar_declaracoes_empresa,
    salvar_faturamentos_lote,
    pendencias_faturamento_por_empresa,
)
from .schemas import FaturamentoCreate, FaturamentoUpdate, FaturamentoLoteCreate


MESES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def competencia_anterior() -> tuple[int, int]:
    hoje = date.today()
    ano = hoje.year
    mes = hoje.month - 1
    if mes == 0:
        return ano - 1, 12
    return ano, mes


def nome_mes(mes: int) -> str:
    return MESES[mes]


def registrar_faturamento(dados: FaturamentoCreate) -> dict[str, Any]:
    if not empresa_existe(dados.empresa_id):
        raise LookupError("Empresa não encontrada.")
    return criar_faturamento(dados)


def registrar_faturamentos_lote(empresa_id: int, dados: FaturamentoLoteCreate) -> dict[str, Any]:
    if not empresa_existe(empresa_id):
        raise LookupError("Empresa não encontrada.")
    return salvar_faturamentos_lote(empresa_id, dados)


def editar_faturamento(faturamento_id: int, dados: FaturamentoUpdate) -> dict[str, Any]:
    if not obter_faturamento(faturamento_id):
        raise LookupError("Faturamento não encontrado.")
    result = atualizar_faturamento(faturamento_id, dados)
    if result is None:
        raise LookupError("Faturamento não encontrado.")
    return result


def salvar_observacao_empresa(empresa_id: int, observacao: str | None) -> dict[str, Any]:
    if not empresa_existe(empresa_id):
        raise LookupError("Empresa não encontrada.")
    result = atualizar_observacao_empresa(empresa_id, observacao)
    if result is None:
        raise LookupError("Empresa não encontrada.")
    return result


def obter_dashboard_faturamento(
    regime: str | None = None,
    busca: str | None = None,
    ano: int | None = None,
    mes: int | None = None,
) -> dict[str, Any]:
    if ano is None or mes is None:
        ano, mes = competencia_anterior()

    empresas = listar_empresas_faturamento(
        ano_competencia=ano,
        mes_competencia=mes,
        regime=regime,
        busca=busca,
    )
    todas = listar_empresas_faturamento(ano_competencia=ano, mes_competencia=mes)

    hoje = date.today()
    ultimo_mes_encerrado = hoje.month - 1 if ano == hoje.year else (12 if ano < hoje.year else 0)
    pendencias = pendencias_faturamento_por_empresa(ano, ultimo_mes_encerrado)
    for item in todas:
        item["meses_pendentes"] = pendencias.get(item["id"], [])
        item["quantidade_meses_pendentes"] = len(item["meses_pendentes"])
    pendencias_filtradas = {item["id"]: pendencias.get(item["id"], []) for item in empresas}
    for item in empresas:
        item["meses_pendentes"] = pendencias_filtradas.get(item["id"], [])
        item["quantidade_meses_pendentes"] = len(item["meses_pendentes"])
    simples = sum(1 for item in todas if (item.get("regime_tributario") or "").upper() == "SIMPLES NACIONAL")
    presumido = sum(1 for item in todas if (item.get("regime_tributario") or "").upper() == "LUCRO PRESUMIDO")
    real = sum(1 for item in todas if (item.get("regime_tributario") or "").upper() == "LUCRO REAL")
    informados = sum(1 for item in todas if item["status_competencia"] == "informado")
    pendentes = len(todas) - informados
    faturamento_competencia = sum(float(item.get("valor_competencia") or 0) for item in todas)

    return {
        "competencia": {
            "ano": ano,
            "mes": mes,
            "nome": nome_mes(mes),
            "label": f"{nome_mes(mes)}/{ano}",
        },
        # Alias mantido para compatibilidade com a versão anterior.
        "competencia_pendente": {
            "ano": ano,
            "mes": mes,
            "nome": nome_mes(mes),
            "label": f"{nome_mes(mes)}/{ano}",
        },
        "indicadores": {
            "total_empresas": len(todas),
            "faturamentos_pendentes": pendentes,
            "faturamentos_informados": informados,
            "valor_competencia": faturamento_competencia,
            "regimes": {
                "TODOS": len(todas),
                "SIMPLES NACIONAL": simples,
                "LUCRO PRESUMIDO": presumido,
                "LUCRO REAL": real,
            },
        },
        "empresas": empresas,
    }


def obter_empresa_faturamento(empresa_id: int, ano: int | None = None) -> dict[str, Any]:
    empresa = obter_empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")
    ano_referencia = ano or date.today().year
    return {
        "ano": ano_referencia,
        "empresa": empresa,
        "faturamentos": listar_faturamentos_empresa(empresa_id, ano=ano_referencia),
        "competencias": listar_meses_ano(empresa_id, ano_referencia),
        "resumo": resumo_faturamento(empresa_id, ano_referencia),
        "declaracoes": listar_declaracoes_empresa(empresa_id),
    }
