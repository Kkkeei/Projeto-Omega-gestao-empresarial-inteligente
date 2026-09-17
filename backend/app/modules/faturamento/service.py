from datetime import date
from typing import Any

from .repository import (
    atualizar_faturamento,
    criar_faturamento,
    empresa_existe,
    listar_empresas_faturamento,
    listar_faturamentos_empresa,
    obter_empresa,
    obter_faturamento,
    resumo_faturamento,
    listar_declaracoes_empresa,
)
from .schemas import FaturamentoCreate, FaturamentoUpdate


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


def editar_faturamento(faturamento_id: int, dados: FaturamentoUpdate) -> dict[str, Any]:
    if not obter_faturamento(faturamento_id):
        raise LookupError("Faturamento não encontrado.")
    result = atualizar_faturamento(faturamento_id, dados)
    if result is None:
        raise LookupError("Faturamento não encontrado.")
    return result


def obter_dashboard_faturamento(regime: str | None = None, busca: str | None = None) -> dict[str, Any]:
    ano, mes = competencia_anterior()
    return {
        "competencia_pendente": {
            "ano": ano,
            "mes": mes,
            "nome": nome_mes(mes),
            "label": f"{nome_mes(mes)}/{ano}",
        },
        "empresas": listar_empresas_faturamento(
            ano_competencia=ano,
            mes_competencia=mes,
            regime=regime,
            busca=busca,
        ),
    }


def obter_empresa_faturamento(empresa_id: int) -> dict[str, Any]:
    empresa = obter_empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")
    return {
        "empresa": empresa,
        "faturamentos": listar_faturamentos_empresa(empresa_id),
        "resumo": resumo_faturamento(empresa_id),
        "declaracoes": listar_declaracoes_empresa(empresa_id),
    }
