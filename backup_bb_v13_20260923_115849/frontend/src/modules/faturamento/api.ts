import { API_URL, apiFetch } from '../../services/api/client';

/* =========================================================
   TIPOS
   ========================================================= */

export type PeriodicidadeFaturamento =
  | 'Mensal'
  | 'Trimestral'
  | 'Semestral'
  | 'Anual'
  | 'Personalizado';

export type Competencia = {
  ano: number;
  mes: number;
  nome: string;
  label: string;
};

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

export type DashboardFaturamento = {
  competencia: Competencia;
  competencia_pendente?: Competencia | null;

  indicadores: {
    total_empresas: number;
    faturamentos_pendentes: number;
    faturamentos_informados: number;
    valor_competencia: number;
    regimes: Record<string, number>;
  };

  empresas: FaturamentoEmpresa[];
};

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

    primeiro_faturamento?: {
      competencia_ano: number;
      competencia_mes: number;
      valor: number;
    } | null;

    ultimo_faturamento?: {
      competencia_ano: number;
      competencia_mes: number;
      valor: number;
    } | null;
  };

  declaracoes: DeclaracaoFaturamento[];
};

/* =========================================================
   EMPRESAS
   ========================================================= */

export async function listarEmpresasFaturamento(
  params?: {
    regime?: string;
    busca?: string;
    ano?: number;
    mes?: number;
  }
): Promise<DashboardFaturamento> {
  const query = new URLSearchParams();

  if (params?.regime && params.regime !== 'TODOS') {
    query.set('regime', params.regime);
  }

  if (params?.busca?.trim()) {
    query.set('busca', params.busca.trim());
  }

  if (params?.ano !== undefined) {
    query.set('ano', String(params.ano));
  }

  if (params?.mes !== undefined) {
    query.set('mes', String(params.mes));
  }

  const qs = query.toString();

  return apiFetch<DashboardFaturamento>(
    `/api/v1/faturamento/empresas${qs ? `?${qs}` : ''}`
  );
}

/* =========================================================
   EMPRESA / FATURAMENTO
   ========================================================= */

export async function obterEmpresaFaturamento(
  empresaId: number,
  ano?: number
): Promise<EmpresaFaturamento> {
  const qs =
    ano !== undefined
      ? `?ano=${encodeURIComponent(String(ano))}`
      : '';

  return apiFetch<EmpresaFaturamento>(
    `/api/v1/empresas/${empresaId}/faturamento${qs}`
  );
}

/* =========================================================
   CRIAR FATURAMENTO
   ========================================================= */

export async function criarFaturamento(data: {
  empresa_id: number;
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string;
  data_faturamento?: string | null;
  periodicidade?: PeriodicidadeFaturamento;
}): Promise<Faturamento> {
  return apiFetch<Faturamento>(
    `/api/v1/empresas/${data.empresa_id}/faturamento`,
    {
      method: 'POST',
      body: JSON.stringify({
        empresa_id: data.empresa_id,
        competencia_ano: data.competencia_ano,
        competencia_mes: data.competencia_mes,
        valor: data.valor,
        observacao: data.observacao ?? null,
        data_faturamento: data.data_faturamento ?? null,
        periodicidade: data.periodicidade ?? 'Mensal',
      }),
    }
  );
}

/* =========================================================
   CRIAR VÁRIOS FATURAMENTOS
   ========================================================= */

export async function criarFaturamentosLote(
  empresaId: number,
  itens: Array<{
    competencia_ano: number;
    competencia_mes: number;
    valor: number;
    observacao?: string;
    data_faturamento?: string | null;
    periodicidade?: PeriodicidadeFaturamento;
  }>
): Promise<{
  meses_atualizados: number;
  valor_total: number;
  itens?: Faturamento[];
}> {
  return apiFetch<{
    meses_atualizados: number;
    valor_total: number;
    itens?: Faturamento[];
  }>(
    `/api/v1/empresas/${empresaId}/faturamento/lote`,
    {
      method: 'POST',
      body: JSON.stringify({
        itens,
      }),
    }
  );
}

/* =========================================================
   ATUALIZAR FATURAMENTO
   ========================================================= */

export async function atualizarFaturamento(
  id: number,
  data: {
    valor: number;
    observacao?: string;
    data_faturamento?: string | null;
    periodicidade?: PeriodicidadeFaturamento;
  }
): Promise<Faturamento> {
  return apiFetch<Faturamento>(
    `/api/v1/faturamentos/${id}`,
    {
      method: 'PUT',
      body: JSON.stringify({
        valor: data.valor,
        observacao: data.observacao ?? null,
        data_faturamento: data.data_faturamento ?? null,
        periodicidade: data.periodicidade ?? 'Mensal',
      }),
    }
  );
}

/* =========================================================
   OBSERVAÇÃO DA EMPRESA
   ========================================================= */

export async function atualizarObservacaoEmpresaFaturamento(
  empresaId: number,
  observacao: string
): Promise<{
  id: number;
  observacoes?: string | null;
}> {
  return apiFetch<{
    id: number;
    observacoes?: string | null;
  }>(
    `/api/v1/empresas/${empresaId}/faturamento/observacao`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        observacao,
      }),
    }
  );
}

/* =========================================================
   DECLARAÇÕES
   ========================================================= */

export async function gerarDeclaracao12Meses(
  empresaId: number
): Promise<DeclaracaoFaturamento> {
  return apiFetch<DeclaracaoFaturamento>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/12-meses`,
    {
      method: 'POST',
      body: JSON.stringify({}),
    }
  );
}

export async function gerarDeclaracaoAnual(
  empresaId: number,
  ano: number
): Promise<DeclaracaoFaturamento> {
  return apiFetch<DeclaracaoFaturamento>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/anual`,
    {
      method: 'POST',
      body: JSON.stringify({
        ano,
      }),
    }
  );
}

export async function gerarDeclaracaoPersonalizada(
  empresaId: number,
  data: {
    ano_inicio: number;
    mes_inicio: number;
    ano_fim: number;
    mes_fim: number;
  }
): Promise<DeclaracaoFaturamento> {
  return apiFetch<DeclaracaoFaturamento>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/personalizada`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  );
}

/* =========================================================
   LISTAR DECLARAÇÕES
   ========================================================= */

export async function listarDeclaracoesFaturamento(
  empresaId: number
): Promise<{
  declaracoes: DeclaracaoFaturamento[];
}> {
  return apiFetch<{
    declaracoes: DeclaracaoFaturamento[];
  }>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento`
  );
}

/* =========================================================
   DETALHE DA DECLARAÇÃO
   ========================================================= */

export async function obterDeclaracao(
  declaracaoId: number
): Promise<DeclaracaoFaturamento> {
  return apiFetch<DeclaracaoFaturamento>(
    `/api/v1/declaracoes-faturamento/${declaracaoId}`
  );
}

/* =========================================================
   URLS DE PDF
   ========================================================= */

export function declaracaoVisualizacaoUrl(
  declaracaoId: number
): string {
  return `${API_URL}/api/v1/declaracoes-faturamento/${declaracaoId}/visualizar`;
}

export function declaracaoDownloadUrl(
  declaracaoId: number
): string {
  return `${API_URL}/api/v1/declaracoes-faturamento/${declaracaoId}/download`;
}

/* =========================================================
   FETCH AUTENTICADO DO PDF
   ========================================================= */

async function obterPdfDeclaracao(
  id: number
): Promise<{
  blob: Blob;
  contentDisposition: string;
}> {
  const token = localStorage.getItem('omega_access_token');

  const controller = new AbortController();

  const timeout = window.setTimeout(() => {
    controller.abort();
  }, 30000);

  try {
    const response = await fetch(
      declaracaoVisualizacaoUrl(id),
      {
        method: 'GET',

        headers: {
          ...(token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {}),
        },

        credentials: 'include',

        signal: controller.signal,
      }
    );

    if (response.status === 401) {
      throw new Error(
        'Sua sessão não está autenticada. Faça login novamente na ÔMEGA.'
      );
    }

    if (response.status === 404) {
      throw new Error(
        'A declaração ou o arquivo PDF não foi encontrado.'
      );
    }

    if (!response.ok) {
      let detalhe =
        'Não foi possível acessar a declaração.';

      try {
        const contentType =
          response.headers.get('content-type') || '';

        if (contentType.includes('application/json')) {
          const data = await response.json();

          if (
            data &&
            typeof data.detail === 'string'
          ) {
            detalhe = data.detail;
          }
        }
      } catch {
        // ignora erro na leitura da mensagem
      }

      throw new Error(detalhe);
    }

    const blob = await response.blob();

    return {
      blob,

      contentDisposition:
        response.headers.get(
          'content-disposition'
        ) || '',
    };
  } catch (error) {
    if (
      error instanceof DOMException &&
      error.name === 'AbortError'
    ) {
      throw new Error(
        'O backend demorou mais de 30 segundos para gerar ou localizar o PDF.'
      );
    }

    if (error instanceof Error) {
      throw error;
    }

    throw new Error(
      'Não foi possível acessar o PDF da declaração.'
    );
  } finally {
    window.clearTimeout(timeout);
  }
}

/* =========================================================
   NOME DO ARQUIVO
   ========================================================= */

function nomeArquivoDeclaracao(
  contentDisposition: string,
  fallback: string
): string {
  const utf8 =
    contentDisposition.match(
      /filename\*=UTF-8''([^;]+)/i
    );

  if (utf8?.[1]) {
    try {
      return decodeURIComponent(
        utf8[1].replace(/["']/g, '')
      );
    } catch {
      return utf8[1].replace(/["']/g, '');
    }
  }

  const simples =
    contentDisposition.match(
      /filename="([^"]+)"/i
    );

  if (simples?.[1]) {
    return simples[1];
  }

  const simplesSemAspas =
    contentDisposition.match(
      /filename=([^;]+)/i
    );

  if (simplesSemAspas?.[1]) {
    return simplesSemAspas[1].trim();
  }

  return fallback;
}

/* =========================================================
   VISUALIZAR DECLARAÇÃO
   ========================================================= */

export async function visualizarDeclaracao(
  id: number
): Promise<void> {
  const { blob } =
    await obterPdfDeclaracao(id);

  const url =
    URL.createObjectURL(blob);

  const novaAba =
    window.open(
      '',
      '_blank'
    );

  if (!novaAba) {
    URL.revokeObjectURL(url);

    throw new Error(
      'O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.'
    );
  }

  novaAba.location.href = url;

  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 60_000);
}

/* =========================================================
   BAIXAR DECLARAÇÃO
   ========================================================= */

export async function baixarDeclaracao(
  id: number,
  nome?: string
): Promise<void> {
  const {
    blob,
    contentDisposition,
  } =
    await obterPdfDeclaracao(id);

  const url =
    URL.createObjectURL(blob);

  const a =
    document.createElement('a');

  a.href = url;

  a.download =
    nome ||
    nomeArquivoDeclaracao(
      contentDisposition,
      `declaracao_faturamento_${id}.pdf`
    );

  document.body.appendChild(a);

  a.click();

  a.remove();

  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 1_000);
}

/* =========================================================
   EXPORTAÇÃO AUXILIAR
   ========================================================= */

export const faturamentoApi = {
  listarEmpresasFaturamento,
  obterEmpresaFaturamento,

  criarFaturamento,
  criarFaturamentosLote,
  atualizarFaturamento,

  atualizarObservacaoEmpresaFaturamento,

  gerarDeclaracao12Meses,
  gerarDeclaracaoAnual,
  gerarDeclaracaoPersonalizada,

  listarDeclaracoesFaturamento,
  obterDeclaracao,

  visualizarDeclaracao,
  baixarDeclaracao,

  declaracaoVisualizacaoUrl,
  declaracaoDownloadUrl,
};
/* =========================================================
   BANCO DO BRASIL
   ========================================================= */

export type BancoBrasilConfig = {
  percentual_a_vista: number;
  percentual_a_prazo: number;
  percentual_cartao?: number | null;
  percentual_cheque?: number | null;
  percentual_boleto?: number | null;
  prazo_medio_dias?: number | null;
};

export async function gerarDeclaracaoBancoBrasil(
  empresaId: number,
  data: Partial<BancoBrasilConfig> = {},
): Promise<DeclaracaoFaturamento> {
  return apiFetch<DeclaracaoFaturamento>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/banco-brasil`,
    {
      method: 'POST',
      body: JSON.stringify({
        percentual_a_vista: 20,
        percentual_a_prazo: 80,
        ...data,
      }),
    }
  );
}
