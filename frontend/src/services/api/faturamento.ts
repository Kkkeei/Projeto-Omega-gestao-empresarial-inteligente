import {apiFetch} from './client';

export type FaturamentoEmpresa = {
  id: number;
  cnpj: string;
  razao_social: string;
  nome_fantasia?: string | null;
  nire?: string | null;
  regime_tributario?: string | null;
  ativo: number;
  status_competencia: 'pendente' | 'informado';
  valor_competencia?: number | null;
  faturamento_competencia_id?: number | null;
  ultima_competencia_ano?: number | null;
  ultima_competencia_mes?: number | null;
  ultimo_valor?: number | null;
  data_faturamento_competencia?: string | null;
  periodicidade_competencia?: PeriodicidadeFaturamento;
  observacao_competencia?: string | null;
  meses_pendentes?: number[];
  quantidade_meses_pendentes?: number;
};

export type Competencia = {
  ano: number;
  mes: number;
  nome: string;
  label: string;
};

export type DashboardFaturamento = {
  competencia: Competencia;
  competencia_pendente?: Competencia;
  indicadores: {
    total_empresas: number;
    faturamentos_pendentes: number;
    faturamentos_informados: number;
    valor_competencia: number;
    regimes: Record<string, number>;
  };
  empresas: FaturamentoEmpresa[];
};

export type PeriodicidadeFaturamento = 'Mensal' | 'Trimestral' | 'Semestral' | 'Anual' | 'Personalizado';

export type Faturamento = {
  id: number;
  empresa_id: number;
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string | null;
  data_faturamento?: string | null;
  periodicidade: PeriodicidadeFaturamento;
  criado_em: string;
  atualizado_em: string;
};

export type MesFaturamento = {
  id?: number | null;
  competencia_ano: number;
  competencia_mes: number;
  valor?: number | null;
  observacao?: string | null;
  data_faturamento?: string | null;
  periodicidade?: PeriodicidadeFaturamento;
  atualizado_em?: string | null;
  informado: boolean;
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
  ano: number;
  empresa: {
    id: number;
    cnpj: string;
    razao_social: string;
    nome_fantasia?: string | null;
    regime_tributario?: string | null;
    ativo: number;
    observacoes?: string | null;
  };
  faturamentos: Faturamento[];
  competencias: MesFaturamento[];
  resumo: {
    ano: number;
    quantidade_lancamentos: number;
    meses_informados: number;
    percentual_informado: number;
    valor_total: number;
    media_mensal: number;
    primeiro_faturamento?: {competencia_ano:number;competencia_mes:number;valor:number} | null;
    ultimo_faturamento?: {competencia_ano:number;competencia_mes:number;valor:number} | null;
  };
  declaracoes: DeclaracaoFaturamento[];
};

export async function listarEmpresasFaturamento(params?: {
  regime?: string;
  busca?: string;
  ano?: number;
  mes?: number;
}) {
  const query = new URLSearchParams();
  if (params?.regime && params.regime !== 'TODOS') query.set('regime', params.regime);
  if (params?.busca?.trim()) query.set('busca', params.busca.trim());
  if (params?.ano) query.set('ano', String(params.ano));
  if (params?.mes) query.set('mes', String(params.mes));
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return apiFetch<DashboardFaturamento>(`/api/v1/faturamento/empresas${suffix}`);
}

export async function obterEmpresaFaturamento(empresaId: number, ano?: number) {
  const suffix = ano ? `?ano=${ano}` : '';
  return apiFetch<EmpresaFaturamento>(`/api/v1/empresas/${empresaId}/faturamento${suffix}`);
}

export async function criarFaturamento(data: {
  empresa_id: number;
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string;
  data_faturamento?: string | null;
  periodicidade?: PeriodicidadeFaturamento;
}) {
  return apiFetch<Faturamento>(`/api/v1/empresas/${data.empresa_id}/faturamento`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function criarFaturamentosLote(empresaId: number, itens: Array<{
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string;
  data_faturamento?: string | null;
  periodicidade?: PeriodicidadeFaturamento;
}>) {
  return apiFetch<{meses_atualizados:number;valor_total:number}>(`/api/v1/empresas/${empresaId}/faturamento/lote`, {
    method: 'POST',
    body: JSON.stringify({itens}),
  });
}

export async function atualizarFaturamento(id: number, data: {valor: number; observacao?: string; data_faturamento?: string | null; periodicidade?: PeriodicidadeFaturamento}) {
  return apiFetch<Faturamento>(`/api/v1/faturamentos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function atualizarObservacaoEmpresaFaturamento(empresaId: number, observacao: string) {
  return apiFetch<{id:number;observacoes?:string|null}>(`/api/v1/empresas/${empresaId}/faturamento/observacao`, {
    method: 'PATCH',
    body: JSON.stringify({observacao}),
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

async function obterPdfDeclaracao(id: number): Promise<{blob: Blob; contentDisposition: string}> {
  const token = localStorage.getItem('omega_access_token');
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(declaracaoVisualizacaoUrl(id), {
      method: 'GET',
      headers: {
        ...(token ? {Authorization: `Bearer ${token}`} : {}),
      },
      credentials: 'include',
      signal: controller.signal,
    });

    if (response.status === 401) {
      throw new Error('Sua sessão não está autenticada. Faça login novamente na ÔMEGA.');
    }
    if (response.status === 404) {
      throw new Error('A declaração ou o arquivo PDF não foi encontrado.');
    }
    if (!response.ok) {
      let detalhe = 'Não foi possível acessar a declaração.';
      try {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const data = await response.json();
          if (data && typeof data.detail === 'string') detalhe = data.detail;
        }
      } catch {
        // ignora erro na leitura da mensagem
      }
      throw new Error(detalhe);
    }

    const blob = await response.blob();
    return {
      blob,
      contentDisposition: response.headers.get('content-disposition') || '',
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('O backend demorou mais de 30 segundos para gerar ou localizar o PDF.');
    }
    if (error instanceof Error) throw error;
    throw new Error('Não foi possível acessar o PDF da declaração.');
  } finally {
    window.clearTimeout(timeout);
  }
}

function nomeArquivoDeclaracao(contentDisposition: string, fallback: string): string {
  const utf8 = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1].replace(/["']/g, ''));
    } catch {
      return utf8[1].replace(/["']/g, '');
    }
  }

  const simples = contentDisposition.match(/filename="([^"]+)"/i);
  if (simples?.[1]) return simples[1];

  const simplesSemAspas = contentDisposition.match(/filename=([^;]+)/i);
  if (simplesSemAspas?.[1]) return simplesSemAspas[1].trim();

  return fallback;
}

export async function visualizarDeclaracao(id: number, target?: Window | null): Promise<void> {
  const novaAba = target ?? window.open('about:blank', '_blank');
  if (!novaAba) {
    throw new Error('O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.');
  }

  try {
    const {blob} = await obterPdfDeclaracao(id);
    const url = URL.createObjectURL(blob);
    novaAba.location.href = url;
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (error) {
    if (!target) novaAba.close();
    throw error;
  }
}

export async function baixarDeclaracao(id: number, nome?: string): Promise<void> {
  const {blob, contentDisposition} = await obterPdfDeclaracao(id);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nome || nomeArquivoDeclaracao(contentDisposition, `declaracao_faturamento_${id}.pdf`);
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
