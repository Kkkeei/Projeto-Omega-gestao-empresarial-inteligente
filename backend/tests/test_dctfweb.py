from types import SimpleNamespace

import pytest

from app.modules.dctfweb import service


@pytest.mark.parametrize(
    ("status", "exists", "expected_status", "finalizada"),
    [
        (None, False, "PENDENTE", False),
        ("PENDENTE", True, "PENDENTE", False),
        ("CREDOR", True, "CREDOR", True),
        ("SEM_MOVIMENTACAO", True, "SEM_MOVIMENTACAO", True),
        ("SEM_MOVIMENTO", True, "SEM_MOVIMENTACAO", True),
        ("A_PAGAR", True, "VALOR_INFORMADO", True),
        ("A_VENCER", True, "VALOR_INFORMADO", True),
        ("EM_ATRASO", True, "VALOR_INFORMADO", True),
        ("PAGO", True, "PAGO", True),
        ("SEM_APURACAO", True, "PENDENTE", False),
        ("ESTADO_DESCONHECIDO", True, "PENDENTE", False),
    ],
)
def test_status_obrigacao_nao_confunde_ausencia_com_sem_movimento(
    status, exists, expected_status, finalizada
):
    assert service._status_obrigacao(status, exists) == (expected_status, finalizada)


def test_competencia_sem_obrigacoes_nao_libera_fechamento(monkeypatch):
    class FakeConnection:
        def execute(self, *_args):
            return SimpleNamespace(fetchall=lambda: [])

        def close(self):
            pass

    monkeypatch.setattr(service, "conectar_banco", FakeConnection)
    result = service.dashboard(2026, 8)

    assert result["competencia"] == {
        "ano": 2026,
        "mes": 8,
        "label": "Agosto/2026",
    }
    assert result["indicadores"]["total_obrigacoes"] == 0
    assert result["indicadores"]["percentual"] == 0
    assert result["indicadores"]["liberada"] is False


@pytest.mark.parametrize(("ano", "mes"), [(1999, 1), (2101, 1), (2026, 0), (2026, 13)])
def test_competencia_invalida_e_rejeitada(ano, mes):
    with pytest.raises(ValueError, match="Competência inválida"):
        service.dashboard(ano, mes)
