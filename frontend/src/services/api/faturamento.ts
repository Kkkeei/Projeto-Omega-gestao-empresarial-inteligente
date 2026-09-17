import {apiFetch} from './client';

export type FaturamentoEmpresa = {
  id: number;
  cnpj: string;
  razao_social: string;
  nome_fantasia?: string | null;
  regime_tributario?: string | null;
  ativo: number;
  status_competencia: 'pendente' | 'informado';
  valor_competencia?: number | null;
  ultima_competencia_ano?: number | null;
  ultima_competencia_mes?: number | null;
  ultimo_valor?: number | null;
};

export type CompetenciaPendente = {
  ano: number;
  mes: number;
  nome: string;
  label: string;
};

export type DashboardFaturamento = {
  competencia_pendente: CompetenciaPendente;
  empresas: FaturamentoEmpresa[];
};

export type Faturamento = {
  id: number;
  empresa_id: number;
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string | null;
  criado_em: string;
  atualizado_em: string;
};

export type DeclaracaoFaturamento = {
  id: number;
  empresa_id: number;
  tipo: string;
  periodo_inicio: string;
  periodo_fim: string;
  valor_total: number;
  nome_arquivo: string;
  caminho_arquivo: string;
  usuario_id: number | null;
  usuario_nome?: string | null;
  data_geracao: string;
};

export type EmpresaFaturamento = {
  empresa: {
    id: number;
    cnpj: string;
    razao_social: string;
    nome_fantasia?: string | null;
    regime_tributario?: string | null;
    ativo: number;
  };
  faturamentos: Faturamento[];
  resumo: {
    quantidade_lancamentos: number;
    valor_total: number;
    ultimo_faturamento?: {
      competencia_ano: number;
      competencia_mes: number;
      valor: number;
    } | null;
  };
  declaracoes: DeclaracaoFaturamento[];
};

export async function listarEmpresasFaturamento(params?: {
  regime?: string;
  busca?: string;
}) {
  const query = new URLSearchParams();
  if (params?.regime) query.set('regime', params.regime);
  if (params?.busca?.trim()) query.set('busca', params.busca.trim());
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<DashboardFaturamento>(`/api/v1/faturamento/empresas${suffix}`);
}

export async function obterEmpresaFaturamento(empresaId: number) {
  return apiFetch<EmpresaFaturamento>(`/api/v1/empresas/${empresaId}/faturamento`);
}

export async function criarFaturamento(data: {
  empresa_id: number;
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string;
}) {
  return apiFetch<Faturamento>(`/api/v1/empresas/${data.empresa_id}/faturamento`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function atualizarFaturamento(id: number, data: {valor: number; observacao?: string}) {
  return apiFetch<Faturamento>(`/api/v1/faturamentos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function gerarDeclaracao12Meses(empresaId: number) {
  return apiFetch<DeclaracaoFaturamento>(`/api/v1/empresas/${empresaId}/declaracoes-faturamento/12-meses`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export async function gerarDeclaracaoAnual(empresaId: number, ano: number) {
  return apiFetch<DeclaracaoFaturamento>(`/api/v1/empresas/${empresaId}/declaracoes-faturamento/anual`, {
    method: 'POST',
    body: JSON.stringify({ano}),
  });
}

export async function gerarDeclaracaoPersonalizada(empresaId: number, data: {
  ano_inicio: number;
  mes_inicio: number;
  ano_fim: number;
  mes_fim: number;
}) {
  return apiFetch<DeclaracaoFaturamento>(`/api/v1/empresas/${empresaId}/declaracoes-faturamento/personalizada`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function declaracaoVisualizacaoUrl(id: number) {
  return `${location.origin.replace(/:5173$/, ':8000')}/api/v1/declaracoes-faturamento/${id}/visualizar`;
}

export function declaracaoDownloadUrl(id: number) {
  return `${location.origin.replace(/:5173$/, ':8000')}/api/v1/declaracoes-faturamento/${id}/download`;
}
