import { apiFetch, API_URL } from '../../services/api/client';

export type EmpresaFaturamento = {
  id: number;
  cnpj: string;
  razao_social: string;
  nome_fantasia?: string | null;
  regime_tributario?: string | null;
  status_competencia: 'pendente' | 'informado';
  valor_competencia?: number | null;
  ultima_competencia_ano?: number | null;
  ultima_competencia_mes?: number | null;
  ultimo_valor?: number | null;
};

export type Faturamento = {
  id: number;
  empresa_id: number;
  competencia_ano: number;
  competencia_mes: number;
  valor: number;
  observacao?: string | null;
  usuario_id?: number | null;
  usuario_nome?: string | null;
  criado_em?: string | null;
  atualizado_em?: string | null;
};

export type Declaracao = {
  id: number;
  empresa_id: number;
  tipo: string;
  periodo_inicio: string;
  periodo_fim: string;
  valor_total: number;
  nome_arquivo: string;
  caminho_arquivo?: string | null;
  usuario_id?: number | null;
  usuario_nome?: string | null;
  data_geracao: string;
};

export type ListaEmpresasResponse = {
  competencia_pendente: {
    ano: number;
    mes: number;
    nome: string;
    label: string;
  };
  empresas: EmpresaFaturamento[];
};

export type EmpresaFaturamentoResponse = {
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
  declaracoes: Declaracao[];
};

function queryString(params: Record<string, string | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([chave, valor]) => {
    if (valor) search.set(chave, valor);
  });
  const texto = search.toString();
  return texto ? `?${texto}` : '';
}

export const listarEmpresas = (regime?: string, busca?: string) =>
  apiFetch<ListaEmpresasResponse>(
    `/api/v1/faturamento/empresas${queryString({ regime, busca })}`,
  );

export const consultarEmpresa = (empresaId: number) =>
  apiFetch<EmpresaFaturamentoResponse>(
    `/api/v1/empresas/${empresaId}/faturamento`,
  );

export const salvarFaturamento = (
  empresaId: number,
  dados: {
    empresa_id: number;
    competencia_ano: number;
    competencia_mes: number;
    valor: number;
    observacao?: string;
  },
) =>
  apiFetch<Faturamento>(
    `/api/v1/empresas/${empresaId}/faturamento`,
    {
      method: 'POST',
      body: JSON.stringify(dados),
    },
  );

export const editarFaturamento = (
  faturamentoId: number,
  dados: { valor: number; observacao?: string },
) =>
  apiFetch<Faturamento>(
    `/api/v1/faturamentos/${faturamentoId}`,
    {
      method: 'PUT',
      body: JSON.stringify(dados),
    },
  );

export const gerar12Meses = (empresaId: number) =>
  apiFetch<Declaracao>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/12-meses`,
    { method: 'POST' },
  );

export const gerarAnual = (empresaId: number, ano: number) =>
  apiFetch<Declaracao>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/anual`,
    {
      method: 'POST',
      body: JSON.stringify({ ano }),
    },
  );

export const gerarPersonalizada = (
  empresaId: number,
  dados: {
    ano_inicio: number;
    mes_inicio: number;
    ano_fim: number;
    mes_fim: number;
  },
) =>
  apiFetch<Declaracao>(
    `/api/v1/empresas/${empresaId}/declaracoes-faturamento/personalizada`,
    {
      method: 'POST',
      body: JSON.stringify(dados),
    },
  );

async function arquivoBlob(url: string) {
  const token = localStorage.getItem('omega_access_token');
  const resposta = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!resposta.ok) {
    let detalhe = 'Não foi possível acessar o arquivo.';
    try {
      const erro = await resposta.json();
      detalhe = erro?.detail || detalhe;
    } catch {
      // Mantém a mensagem padrão.
    }
    throw new Error(detalhe);
  }

  return resposta.blob();
}

export async function visualizarDeclaracao(id: number) {
  const blob = await arquivoBlob(urlVisualizarDeclaracao(id));
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener,noreferrer');
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export async function baixarDeclaracao(id: number, nome?: string) {
  const blob = await arquivoBlob(urlDownloadDeclaracao(id));
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nome || 'declaracao-faturamento.pdf';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 2_000);
}

export function urlVisualizarDeclaracao(id: number) {
  return `${API_URL}/api/v1/declaracoes-faturamento/${id}/visualizar`;
}

export function urlDownloadDeclaracao(id: number) {
  return `${API_URL}/api/v1/declaracoes-faturamento/${id}/download`;
}
