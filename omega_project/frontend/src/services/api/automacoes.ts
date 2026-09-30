import {apiFetch} from './client';
export const listarExecucoes=(empresaId?:number)=>apiFetch<{total:number;execucoes:any[]}>(`/api/v1/automacoes/execucoes${empresaId?`?empresa_id=${empresaId}`:''}`);
export const executarAutomacao=(tipo:string,empresa_id?:number)=>apiFetch<any>('/api/v1/automacoes/executar',{method:'POST',body:JSON.stringify({tipo,empresa_id:empresa_id??null})});
