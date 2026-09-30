from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EmpresaBase(BaseModel):
    cnpj: str = Field(min_length=11, max_length=18)
    razao_social: str = Field(min_length=1)
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    email: Optional[str] = None
    nire: Optional[str] = None
    regime_tributario: Optional[str] = None
    data_entrada: Optional[str] = None
    data_saida: Optional[str] = None
    data_abertura: Optional[str] = None
    natureza_juridica: Optional[str] = None
    porte: Optional[str] = None
    capital_social: Optional[float] = None
    cnae_principal: Optional[str] = None
    cnaes_secundarios: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    municipio: Optional[str] = None
    codigo_ibge: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    responsavel: Optional[str] = None
    segmento: Optional[str] = None
    grupo_empresarial: Optional[str] = None
    observacoes: Optional[str] = None


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome_fantasia: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    email: Optional[str] = None
    nire: Optional[str] = None
    data_entrada: Optional[str] = None
    data_abertura: Optional[str] = None
    natureza_juridica: Optional[str] = None
    porte: Optional[str] = None
    capital_social: Optional[float] = None
    cnae_principal: Optional[str] = None
    cnaes_secundarios: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    municipio: Optional[str] = None
    codigo_ibge: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    responsavel: Optional[str] = None
    segmento: Optional[str] = None
    grupo_empresarial: Optional[str] = None
    observacoes: Optional[str] = None


class InativarEmpresa(BaseModel):
    data_saida: str
    observacao: Optional[str] = None


class AlterarRegime(BaseModel):
    regime_tributario: str
    mes_inicio: int = Field(ge=1, le=12)
    ano_inicio: int = Field(ge=2000, le=2100)
    observacao: Optional[str] = None


class EmpresaOut(EmpresaBase):
    id: int
    ativo: bool
    criado_em: str
    atualizado_em: str
    ultima_sincronizacao: Optional[str] = None
