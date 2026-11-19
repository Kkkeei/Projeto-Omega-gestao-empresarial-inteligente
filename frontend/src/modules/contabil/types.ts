export type RegimeContabil = 'SIMPLES NACIONAL' | 'LUCRO PRESUMIDO' | 'LUCRO REAL' | string;
export type StatusDocumentacao = 'SEM_RECEBIMENTO' | 'PARCIAL' | 'COMPLETA';
export type StatusObrigacao = 'RECEBIDO' | 'PENDENTE' | 'NAO_RECEBIDO' | 'DOCUMENTO_NAO_RECEBIDO' | 'FUTURO' | 'INATIVO';

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

export type SituacaoLancamentos =
  | 'CONCLUIDO'
  | 'EM_ANDAMENTO'
  | 'PENDENTE'
  | 'ATRASADO'
  | 'SEM_MOVIMENTACOES';
export type IndicadorLancamentos = 'VERDE' | 'AZUL' | 'LARANJA' | 'VERMELHO' | 'CINZA';

export interface EmpresaLancamentos {
  id: number;
  razao_social: string;
  nome_fantasia?: string | null;
  cnpj: string;
  regime_tributario?: RegimeContabil | null;
  responsavel_id?: number | null;
  responsavel_nome?: string | null;
  movimentacoes_total: number;
  movimentacoes_concluidas: number;
  progresso_percentual: number;
  movimentacoes_atrasadas: number;
  aguardando_documento: number;
  situacao: SituacaoLancamentos;
  indicador: IndicadorLancamentos;
  descricao_situacao: string;
}

export interface DashboardLancamentosResponse {
  competencia: number;
  resumo: Pick<ContabilResumo, 'total_empresas' | 'simples_nacional' | 'lucro_presumido' | 'lucro_real'>;
  empresas: EmpresaLancamentos[];
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
  obrigacoes_nao_recebidas?: number;
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
  nao_recebido_confirmado: boolean;
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
  competencias_ano?: Array<{ mes: number; status: 'COMPLETA' | 'PARCIAL' | 'SEM_RECEBIMENTO' | 'FUTURA' | 'SEM_DOCUMENTACAO' }>;
  resumo: {
    total: number;
    recebidos: number;
    pendentes: number;
    nao_recebidos: number;
  };
}


export interface MovimentacaoCompetencia {
  competencia_id: number;
  movimentacao_id: number;
  empresa_id: number;
  competencia: number;
  data_limite?: string | null;
  aplicavel: boolean;
  ativa: boolean;
  justificativa_nao_aplicavel?: string | null;
  lancado: boolean;
  conferido: boolean;
  lancado_por?: number | null;
  lancado_em?: string | null;
  conferido_por?: number | null;
  conferido_em?: string | null;
  nome: string;
  origem: 'DOCUMENTACAO' | 'LANCAMENTOS_CONFERENCIAS';
  categoria_id?: number | null;
  categoria_nome?: string | null;
  documento_origem_id?: number | null;
  obrigacao_id?: number | null;
  documento_disponivel: boolean;
  recebido: boolean;
  quantidade_arquivos: number;
  status_documento: 'AGUARDANDO_DOCUMENTO' | 'DOCUMENTO_NAO_RECEBIDO' | 'RECEBIDO' | 'NAO_SE_APLICA';
  nao_recebido_confirmado: boolean;
  concluida: boolean;
}

export interface EmpresaLancamentosDetalhe {
  empresa: EmpresaLancamentos;
  competencia: number;
  movimentacoes: MovimentacaoCompetencia[];
  categorias: Array<{ id: number; nome: string; ordem: number }>;
  competencias_ano?: Array<{ mes: number; status: 'COMPLETA' | 'PARCIAL' | 'SEM_RECEBIMENTO' | 'FUTURA' | 'SEM_DOCUMENTACAO' }>;
  resumo: { total: number; concluidas: number; pendentes: number; aguardando_documento: number; progresso_percentual: number };
}
