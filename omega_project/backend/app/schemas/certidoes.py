from typing import Optional
from pydantic import BaseModel, Field


class CertidaoCreate(BaseModel):
    empresa_id: int
    tipo_certidao_id: int
    situacao: str = Field(min_length=1)
    numero_certidao: Optional[str] = None
    data_emissao: Optional[str] = None
    data_validade: Optional[str] = None
    pdf_path: Optional[str] = None
    origem: Optional[str] = "MANUAL"
    observacao: Optional[str] = None
    mensagem: Optional[str] = None
    pendencia: bool = False
    pendencia_detalhes: Optional[str] = None
    nome_arquivo_original: Optional[str] = None
    status_processamento: Optional[str] = None
    erro_tecnico: Optional[str] = None


class CertidaoOut(BaseModel):
    id: int
    empresa_id: int
    tipo_certidao_id: int
    tipo_certidao: str
    situacao: str
    numero_certidao: Optional[str] = None
    data_emissao: Optional[str] = None
    data_validade: Optional[str] = None
    documento_id: Optional[int] = None
    origem: Optional[str] = None
    observacao: Optional[str] = None
    atualizada_em: str
