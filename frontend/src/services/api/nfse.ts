import {API_URL,apiFetch} from './client';

export type NfseContext={
  origem:'PJ'|'PF';
  entidade_id:number;
  entidade:{id:number;documento:string;nome:string;municipio?:string|null;codigo_ibge?:string|null;uf?:string|null};
  certificado:{id:number;tipo:'A1'|'A3';meio_armazenamento:'PFX'|'CARTAO'|'TOKEN';titular?:string|null;documento?:string|null;validade?:string|null;thumbprint_sha256?:string|null}|null;
  mensagem_certificado?:string|null;
  certificados_cadastrados?:Array<{
    id:number;tipo:string;status:string;validade?:string|null;titular?:string|null;
    documento?:string|null;apto_para_uso:boolean;selecionavel:boolean;motivo?:string|null;
  }>;
  provider:string;
  ambiente:string;
  ultimo_nsu:number;
  ultimo_sync?:string|null;
  status:string;
};

export type NfseDocumento={
  id:number;origem:'PJ'|'PF';entidade_id:number;provider:string;nsu?:number|null;schema?:string|null;
  chave_acesso?:string|null;numero?:string|null;data_emissao?:string|null;valor?:number|null;situacao:string;xml_path?:string|null;
  criado_em:string;atualizado_em:string;xml?:string|null;resposta_json?:string|null;
};

export const contextoNfse=(origem:'PJ'|'PF',entidadeId:number)=>
  apiFetch<NfseContext>(`/api/v1/nfse/contexto?origem=${origem}&entidade_id=${entidadeId}`);

export const detalheNfse=(id:number)=>apiFetch<NfseDocumento>(`/api/v1/nfse/${id}`);

export const listarNfse=(origem?:'PJ'|'PF',entidadeId?:number,limit=500,offset=0)=>{
  const q=new URLSearchParams(); if(origem)q.set('origem',origem); if(entidadeId)q.set('entidade_id',String(entidadeId)); q.set('limit',String(Math.min(500,Math.max(1,limit)))); q.set('offset',String(Math.max(0,offset)));
  const suffix=q.toString()?`?${q.toString()}`:'';
  return apiFetch<{total:number;nfse:NfseDocumento[]}>(`/api/v1/nfse${suffix}`);
};

export const consultarNfseA1=(origem:'PJ'|'PF',entidadeId:number)=>
  apiFetch<{ok:boolean;provider:string;certificado_tipo:string;http_status:number;documentos_encontrados:number;documentos_importados:number;ultimo_nsu:number;max_nsu?:number|null}>('/api/v1/nfse/consultar',{
    method:'POST',body:JSON.stringify({origem,entidade_id:entidadeId}),timeoutMs:90000,
  });

export async function bridgeFetchNfseDfe(url:string,thumbprint:string){
  const base=(import.meta.env.VITE_OMEGA_BRIDGE_URL||'http://127.0.0.1:8765').replace(/\/$/,'');
  const token=import.meta.env.VITE_OMEGA_BRIDGE_TOKEN||'omega-local-a3-bridge-v1';
  const response=await fetch(`${base}/nfse/dfe`,{
    method:'POST',
    headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},
    body:JSON.stringify({url,certificate_thumbprint:thumbprint}),
  });
  if(!response.ok){let msg=`Bridge HTTP ${response.status}`;try{const j=await response.json();msg=j.detail||msg}catch{}throw new Error(msg)}
  return await response.json() as {status_code:number;content_type:string;body_b64:string};
}

export const importarNfseA3=(origem:'PJ'|'PF',entidadeId:number,thumbprint:string,contentType:string,bodyB64:string)=>
  apiFetch<{ok:boolean;documentos_encontrados:number;documentos_importados:number;ultimo_nsu?:number|null;max_nsu?:number|null}>('/api/v1/nfse/a3/importar',{
    method:'POST',body:JSON.stringify({origem,entidade_id:entidadeId,thumbprint_sha256:thumbprint,content_type:contentType,body_b64:bodyB64}),timeoutMs:30000,
  });

export async function baixarNfsePdf(id:number){
  const token=localStorage.getItem('omega_access_token');
  const response=await fetch(`${API_URL}/api/v1/nfse/${id}/pdf`,{headers:token?{Authorization:`Bearer ${token}`}:{}});
  if(!response.ok){let message='Não foi possível gerar o PDF desta NFS-e.';try{const body=await response.json();if(typeof body?.detail==='string')message=body.detail}catch{}throw new Error(message)}
  return {blob:await response.blob(),name:response.headers.get('content-disposition')||`nfse-${id}.pdf`};
}
