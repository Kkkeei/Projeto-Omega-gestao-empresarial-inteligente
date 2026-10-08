
import {apiFetch, apiFetchBlob} from './client';

export type Certificado={
  id:number; empresa_id?:number; pessoa_id?:number; origem?:'PJ'|'PF'; razao_social:string; cnpj?:string|null; cpf?:string|null;
  tipo:'A1'|'A3'; meio_armazenamento:'PFX'|'CARTAO'|'TOKEN';
  titular_tipo:'PJ'|'PF'|'NAO_IDENTIFICADO'; nome_titular?:string|null;
  documento_titular?:string|null; emissor?:string|null; numero_serie?:string|null;
  thumbprint_sha256?:string|null; algoritmo?:string|null;
  data_emissao?:string|null; data_validade?:string|null;
  status:'ATIVO'|'INATIVO'|'EXPIRADO'|'NAO_VINCULADO';
  apto_para_uso:boolean; dispositivo_modelo?:string|null;
  dispositivo_identificador?:string|null;
  criado_em:string; atualizado_em:string;
};
export type CertificadoEvento={id:number;tipo_evento:string;descricao?:string;dados?:string;criado_em:string;usuario?:string|null};

export const listarCertificados=async(empresaId?:number,tipo?:string)=>{
  const pj=await apiFetch<{total:number;certificados:Certificado[]}>(`/api/v1/certificados${empresaId?`?empresa_id=${empresaId}`:tipo?`?tipo=${tipo}`:''}`);
  if(empresaId||tipo) return pj;
  const pf=await apiFetch<{total:number;certificados:Certificado[]}>('/api/v1/certificados/pf');
  return {total:pj.total+pf.total,certificados:[...pj.certificados,...pf.certificados]};
};
export const resumoCertificados=()=>apiFetch<{empresas_ativas:number;pessoas_fisicas_ativas:number;certificados_ativos:number;vencem_30_dias:number;vencem_7_dias:number;vencidos:number;empresas_sem_certificado:number;pessoas_fisicas_sem_certificado:number}>('/api/v1/certificados/resumo');
export const detalheCertificado=(id:number,origem:'PJ'|'PF'='PJ')=>apiFetch<Certificado>(origem==='PF'?`/api/v1/certificados/pf/${id}`:`/api/v1/certificados/${id}`);
export const eventosCertificado=(id:number,origem:'PJ'|'PF'='PJ')=>apiFetch<{total:number;eventos:CertificadoEvento[]}>(origem==='PF'?`/api/v1/certificados/pf/${id}/eventos`:`/api/v1/certificados/${id}/eventos`);
export const cadastrarA1=async(empresaId:number,arquivo:File,senha:string)=>{
  const form=new FormData(); form.append('empresa_id',String(empresaId)); form.append('senha',senha); form.append('arquivo',arquivo);
  return apiFetch<Certificado>('/api/v1/certificados/a1',{method:'POST',body:form});
};
export const cadastrarPFA1=async(cpf:string,nome:string,arquivo:File,senha:string,email?:string,telefone?:string)=>{
  const form=new FormData(); form.append('cpf',cpf); form.append('nome',nome); form.append('senha',senha); form.append('arquivo',arquivo);
  if(email)form.append('email',email); if(telefone)form.append('telefone',telefone);
  return apiFetch<Certificado>('/api/v1/certificados/pf/a1',{method:'POST',body:form});
};
export const cadastrarPFA3=async(data:Record<string,string>)=>{
  const form=new FormData(); Object.entries(data).forEach(([k,v])=>{if(v!==undefined&&v!==null)form.append(k,v)});
  return apiFetch<Certificado>('/api/v1/certificados/pf/a3',{method:'POST',body:form});
};
export const cadastrarA3=async(data:Record<string,string>)=>{
  const form=new FormData(); Object.entries(data).forEach(([k,v])=>{if(v!==undefined&&v!==null)form.append(k,v)});
  return apiFetch<Certificado>('/api/v1/certificados/a3',{method:'POST',body:form});
};
export const testarCertificado=(id:number,origem:'PJ'|'PF'='PJ')=>apiFetch<Record<string,unknown>>(origem==='PF'?`/api/v1/certificados/pf/${id}/testar`:`/api/v1/certificados/${id}/testar`,{method:'POST'});
export const desativarCertificado=(id:number,origem:'PJ'|'PF'='PJ')=>apiFetch<Certificado>(origem==='PF'?`/api/v1/certificados/pf/${id}/desativar`:`/api/v1/certificados/${id}/desativar`,{method:'POST'});
export const solicitarSubstituicao=(id:number,origem:'PJ'|'PF'='PJ')=>apiFetch<{ok:boolean;mensagem:string}>(origem==='PF'?`/api/v1/certificados/pf/${id}/solicitar-substituicao`:`/api/v1/certificados/${id}/solicitar-substituicao`,{method:'POST'});
export const obterSenhaA1=(id:number,origem:'PJ'|'PF'='PJ')=>apiFetch<{certificado_id:number;senha:string;mensagem:string}>(origem==='PF'?`/api/v1/certificados/pf/${id}/senha`:`/api/v1/certificados/${id}/senha`);
export const baixarSenhaA1=async(id:number,origem:'PJ'|'PF'='PJ')=>{
  const {blob,contentDisposition}=await apiFetchBlob(origem==='PF'?`/api/v1/certificados/pf/${id}/senha/download`:`/api/v1/certificados/${id}/senha/download`);
  const a=document.createElement('a'); const url=URL.createObjectURL(blob); a.href=url;
  const m=/filename="?([^";]+)"?/i.exec(contentDisposition); a.download=m?.[1]||`senha-certificado-${id}.txt`;
  document.body.appendChild(a); a.click(); a.remove(); window.setTimeout(()=>URL.revokeObjectURL(url),1000);
};

export const baixarA1=async(id:number,filename:string,origem:'PJ'|'PF'='PJ')=>{
  const {blob,contentDisposition}=await apiFetchBlob(origem==='PF'?`/api/v1/certificados/pf/${id}/download`:`/api/v1/certificados/${id}/download`);
  const a=document.createElement('a'); const url=URL.createObjectURL(blob); a.href=url;
  const m=/filename="?([^";]+)"?/i.exec(contentDisposition); a.download=m?.[1]||filename||'certificado.p12';
  document.body.appendChild(a); a.click(); a.remove(); window.setTimeout(()=>URL.revokeObjectURL(url),1000);
};

export type BridgeStatus={status:string;bridge:string;version:string;pcsc:boolean;pkcs11_configured:boolean;pkcs11_module?:string|null};
export type BridgeDiagnostics={platform:string;pcsc:boolean;readers:string[];reader_error?:string|null;pkcs11_configured:boolean;pkcs11_module?:string|null;hint?:string|null};
export type BridgeCertificate={slot:string;token_label:string;label?:string;id:string;subject:string;issuer:string;serial:string;thumbprint_sha256:string;valid_from:string;valid_to:string;documento_titular?:string|null;titular_tipo?:'PJ'|'PF'|'NAO_IDENTIFICADO'};
export async function bridgeStatus(){
  const base=(import.meta.env.VITE_OMEGA_BRIDGE_URL||'http://127.0.0.1:8765').replace(/\/$/,'');
  const token=import.meta.env.VITE_OMEGA_BRIDGE_TOKEN||'';
  const r=await fetch(`${base}/health`,{headers:token?{Authorization:`Bearer ${token}`}:{},});
  if(!r.ok) throw new Error(`Bridge HTTP ${r.status}`);
  return await r.json() as BridgeStatus;
}
export async function bridgeDiagnostics(){
  const base=(import.meta.env.VITE_OMEGA_BRIDGE_URL||'http://127.0.0.1:8765').replace(/\/$/,'');
  const token=import.meta.env.VITE_OMEGA_BRIDGE_TOKEN||'';
  const r=await fetch(`${base}/diagnostics`,{headers:{Authorization:`Bearer ${token}`}});
  if(!r.ok){let msg=`Bridge HTTP ${r.status}`;try{const j=await r.json();msg=j.detail||msg}catch{}throw new Error(msg)}
  return await r.json() as BridgeDiagnostics;
}
export async function bridgeCertificates(){
  const base=(import.meta.env.VITE_OMEGA_BRIDGE_URL||'http://127.0.0.1:8765').replace(/\/$/,'');
  const token=import.meta.env.VITE_OMEGA_BRIDGE_TOKEN||'';
  const r=await fetch(`${base}/certificates`,{headers:{Authorization:`Bearer ${token}`}});
  if(!r.ok){let msg=`Bridge HTTP ${r.status}`;try{const j=await r.json();msg=j.detail||msg}catch{}throw new Error(msg)}
  return await r.json() as {total:number;certificates:BridgeCertificate[]};
}

export async function bridgeSignTest(thumbprint:string,pin:string){
  const base=(import.meta.env.VITE_OMEGA_BRIDGE_URL||'http://127.0.0.1:8765').replace(/\/$/,'');
  const token=import.meta.env.VITE_OMEGA_BRIDGE_TOKEN||'';
  const challenge=new Uint8Array(32); crypto.getRandomValues(challenge);
  let binary=''; challenge.forEach(b=>binary+=String.fromCharCode(b));
  const data_b64=btoa(binary);
  const r=await fetch(`${base}/sign`,{method:'POST',headers:{'Content-Type':'application/json','Authorization':`Bearer ${token}`},body:JSON.stringify({certificate_thumbprint:thumbprint,data_b64,pin,algorithm:'AUTO'})});
  if(!r.ok){let msg=`Bridge HTTP ${r.status}`;try{const j=await r.json();msg=j.detail||msg}catch{}throw new Error(msg)}
  return await r.json() as {ok:boolean;signature_b64:string;certificate_thumbprint:string};
}
