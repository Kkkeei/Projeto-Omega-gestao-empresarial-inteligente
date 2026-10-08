from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field, model_validator


ESFERAS = {"Federal", "Estadual", "Municipal"}


class TributoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    sigla: str = Field(min_length=1, max_length=30, description="Código do tributo")
    esfera: str = Field(min_length=1, max_length=30)
    categoria: str | None = Field(default=None, max_length=60)
    periodicidade: str | None = Field(default="Mensal", max_length=30)
    descricao: str | None = None

    @model_validator(mode="after")
    def validar_esfera(self):
        self.esfera = self.esfera.title().strip()
        if self.esfera not in ESFERAS:
            raise ValueError("Esfera deve ser Federal, Estadual ou Municipal.")
        return self


class TributoUpdate(TributoCreate):
    ativo: bool = True


class VinculoTributoCreate(BaseModel):
    tributo_id: int
    obrigatorio: bool = True
    vigencia_inicio: str = Field(min_length=7, max_length=10)
    vigencia_fim: str | None = Field(default=None, min_length=7, max_length=10)
    observacao: str | None = None


class VinculoTributoUpdate(BaseModel):
    obrigatorio: bool = True
    vigencia_inicio: str | None = None
    vigencia_fim: str | None = None
    status: str = Field(default="ATIVO", pattern="^(ATIVO|INATIVO)$")
    observacao: str | None = None


class ImpostoMensalCreate(BaseModel):
    tributo_id: int
    competencia_ano: int = Field(ge=2000, le=2100)
    competencia_mes: int = Field(ge=1, le=12)
    status: str = Field(default="PENDENTE", min_length=3, max_length=30)
    valor: float | None = Field(default=None, ge=0)
    data_vencimento: date | None = None
    data_pagamento: date | None = None
    numero_documento: str | None = Field(default=None, max_length=120)
    observacao: str | None = None


class RegistroSituacaoCreate(BaseModel):
    tributo_id: int
    competencia_ano: int = Field(ge=2000, le=2100)
    competencia_mes: int = Field(ge=1, le=12)
    observacao: str | None = None


class GuiaConfirmacao(BaseModel):
    documento_id: int
    competencia_ano: int = Field(ge=2000, le=2100)
    competencia_mes: int = Field(ge=1, le=12)
    competencia_extraida: str | None = None
    valor: float | None = Field(default=None, ge=0)
    vencimento: str | None = None
    codigo_receita: str | None = None
    cnpj: str | None = None
    data_pagamento: str | None = None
    periodo_apuracao_inicio: str | None = None
    periodo_apuracao_fim: str | None = None
    mensagem_cliente: str | None = None
    observacao: str | None = None


class NotificacaoConfigUpdate(BaseModel):
    publico: str = Field(pattern="^(CLIENTE|CONTABILIDADE)$")
    guia_enviada: bool = True
    antes_vencimento: bool = True
    dias_antes: int = Field(default=5, ge=1, le=15)
    dia_vencimento: bool = True
    nao_pagamento: bool = True
    imposto_vencido: bool = True


class RelatorioFiltros(BaseModel):
    ano_inicio: int = Field(ge=2000, le=2100)
    mes_inicio: int = Field(ge=1, le=12)
    ano_fim: int = Field(ge=2000, le=2100)
    mes_fim: int = Field(ge=1, le=12)

    @model_validator(mode="after")
    def validar_periodo(self):
        if (self.ano_inicio, self.mes_inicio) > (self.ano_fim, self.mes_fim):
            raise ValueError("O período inicial não pode ser posterior ao período final.")
        return self
