from __future__ import annotations

from . import repository


def dashboard(q: str | None = None, regime: str | None = None, ano: int | None = None, mes: int | None = None):
    from datetime import date

    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or (hoje.month - 1 or 12)
    if mes == 12 and hoje.month == 1 and ano == hoje.year:
        ano -= 1
    return repository.listar_empresas_impostos(q, regime, ano, mes)


def detalhe_empresa(empresa_id: int, ano: int | None = None, mes: int | None = None):
    from datetime import date

    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or (hoje.month - 1 or 12)
    if mes == 12 and hoje.month == 1 and ano == hoje.year:
        ano -= 1
    data = repository.obter_empresa_impostos(empresa_id, ano, mes)
    if not data:
        raise LookupError("Empresa não encontrada.")
    return data
