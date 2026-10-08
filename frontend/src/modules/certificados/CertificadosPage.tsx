import {useEffect,useMemo,useState,type FormEvent} from 'react';
import {AlertTriangle,ArrowLeft,CheckCircle2,Clock3,Download,Eye,EyeOff,KeyRound,LockKeyhole,Plus,RefreshCw,Search,ShieldCheck,Smartphone,TestTube2,Trash2,Upload,Wifi,X} from 'lucide-react';
import {useAuth} from '../../auth/AuthContext';
import {listarEmpresasParaSelecao} from '../../services/api/certidoes';
import {baixarA1,baixarSenhaA1,bridgeCertificates,bridgeSignTest,cadastrarA1,cadastrarA3,cadastrarPFA1,cadastrarPFA3,desativarCertificado,detalheCertificado,eventosCertificado,listarCertificados,obterSenhaA1,resumoCertificados,solicitarSubstituicao,testarCertificado,type BridgeCertificate,type Certificado,type CertificadoEvento} from '../../services/api/certificados';
import type {Empresa} from '../../types';

function fmtDate(v?:string|null){if(!v)return '—';const d=new Date(v);return Number.isNaN(d.getTime())?'—':d.toLocaleDateString('pt-BR');}
function days(v?:string|null){if(!v)return null;const d=new Date(v);if(Number.isNaN(d.getTime()))return null;return Math.ceil((d.getTime()-Date.now())/86400000);}
function validity(c?:Certificado){
  const d=days(c?.data_validade);
  if(c?.status==='INATIVO')return ['Inativo','neutral'];
  if(c?.status==='NAO_VINCULADO')return ['Sem vínculo','neutral'];
  if(d!==null&&d<0)return ['Vencido','bad'];
  if(d!==null&&d<=7)return [`${d} dias`,'bad'];
  if(d!==null&&d<=30)return [`${d} dias`,'warn'];
  return ['Ativo','ok'];
}
function maskDocument(v?:string|null){if(!v)return '—';return v.length===14?v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,'$1.$2.$3/$4-$5'):v.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/,'$1.$2.$3-$4');}

type Origin='PJ'|'PF';
type Mode={kind:'A1'|'A3';origin:Origin;empresaId?:number;pessoaId?:number;cpf?:string;nome?:string;replaceId?:number}|null;

export function CertificadosPage(){
  const {usuario}=useAuth();
  const [empresas,setEmpresas]=useState<Empresa[]>([]);
  const [certs,setCerts]=useState<Certificado[]>([]);
  const [summary,setSummary]=useState({empresas_ativas:0,pessoas_fisicas_ativas:0,certificados_ativos:0,vencem_30_dias:0,vencem_7_dias:0,vencidos:0,empresas_sem_certificado:0,pessoas_fisicas_sem_certificado:0});
  const [selected,setSelected]=useState<Certificado|null>(null);
  const [history,setHistory]=useState<CertificadoEvento[]>([]);
  const [search,setSearch]=useState('');
  const [filter,setFilter]=useState<'TODOS'|'A1'|'A3'|'VENCENDO'|'VENCIDOS'|'SEM'>('TODOS');
  const [personType,setPersonType]=useState<Origin>('PJ');
  const [detailTab,setDetailTab]=useState<'CERTIFICADO'|'SENHA'|'HISTORICO'>('CERTIFICADO');
  const [password,setPassword]=useState<string|null>(null);
  const [passwordLoading,setPasswordLoading]=useState(false);
  const [mode,setMode]=useState<Mode>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [bridgeLoading,setBridgeLoading]=useState(false);
  const [bridgeCerts,setBridgeCerts]=useState<BridgeCertificate[]>([]);
  const canAdmin=usuario?.perfil==='ADMIN';

  async function load(){
    setLoading(true);setError('');
    try{
      const [cs,s,es]=await Promise.all([listarCertificados(),resumoCertificados(),listarEmpresasParaSelecao()]);
      setCerts(cs.certificados);setEmpresas(es.empresas);
      const all=cs.certificados.filter(c=>c.status!=='INATIVO');
      const ativos=all.filter(c=>c.apto_para_uso&&c.status==='ATIVO'&&(days(c.data_validade)===null||(days(c.data_validade) as number)>=0)).length;
      const vencidos=all.filter(c=>(days(c.data_validade)??0)<0).length;
      const venc30=all.filter(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=30}).length;
      const venc7=all.filter(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=7}).length;
      setSummary({...s,certificados_ativos:ativos,vencidos,vencem_30_dias:venc30,vencem_7_dias:venc7});
      if(selected){const fresh=cs.certificados.find(c=>c.id===selected.id&&((c.origem||'PJ')===(selected.origem||'PJ')));setSelected(fresh||null)}
    }catch(e){setError(e instanceof Error?e.message:'Não foi possível carregar certificados.')}
    finally{setLoading(false)}
  }
  useEffect(()=>{void load()},[]);

  async function open(c:Certificado){
    setSelected(c);setMode(null);setMessage('');setError('');setPassword(null);setDetailTab('CERTIFICADO');
    try{const h=await eventosCertificado(c.id,(c.origem||'PJ') as Origin);setHistory(h.eventos)}catch{setHistory([])}
  }

  async function revealPassword(){
    if(!selected||selected.tipo!=='A1'||!canAdmin)return;
    setPasswordLoading(true);setError('');setMessage('');
    try{const r=await obterSenhaA1(selected.id,(selected.origem||'PJ') as Origin);setPassword(r.senha);setDetailTab('SENHA')}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível recuperar a senha deste certificado.')}
    finally{setPasswordLoading(false)}
  }

  function start(kind:'A1'|'A3',origin:Origin,entity?:Empresa|Certificado,replaceId?:number){
    setError('');setMessage('');
    if(origin==='PJ'){
      const empresa='razao_social' in (entity||{})?(entity as Empresa).id:undefined;
      setMode({kind,origin,empresaId:empresa,replaceId});
    }else{
      const c=entity as Certificado|undefined;
      setMode({kind,origin,pessoaId:c?.pessoa_id,cpf:c?.cpf||c?.documento_titular,nome:c?.nome_titular||c?.razao_social,replaceId});
    }
  }

  async function submitA1(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!mode)return;
    const fd=new FormData(e.currentTarget);const file=fd.get('arquivo');const senha=String(fd.get('senha')||'');
    if(!(file instanceof File)||!file.size){setError('Selecione o arquivo PFX/P12.');return}
    setBusy(true);setError('');
    try{
      let c:Certificado;
      if(mode.origin==='PF'){
        const cpf=String(fd.get('cpf')||'').replace(/\D/g,'');const nome=String(fd.get('nome')||'').trim();
        if(!cpf||!nome){setError('Informe CPF e nome completo da pessoa física.');return}
        c=await cadastrarPFA1(cpf,nome,file,senha,String(fd.get('email')||''),String(fd.get('telefone')||''));
      }else{
        if(!mode.empresaId)throw new Error('Empresa não identificada.');
        c=await cadastrarA1(mode.empresaId,file,senha);
      }
      setMessage(mode.replaceId?'Certificado A1 substituído com sucesso.':'Certificado A1 cadastrado com sucesso.');setMode(null);await load();await open(c)
    }catch(err){setError(err instanceof Error?err.message:'Não foi possível cadastrar o certificado.')}
    finally{setBusy(false)}
  }

  async function detectBridge(){
    setBridgeLoading(true);setError('');
    try{const r=await bridgeCertificates();setBridgeCerts(r.certificates);if(!r.certificates.length)setError('O Bridge respondeu, mas nenhum certificado A3 foi encontrado no dispositivo.')}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível comunicar com o OMEGA Bridge.');setBridgeCerts([])}
    finally{setBridgeLoading(false)}
  }

  async function submitA3(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!mode)return;
    const fd=new FormData(e.currentTarget);const data:Record<string,string>={meio:String(fd.get('meio')||'CARTAO')};
    ['documento_titular','nome_titular','emissor','numero_serie','data_emissao','data_validade','algoritmo','thumbprint_sha256','dispositivo_modelo','dispositivo_identificador','email','telefone'].forEach(k=>data[k]=String(fd.get(k)||''));
    setBusy(true);setError('');
    try{
      let c:Certificado;
      if(mode.origin==='PF') c=await cadastrarPFA3(data);
      else {if(!mode.empresaId)throw new Error('Empresa não identificada.');data.empresa_id=String(mode.empresaId);data.titular_tipo=String(fd.get('titular_tipo')||'PJ');c=await cadastrarA3(data)}
      setMessage(mode.replaceId?'Certificado A3 substituído com sucesso.':'Identidade A3 cadastrada com sucesso.');setMode(null);await load();await open(c)
    }catch(err){setError(err instanceof Error?err.message:'Não foi possível cadastrar o A3.')}
    finally{setBusy(false)}
  }

  async function testA3Local(){
    if(!selected?.thumbprint_sha256)return;
    const pin=window.prompt('PIN do certificado A3. O PIN será enviado somente ao OMEGA Bridge e não será armazenado pelo ÔMEGA:');
    if(!pin)return;
    setBusy(true);setError('');setMessage('');
    try{const result=await bridgeSignTest(selected.thumbprint_sha256,pin);if(result.ok){setMessage('A3 testado com sucesso: o dispositivo realizou uma assinatura local.');await load()}}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível testar o A3.')}
    finally{setBusy(false)}
  }

  async function action(fn:()=>Promise<unknown>,success:string){
    setBusy(true);setError('');setMessage('');
    try{await fn();setMessage(success);await load();if(selected){const c=await detalheCertificado(selected.id,(selected.origem||'PJ') as Origin);await open(c)}}catch(e){setError(e instanceof Error?e.message:'Operação não concluída.')}finally{setBusy(false)}
  }

  const certByEmpresa=useMemo(()=>{
    const map=new Map<number,Certificado[]>();
    for(const cert of certs.filter(c=>(c.origem||'PJ')==='PJ'&&c.empresa_id!=null)){const list=map.get(cert.empresa_id as number)||[];list.push(cert);map.set(cert.empresa_id as number,list)}
    for(const list of map.values())list.sort((a,b)=>{const rank=(c:Certificado)=>c.status==='ATIVO'?0:c.status==='NAO_VINCULADO'?1:c.status==='EXPIRADO'?2:3;return rank(a)-rank(b)||(new Date(b.atualizado_em||0).getTime()-new Date(a.atualizado_em||0).getTime())});
    return map;
  },[certs]);
  const certByPessoa=useMemo(()=>{
    const map=new Map<number,Certificado[]>();
    for(const cert of certs.filter(c=>(c.origem||'PJ')==='PF'&&c.pessoa_id!=null)){const list=map.get(cert.pessoa_id as number)||[];list.push(cert);map.set(cert.pessoa_id as number,list)}
    for(const list of map.values())list.sort((a,b)=>{const rank=(c:Certificado)=>c.status==='ATIVO'?0:c.status==='NAO_VINCULADO'?1:c.status==='EXPIRADO'?2:3;return rank(a)-rank(b)||(new Date(b.atualizado_em||0).getTime()-new Date(a.atualizado_em||0).getTime())});
    return map;
  },[certs]);

  const rowsPJ=useMemo(()=>{
    const q=search.trim().toLowerCase();
    return empresas.filter(e=>e.ativo!==0).map(empresa=>({empresa,certs:(certByEmpresa.get(empresa.id)||[])})).filter(({empresa,certs:companyCerts})=>{
      const searchable=[empresa.razao_social,empresa.cnpj,...companyCerts.flatMap(c=>[c.nome_titular||'',c.numero_serie||'',c.tipo,c.emissor||''])].join(' ').toLowerCase();
      if(q&&!searchable.includes(q))return false;if(filter==='A1'&&!companyCerts.some(c=>c.tipo==='A1'))return false;if(filter==='A3'&&!companyCerts.some(c=>c.tipo==='A3'))return false;if(filter==='SEM'&&companyCerts.some(c=>c.apto_para_uso&&c.status==='ATIVO'))return false;if(filter==='VENCIDOS'&&!companyCerts.some(c=>(days(c.data_validade)??0)<0))return false;if(filter==='VENCENDO'&&!companyCerts.some(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=30}))return false;return true;
    }).sort((a,b)=>{const valid=(cs:Certificado[])=>Math.min(...cs.filter(c=>c.data_validade).map(c=>new Date(c.data_validade as string).getTime()),Infinity);return valid(a.certs)-valid(b.certs)});
  },[empresas,certByEmpresa,search,filter]);

  const rowsPF=useMemo(()=>{
    const q=search.trim().toLowerCase();const groups=[...certByPessoa.entries()].map(([pessoaId,items])=>({pessoaId,certs:items}));
    return groups.filter(({certs:items})=>{const primary=items.find(c=>c.status==='ATIVO')||items[0];const searchable=[primary?.nome_titular||primary?.razao_social||'',primary?.cpf||primary?.documento_titular||'',...items.flatMap(c=>[c.numero_serie||'',c.tipo,c.emissor||''])].join(' ').toLowerCase();if(q&&!searchable.includes(q))return false;if(filter==='A1'&&!items.some(c=>c.tipo==='A1'))return false;if(filter==='A3'&&!items.some(c=>c.tipo==='A3'))return false;if(filter==='VENCIDOS'&&!items.some(c=>(days(c.data_validade)??0)<0))return false;if(filter==='VENCENDO'&&!items.some(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=30}))return false;if(filter==='SEM')return false;return true}).sort((a,b)=>{const av=Math.min(...a.certs.filter(c=>c.data_validade).map(c=>new Date(c.data_validade as string).getTime()),Infinity);const bv=Math.min(...b.certs.filter(c=>c.data_validade).map(c=>new Date(c.data_validade as string).getTime()),Infinity);return av-bv});
  },[certByPessoa,search,filter]);

  const entityCerts=selected?.origem==='PF'?(certByPessoa.get(selected.pessoa_id||-1)||[]):(certByEmpresa.get(selected?.empresa_id||-1)||[]);
  const entityName=selected?.origem==='PF'?(selected?.nome_titular||selected?.razao_social||'Pessoa Física'):(selected?.razao_social||'Empresa');

  return <div className="page cert-digital-page">
    <div className="page-heading"><div><span className="eyebrow">INFRAESTRUTURA DE IDENTIDADE DIGITAL</span><h2>Certificados Digitais</h2><p>A1 e A3 centralizados para uso seguro pelos módulos do ÔMEGA.</p></div><div className="actions"><button className="button secondary" onClick={()=>void load()} disabled={loading||busy}><RefreshCw size={15}/> Atualizar</button></div></div>
    {error&&<div className="form-error"><AlertTriangle size={15}/>{error}</div>}{message&&<div className="cert-success"><CheckCircle2 size={15}/>{message}</div>}
    <div className="metric-grid cert-metrics"><button className={`metric-card cert-filter ${filter==='TODOS'?'active':''}`} onClick={()=>setFilter('TODOS')}><ShieldCheck size={18}/><span>Certificados ativos</span><strong>{summary.certificados_ativos}</strong><small>A1 + A3 aptos para uso</small></button><button className={`metric-card cert-filter ${filter==='VENCENDO'?'active':''}`} onClick={()=>setFilter('VENCENDO')}><Clock3 size={18}/><span>Vencem em 30 dias</span><strong>{summary.vencem_30_dias}</strong><small>inclui os que vencem em 7 dias</small></button><button className={`metric-card cert-filter ${filter==='VENCIDOS'?'active':''}`} onClick={()=>setFilter('VENCIDOS')}><AlertTriangle size={18}/><span>Vencidos</span><strong>{summary.vencidos}</strong><small>exigem substituição</small></button><button className="metric-card"><KeyRound size={18}/><span>{personType==='PF'?'Pessoas sem certificado':'Empresas sem certificado'}</span><strong>{personType==='PF'?summary.pessoas_fisicas_sem_certificado:summary.empresas_sem_certificado}</strong><small>{personType==='PF'?'pessoas ativas':'empresas ativas'}</small></button></div>
    <section className="panel cert-toolbar-panel"><div className="cert-toolbar"><div className="cert-person-switch" role="tablist" aria-label="Tipo de titular"><button className={personType==='PJ'?'active':''} onClick={()=>{setPersonType('PJ');setFilter('TODOS');setSelected(null)}}>Pessoa Jurídica (PJ)</button><button className={personType==='PF'?'active':''} onClick={()=>{setPersonType('PF');setFilter('TODOS');setSelected(null)}}>Pessoa Física (PF)</button></div><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder={personType==='PF'?'Pesquisar CPF, nome ou série...':'Pesquisar empresa, CNPJ, titular ou série...'}/></div><div className="cert-filters">{(['TODOS','A1','A3','VENCENDO','VENCIDOS','SEM'] as const).map(f=><button key={f} className={`filter-chip ${filter===f?'active':''}`} onClick={()=>setFilter(f)} disabled={personType==='PF'&&f==='SEM'}>{f==='SEM'?'Sem certificado':f==='VENCENDO'?'A vencer':f==='VENCIDOS'?'Vencidos':f}</button>)}</div><button className="button primary" onClick={()=>start('A1',personType)}><Plus size={15}/> {personType==='PF'?'Adicionar PF':'Adicionar certificado'}</button></div></section>

    <section className="panel cert-list-panel cert-list-full"><div className="panel-header"><div><span className="eyebrow">{personType==='PF'?'PESSOAS FÍSICAS':'EMPRESAS'}</span><h3>{personType==='PF'?rowsPF.length:rowsPJ.length} {personType==='PF'?'pessoa(s)':'empresa(s)'}</h3></div><span className="muted">ordenadas pela validade</span></div>
      {loading?<div className="empty"><div className="spinner"/><span>Carregando certificados...</span></div>:personType==='PJ'?<div className="table-wrap"><table><thead><tr><th>Empresa</th><th>Certificado</th><th>Titular / emissor</th><th>Validade</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{rowsPJ.map(({empresa,certs:companyCerts})=>{const primary=companyCerts.find(c=>c.status==='ATIVO')||companyCerts[0];const [label,cls]=validity(primary);const selectedRow=companyCerts.some(c=>c.id===selected?.id&&selected?.origem==='PJ');return <tr key={empresa.id} className={selectedRow?'selected-row':''} onClick={()=>primary?void open(primary):start('A1','PJ',empresa)} title={primary?'Clique para abrir os detalhes e ações':'Clique para adicionar um certificado'}><td><strong>{empresa.razao_social}</strong><small>{empresa.cnpj}</small></td><td>{companyCerts.length?<div className="cert-type-list">{companyCerts.map(cert=><button key={cert.id} className="cert-inline-button" onClick={event=>{event.stopPropagation();void open(cert)}}><strong>{cert.tipo}</strong><small>{cert.meio_armazenamento}</small></button>)}</div>:<span className="badge neutral">Sem certificado</span>}</td><td>{primary?<><strong>{primary.nome_titular||'—'}</strong><small>{primary.emissor||'Emissor não informado'}</small></>:<span>—</span>}</td><td>{primary?<><strong>{fmtDate(primary.data_validade)}</strong><small>{days(primary.data_validade)!==null&&days(primary.data_validade)!==-0?`${days(primary.data_validade)} dias restantes`:label}</small></>:<span>—</span>}</td><td><span className={`badge ${cls}`}>{label}</span></td><td><button className="icon-button" title={primary?'Acessar certificado':'Adicionar certificado'} onClick={event=>{event.stopPropagation();primary?void open(primary):start('A1','PJ',empresa)}}>{primary?<ArrowLeft size={15} style={{transform:'rotate(180deg)'}}/>:<Plus size={15}/>}</button></td></tr>})}{!rowsPJ.length&&<tr><td colSpan={6}><div className="empty compact"><KeyRound size={25}/><strong>Nenhuma empresa encontrada</strong><span>Ajuste os filtros.</span></div></td></tr>}</tbody></table></div>:<div className="table-wrap"><table><thead><tr><th>Pessoa física</th><th>Certificado</th><th>Titular / emissor</th><th>Validade</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{rowsPF.map(({pessoaId,certs:items})=>{const primary=items.find(c=>c.status==='ATIVO')||items[0];const [label,cls]=validity(primary);const selectedRow=items.some(c=>c.id===selected?.id&&selected?.origem==='PF');return <tr key={`pf-${pessoaId}`} className={selectedRow?'selected-row':''} onClick={()=>void open(primary)}><td><strong>{primary.nome_titular||primary.razao_social}</strong><small>CPF {maskDocument(primary.cpf||primary.documento_titular)}</small></td><td><div className="cert-type-list">{items.map(cert=><button key={cert.id} className="cert-inline-button" onClick={event=>{event.stopPropagation();void open(cert)}}><strong>{cert.tipo}</strong><small>{cert.meio_armazenamento}</small></button>)}</div></td><td><strong>{primary.nome_titular||'—'}</strong><small>{primary.emissor||'Emissor não informado'}</small></td><td><strong>{fmtDate(primary.data_validade)}</strong><small>{label}</small></td><td><span className={`badge ${cls}`}>{label}</span></td><td><button className="icon-button" onClick={event=>{event.stopPropagation();void open(primary)}}><ArrowLeft size={15} style={{transform:'rotate(180deg)'}}/></button></td></tr>})}{!rowsPF.length&&<tr><td colSpan={6}><div className="empty compact"><KeyRound size={25}/><strong>Nenhuma pessoa física cadastrada</strong><span>Use “Adicionar PF” para cadastrar um certificado A1 ou A3.</span></div></td></tr>}</tbody></table></div>}
    </section>

    {selected&&<div className="cert-detail-overlay" role="dialog" aria-modal="true" aria-label={`Detalhes do certificado de ${entityName}`} onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null)}}><div className="panel cert-detail-panel cert-detail-modal"><div className="panel-header"><div><span className="eyebrow">{selected.origem==='PF'?'PESSOA FÍSICA':'CERTIFICADO'}</span><h3>{entityName}</h3></div><button className="icon-button" onClick={()=>setSelected(null)}><X size={15}/></button></div><div className="cert-detail-tabs" role="tablist"><button className={detailTab==='SENHA'?'active':''} onClick={()=>void (password?setDetailTab('SENHA'):revealPassword())} disabled={selected.tipo!=='A1'||!canAdmin}>{selected.tipo==='A1'?'Senha do certificado':'PIN do A3'}</button><button className={detailTab==='CERTIFICADO'?'active':''} onClick={()=>setDetailTab('CERTIFICADO')}>Certificado</button><button className={detailTab==='HISTORICO'?'active':''} onClick={()=>setDetailTab('HISTORICO')}>Histórico</button></div><div className="cert-detail-body">
      {detailTab==='CERTIFICADO'&&<><div className="cert-identity"><div className="cert-type-icon">{selected.tipo==='A1'?<KeyRound size={22}/>:<Smartphone size={22}/>}</div><div><strong>{selected.tipo} · {selected.meio_armazenamento}</strong><span>{selected.apto_para_uso?'Pronto para utilização':'Não apto para uso'}</span></div></div><div className="details cert-details"><div><span>Titular</span><strong>{selected.nome_titular||'—'}</strong></div><div><span>CPF/CNPJ</span><strong>{maskDocument(selected.documento_titular||selected.cpf)}</strong></div><div><span>Emissor</span><strong>{selected.emissor||'—'}</strong></div><div><span>Número de série</span><strong>{selected.numero_serie||'—'}</strong></div><div><span>Emissão</span><strong>{fmtDate(selected.data_emissao)}</strong></div><div><span>Validade</span><strong>{fmtDate(selected.data_validade)}</strong></div><div><span>Algoritmo</span><strong>{selected.algoritmo||'—'}</strong></div><div><span>Status</span><strong>{validity(selected)[0]}</strong></div></div>{selected.status==='NAO_VINCULADO'&&<div className="cert-warning"><AlertTriangle size={15}/><span>Este certificado está cadastrado, mas não está apto para uso.</span></div>}<div className="cert-actions">{canAdmin&&<><button className="button primary" onClick={()=>start(selected.tipo,(selected.origem||'PJ') as Origin,selected,selected.id)} disabled={busy}><RefreshCw size={14}/> Substituir</button><button className="button secondary" onClick={()=>selected.tipo==='A3'?void testA3Local():void action(()=>testarCertificado(selected.id,(selected.origem||'PJ') as Origin),'Teste concluído.')} disabled={busy}><TestTube2 size={14}/> Testar acesso</button>{selected.tipo==='A1'&&<><button className="button secondary" onClick={()=>void baixarA1(selected.id,'certificado.p12',(selected.origem||'PJ') as Origin)} disabled={busy}><Download size={14}/> Baixar A1</button><button className="button secondary" onClick={()=>void revealPassword()} disabled={busy||passwordLoading}><KeyRound size={14}/> {passwordLoading?'Carregando senha...':'Ver senha'}</button></>}<button className="button danger" onClick={()=>{if(confirm('Desativar este certificado?'))void action(()=>desativarCertificado(selected.id,(selected.origem||'PJ') as Origin),'Certificado desativado.')}} disabled={busy}><Trash2 size={14}/> Desativar</button></>}{!canAdmin&&<button className="button secondary" onClick={()=>void action(()=>solicitarSubstituicao(selected.id,(selected.origem||'PJ') as Origin),'Solicitação de substituição registrada.')} disabled={busy}><RefreshCw size={14}/> Solicitar substituição</button>}</div><div className="cert-credential-note"><LockKeyhole size={15}/><div><strong>{selected.tipo==='A1'?'Senha protegida e recuperável':'PIN protegido no dispositivo'}</strong><span>{selected.tipo==='A1'?'A senha do A1 fica criptografada e pode ser recuperada inclusive em certificados vencidos ou substituídos, se ainda estiver armazenada.':'A chave privada e o PIN permanecem no cartão/token e nunca são enviados ao servidor.'}</span></div></div></>}
      {detailTab==='SENHA'&&<div className="cert-password-tab">{selected.tipo==='A1'&&canAdmin?<>{password===null?<div className="cert-password-locked"><LockKeyhole size={24}/><strong>Senha protegida</strong><span>Clique em “Ver senha” para recuperá-la do armazenamento criptografado.</span><button className="button primary" onClick={()=>void revealPassword()} disabled={passwordLoading}>{passwordLoading?'Recuperando...':<><Eye size={14}/> Ver senha</>}</button></div>:<div className="cert-password-value"><label>Senha armazenada</label><div className="password-field"><input value={password} readOnly type="text" aria-label="Senha do certificado"/><button className="icon-button" title="Ocultar senha" onClick={()=>setPassword(null)}><EyeOff size={15}/></button></div><div className="cert-password-actions"><button className="button secondary" onClick={()=>void baixarSenhaA1(selected.id,(selected.origem||'PJ') as Origin)}><Download size={14}/> Baixar senha (.txt)</button><button className="button secondary" onClick={()=>{if(navigator.clipboard)void navigator.clipboard.writeText(password).then(()=>setMessage('Senha copiada para a área de transferência.'))}}><KeyRound size={14}/> Copiar senha</button></div><small>Uso restrito a administradores.</small></div>}</>:<div className="cert-password-locked"><Smartphone size={25}/><strong>PIN do A3 não é armazenado</strong><span>O ÔMEGA nunca grava o PIN de cartão/token. O acesso é feito pelo OMEGA Bridge.</span></div>}</div>}
      {detailTab==='HISTORICO'&&<><div className="cert-related-panel"><div className="section-title-row"><div><span className="eyebrow">TODOS OS REGISTROS</span><h4>Certificados de {selected.origem==='PF'?'esta pessoa':'esta empresa'}</h4></div><span className="download-count">{entityCerts.length} registro(s)</span></div><div className="cert-related-list">{entityCerts.map(c=><button key={`${c.origem||'PJ'}-${c.id}`} className={`cert-related-item ${c.id===selected.id?'active':''}`} onClick={()=>void open(c)}><div><strong>{c.tipo} · {c.meio_armazenamento}</strong><span>{c.nome_titular||'Titular não informado'} · validade {fmtDate(c.data_validade)}</span></div><span className={`badge ${validity(c)[1]}`}>{validity(c)[0]}</span></button>)}</div></div><div className="cert-history"><div className="section-title-row"><div><span className="eyebrow">HISTÓRICO</span><h4>Eventos</h4></div></div>{history.length?history.map(h=><div className="history-item" key={h.id}><strong>{h.tipo_evento}</strong><span>{h.descricao}</span><small>{h.usuario||'Sistema'} · {fmtDate(h.criado_em)}</small></div>):<span className="muted">Nenhum evento registrado.</span>}</div></>}
    </div></div></div>}

    {mode&&<div className="cert-form-overlay" role="dialog" aria-modal="true"><div className="cert-form-dialog"><div className="panel-header"><div><span className="eyebrow">{mode.replaceId?'SUBSTITUIR':'ADICIONAR'} CERTIFICADO</span><h3>{mode.kind} · {mode.origin==='PF'?(mode.nome||'Pessoa Física'):(empresas.find(e=>e.id===mode.empresaId)?.razao_social||'Empresa')}</h3></div><button className="icon-button" onClick={()=>!busy&&setMode(null)}><X size={15}/></button></div>{mode.kind==='A1'?<form onSubmit={submitA1}><div className="cert-form-body">{mode.origin==='PF'&&<div className="cert-a3-grid"><label>CPF<input name="cpf" defaultValue={mode.cpf||''} placeholder="Somente números" required/></label><label>Nome completo<input name="nome" defaultValue={mode.nome||''} required/></label><label>E-mail<input name="email" type="email"/></label><label>Telefone<input name="telefone"/></label></div>}<div className="upload-drop"><Upload size={25}/><strong>Selecione o certificado .PFX ou .P12</strong><span>Limite de 10 MB · o arquivo será criptografado no servidor</span><input name="arquivo" type="file" accept=".pfx,.p12,application/x-pkcs12" required/></div><label>Senha do certificado<input name="senha" type="password" autoComplete="new-password" required maxLength={200}/><small>Usada somente para validar e operar o PFX; a senha fica criptografada.</small></label></div><div className="form-actions"><button type="button" className="button secondary" onClick={()=>setMode(null)} disabled={busy}>Cancelar</button><button className="button primary" disabled={busy}>{busy?'Validando...':'Validar e salvar A1'}</button></div></form>:<form onSubmit={submitA3}><div className="cert-a3-bridge-bar"><div><strong>OMEGA Bridge</strong><span>Detecte o certificado diretamente no cartão/token sem enviar a chave privada.</span></div><button type="button" className="button secondary" onClick={()=>void detectBridge()} disabled={bridgeLoading}>{bridgeLoading?<><RefreshCw size={14}/> Consultando...</>:<><Wifi size={14}/> Detectar dispositivo</>}</button></div>{bridgeCerts.length>0&&<div className="cert-a3-detected"><label>Certificado detectado<select defaultValue="" onChange={e=>{const c=bridgeCerts.find(x=>x.thumbprint_sha256===e.target.value);if(!c)return;const form=e.currentTarget.form;if(!form)return;(form.elements.namedItem('nome_titular') as HTMLInputElement|null)!.value=c.subject;(form.elements.namedItem('documento_titular') as HTMLInputElement|null)!.value=c.documento_titular||'';(form.elements.namedItem('emissor') as HTMLInputElement|null)!.value=c.issuer;(form.elements.namedItem('numero_serie') as HTMLInputElement|null)!.value=c.serial;(form.elements.namedItem('data_emissao') as HTMLInputElement|null)!.value=c.valid_from.slice(0,10);(form.elements.namedItem('data_validade') as HTMLInputElement|null)!.value=c.valid_to.slice(0,10);(form.elements.namedItem('dispositivo_identificador') as HTMLInputElement|null)!.value=c.thumbprint_sha256;(form.elements.namedItem('thumbprint_sha256') as HTMLInputElement|null)!.value=c.thumbprint_sha256}}><option value="">Selecione...</option>{bridgeCerts.map(c=><option key={c.thumbprint_sha256} value={c.thumbprint_sha256}>{c.token_label} · {c.label||c.serial}</option>)}</select></label></div>}
      <div className="cert-form-body cert-a3-grid">{mode.origin==='PF'&&<><label>CPF<input name="documento_titular" defaultValue={mode.cpf||''} placeholder="Somente números" required/></label><label>Nome completo<input name="nome_titular" defaultValue={mode.nome||''} required/></label></>}{mode.origin==='PJ'&&<label>Tipo do titular<select name="titular_tipo" defaultValue="PJ"><option value="PJ">Pessoa Jurídica</option><option value="PF">Pessoa Física</option></select></label>}<label>Meio<select name="meio" defaultValue="CARTAO"><option value="CARTAO">Cartão</option><option value="TOKEN">Token</option></select></label>{mode.origin==='PJ'&&<label>CPF/CNPJ do titular<input name="documento_titular" placeholder="Somente números" required/></label>}<label>Emissor<input name="emissor" placeholder="Autoridade certificadora"/></label><label>Número de série<input name="numero_serie"/></label><label>Data de emissão<input name="data_emissao" type="date"/></label><label>Data de validade<input name="data_validade" type="date"/></label><label>Algoritmo<input name="algoritmo" placeholder="Ex.: SHA256withRSA"/></label><input type="hidden" name="thumbprint_sha256"/><label>Modelo do dispositivo<input name="dispositivo_modelo" placeholder="Fabricante/modelo"/></label><label>Identificador do dispositivo<input name="dispositivo_identificador" placeholder="Não informe PIN"/></label></div><div className="cert-a3-security"><ShieldCheck size={16}/><span>A chave privada e o PIN não entram no cadastro. O A3 é usado pelo OMEGA Bridge diretamente no cartão/token.</span></div><div className="form-actions"><button type="button" className="button secondary" onClick={()=>setMode(null)} disabled={busy}>Cancelar</button><button className="button primary" disabled={busy}>{busy?'Salvando...':'Salvar A3'}</button></div></form>}</div></div>}
  </div>;
}
