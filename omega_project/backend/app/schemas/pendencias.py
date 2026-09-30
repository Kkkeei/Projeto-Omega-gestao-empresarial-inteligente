from typing import Optional
from pydantic import BaseModel


class PendenciaCreate(BaseModel):
    empresa_id: int
    tipo: str
    origem: Optional[str] = None
    titulo: str
    descricao: Optional[str] = None
    status: str = "ABERTA"
    prioridade: str = "NORMAL"
    data_identificacao: Optional[str] = None
    prazo: Optional[str] = None
    observacao: Optional[str] = None


class PendenciaUpdate(BaseModel):
    descricao: Optional[str] = None
    status: Optional[str] = None
    prioridade: Optional[str] = None
    prazo: Optional[str] = None
    data_resolucao: Optional[str] = None
    observacao: Optional[str] = None

