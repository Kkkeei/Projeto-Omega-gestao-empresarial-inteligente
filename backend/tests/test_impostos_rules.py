from datetime import date, timedelta

from app.modules.impostos import repository
from app.modules.impostos.service import _parse_extracao
from app.modules.impostos.relatorio_service import _meses


def test_status_exibicao_pago_nao_vira_atrasado():
    status, dias = repository._status_exibicao(
        {"status_mensal": "PAGO", "data_vencimento": "2020-01-01"},
        hoje=date(2026, 10, 20),
    )
    assert status == "PAGO"
    assert dias is None


def test_status_exibicao_classifica_vencido():
    status, dias = repository._status_exibicao(
        {"status_mensal": "A_PAGAR", "data_vencimento": "2026-10-19"},
        hoje=date(2026, 10, 20),
    )
    assert status == "EM_ATRASO"
    assert dias == -1


def test_status_exibicao_classifica_vencimento_dentro_de_sete_dias():
    status, dias = repository._status_exibicao(
        {"status_mensal": "A_PAGAR", "data_vencimento": "2026-10-27"},
        hoje=date(2026, 10, 20),
    )
    assert status == "A_VENCER"
    assert dias == 7


def test_status_exibicao_nao_confunde_credor_com_pendente():
    status, dias = repository._status_exibicao(
        {"status_mensal": "CREDOR", "data_vencimento": None},
        hoje=date(2026, 10, 20),
    )
    assert status == "CREDOR"
    assert dias is None


def test_status_geral_prioriza_vencido_sobre_vencendo_e_pendente():
    hoje = date.today()
    items = [
        {"status_mensal": "A_PAGAR", "data_vencimento": (hoje + timedelta(days=1)).isoformat()},
        {"status_mensal": "PENDENTE", "data_vencimento": None},
        {"status_mensal": "A_PAGAR", "data_vencimento": (hoje - timedelta(days=1)).isoformat()},
    ]
    status = repository._status_geral(items)
    assert status["chave"] == "VENCIDO"
    assert status["quantidade"] == 1


def test_status_geral_prioriza_vencendo_sobre_pendente():
    hoje = date.today()
    items = [
        {"status_mensal": "PENDENTE", "data_vencimento": None},
        {"status_mensal": "A_PAGAR", "data_vencimento": (hoje + timedelta(days=2)).isoformat()},
    ]
    status = repository._status_geral(items)
    assert status["chave"] == "VENCENDO"
    assert status["quantidade"] == 1


def test_parse_extracao_identifica_dados_basicos_de_darf():
    text = (
        "DARF\nCompetência 08/2026\nVencimento 25/09/2026\n"
        "Valor total R$ 3.200,00\nCódigo da receita 8109\n"
        "CNPJ 12.345.678/0001-90\nPeríodo de apuração 01/08/2026 a 31/08/2026"
    )
    data = _parse_extracao(text)
    assert data["competencia_extraida"] == "08/2026"
    assert data["vencimento_extraido"] == "2026-09-25"
    assert data["valor_extraido"] == 3200.0
    assert data["codigo_receita"] == "8109"
    assert data["cnpj_extraido"] == "12.345.678/0001-90"
    assert data["periodo_apuracao_inicio"] == "2026-08-01"
    assert data["periodo_apuracao_fim"] == "2026-08-31"


def test_relatorio_gera_meses_contiguos_ao_cruzar_ano():
    assert _meses(2026, 11, 2027, 2) == [
        (2026, 11), (2026, 12), (2027, 1), (2027, 2)
    ]
