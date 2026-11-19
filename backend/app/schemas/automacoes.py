from typing import Optional
from pydantic import BaseModel


class AutomacaoExecutar(BaseModel):
    tipo: str
    empresa_id: Optional[int] = None
    automacao_id: Optional[int] = None
    configuracao: Optional[dict] = None
