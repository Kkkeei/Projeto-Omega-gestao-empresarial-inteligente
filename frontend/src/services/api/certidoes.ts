import {apiFetch, API_URL} from './client';
import type {Certidao,TipoCertidao,Empresa,CertidaoConsultaResultado} from '../../types';

export const listarCertidoes=(empresaId?:number)=>apiFetch<{total:number;certidoes:Certidao[]}>(`/api/v1/certidoes${empresaId?`?empresa_id=${empresaId}`:''}`);
export const listarTiposCertidao=()=>apiFetch<{total:number;tipos:TipoCertidao[]}>('/api/v1/certidoes/tipos');
export const registrarCertidao=(p:Record<string,unknown>)=>apiFetch<Certidao>('/api/v1/certidoes',{method:'POST',body:JSON.stringify(p)});
export const historicoCertidoes=(empresaId:number,tipoId?:number)=>apiFetch<{total:number;historico:Record<string,unknown>[]}>(`/api/v1/certidoes/empresa/${empresaId}/historico${tipoId?`?tipo_certidao_id=${tipoId}`:''}`);
export const listarEmpresasParaSelecao=()=>apiFetch<{total:number;empresas:Empresa[]}>('/api/v1/empresas');
// Alias retrocompatível para chamadas existentes.
export const buscarEmpresasParaSelecao=listarEmpresasParaSelecao;
export const consultarCertidaoNarrativa=(empresaId:number,certificadoNome?:string)=>apiFetch<CertidaoConsultaResultado>(`/api/v1/certidoes/narrativa/consultar/${empresaId}${certificadoNome?`?certificado_nome=${encodeURIComponent(certificadoNome)}`:''}`,{method:'POST', timeoutMs:120000});
export const consultarCertidaoFederal=(empresaId:number)=>apiFetch<CertidaoConsultaResultado>(`/api/v1/certidoes/federal/consultar/${empresaId}`,{method:'POST', timeoutMs:120000});
export const consultarCertidaoEstadual=(empresaId:number)=>apiFetch<CertidaoConsultaResultado>(`/api/v1/certidoes/estadual/consultar/${empresaId}`,{method:'POST', timeoutMs:120000});
export const pdfUrl=(path:string)=>`${API_URL}/api/v1/certidoes/pdf?path=${encodeURIComponent(path)}`;
export const pdfDownloadUrl=(path:string)=>`${API_URL}/api/v1/certidoes/pdf?path=${encodeURIComponent(path)}&download=true`;

export const consultarTodasCertidoesEstaduais=()=>apiFetch<{resumo:Record<string,number>;resultados:CertidaoConsultaResultado[]}>('/api/v1/certidoes/estadual/consultar-todas',{method:'POST', timeoutMs:600000});

export const statusAutomacaoCertidoes=()=>apiFetch<{ocupada:boolean;tipo?:string;empresa_id?:number|null;empresa?:string;iniciado_em?:string;expira_em?:string;mensagem?:string}>('/api/v1/certidoes/automacao/status');

export async function abrirPdfCertidaoAutenticado(path: string, download = false): Promise<void> {
  const target = download ? null : window.open('', '_blank', 'noopener,noreferrer');
  if (!download && !target) throw new Error('O navegador bloqueou a nova aba. Permita pop-ups para visualizar o PDF.');
  try {
    const {blob, contentDisposition} = await apiFetchBlob(
      `/api/v1/certidoes/pdf?path=${encodeURIComponent(path)}${download ? '&download=true' : ''}`,
      {timeoutMs: 30000},
    );
    const url = URL.createObjectURL(blob);
    if (download) {
      const a = document.createElement('a');
      a.href = url;
      const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
      a.download = match?.[1] || 'certidao.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } else if (target) {
      target.location.href = url;
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    }
  } catch (error) {
    target?.close();
    throw error;
  }
}
