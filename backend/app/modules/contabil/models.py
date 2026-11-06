from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


StatusObrigacao = Literal["RECEBIDO", "FUTURO", "PENDENTE", "NAO_RECEBIDO"]
StatusEmpresa = Literal["COMPLETA", "PARCIAL", "SEM_RECEBIMENTO", "FUTURA"]

COMPETENCIA_MINIMA = 190001
COMPETENCIA_MAXIMA = 299912

CATEGORIAS_PADRAO = (
    "Extratos Bancários",
    "Aplicações Financeiras",
    "Financiamentos / Empréstimos",
    "Consórcios",
    "Administradoras de Cartões",
    "Outros Documentos",
)


def competencia_anterior(data: date | None = None) -> int:
    referencia = data or date.today()
    primeiro_dia = referencia.replace(day=1)
    anterior = primeiro_dia - timedelta(days=1)
    return anterior.year * 100 + anterior.month


@dataclass(frozen=True)
class EmpresaContabilResumo:
    id: int
    razao_social: str
    nome_fantasia: str | None
    cnpj: str
    regime_tributario: str | None
    ativo: bool
    documentos_recebidos: int = 0
    documentos_total: int = 0
