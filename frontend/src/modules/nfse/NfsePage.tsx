import {useEffect,useMemo,useRef,useState} from 'react';
import {AlertTriangle,Building2,CheckCircle2,Download,Eye,FileCode2,KeyRound,RefreshCw,Search,ShieldCheck,Smartphone,Wifi,X} from 'lucide-react';
import {listarEmpresasParaSelecao} from '../../services/api/certidoes';
import {listarPessoasFisicas,type PessoaFisica} from '../../services/api/certificados';
import {bridgeCertificates} from '../../services/api/certificados';
import {bridgeFetchNfseDfe,consultarNfseA1,contextoNfse,detalheNfse,importarNfseA3,listarNfse,baixarNfsePdf,type NfseContext,type NfseDocumento} from '../../services/api/nfse';
import type {Empresa} from '../../types';

const ADN_BASE=()=> (import.meta.env.VITE_OMEGA_NFSE_ADN_URL||'https://adn.nfse.gov.br/contribuintes').replace(/\/$/,'');
const currentMonth=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`};
function csvCell(value:unknown){return `\"${String(value??'').replace(/\"/g,'\"\"')}\"`;}
function downloadBlob(blob:Blob,name:string){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1500);}
function crc32(bytes:Uint8Array){let c=0xffffffff;for(const b of bytes){c^=b;for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
function zipStore(files:Array<{name:string;data:Uint8Array}>){const enc=new TextEncoder();const local:Uint8Array[]=[];const central:Uint8Array[]=[];let offset=0;for(const f of files){const name=enc.encode(f.name),crc=crc32(f.data);const h=new Uint8Array(30+name.length);const v=new DataView(h.buffer);v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x0800,true);v.setUint16(8,0,true);v.setUint32(14,crc,true);v.setUint32(18,f.data.length,true);v.setUint32(22,f.data.length,true);v.setUint16(26,name.length,true);h.set(name,30);local.push(h,f.data);const c=new Uint8Array(46+name.length);const cv=new DataView(c.buffer);cv.setUint32(0,0x02014b50,true);cv.setUint16(4,20,true);cv.setUint16(6,20,true);cv.setUint16(8,0x0800,true);cv.setUint16(10,0,true);cv.setUint32(16,crc,true);cv.setUint32(20,f.data.length,true);cv.setUint32(24,f.data.length,true);cv.setUint16(28,name.length,true);cv.setUint32(42,offset,true);c.set(name,46);central.push(c);offset+=h.length+f.data.length;}const centralSize=central.reduce((n,a)=>n+a.length,0);const end=new Uint8Array(22);const ev=new DataView(end.buffer);ev.setUint32(0,0x06054b50,true);ev.setUint16(8,files.length,true);ev.setUint16(10,files.length,true);ev.setUint32(12,centralSize,true);ev.setUint32(16,offset,true);const parts=[...local,...central,end];const size=parts.reduce((n,part)=>n+part.length,0);const bytes=new Uint8Array(size);let cursor=0;for(const part of parts){bytes.set(part,cursor);cursor+=part.length;}return new Blob([bytes.buffer as ArrayBuffer],{type:'application/zip'});}
function fmtDate(value?:string|null){
  if(!value)return '—';
  const raw=String(value);
  const dateOnly=/^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  const d=dateOnly?new Date(Number(dateOnly[1]),Number(dateOnly[2])-1,Number(dateOnly[3])):new Date(raw);
  return Number.isNaN(d.getTime())?'—':d.toLocaleDateString('pt-BR');
}
function money(value?:number|null){return value==null||!Number.isFinite(Number(value))?'—':Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});}
async function listarTodasNfse(origem?:'PJ'|'PF',entidadeId?:number){const all:NfseDocumento[]=[];for(let offset=0;offset<100000;offset+=500){const page=await listarNfse(origem,entidadeId,500,offset);all.push(...page.nfse);if(page.nfse.length<500)break;}return all;}

export function NfsePage(){
  const [empresas,setEmpresas]=useState<Empresa[]>([]);
  const [pessoas,setPessoas]=useState<PessoaFisica[]>([]);
  const [officeDocs,setOfficeDocs]=useState<NfseDocumento[]>([]);
  const [officeSearch,setOfficeSearch]=useState('');
  const [officeStatus,setOfficeStatus]=useState<'TODAS'|'COM'|'SEM'>('TODAS');
  const [competence,setCompetence]=useState(currentMonth);
  const [selectedDocs,setSelectedDocs]=useState<number[]>([]);
  const [origin,setOrigin]=useState<'PJ'|'PF'>('PJ');
  const [entityId,setEntityId]=useState<number|''>('');
  const [context,setContext]=useState<NfseContext|null>(null);
  const [docs,setDocs]=useState<NfseDocumento[]>([]);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [bridgeLoading,setBridgeLoading]=useState(false);
  const [bridgeReady,setBridgeReady]=useState(false);
  const [message,setMessage]=useState('');
  const [error,setError]=useState('');
  const [search,setSearch]=useState('');
  const [selectedDoc,setSelectedDoc]=useState<NfseDocumento|null>(null);
  const [detailLoading,setDetailLoading]=useState(false);
  const [detailError,setDetailError]=useState('');
  const requestSequence=useRef(0);

  async function loadBase(){
    setLoading(true);
    setError('');
    setMessage('');
    // Carrega PJ e PF independentemente: uma falha em uma origem não pode
    // impedir que a outra lista apareça.
    const [empresasResult, pessoasResult, documentosResult] = await Promise.allSettled([
      listarEmpresasParaSelecao(),
      listarPessoasFisicas(),
      listarTodasNfse(),
    ]);

    let empresasCarregadas: Empresa[] = [];
    let pessoasCarregadas: PessoaFisica[] = [];
    const erros: string[] = [];

    if (empresasResult.status === 'fulfilled') {
      empresasCarregadas = Array.isArray(empresasResult.value.empresas)
        ? empresasResult.value.empresas : [];
      setEmpresas(empresasCarregadas);
    } else {
      setEmpresas([]);
      erros.push(`Empresas (PJ): ${empresasResult.reason instanceof Error ? empresasResult.reason.message : 'falha ao carregar'}`);
    }

    if (pessoasResult.status === 'fulfilled') {
      pessoasCarregadas = Array.isArray(pessoasResult.value.pessoas)
        ? pessoasResult.value.pessoas : [];
      setPessoas(pessoasCarregadas);
    } else {
      setPessoas([]);
      erros.push(`Pessoas físicas (PF): ${pessoasResult.reason instanceof Error ? pessoasResult.reason.message : 'falha ao carregar'}`);
    }

    if (documentosResult.status === 'fulfilled') {
      setOfficeDocs(documentosResult.value);
    } else {
      setOfficeDocs([]);
      erros.push(`Documentos: ${documentosResult.reason instanceof Error ? documentosResult.reason.message : 'falha ao carregar'}`);
    }

    // Só preserva a seleção se ela existir na lista da origem atual.
    const current = origin === 'PJ' ? empresasCarregadas : pessoasCarregadas;
    setEntityId(previous =>
      typeof previous === 'number' && current.some(item => item.id === previous)
        ? previous : ''
    );

    if (erros.length) {
      setError(`Atualização parcial. ${erros.join(' | ')}`);
    } else {
      setMessage(`Titulares atualizados: ${empresasCarregadas.length} empresa(s) e ${pessoasCarregadas.length} pessoa(s) física(s).`);
    }
    setLoading(false);
  }

  async function loadContext(id:number,currentOrigin: 'PJ'|'PF'=origin){
    const sequence=++requestSequence.current;
    setError('');setMessage('');setContext(null);setBridgeReady(false);setSelectedDoc(null);setSelectedDocs([]);
    const [ctxResult,listResult]=await Promise.allSettled([
      contextoNfse(currentOrigin,id),
      listarTodasNfse(currentOrigin,id).then(nfse=>({nfse})),
    ]);
    if(sequence!==requestSequence.current)return;
    if(listResult.status==='fulfilled')setDocs(listResult.value.nfse);
    else {setDocs([]);setError(listResult.reason instanceof Error?listResult.reason.message:'Não foi possível carregar as NFS-e importadas.');}
    if(ctxResult.status==='fulfilled')setContext(ctxResult.value);
    else if(listResult.status==='rejected')setError(ctxResult.reason instanceof Error?ctxResult.reason.message:'Não foi possível carregar o contexto da NFS-e.');
    else setError(ctxResult.reason instanceof Error?ctxResult.reason.message:'Não foi possível carregar o certificado deste titular.');
  }

  useEffect(()=>{void loadBase();},[]);
  useEffect(()=>{if(typeof entityId==='number')void loadContext(entityId,origin);else{setContext(null);setDocs([]);}},[entityId,origin]);

  const entities=origin==='PJ'?empresas:pessoas;
  const filteredDocs=useMemo(()=>{
    const q=search.trim().toLowerCase();
    return docs.filter(d=>(!competence||String(d.data_emissao||'').startsWith(competence))&&(!q||[d.chave_acesso,d.numero,d.schema,d.situacao,String(d.nsu??'')].some(v=>String(v||'').toLowerCase().includes(q))));
  },[docs,search,competence]);

  function switchOrigin(next:'PJ'|'PF'){
    requestSequence.current++;
    setOrigin(next);setContext(null);setDocs([]);setMessage('');setError('');setBridgeReady(false);setSelectedDoc(null);
    // Ao alternar PJ/PF, aguardar a seleção explícita do titular.
    setEntityId('');
  }

  async function detectA3(){
    if(!context?.certificado||context.certificado.tipo!=='A3')return;
    setBridgeLoading(true);setError('');setMessage('');setBridgeReady(false);
    try{
      if(!context.certificado.thumbprint_sha256)throw new Error('O cadastro A3 não possui thumbprint. Abra Certificados, detecte o cartão novamente e atualize o cadastro.');
      const r=await bridgeCertificates();
      const found=r.certificates.find(c=>c.thumbprint_sha256.toLowerCase()===String(context.certificado?.thumbprint_sha256||'').toLowerCase());
      if(!found)throw new Error('O Bridge respondeu, mas o certificado A3 cadastrado para este titular não foi encontrado no cartão/token.');
      setBridgeReady(true);setMessage('Cartão/token detectado e certificado A3 conferido.');
    }catch(e){setError(e instanceof Error?e.message:'Não foi possível detectar o cartão/token A3.');}
    finally{setBridgeLoading(false);}
  }

  async function consultar(){
    if(typeof entityId!=='number'){
      setError('Selecione uma empresa ou pessoa física antes de consultar.');
      return;
    }
    if(!context){
      setError('O contexto do titular ainda não foi carregado. Clique em Atualizar titulares e selecione novamente.');
      return;
    }
    if(!context.certificado){
      setError(context.mensagem_certificado || 'Este titular não possui certificado disponível para consulta. Confira a aba Certificados.');
      return;
    }
    setBusy(true);setError('');setMessage('');
    try{
      if(context.certificado.tipo==='A1'){
        const r=await consultarNfseA1(origin,entityId);
        setMessage(`${r.documentos_importados} NFS-e importada(s). NSU atual: ${r.ultimo_nsu}.`);
      }else{
        if(!bridgeReady)throw new Error('Insira o cartão/token e clique em “Detectar cartão” antes de consultar.');
        const thumbprint=context.certificado.thumbprint_sha256||'';
        const url=`${ADN_BASE()}/DFe/${context.ultimo_nsu||0}?tipoNSU=DISTRIBUICAO&lote=true`;
        const r=await bridgeFetchNfseDfe(url,thumbprint);
        if(r.status_code>=400)throw new Error(`ADN respondeu HTTP ${r.status_code}. Verifique o certificado, a autorização do contribuinte e o ambiente.`);
        const saved=await importarNfseA3(origin,entityId,thumbprint,r.content_type,r.body_b64);
        setMessage(`${saved.documentos_importados} NFS-e importada(s) pelo A3. NSU atual: ${saved.ultimo_nsu??context.ultimo_nsu}.`);
      }
      await loadContext(entityId,origin);
      const refreshed=await listarTodasNfse();setOfficeDocs(refreshed);
    }catch(e){setError(e instanceof Error?e.message:'Não foi possível consultar a NFS-e.');}
    finally{setBusy(false);}
  }

  async function openDetail(doc:NfseDocumento){
    setSelectedDoc(doc);setDetailLoading(true);setDetailError('');
    try{setSelectedDoc(await detalheNfse(doc.id));}
    catch(e){setDetailError(e instanceof Error?e.message:'Não foi possível carregar o XML desta NFS-e.');}
    finally{setDetailLoading(false);}
  }

  async function downloadPdf(){
    if(!selectedDoc)return;
    setDetailError('');
    try{const r=await baixarNfsePdf(selectedDoc.id);const url=URL.createObjectURL(r.blob);const a=document.createElement('a');a.href=url;a.download=`nfse-${selectedDoc.numero||selectedDoc.nsu||selectedDoc.id}.pdf`;document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1500);}
    catch(e){setDetailError(e instanceof Error?e.message:'Não foi possível converter o XML em PDF.');}
  }

  function downloadXml(){
    if(!selectedDoc?.xml)return;
    const blob=new Blob([selectedDoc.xml],{type:'application/xml;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');
    a.href=url;a.download=`nfse-${selectedDoc.numero||selectedDoc.nsu||selectedDoc.id}.xml`;
    document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }

  const officeAllRows=useMemo(()=>[...empresas.map(e=>({key:`PJ:${e.id}`,origin:'PJ' as const,id:e.id,name:e.razao_social,document:e.cnpj})),...pessoas.map(p=>({key:`PF:${p.id}`,origin:'PF' as const,id:p.id,name:p.nome,document:p.cpf}))].map(e=>{const docsFor=officeDocs.filter(d=>d.origem===e.origin&&d.entidade_id===e.id&&(!competence||String(d.data_emissao||'').startsWith(competence)));return {...e,docs:docsFor,count:docsFor.length,total:docsFor.reduce((sum,d)=>sum+(Number(d.valor)||0),0)};}),[empresas,pessoas,officeDocs,competence]);
  const officeRows=useMemo(()=>{const q=officeSearch.trim().toLocaleLowerCase('pt-BR');return officeAllRows.filter(r=>(!q||`${r.name} ${r.document}`.toLocaleLowerCase('pt-BR').includes(q))&&(officeStatus==='TODAS'||(officeStatus==='COM'?r.count>0:r.count===0))).sort((a,b)=>a.name.localeCompare(b.name,'pt-BR'));},[officeAllRows,officeSearch,officeStatus]);

  function openOfficeEntity(nextOrigin:'PJ'|'PF',id:number){requestSequence.current++;setOrigin(nextOrigin);setEntityId(id);setContext(null);setDocs([]);setMessage('');setError('');setBridgeReady(false);setSelectedDoc(null);setSelectedDocs([]);}
  function exportCsv(){const rows=[['Origem','Titular','Número','Data de emissão','Chave de acesso','Valor','Situação','NSU'],...filteredDocs.map(d=>[d.origem,selectedName,d.numero||'',d.data_emissao||'',d.chave_acesso||'',d.valor??'',d.situacao,d.nsu??''])];downloadBlob(new Blob(['\ufeff'+rows.map(r=>r.map(csvCell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'}),`nfse-${origin.toLowerCase()}-${competence||'todas'}.csv`);}
  async function downloadSelectedZip(){const chosen=filteredDocs.filter(d=>selectedDocs.includes(d.id));if(!chosen.length){setError('Selecione ao menos uma NFS-e.');return;}setBusy(true);setError('');setMessage('Preparando ZIP dos XMLs selecionados...');try{const files:Array<{name:string;data:Uint8Array}>=[];const failures:string[]=[];for(const doc of chosen){try{const full=await detalheNfse(doc.id);if(!full.xml){failures.push(`NFS-e ${doc.numero||doc.id}: XML indisponível`);continue;}const safe=String(doc.numero||doc.nsu||doc.id).replace(/[^a-zA-Z0-9_-]/g,'_');files.push({name:`nfse-${safe}.xml`,data:new TextEncoder().encode(full.xml)});}catch{failures.push(`NFS-e ${doc.numero||doc.id}: falha ao obter XML`);}}if(!files.length)throw new Error(failures.join('; ')||'Nenhum XML disponível para download.');downloadBlob(zipStore(files),`nfse-${origin.toLowerCase()}-${competence||'selecionadas'}.zip`);setMessage(`${files.length} XML(s) incluído(s) no ZIP.${failures.length?` Não incluídos: ${failures.join('; ')}.`:''}`);setSelectedDocs([]);}catch(e){setError(e instanceof Error?e.message:'Não foi possível gerar o ZIP.');}finally{setBusy(false);}}

  const selectedName=origin==='PJ'?(empresas.find(x=>x.id===entityId)?.razao_social||'Empresa'):(pessoas.find(x=>x.id===entityId)?.nome||'Pessoa Física');

  return <div className="page nfse-page">
    <div className="page-heading"><div><span className="eyebrow">DOCUMENTOS FISCAIS DE SERVIÇO</span><h2>NFS-e</h2><p>Consulte e importe documentos distribuídos pelo ambiente nacional usando o certificado cadastrado no ÔMEGA.</p></div><div className="actions">{typeof entityId==='number'&&<button className="button secondary" onClick={()=>{requestSequence.current++;setEntityId('');setContext(null);setDocs([]);setSelectedDocs([]);setMessage('');setError('');void listarTodasNfse().then(setOfficeDocs).catch(()=>{});}}>Voltar ao painel</button>}<button className="button secondary" onClick={()=>void loadBase()} disabled={loading||busy}><RefreshCw size={15}/> Atualizar titulares</button></div></div>
    {error&&<div className="form-error"><AlertTriangle size={15}/>{error}</div>}{message&&<div className="cert-success"><CheckCircle2 size={15}/>{message}</div>}

    {typeof entityId!=='number'&&<section className="panel nfse-office-panel"><div className="nfse-office-top"><div><span className="eyebrow">VISÃO DO ESCRITÓRIO</span><h3>Painel de NFS-e por competência</h3><p>Indicadores calculados a partir dos documentos já importados no ÔMEGA.</p></div><div className="nfse-office-tools"><label className="nfse-select-label">Competência<input type="month" value={competence} onChange={e=>setCompetence(e.target.value)}/></label><button className="button secondary" onClick={()=>void loadBase()} disabled={loading||busy}><RefreshCw size={14}/> Atualizar</button></div></div><div className="nfse-office-kpis"><div><span>Titulares cadastrados</span><strong>{empresas.length+pessoas.length}</strong></div><div><span>Com documentos no período</span><strong>{officeAllRows.filter(r=>r.count>0).length}</strong></div><div><span>Documentos importados</span><strong>{officeAllRows.reduce((n,r)=>n+r.count,0)}</strong></div><div><span>Valor registrado</span><strong>{money(officeAllRows.reduce((n,r)=>n+r.total,0))}</strong></div></div><div className="nfse-office-filters"><div className="search-box"><Search size={16}/><input value={officeSearch} onChange={e=>setOfficeSearch(e.target.value)} placeholder="Pesquisar empresa, nome ou CPF/CNPJ..."/></div><div className="cert-person-switch" role="group" aria-label="Filtrar titulares"><button className={officeStatus==='TODAS'?'active':''} onClick={()=>setOfficeStatus('TODAS')}>Todas</button><button className={officeStatus==='COM'?'active':''} onClick={()=>setOfficeStatus('COM')}>Com documentos</button><button className={officeStatus==='SEM'?'active':''} onClick={()=>setOfficeStatus('SEM')}>Sem documentos</button></div></div>{loading?<div className="empty"><RefreshCw size={20}/><span>Carregando empresas e documentos...</span></div>:officeRows.length===0?<div className="empty"><Building2 size={22}/><strong>Nenhum titular encontrado</strong><span>Altere a pesquisa ou a competência.</span></div>:<div className="nfse-office-table"><div className="nfse-office-row nfse-office-head"><span>Titular</span><span>Tipo</span><span>Documentos</span><span>Valor registrado</span><span>Situação dos dados</span><span>Ação</span></div>{officeRows.map(r=><div className="nfse-office-row" key={r.key}><span><strong>{r.name}</strong><small>{r.document||'Documento não informado'}</small></span><span>{r.origin==='PJ'?'Pessoa Jurídica':'Pessoa Física'}</span><span>{r.count}</span><span>{money(r.total)}</span><span><span className={`badge ${r.count?'ok':'neutral'}`}>{r.count?'Com documentos':'Sem documentos importados'}</span></span><span><button className="button secondary small" onClick={()=>openOfficeEntity(r.origin,r.id)}>Abrir</button></span></div>)}</div>}<p className="nfse-office-note">“Sem documentos importados” não significa necessariamente ausência de movimento fiscal. Significa apenas que não há documentos importados para o titular e competência selecionados. O painel não presume notas prestadas/tomadas nem calcula retenções que não estejam estruturadas nos dados atuais.</p></section>}

    <section className="panel nfse-toolbar"><div className="cert-person-switch" role="tablist" aria-label="Titular da NFS-e"><button className={origin==='PJ'?'active':''} onClick={()=>switchOrigin('PJ')}><Building2 size={14}/> Pessoa Jurídica</button><button className={origin==='PF'?'active':''} onClick={()=>switchOrigin('PF')}><KeyRound size={14}/> Pessoa Física</button></div><label className="nfse-select-label">Titular<select value={entityId} onChange={e=>setEntityId(e.target.value?Number(e.target.value):'')} disabled={loading||busy}><option value="">Selecione...</option>{entities.map(e=><option key={e.id} value={e.id}>{origin==='PJ'?(e as Empresa).razao_social:`${(e as PessoaFisica).nome} · ${(e as PessoaFisica).cpf}`}</option>)}</select></label><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Pesquisar NFS-e, NSU ou chave..."/></div></section>

    {context?.certificado&&<section className="nfse-cert-card"><div className="nfse-cert-main"><div className={`nfse-cert-icon ${context.certificado.tipo==='A3'?'a3':'a1'}`}>{context.certificado.tipo==='A3'?<Smartphone size={21}/>:<KeyRound size={21}/>}</div><div><span className="eyebrow">CERTIFICADO ATIVO</span><h3>{selectedName}</h3><p>{context.certificado.tipo} · {context.certificado.meio_armazenamento} · titular {context.certificado.titular||context.certificado.documento||'não informado'}</p><small>Validade: {fmtDate(context.certificado.validade)} · Ambiente: {context.ambiente}</small></div></div><div className="nfse-cert-actions">{context.certificado.tipo==='A3'&&<button className="button secondary" onClick={()=>void detectA3()} disabled={bridgeLoading||busy}>{bridgeLoading?<><RefreshCw size={14}/> Detectando...</>:<><Wifi size={14}/> Detectar cartão</>}</button>}<button className="button primary" onClick={()=>void consultar()} disabled={busy||(context.certificado.tipo==='A3'&&!bridgeReady)}>{busy?'Consultando...':'Consultar NFS-e'}</button></div></section>}

    {context&&!context.certificado&&<div className="nfse-a3-note nfse-no-certificate"><ShieldCheck size={18}/><div><strong>{context.certificados_cadastrados?.length?'Certificado cadastrado, mas não disponível para consulta':'Nenhum certificado encontrado para este titular'}</strong><span>{context.mensagem_certificado||'Cadastre ou valide um certificado A1/A3 na aba Certificados. Os documentos já importados continuam disponíveis abaixo.'}</span>{Boolean(context.certificados_cadastrados?.length)&&<div className="nfse-cert-diagnostics">{context.certificados_cadastrados?.map(c=><div key={`${c.tipo}-${c.id}`}><strong>{c.tipo} · #{c.id} · {c.status}</strong><span>Validade: {fmtDate(c.validade)}{c.titular?` · ${c.titular}`:''}{c.documento?` · ${c.documento}`:''}</span>{c.motivo&&<span>{c.motivo}</span>}</div>)}</div>}</div></div>}
    {!context&&typeof entityId==='number'&&!error&&<div className="panel empty"><ShieldCheck size={24}/><strong>Carregando titular</strong><span>O ÔMEGA está carregando o certificado e os documentos existentes.</span></div>}
    {context?.certificado?.tipo==='A3'&&!bridgeReady&&<div className="nfse-a3-note"><Smartphone size={18}/><div><strong>Certificado A3: cartão/token necessário</strong><span>Conecte o leitor no computador em que o OMEGA Bridge está instalado, insira o cartão e clique em Detectar cartão.</span></div></div>}

    <section className="panel nfse-list-panel"><div className="section-title-row"><div><span className="eyebrow">NFS-e IMPORTADAS</span><h3>{filteredDocs.length} documento(s)</h3></div><div className="nfse-list-actions"><button className="button secondary small" onClick={exportCsv} disabled={!filteredDocs.length}><Download size={13}/> Exportar CSV/Excel</button><button className="button secondary small" onClick={()=>void downloadSelectedZip()} disabled={!selectedDocs.length||busy}><Download size={13}/> ZIP dos XMLs ({selectedDocs.length})</button><span className="download-count">NSU atual: {context?.ultimo_nsu??0}</span></div></div>{filteredDocs.length===0?<div className="empty"><ReceiptIcon/><strong>Nenhuma NFS-e importada</strong><span>Selecione um titular para ver os documentos importados. Para novas consultas, é necessário certificado válido.</span></div>:<div className="nfse-table"><div className="nfse-row nfse-head"><span>Selecionar</span><span>NSU</span><span>Número</span><span>Chave</span><span>Emissão</span><span>Valor</span><span>Situação</span><span>Ações</span></div>{filteredDocs.map(d=><div className="nfse-row" key={d.id}><span><input type="checkbox" aria-label={`Selecionar NFS-e ${d.numero||d.id}`} checked={selectedDocs.includes(d.id)} onChange={e=>setSelectedDocs(prev=>e.target.checked?[...prev,d.id]:prev.filter(id=>id!==d.id))}/></span><span>{d.nsu??'—'}</span><span>{d.numero||'—'}</span><span className="truncate" title={d.chave_acesso||''}>{d.chave_acesso||'—'}</span><span>{fmtDate(d.data_emissao)}</span><span>{money(d.valor)}</span><span><span className="badge ok">{d.situacao}</span></span><span><button className="icon-button" title="Detalhes e XML" aria-label={`Detalhes da NFS-e ${d.numero||d.id}`} onClick={()=>void openDetail(d)}><Eye size={15}/></button></span></div>)}</div>}</section>

    {selectedDoc&&<div className="nfse-detail-overlay" role="dialog" aria-modal="true" aria-label="Detalhes da NFS-e" onMouseDown={e=>{if(e.target===e.currentTarget)setSelectedDoc(null)}}><section className="panel nfse-detail-dialog"><div className="panel-header"><div><span className="eyebrow">DOCUMENTO FISCAL IMPORTADO</span><h3>NFS-e {selectedDoc.numero||selectedDoc.id}</h3></div><button className="icon-button" onClick={()=>setSelectedDoc(null)} aria-label="Fechar detalhes"><X size={16}/></button></div><div className="nfse-detail-meta"><span><strong>NSU:</strong> {selectedDoc.nsu??'—'}</span><span><strong>Data:</strong> {fmtDate(selectedDoc.data_emissao)}</span><span><strong>Valor:</strong> {money(selectedDoc.valor)}</span><span><strong>Chave:</strong> {selectedDoc.chave_acesso||'—'}</span></div>{detailError&&<div className="form-error">{detailError}</div>}{detailLoading?<div className="empty"><RefreshCw size={20}/><span>Carregando documento...</span></div>:selectedDoc.xml?<><div className="section-title-row"><h4><FileCode2 size={15}/> XML original</h4><div className="actions"><button className="button secondary" onClick={downloadXml}><Download size={14}/> Baixar XML</button><button className="button primary" onClick={()=>void downloadPdf()}><Download size={14}/> Gerar PDF</button></div></div><pre className="nfse-xml-preview">{selectedDoc.xml}</pre></>:<div className="empty"><FileCode2 size={22}/><strong>XML não disponível</strong><span>O registro possui metadados, mas o arquivo XML não está no storage.</span></div>}<div className="form-actions"><button className="button secondary" onClick={()=>setSelectedDoc(null)}>Fechar</button></div></section></div>}
  </div>;
}

function ReceiptIcon(){return <svg width="25" height="25" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M5 3h14v18l-2.5-1.6L14 21l-2-1.6L10 21l-2.5-1.6L5 21V3Z"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>}
