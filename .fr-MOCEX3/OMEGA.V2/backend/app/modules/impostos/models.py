from dataclasses import dataclass
from typing import Optional


@dataclass
class Tributo:
    id: Optional[int] = None
    nome: str = ""
    sigla: Optional[str] = None
    esfera: Optional[str] = None
    categoria: Optional[str] = None
    periodicidade: Optional[str] = None
    descricao: Optional[str] = None
    ativo: int = 1


@dataclass
class EmpresaImposto:
    id: Optional[int] = None
    empresa_id: int = 0
    tributo_id: int = 0
    regime_tributario: Optional[str] = None
    obrigatorio: int = 1
    vigencia_inicio: Optional[str] = None
    vigencia_fim: Optional[str] = None
    status: str = "ATIVO"
    observacao: Optional[str] = None


@dataclass
class ImpostoMensal:
    id: Optional[int] = None
    empresa_id: int = 0
    tributo_id: int = 0
    competencia_ano: int = 0
    competencia_mes: int = 0
    status: str = "PENDENTE"
    valor: Optional[float] = None
    data_vencimento: Optional[str] = None
    data_pagamento: Optional[str] = None
    numero_documento: Optional[str] = None
    observacao: Optional[str] = None


@dataclass
class DocumentoImposto:
    id: Optional[int] = None
    imposto_mensal_id: int = 0
    nome_arquivo: str = ""
    caminho_arquivo: str = ""
    extensao: Optional[str] = None
    mime_type: Optional[str] = None
    tamanho: Optional[int] = None
    hash_arquivo: Optional[str] = None
    observacao: Optional[str] = None


@dataclass
class NotificacaoImposto:
    id: Optional[int] = None
    empresa_id: int = 0
    imposto_mensal_id: Optional[int] = None
    tipo: str = ""
    titulo: str = ""
    mensagem: Optional[str] = None
    prioridade: str = "NORMAL"
    status: str = "PENDENTE"
    prazo: Optional[str] = None
    lida_em: Optional[str] = None
