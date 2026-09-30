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


class BancoBrasilConfig(BaseModel):
    percentual_a_vista: float = Field(default=20, ge=0, le=100)
    percentual_a_prazo: float = Field(default=80, ge=0, le=100)
    percentual_cartao: float | None = Field(default=None, ge=0, le=100)
    percentual_cheque: float | None = Field(default=None, ge=0, le=100)
    percentual_boleto: float | None = Field(default=None, ge=0, le=100)
    prazo_medio_dias: int | None = Field(default=None, ge=0, le=3650)

    @model_validator(mode="after")
    def validar_percentuais(self):
        if abs((self.percentual_a_vista + self.percentual_a_prazo) - 100) > 0.01:
            raise ValueError("Percentual à vista + percentual a prazo deve totalizar 100%.")
        meios = [self.percentual_cartao, self.percentual_cheque, self.percentual_boleto]
        informados = [float(v) for v in meios if v is not None]
        if informados and abs(sum(informados) - 100) > 0.01:
            raise ValueError("Cartão + cheque + boleto/título deve totalizar 100% quando informado.")
        return self
