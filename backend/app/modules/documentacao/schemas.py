from pydantic import BaseModel, Field

class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: str | None = Field(default=None, max_length=500)
    categoria_pai_id: int | None = None

class CategoriaOut(BaseModel):
    id: int
    empresa_id: int
    categoria_pai_id: int | None
    nome: str
    descricao: str | None
    ordem: int
    ativo: int
    documentos_count: int = 0

class DocumentoOut(BaseModel):
    id: int
    empresa_id: int
    categoria_id: int | None
    nome: str
    descricao: str | None
    categoria_nome: str | None
    versoes_count: int
    ultima_versao: int | None
    nome_arquivo: str | None
    criado_em: str
    atualizado_em: str
