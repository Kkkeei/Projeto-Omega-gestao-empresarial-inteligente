import {apiFetch, API_URL} from './client';
import type {Certidao,TipoCertidao,Empresa,CertidaoConsultaResultado} from '../../types';

export const listarCertidoes=(empresaId?:number)=>apiFetch<{total:number;certidoes:Certidao[]}>(`/api/v1/certidoes${empresaId?`?empresa_id=${empresaId}`:''}`);
export const listarTiposCertidao=()=>apiFetch<{total:number;tipos:TipoCertidao[]}>('/api/v1/certidoes/tipos');
export const registrarCertidao=(p:Record<string,unknown>)=>apiFetch<Certidao>('/api/v1/certidoes',{method:'POST',body:JSON.stringify(p)});
export const historicoCertidoes=(empresaId:number,tipoId?:number)=>apiFetch<{total:number;historico:Record<string,unknown>[]}>(`/api/v1/certidoes/empresa/${empresaId}/historico${tipoId?`?tipo_certidao_id=${tipoId}`:''}`);
export const listarEmpresasParaSelecao=()=>apiFetch<{total:number;empresas:Empresa[]}>('/api/v1/empresas');
// Alias retrocompatível para chamadas existentes.
export const buscarEmpresasParaSelecao=listarEmpresasParaSelecao;
export const consultarCertidaoNarrativa=(empresaId:number,certificadoNome?:string)=>apiFetch<CertidaoConsultaResultado>(`/api/v1/certidoes/narrativa/consultar/${empresaId}${certificadoNome?`?certificado_nome=${encodeURIComponent(certificadoNome)}`:''}`,{method:'POST'});
export const consultarCertidaoFederal=(empresaId:number)=>apiFetch<CertidaoConsultaResultado>(`/api/v1/certidoes/federal/consultar/${empresaId}`,{method:'POST'});
export const consultarCertidaoEstadual=(empresaId:number)=>apiFetch<CertidaoConsultaResultado>(`/api/v1/certidoes/estadual/consultar/${empresaId}`,{method:'POST'});
export const pdfUrl=(path:string)=>`${API_URL}/api/v1/certidoes/pdf?path=${encodeURIComponent(path)}`;

export const consultarTodasCertidoesEstaduais=()=>apiFetch<{resumo:Record<string,number>;resultados:CertidaoConsultaResultado[]}>('/api/v1/certidoes/estadual/consultar-todas',{method:'POST'});
