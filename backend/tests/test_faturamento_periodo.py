from datetime import date as RealDate
from unittest.mock import patch

from app.modules.faturamento import declaracao_service as ds


class FakeDate(RealDate):
    @classmethod
    def today(cls):
        return cls(2026, 9, 23)


def test_jan_to_aug_use_august_as_last_month():
    rows = [
        {"competencia_ano": 2026, "competencia_mes": mes, "valor": 100}
        for mes in range(1, 9)
    ]
    with patch.object(ds, "date", FakeDate), patch.object(
        ds, "listar_faturamentos_empresa", return_value=rows
    ):
        assert ds.periodo_12_meses_por_empresa(1) == (2025, 9, 2026, 8, True)


def test_if_august_is_missing_but_july_is_last_use_july():
    rows = [
        {"competencia_ano": 2026, "competencia_mes": mes, "valor": 100}
        for mes in range(1, 8)
    ]
    with patch.object(ds, "date", FakeDate), patch.object(
        ds, "listar_faturamentos_empresa", return_value=rows
    ):
        assert ds.periodo_12_meses_por_empresa(1) == (2025, 8, 2026, 7, True)


def test_with_no_faturamento_use_previous_month_and_allow_zero_months():
    with patch.object(ds, "date", FakeDate), patch.object(
        ds, "listar_faturamentos_empresa", return_value=[]
    ):
        assert ds.periodo_12_meses_por_empresa(1) == (2025, 9, 2026, 8, False)


def test_detail_is_available_only_after_twelve_months_of_activity():
    from app.modules.faturamento import banco_brasil_service as bb

    with patch.object(bb, "obter_empresa", return_value={"data_abertura": "2026-01-15"}), \
         patch.object(bb, "listar_faturamentos_periodo", return_value=[
             {"competencia_ano": 2026, "competencia_mes": mes, "valor": 100}
             for mes in range(1, 9)
         ]), \
         patch.object(bb, "_periodo_12_meses_dinamico", return_value=(2025, 9, 2026, 8, True)):
        result = bb.obter_periodo_banco_brasil(1)
        assert result["detalhamento_disponivel"] is False
