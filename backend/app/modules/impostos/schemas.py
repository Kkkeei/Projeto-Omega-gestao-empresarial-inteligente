from __future__ import annotations

from datetime import date
from pydantic import BaseModel, Field


class TributoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    sigla: str | None = Field(default=None, max_length=20)
    esfera: str | None = Field(default=None, max_length=30)
    categoria: str | None = Field(default=None, max_length=60)
    periodicidade: str | None = Field(default=None, max_length=30)
    descricao: str | None = None


class TributoUpdate(TributoCreate):
    ativo: bool = True


class VinculoTributoCreate(BaseModel):
    tributo_id: int
    obrigatorio: bool = True
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None
    observacao: str | None = None


class ImpostoMensalCreate(BaseModel):
    tributo_id: int
    competencia_ano: int = Field(ge=2000, le=2100)
    competencia_mes: int = Field(ge=1, le=12)
    status: str = Field(default="PENDENTE", min_length=3, max_length=30)
    valor: float | None = None
    data_vencimento: date | None = None
    data_pagamento: date | None = None
    numero_documento: str | None = Field(default=None, max_length=80)
    observacao: str | None = None
