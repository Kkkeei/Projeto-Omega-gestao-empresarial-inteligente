export type RegimeContabil = 'SIMPLES NACIONAL' | 'LUCRO PRESUMIDO' | 'LUCRO REAL' | string;
export type StatusDocumentacao = 'SEM_RECEBIMENTO' | 'PARCIAL' | 'COMPLETA';
export type StatusObrigacao = 'RECEBIDO' | 'PENDENTE' | 'NAO_RECEBIDO' | 'FUTURO';

export interface ResponsavelContabil {
  id: number;
  nome: string;
  email: string;
  perfil: 'ADMIN' | 'USUARIO';
  ativo: boolean;
  empresas_atribuidas: number;
}

export interface EmpresaContabil {
  id: number;
  razao_social: string;
  nome_fantasia?: string | null;
  cnpj: string;
  regime_tributario?: RegimeContabil | null;
  ativo: boolean;
  documentos_recebidos: number;
  documentos_total: number;
  status_documentacao: StatusDocumentacao;
  responsavel_id?: number | null;
  responsavel_nome?: string | null;
}

export interface ContabilResumo {
  total_empresas: number;
  simples_nacional: number;
  lucro_presumido: number;
  lucro_real: number;
  documentacao_completa: number;
  documentacao_parcial: number;
  sem_recebimento: number;
}

export interface DashboardContabilResponse {
  competencia: number;
  resumo: ContabilResumo;
  empresas: EmpresaContabil[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface AtribuicaoAlteracao {
  empresa_id: number;
  responsavel_id: number | null;
  confirmar_transferencia: boolean;
  motivo?: string | null;
}

export interface AtribuicaoLoteResponse {
  alteradas: number;
  atribuicoes: Array<{ empresa_id: number; responsavel_id: number | null; responsavel_nome?: string | null }>;
}

export interface CategoriaContabil {
  id: number;
  empresa_id: number;
  nome: string;
  descricao?: string | null;
  ordem: number;
  ativo: boolean;
  documentos_count: number;
  obrigacoes_pendentes: number;
  obrigacoes_recebidas: number;
}

export interface ArquivoContabil {
  id: number;
  obrigacao_id: number;
  nome_original: string;
  tamanho: number;
  mime_type?: string | null;
  enviado_em: string;
  enviado_por_nome?: string | null;
}

export interface DocumentoContabil {
  id: number;
  empresa_id: number;
  categoria_id: number;
  categoria_nome: string;
  nome: string;
  observacao?: string | null;
  competencia_inicio: number;
  competencia_fim?: number | null;
  ativo: boolean;
  obrigacao_id: number;
  status: StatusObrigacao;
  quantidade_arquivos: number;
  ultimo_upload?: string | null;
  arquivos?: ArquivoContabil[];
}

export interface EmpresaDocumentacaoContabilResponse {
  empresa: {
    id: number;
    razao_social: string;
    nome_fantasia?: string | null;
    cnpj: string;
    regime_tributario?: string | null;
  };
  competencia: number;
  categorias: CategoriaContabil[];
  documentos: DocumentoContabil[];
  competencias_ano?: Array<{ mes: number; status: 'COMPLETA' | 'PARCIAL' | 'SEM_RECEBIMENTO' | 'FUTURA' }>;
  resumo: {
    total: number;
    recebidos: number;
    pendentes: number;
    nao_recebidos: number;
  };
}
