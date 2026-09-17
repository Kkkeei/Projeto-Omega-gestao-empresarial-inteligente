from pydantic import BaseModel, Field


class FaturamentoCreate(BaseModel):
    empresa_id: int
    competencia_ano: int = Field(..., ge=2000, le=2100)
    competencia_mes: int = Field(..., ge=1, le=12)
    valor: float = Field(..., ge=0)
    observacao: str | None = None


class FaturamentoUpdate(BaseModel):
    valor: float = Field(..., ge=0)
    observacao: str | None = None


class DeclaracaoAnualCreate(BaseModel):
    ano: int = Field(..., ge=2000, le=2100)


class DeclaracaoPersonalizadaCreate(BaseModel):
    ano_inicio: int = Field(..., ge=2000, le=2100)
    mes_inicio: int = Field(..., ge=1, le=12)
    ano_fim: int = Field(..., ge=2000, le=2100)
    mes_fim: int = Field(..., ge=1, le=12)
