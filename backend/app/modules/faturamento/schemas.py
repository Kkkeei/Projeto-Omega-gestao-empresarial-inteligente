from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Periodicidade = Literal["Mensal", "Trimestral", "Semestral", "Anual", "Personalizado"]


class FaturamentoCreate(BaseModel):
    empresa_id: int = Field(gt=0)
    competencia_ano: int = Field(ge=2000, le=2100)
    competencia_mes: int = Field(ge=1, le=12)
    valor: float = Field(ge=0)
    observacao: str | None = Field(default=None, max_length=1000)
    data_faturamento: date | None = None
    periodicidade: Periodicidade = "Mensal"


class FaturamentoUpdate(BaseModel):
    valor: float = Field(ge=0)
    observacao: str | None = Field(default=None, max_length=1000)
    data_faturamento: date | None = None
    periodicidade: Periodicidade = "Mensal"


class FaturamentoLoteItem(BaseModel):
    competencia_ano: int = Field(ge=2000, le=2100)
    competencia_mes: int = Field(ge=1, le=12)
    valor: float = Field(ge=0)
    observacao: str | None = Field(default=None, max_length=1000)
    data_faturamento: date | None = None
    periodicidade: Periodicidade = "Mensal"


class FaturamentoLoteCreate(BaseModel):
    itens: list[FaturamentoLoteItem] = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def validar_competencias_unicas(self):
        competencias = [(item.competencia_ano, item.competencia_mes) for item in self.itens]
        if len(competencias) != len(set(competencias)):
            raise ValueError("Não é permitido repetir a mesma competência no preenchimento em lote.")
        return self


class ObservacaoEmpresaFaturamento(BaseModel):
    observacao: str | None = Field(default=None, max_length=2000)


class DeclaracaoAnualCreate(BaseModel):
    ano: int = Field(ge=2000, le=2100)
    usuario_id: int | None = Field(default=None, gt=0)


class DeclaracaoPersonalizadaCreate(BaseModel):
    ano_inicio: int = Field(ge=2000, le=2100)
    mes_inicio: int = Field(ge=1, le=12)
    ano_fim: int = Field(ge=2000, le=2100)
    mes_fim: int = Field(ge=1, le=12)
    usuario_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validar_periodo(self):
        inicio = self.ano_inicio * 12 + self.mes_inicio
        fim = self.ano_fim * 12 + self.mes_fim
        if inicio > fim:
            raise ValueError("O período inicial não pode ser maior que o período final.")
        return self
