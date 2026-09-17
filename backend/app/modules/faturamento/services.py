from datetime import date, timedelta

from .schema import (
    FaturamentoCreate,
    FaturamentoUpdate,
)

from .repository import (
    empresa_existe,
    criar_faturamento,
    atualizar_faturamento,
    obter_faturamento,
    obter_empresa,
    listar_faturamentos_empresa,
    resumo_faturamento,
    listar_empresas_faturamento,
    listar_declaracoes_empresa,
)


MESES = [
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]


def competencia_anterior():
    hoje = date.today()

    primeiro_dia_mes_atual = hoje.replace(day=1)

    ultimo_dia_mes_anterior = (
        primeiro_dia_mes_atual - timedelta(days=1)
    )

    return (
        ultimo_dia_mes_anterior.year,
        ultimo_dia_mes_anterior.month,
    )


def nome_mes(mes: int) -> str:
    return MESES[mes]


def registrar_faturamento(dados: FaturamentoCreate):

    if not empresa_existe(dados.empresa_id):
        raise ValueError("Empresa não encontrada.")

    return criar_faturamento(dados)


def editar_faturamento(
    faturamento_id: int,
    dados: FaturamentoUpdate,
):
    faturamento = obter_faturamento(faturamento_id)

    if faturamento is None:
        raise ValueError("Faturamento não encontrado.")

    return atualizar_faturamento(
        faturamento_id,
        dados,
    )


def obter_tela_empresas(
    regime: str | None = None,
    busca: str | None = None,
):
    ano, mes = competencia_anterior()

    empresas = listar_empresas_faturamento(
        ano_pendente=ano,
        mes_pendente=mes,
        regime=regime,
        busca=busca,
    )

    return {
        "competencia_pendente": {
            "ano": ano,
            "mes": mes,
            "nome": nome_mes(mes),
            "label": f"{nome_mes(mes)}/{ano}",
        },
        "empresas": empresas,
    }


def obter_tela_empresa(empresa_id: int):

    empresa = obter_empresa(empresa_id)

    if empresa is None:
        raise ValueError("Empresa não encontrada.")

    faturamentos = listar_faturamentos_empresa(
        empresa_id
    )

    resumo = resumo_faturamento(
        empresa_id
    )

    declaracoes = listar_declaracoes_empresa(
        empresa_id
    )

    return {
        "empresa": empresa,
        "faturamentos": faturamentos,
        "resumo": resumo,
        "declaracoes": declaracoes,
    }