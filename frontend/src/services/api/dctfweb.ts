import {apiFetch} from './client';

export type ObrigacaoDctfweb = {
  tributo_id:number; nome:string; sigla?:string|null;
  status:'PENDENTE'|'CREDOR'|'SEM_MOVIMENTACAO'|'VALOR_INFORMADO'|'PAGO';
  valor:number|null; numero_documento?:string|null; finalizada:boolean;
};
export type EmpresaDctfweb = {
  id:number; razao_social:string; nome_fantasia?:string|null; cnpj:string;
  regime_tributario:string; obrigacoes:ObrigacaoDctfweb[];
  total_obrigacoes:number; finalizadas:number; pendentes:number;
  status_geral:'COMPLETA'|'PENDENTE';
};
export type TributoDctfweb = {id:number;nome:string;sigla?:string|null;esfera:string};
export type DashboardDctfweb = {
  competencia:{ano:number;mes:number;label:string};
  tributos:TributoDctfweb[];
  empresas:EmpresaDctfweb[];
  indicadores:{total_empresas:number;total_obrigacoes:number;finalizadas:number;pendentes:number;empresas_com_pendencias:number;percentual:number;liberada:boolean};
};
export const obterDashboardDctfweb=(ano:number,mes:number)=>apiFetch<DashboardDctfweb>(`/api/v1/dctfweb/dashboard?ano=${ano}&mes=${mes}`);
