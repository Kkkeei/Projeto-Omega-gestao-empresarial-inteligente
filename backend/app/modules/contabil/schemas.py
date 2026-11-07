from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CompetenciaQuery(BaseModel):
    competencia: int = Field(ge=190001, le=299912)

    @model_validator(mode="after")
    def validar_mes(self):
        if self.competencia % 100 not in range(1, 13):
            raise ValueError("A competência deve estar no formato YYYYMM.")
        return self


class DashboardQuery(CompetenciaQuery):
    busca: str | None = Field(default=None, max_length=200)
    regime: str | None = Field(default=None, max_length=80)
    responsavel_id: int | None = Field(default=None, gt=0)
    sem_responsavel: bool = False
    pagina: int = Field(default=1, ge=1)
    por_pagina: int = Field(default=100, ge=1, le=200)


class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=160)
    descricao: str | None = Field(default=None, max_length=1000)


class DocumentoCreate(BaseModel):
    categoria_id: int = Field(gt=0)
    nome: str = Field(min_length=1, max_length=200)
    observacao: str | None = Field(default=None, max_length=2000)
    competencia_inicio: int = Field(ge=190001, le=299912)
    competencia_fim: int | None = Field(default=None, ge=190001, le=299912)

    @model_validator(mode="after")
    def validar_periodo(self):
        for competencia in (self.competencia_inicio, self.competencia_fim):
            if competencia is not None and competencia % 100 not in range(1, 13):
                raise ValueError("A competência deve estar no formato YYYYMM.")
        if self.competencia_fim is not None and self.competencia_fim < self.competencia_inicio:
            raise ValueError("A competência final não pode ser anterior à inicial.")
        return self


class AtribuicaoItem(BaseModel):
    empresa_id: int = Field(gt=0)
    responsavel_id: int | None = Field(default=None, gt=0)
    confirmar_transferencia: bool = False
    motivo: str | None = Field(default=None, max_length=1000)


class AtribuicaoLote(BaseModel):
    alteracoes: list[AtribuicaoItem] = Field(min_length=1, max_length=500)


class DocumentoUpdate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    categoria_id: int = Field(gt=0)
    observacao: str | None = Field(default=None, max_length=2000)


class DocumentoInativar(BaseModel):
    competencia_fim: int = Field(ge=190001, le=299912)
    motivo: str = Field(min_length=1, max_length=500)
    observacao: str | None = Field(default=None, max_length=2000)


class ArquivoRename(BaseModel):
    nome: str = Field(min_length=1, max_length=255)


class ArquivoDelete(BaseModel):
    motivo: str | None = Field(default=None, max_length=500)
