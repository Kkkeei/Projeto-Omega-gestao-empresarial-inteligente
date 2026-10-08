import {apiFetch, API_URL} from './client';

export type Tributo={id:number;nome:string;sigla?:string|null;esfera:string;categoria?:string|null;periodicidade?:string|null;descricao?:string|null;ativo:number};
export type ImpostoEmpresa={id:number;razao_social:string;nome_fantasia?:string|null;cnpj:string;regime_tributario?:string|null;tributos_vinculados:number;impostos_informados:number;impostos_pendentes:number;impostos_atrasados:number;impostos_vencendo:number;valor_a_pagar:number;status_geral:{chave:string;rotulo:string;quantidade:number;dias?:number}};
export type DashboardImpostos={empresas:ImpostoEmpresa[];indicadores:{total_empresas:number;regimes:Record<string,number>;empresas_configuradas:number;impostos_pendentes:number;impostos_pagos:number;valor_a_pagar:number;competencia:{ano:number;mes:number;label:string}};competencia:{ano:number;mes:number;label:string}};
export type TributarioMensal={vinculo_id:number;tributo_id:number;nome:string;sigla?:string|null;esfera?:string|null;categoria?:string|null;periodicidade?:string|null;obrigatorio:number;vigencia_inicio?:string|null;vigencia_fim?:string|null;vinculo_status?:string|null;imposto_mensal_id:number;status_mensal:string;status_exibicao:string;dias_para_vencimento?:number|null;valor?:number|null;data_vencimento?:string|null;data_pagamento?:string|null;numero_documento?:string|null;mensal_observacao?:string|null};
export type EmpresaImpostos={empresa:{id:number;cnpj:string;razao_social:string;nome_fantasia?:string|null;regime_tributario?:string|null;municipio?:string|null;uf?:string|null;ativo:number};competencia:{ano:number;mes:number;label:string};resumo:{tributos_vinculados:number;informados:number;atrasados:number;vencendo:number;sem_valor:number;valor_a_pagar:number};tributos:TributarioMensal[];grupos:Record<string,TributarioMensal[]>};
export type ConfiguracaoEmpresa={id:number;empresa_id:number;tributo_id:number;nome:string;sigla:string;esfera:string;vigencia_inicio:string;vigencia_fim?:string|null;status:string;obrigatorio:number;observacao?:string|null};
export type ImpostoDetalhe={empresa:{id:number;razao_social:string;nome_fantasia?:string|null;cnpj:string;regime_tributario?:string|null};tributo:{id:number;nome:string;sigla:string;esfera:string;vigencia_inicio?:string|null;vigencia_fim?:string|null;status:string};competencia:{ano:number;mes:number;label:string};mensal:{id:number;status:string;status_exibicao:string;valor?:number|null;data_vencimento?:string|null;data_pagamento?:string|null;numero_documento?:string|null;observacao?:string|null};documentos:DocumentoImposto[];notificacoes:NotificacaoEvento[];historico:unknown[]};
export type DocumentoImposto={id:number;nome_arquivo:string;caminho_arquivo:string;extensao?:string|null;mime_type?:string|null;tamanho?:number|null;hash_arquivo?:string|null;competencia_extraida?:string|null;valor_extraido?:number|null;vencimento_extraido?:string|null;codigo_receita?:string|null;cnpj_extraido?:string|null;data_pagamento_extraida?:string|null;periodo_apuracao_inicio?:string|null;periodo_apuracao_fim?:string|null;mensagem_cliente?:string|null;usuario_upload_nome?:string|null;usuario_upload_id?:number|null;enviado_em?:string|null;status_documento?:string|null;criado_em?:string|null};
export type NotificacaoEvento={id:number;empresa_id:number;imposto_mensal_id?:number|null;publico:string;tipo:string;titulo:string;mensagem?:string|null;agendado_para?:string|null;status:string;enviado_em?:string|null;erro?:string|null};
export type NotificacaoConfig={id:number;publico:'CLIENTE'|'CONTABILIDADE';guia_enviada:number;antes_vencimento:number;dias_antes:number;dia_vencimento:number;nao_pagamento:number;imposto_vencido:number};

const qs=(params:Record<string,unknown>)=>{const u=new URLSearchParams();Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!==null&&v!=='')u.set(k,String(v));});return u.toString()};

export const listarImpostos=(params:{q?:string;regime?:string;situacao?:string;ano?:number;mes?:number}={})=>apiFetch<DashboardImpostos>(`/api/v1/impostos/dashboard?${qs(params)}`);
export const listarTributos=(params:{ativos?:boolean;q?:string;esfera?:string}={})=>apiFetch<{tributos:Tributo[]}>(`/api/v1/impostos/tributos?${qs(params)}`);
export const criarTributo=(data:Partial<Tributo>)=>apiFetch<Tributo>('/api/v1/impostos/tributos',{method:'POST',body:JSON.stringify(data)});
export const atualizarTributo=(id:number,data:Partial<Tributo>)=>apiFetch<Tributo>(`/api/v1/impostos/tributos/${id}`,{method:'PUT',body:JSON.stringify(data)});
export const obterEmpresaImpostos=(id:number,ano?:number,mes?:number)=>apiFetch<EmpresaImpostos>(`/api/v1/impostos/empresas/${id}?${qs({ano,mes})}`);
export const listarConfiguracoesEmpresa=(id:number)=>apiFetch<{configuracoes:ConfiguracaoEmpresa[]}>(`/api/v1/impostos/empresas/${id}/configuracao`);
export const vincularTributo=(empresaId:number,data:{tributo_id:number;obrigatorio?:boolean;vigencia_inicio:string;vigencia_fim?:string|null;observacao?:string|null})=>apiFetch(`/api/v1/impostos/empresas/${empresaId}/tributos`,{method:'POST',body:JSON.stringify(data)});
export const atualizarVinculo=(id:number,data:{obrigatorio?:boolean;vigencia_inicio?:string|null;vigencia_fim?:string|null;status:'ATIVO'|'INATIVO';observacao?:string|null})=>apiFetch(`/api/v1/impostos/vinculos/${id}`,{method:'PUT',body:JSON.stringify(data)});
export const registrarImposto=(empresaId:number,data:Record<string,unknown>)=>apiFetch(`/api/v1/impostos/empresas/${empresaId}/mensais`,{method:'POST',body:JSON.stringify(data)});
export const registrarSituacao=(empresaId:number,data:{tributo_id:number;competencia_ano:number;competencia_mes:number;observacao?:string|null},tipo:'CREDOR'|'SEM_MOVIMENTACAO')=>apiFetch(`/api/v1/impostos/empresas/${empresaId}/mensais/situacao?tipo=${tipo}`,{method:'POST',body:JSON.stringify(data)});
export const marcarComoPago=(empresaId:number,tributoId:number,ano:number,mes:number)=>apiFetch(`/api/v1/impostos/empresas/${empresaId}/mensais/${tributoId}/pago?ano=${ano}&mes=${mes}`,{method:'POST'});
export const obterDetalheImposto=(empresaId:number,tributoId:number,ano?:number,mes?:number)=>apiFetch<ImpostoDetalhe>(`/api/v1/impostos/empresas/${empresaId}/tributos/${tributoId}?${qs({ano,mes})}`);
export const prepararGuia=(empresaId:number,tributoId:number,ano:number,mes:number,file:File)=>{const form=new FormData();form.append('arquivo',file);return apiFetch<{documento:DocumentoImposto;mensal:Record<string,unknown>;extracao:Record<string,unknown>;texto_extraido_disponivel:boolean}>(`/api/v1/impostos/empresas/${empresaId}/tributos/${tributoId}/preparar-guia?ano=${ano}&mes=${mes}`,{method:'POST',body:form});};
export const confirmarGuia=(empresaId:number,tributoId:number,data:Record<string,unknown>)=>apiFetch<ImpostoDetalhe>(`/api/v1/impostos/empresas/${empresaId}/tributos/${tributoId}/confirmar-guia`,{method:'POST',body:JSON.stringify(data)});
export const listarConfiguracoesNotificacoes=()=>apiFetch<{configuracoes:NotificacaoConfig[]}>('/api/v1/impostos/notificacoes/config');
export const salvarConfiguracaoNotificacao=(data:Record<string,unknown>)=>apiFetch<NotificacaoConfig>('/api/v1/impostos/notificacoes/config',{method:'PUT',body:JSON.stringify(data)});
export const listarEventosNotificacoes=(empresaId?:number,impostoMensalId?:number)=>apiFetch<{eventos:NotificacaoEvento[]}>(`/api/v1/impostos/notificacoes/eventos?${qs({empresa_id:empresaId,imposto_mensal_id:impostoMensalId})}`);
export const reenviarNotificacao=(id:number)=>apiFetch<NotificacaoEvento>(`/api/v1/impostos/notificacoes/eventos/${id}/reenviar`,{method:'POST'});
export const gerarPreviaRelatorio=(empresaId:number,data:{ano_inicio:number;mes_inicio:number;ano_fim:number;mes_fim:number})=>apiFetch<any>(`/api/v1/impostos/relatorios/preview?empresa_id=${empresaId}`,{method:'POST',body:JSON.stringify(data)});
export const baixarRelatorioPdf=(empresaId:number,data:{ano_inicio:number;mes_inicio:number;ano_fim:number;mes_fim:number})=>`${API_URL}/api/v1/impostos/relatorios/pdf?${qs({empresa_id:empresaId,...data})}`;
export const linkDownloadDocumento=(id:number)=>`${API_URL}/api/v1/impostos/documentos/${id}/download`;
export const linkVisualizarDocumento=(id:number)=>`${API_URL}/api/v1/impostos/documentos/${id}/visualizar`;
export const tokenAtual=()=>localStorage.getItem('omega_access_token');


export const visualizarDocumento=async(id:number)=>{
 const res=await fetch(linkVisualizarDocumento(id),{headers:{Authorization:`Bearer ${tokenAtual()||''}`}});
 if(!res.ok) throw new Error('Não foi possível visualizar o documento.');
 const blob=await res.blob();
 const url=URL.createObjectURL(blob);
 window.open(url,'_blank','noopener,noreferrer');
 setTimeout(()=>URL.revokeObjectURL(url),60000);
};
export const obterPreviewDocumento=async(id:number)=>{
 const res=await fetch(linkVisualizarDocumento(id),{headers:{Authorization:`Bearer ${tokenAtual()||''}`}});
 if(!res.ok) throw new Error('Não foi possível visualizar o documento.');
 const blob=await res.blob();
 return URL.createObjectURL(blob);
};

export const baixarDocumento=async(id:number)=>{
 const res=await fetch(linkDownloadDocumento(id),{headers:{Authorization:`Bearer ${tokenAtual()||''}`}});
 if(!res.ok) throw new Error('Não foi possível acessar o documento.');
 const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='documento-imposto'; a.click(); URL.revokeObjectURL(url);
};

