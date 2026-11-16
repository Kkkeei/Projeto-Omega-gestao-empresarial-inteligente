import { apiFetch, apiFetchBlob } from '../../services/api/client';
import type {
  AtribuicaoAlteracao,
  AtribuicaoLoteResponse,
  CategoriaContabil,
  DashboardContabilResponse,
  DashboardLancamentosResponse,
  EmpresaContabil,
  EmpresaDocumentacaoContabilResponse,
  ResponsavelContabil,
  DocumentoContabil,
  ArquivoContabil,
  EmpresaLancamentosDetalhe,
  MovimentacaoCompetencia,
} from './types';

const BASE = '/api/v1/contabil';

export async function listarPainelLancamentos(params: {
  competencia: number;
  busca?: string;
  regime?: string;
  responsavel_id?: number | 'NAO_ATRIBUIDO' | null;
}) {
  const query = new URLSearchParams();
  query.set('competencia', String(params.competencia));
  query.set('pagina', '1');
  query.set('por_pagina', '500');
  if (params.busca) query.set('busca', params.busca);
  if (params.regime && params.regime !== 'TODOS') query.set('regime', params.regime);
  if (params.responsavel_id === 'NAO_ATRIBUIDO') query.set('sem_responsavel', 'true');
  else if (typeof params.responsavel_id === 'number') query.set('responsavel_id', String(params.responsavel_id));
  return apiFetch<DashboardLancamentosResponse>(BASE + '/lancamentos-conferencias?' + query.toString());
}

export async function listarDashboardContabil(params: {
  competencia: number;
  busca?: string;
  regime?: string;
  responsavel_id?: number | 'NAO_ATRIBUIDO' | null;
  pagina?: number;
  por_pagina?: number;
}) {
  const query = new URLSearchParams();
  query.set('competencia', String(params.competencia));
  query.set('pagina', String(params.pagina ?? 1));
  query.set('por_pagina', String(params.por_pagina ?? 100));
  if (params.busca) query.set('busca', params.busca);
  if (params.regime && params.regime !== 'TODOS') query.set('regime', params.regime);
  if (params.responsavel_id === 'NAO_ATRIBUIDO') query.set('sem_responsavel', 'true');
  else if (typeof params.responsavel_id === 'number') query.set('responsavel_id', String(params.responsavel_id));
  return apiFetch<DashboardContabilResponse>(BASE + '/dashboard?' + query.toString());
}

export async function listarResponsaveisContabeis() {
  return apiFetch<{ responsaveis: ResponsavelContabil[] }>(BASE + '/responsaveis');
}

export async function adicionarResponsavel(data: { nome: string; email: string; senha: string }) {
  return apiFetch<ResponsavelContabil>('/api/v1/auth/usuarios', {
    method: 'POST',
    body: JSON.stringify({ ...data, perfil: 'USUARIO' }),
  });
}

export async function removerResponsavel(responsavelId: number) {
  return apiFetch<{ ok: boolean }>(`/api/v1/auth/usuarios/${responsavelId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ ativo: false }),
  });
}

export async function listarEmpresasParaAtribuicao(params: { busca?: string; regime?: string } = {}) {
  const query = new URLSearchParams();
  if (params.busca) query.set('busca', params.busca);
  if (params.regime && params.regime !== 'TODOS') query.set('regime', params.regime);
  query.set('incluir_inativas', 'false');
  return apiFetch<{ empresas: EmpresaContabil[] }>(BASE + '/empresas?' + query.toString());
}

export async function salvarAtribuicoes(alteracoes: AtribuicaoAlteracao[]) {
  return apiFetch<AtribuicaoLoteResponse>(BASE + '/atribuicoes/lote', {
    method: 'POST',
    body: JSON.stringify({ alteracoes }),
  });
}

export async function obterDocumentacaoEmpresa(empresaId: number, competencia: number) {
  const ano = Math.floor(competencia / 100);
  return apiFetch<EmpresaDocumentacaoContabilResponse>(
    BASE + '/empresas/' + empresaId + '/documentacao?competencia=' + competencia + '&ano=' + ano,
  );
}

export async function criarCategoriaContabil(empresaId: number, data: { nome: string; descricao?: string }) {
  return apiFetch<CategoriaContabil>(BASE + '/empresas/' + empresaId + '/categorias', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function atualizarCategoriaContabil(categoriaId: number, data: { nome: string; descricao?: string }) {
  return apiFetch<CategoriaContabil>(BASE + '/categorias/' + categoriaId, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function arquivarCategoriaContabil(categoriaId: number) {
  return apiFetch<{ ok: boolean }>(BASE + '/categorias/' + categoriaId, { method: 'DELETE' });
}

export async function criarDocumentoContabil(
  empresaId: number,
  data: { nome: string; categoria_id: number; competencia_inicio: number; observacao?: string },
) {
  return apiFetch<DocumentoContabil>(BASE + '/empresas/' + empresaId + '/documentos', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function atualizarDocumentoContabil(
  documentoId: number,
  data: { nome: string; categoria_id: number; observacao?: string },
) {
  return apiFetch<DocumentoContabil>(BASE + '/documentos/' + documentoId, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function inativarDocumentoContabil(
  documentoId: number,
  data: { competencia_fim: number; motivo: string; observacao?: string },
) {
  return apiFetch<DocumentoContabil>(BASE + '/documentos/' + documentoId + '/inativar', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function listarArquivosContabeis(obrigacaoId: number) {
  return apiFetch<{ arquivos: ArquivoContabil[] }>(BASE + '/obrigacoes/' + obrigacaoId + '/arquivos');
}

export async function enviarArquivosContabeis(obrigacaoId: number, files: File[]) {
  const form = new FormData();
  files.forEach((file) => form.append('arquivos', file));
  return apiFetch<{ arquivos: ArquivoContabil[] }>(BASE + '/obrigacoes/' + obrigacaoId + '/arquivos', {
    method: 'POST',
    body: form,
    timeoutMs: 60000,
  });
}

export async function renomearArquivoContabil(arquivoId: number, nome: string) {
  return apiFetch<ArquivoContabil>(BASE + '/arquivos/' + arquivoId, {
    method: 'PATCH',
    body: JSON.stringify({ nome }),
  });
}

export async function excluirArquivoContabil(arquivoId: number, motivo?: string) {
  return apiFetch<{ ok: boolean }>(BASE + '/arquivos/' + arquivoId, {
    method: 'DELETE',
    body: JSON.stringify({ motivo: motivo ?? null }),
  });
}

function nomeArquivo(header: string, fallback: string) {
  const utf8 = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8?.[1]) {
    try { return decodeURIComponent(utf8[1]); } catch { /* usa fallback */ }
  }
  const ascii = header.match(/filename="?([^";]+)"?/i);
  return ascii?.[1] || fallback;
}

export async function baixarArquivoContabil(arquivoId: number, fallback: string) {
  const result = await apiFetchBlob(BASE + '/arquivos/' + arquivoId + '/download');
  const url = URL.createObjectURL(result.blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = nomeArquivo(result.contentDisposition, fallback);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}


export async function obterPainelEmpresaLancamentos(empresaId: number, competencia: number) {
  return apiFetch<EmpresaLancamentosDetalhe>(BASE + '/empresas/' + empresaId + '/lancamentos-conferencias?competencia=' + competencia, { cache: 'no-store' });
}

export async function atualizarMovimentacaoCompetencia(
  movimentacaoId: number, competencia: number, data: Partial<Pick<MovimentacaoCompetencia, 'data_limite' | 'aplicavel' | 'lancado' | 'conferido'>> & { justificativa?: string },
) {
  return apiFetch<MovimentacaoCompetencia>(BASE + '/movimentacoes/' + movimentacaoId + '/competencias/' + competencia, {
    method: 'PATCH', body: JSON.stringify(data),
  });
}

export async function criarMovimentacaoInterna(
  empresaId: number, data: { nome: string; categoria_id?: number | null; competencia_inicio: number; data_limite?: string | null },
) {
  return apiFetch<{ id: number }>(BASE + '/empresas/' + empresaId + '/movimentacoes', {
    method: 'POST', body: JSON.stringify(data),
  });
}


export async function inativarMovimentacaoInterna(movimentacaoId: number, competenciaFim: number) {
  return apiFetch<{ id: number; ativa: boolean; competencia_fim: number }>(BASE + '/movimentacoes/' + movimentacaoId + '/inativar', {
    method: 'POST', body: JSON.stringify({ competencia_fim: competenciaFim }),
  });
}
