import {useEffect,useMemo,useState,type FormEvent} from 'react';
import {AlertTriangle,ArrowLeft,CheckCircle2,Clock3,Download,Eye,EyeOff,KeyRound,LockKeyhole,Plus,RefreshCw,Search,ShieldCheck,Smartphone,TestTube2,Trash2,Upload,Wifi,X} from 'lucide-react';
import {useAuth} from '../../auth/AuthContext';
import {listarEmpresasParaSelecao} from '../../services/api/certidoes';
import {baixarA1,baixarSenhaA1,bridgeCertificates,bridgeDiagnostics,bridgeSignTest,cadastrarA1,cadastrarA3,cadastrarPFA1,cadastrarPFA3,desativarCertificado,detalheCertificado,eventosCertificado,listarCertificados,listarPessoasFisicas,obterSenhaA1,resumoCertificados,solicitarSubstituicao,testarCertificado,type BridgeCertificate,type Certificado,type CertificadoEvento,type PessoaFisica} from '../../services/api/certificados';
import type {Empresa} from '../../types';

function fmtDate(v?:string|null){if(!v)return '—';const raw=String(v);const dateOnly=/^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);const d=dateOnly?new Date(Number(dateOnly[1]),Number(dateOnly[2])-1,Number(dateOnly[3])):new Date(raw);return Number.isNaN(d.getTime())?'—':d.toLocaleDateString('pt-BR');}
function expiryTimestamp(v?:string|null){if(!v)return null;const raw=String(v);const dateOnly=/^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);const d=dateOnly?new Date(Number(dateOnly[1]),Number(dateOnly[2])-1,Number(dateOnly[3]),23,59,59,999):new Date(raw);return Number.isNaN(d.getTime())?null:d.getTime();}
function isExpired(v?:string|null){const time=expiryTimestamp(v);return time!==null&&time<Date.now();}
function days(v?:string|null){const timestamp=expiryTimestamp(v);if(timestamp===null)return null;return Math.ceil((timestamp-Date.now())/86400000);}
function validity(c?:Certificado){
  if(!c)return ['Sem certificado','neutral'];
  const d=days(c.data_validade);
  if(c.status==='INATIVO')return ['Inativo','neutral'];
  if(c.status==='NAO_VINCULADO')return ['Sem vínculo','neutral'];
  if(c.status==='EXPIRADO'||isExpired(c.data_validade))return ['Vencido','bad'];
  if(!c.apto_para_uso)return ['Não apto','neutral'];
  if(d===null)return ['Validade ausente','warn'];
  if(d<=7)return [`${d} dias`,'bad'];
  if(d<=30)return [`${d} dias`,'warn'];
  return ['Ativo','ok'];
}
function maskDocument(v?:string|null){if(!v)return '—';return v.length===14?v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/,'$1.$2.$3/$4-$5'):v.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/,'$1.$2.$3-$4');}

type Origin='PJ'|'PF';
type Mode={kind:'A1'|'A3';origin:Origin;empresaId?:number;pessoaId?:number;cpf?:string;nome?:string;replaceId?:number}|null;
type SelectedEntity={origin:Origin;empresaId?:number;pessoaId?:number;name:string;document?:string};

export function CertificadosPage(){
  const {usuario}=useAuth();
  const [empresas,setEmpresas]=useState<Empresa[]>([]);
  const [pessoas,setPessoas]=useState<PessoaFisica[]>([]);
  const [certs,setCerts]=useState<Certificado[]>([]);
  const [summary,setSummary]=useState({empresas_ativas:0,pessoas_fisicas_ativas:0,certificados_ativos:0,vencem_30_dias:0,vencem_7_dias:0,vencidos:0,empresas_sem_certificado:0,pessoas_fisicas_sem_certificado:0});
  const [selected,setSelected]=useState<Certificado|null>(null);
  const [selectedEntity,setSelectedEntity]=useState<SelectedEntity|null>(null);
  const [history,setHistory]=useState<CertificadoEvento[]>([]);
  const [search,setSearch]=useState('');
  const [filter,setFilter]=useState<'TODOS'|'A1'|'A3'|'VENCENDO'|'VENCIDOS'|'SEM'>('TODOS');
  const [personType,setPersonType]=useState<Origin>('PJ');
  const [detailTab,setDetailTab]=useState<'CERTIFICADO'|'SENHA'|'HISTORICO'>('CERTIFICADO');
  const [password,setPassword]=useState<string|null>(null);
  const [passwordLoading,setPasswordLoading]=useState(false);
  const [mode,setMode]=useState<Mode>(null);
  const [showPfCreate,setShowPfCreate]=useState(false);
  const [newCertType,setNewCertType]=useState<'A1'|'A3'>('A1');
  const [dragOver,setDragOver]=useState(false);
  const [selectedA1File,setSelectedA1File]=useState<File|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');
  const [bridgeLoading,setBridgeLoading]=useState(false);
  const [bridgeCerts,setBridgeCerts]=useState<BridgeCertificate[]>([]);
  const [detectedA3,setDetectedA3]=useState<BridgeCertificate|null>(null);
  const [a3Cpf,setA3Cpf]=useState('');
  const [a3Nome,setA3Nome]=useState('');
  const [a3Pin,setA3Pin]=useState('');
  const canAdmin=usuario?.perfil==='ADMIN';
  const canViewPassword=Boolean(canAdmin);

  async function load(){
    setLoading(true);setError('');
    try{
      const [cs,s,es,pf]=await Promise.all([listarCertificados(),resumoCertificados(),listarEmpresasParaSelecao(),listarPessoasFisicas()]);
      setCerts(cs.certificados);setEmpresas(es.empresas);setPessoas(pf.pessoas);
      const all=cs.certificados.filter(c=>c.status!=='INATIVO');
      const ativos=all.filter(c=>c.apto_para_uso&&c.status==='ATIVO'&&!isExpired(c.data_validade)&&days(c.data_validade)!==null).length;
      const vencidos=all.filter(c=>c.status==='EXPIRADO'||isExpired(c.data_validade)).length;
      const venc30=all.filter(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=30}).length;
      const venc7=all.filter(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=7}).length;
      setSummary({...s,certificados_ativos:ativos,vencidos,vencem_30_dias:venc30,vencem_7_dias:venc7});
      if(selected){const fresh=cs.certificados.find(c=>c.id===selected.id&&((c.origem||'PJ')===(selected.origem||'PJ')));setSelected(fresh||null)}
    }catch(e){setError(e instanceof Error?e.message:'Não foi possível carregar certificados.')}
    finally{setLoading(false)}
  }
  useEffect(()=>{void load()},[]);

  async function open(c:Certificado){
    setSelected(c);setSelectedEntity({origin:(c.origem||'PJ') as Origin,empresaId:c.empresa_id,pessoaId:c.pessoa_id,name:c.origem==='PF'?(c.nome_titular||c.razao_social||'Pessoa Física'):(c.razao_social||'Empresa'),document:c.cpf||c.documento_titular||undefined});setMode(null);setMessage('');setError('');setPassword(null);setDetailTab('CERTIFICADO');
    try{const h=await eventosCertificado(c.id,(c.origem||'PJ') as Origin);setHistory(h.eventos)}catch{setHistory([])}
  }

  function openEntity(entity:Empresa|PessoaFisica, origin:Origin){
    const isPJ=origin==='PJ';
    const id=isPJ?(entity as Empresa).id:(entity as PessoaFisica).id;
    const list=isPJ?(certByEmpresa.get(id)||[]):(certByPessoa.get(id)||[]);
    const primary=list.find(c=>c.status==='ATIVO')||list[0];
    setSelectedEntity({origin,empresaId:isPJ?id:undefined,pessoaId:isPJ?undefined:id,name:isPJ?(entity as Empresa).razao_social:(entity as PessoaFisica).nome,document:isPJ?(entity as Empresa).cnpj:(entity as PessoaFisica).cpf});
    setSelected(primary||null);
    setMode(null);setMessage('');setError('');setPassword(null);setDetailTab('CERTIFICADO');
    if(primary){void eventosCertificado(primary.id,origin).then(h=>setHistory(h.eventos)).catch(()=>setHistory([]));}
    else setHistory([]);
  }

  async function revealPassword(){
    if(!selected||selected.tipo!=='A1'||!canViewPassword)return;
    setPasswordLoading(true);setError('');setMessage('');
    try{const r=await obterSenhaA1(selected.id,(selected.origem||'PJ') as Origin);setPassword(r.senha);setDetailTab('SENHA')}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível recuperar a senha deste certificado.')}
    finally{setPasswordLoading(false)}
  }

  function start(kind:'A1'|'A3',origin:Origin,entity?:Empresa|Certificado|PessoaFisica,replaceId?:number){
    // O formulário de cadastro/substituição ocupa o próprio fluxo modal.
    // Fechamos o detalhe da empresa antes de abri-lo para evitar modais empilhados.
    setSelected(null);setSelectedEntity(null);
    setError('');setMessage('');setSelectedA1File(null);setDragOver(false);setBridgeCerts([]);setDetectedA3(null);setA3Pin('');
    const entityCert=entity&&'pessoa_id' in entity?entity as Certificado:null;
    const entityPerson=entity&&'cpf' in entity?entity as PessoaFisica:null;
    setA3Cpf(origin==='PF' ? String(entityPerson?.cpf||entityCert?.cpf||entityCert?.documento_titular||'') : '');
    setA3Nome(origin==='PF' ? String(entityPerson?.nome||entityCert?.nome_titular||'') : '');
    if(origin==='PJ'){
      // Ao iniciar a partir de um certificado, use empresa_id (não o ID do
      // próprio certificado); ao iniciar a partir da tabela, use o ID da empresa.
      const company=entity&&'cnpj' in entity?entity as Empresa:null;
      const existingCert=entity&&'empresa_id' in entity?entity as Certificado:null;
      const empresaId=company?.id??existingCert?.empresa_id;
      setMode({kind,origin,empresaId,replaceId});
    }else{
      const c='pessoa_id' in (entity||{})?(entity as Certificado):undefined;
      const pf='cpf' in (entity||{})?(entity as PessoaFisica):undefined;
      setMode({kind,origin,pessoaId:c?.pessoa_id||pf?.id,cpf:c?.cpf||c?.documento_titular||pf?.cpf,nome:c?.nome_titular||c?.razao_social||pf?.nome,replaceId});
    }
  }

  async function submitA1(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!mode)return;
    const fd=new FormData(e.currentTarget);const senha=String(fd.get('senha')||'');
    const chosenFile=selectedA1File;
    if(!chosenFile||!chosenFile.size){setError('Arraste ou selecione o arquivo PFX/P12.');return}
    const ext=chosenFile.name.toLowerCase();
    if(!ext.endsWith('.pfx')&&!ext.endsWith('.p12')){setError('O arquivo precisa ser .PFX ou .P12.');return}
    if(chosenFile.size>10*1024*1024){setError('O certificado deve ter no máximo 10 MB.');return}
    setBusy(true);setError('');
    try{
      let c:Certificado;
      if(mode.origin==='PF'){
        const cpf=String(fd.get('cpf')||'').replace(/\D/g,'');const nome=String(fd.get('nome')||'').trim();
        if(!cpf||!nome){setError('Informe CPF e nome completo da pessoa física.');return}
        c=await cadastrarPFA1(cpf,nome,chosenFile,senha,String(fd.get('email')||''),String(fd.get('telefone')||''));
      }else{
        if(!mode.empresaId)throw new Error('Empresa não identificada.');
        c=await cadastrarA1(mode.empresaId,chosenFile,senha);
      }
      setMessage(mode.replaceId?'Certificado A1 substituído com sucesso.':'Certificado A1 cadastrado com sucesso.');setMode(null);await load();await open(c)
    }catch(err){setError(err instanceof Error?err.message:'Não foi possível cadastrar o certificado.')}
    finally{setBusy(false)}
  }

  async function detectBridge(){
    if(!mode)return;
    const documentDigits=(mode.origin==='PF'?a3Cpf:(empresas.find(e=>e.id===mode.empresaId)?.cnpj||'')).replace(/\D/g,'');
    if((mode.origin==='PF'&&documentDigits.length!==11)||(mode.origin==='PJ'&&documentDigits.length!==14)){
      setError(mode.origin==='PF'?'Informe o CPF da pessoa antes de detectar o cartão.':'Não foi possível identificar o CNPJ da empresa selecionada.');
      return;
    }
    setBridgeLoading(true);setError('');setMessage('');setDetectedA3(null);setBridgeCerts([]);
    try{
      const diag=await bridgeDiagnostics();
      if(!diag.pcsc){throw new Error(diag.reader_error||'Conecte o leitor de cartão.')}
      if(!diag.pkcs11_configured){throw new Error(diag.hint||'Instale o middleware do certificado A3.')}
      const r=await bridgeCertificates();
      const matches=r.certificates.filter(c=>(c.documento_titular||'').replace(/\D/g,'')===documentDigits);
      if(!matches.length)throw new Error(`Nenhum certificado detectado corresponde ao ${mode.origin==='PF'?'CPF':'CNPJ'} informado. Confira o cartão e o middleware.`);
      setBridgeCerts(matches);
      if(matches.length===1)setDetectedA3(matches[0]);
      if(mode.origin==='PF'&&!a3Nome.trim())setA3Nome(matches[0].nome_titular||'');
      setMessage(matches.length===1?'Certificado compatível detectado. Os dados técnicos foram preenchidos automaticamente.':`${matches.length} certificados correspondem à entidade. Selecione o certificado correto.`);
    }
    catch(e){setError(e instanceof Error?e.message:'Não foi possível comunicar com o OMEGA Bridge.');setBridgeCerts([]);setDetectedA3(null)}
    finally{setBridgeLoading(false)}
  }

  function chooseBridgeCertificate(thumbprint:string){
    const found=bridgeCerts.find(c=>c.thumbprint_sha256.toLowerCase()===thumbprint.toLowerCase())||null;
    setDetectedA3(found);
    setError('');
    if(found)setMessage('Certificado selecionado. Confirme o PIN e salve o cadastro.');
  }

  async function submitA3(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!mode)return;
    setBusy(true);setError('');setMessage('');
    try{
      let c:Certificado;
      const medium=detectedA3?.token_label?.toUpperCase().includes('TOKEN')?'TOKEN':'CARTAO';
      const metadata=detectedA3?{
        meio:medium,
        emissor:detectedA3.issuer,
        numero_serie:detectedA3.serial,
        data_emissao:detectedA3.valid_from,
        data_validade:detectedA3.valid_to,
        thumbprint_sha256:detectedA3.thumbprint_sha256,
        dispositivo_modelo:detectedA3.token_label||detectedA3.label||'Dispositivo A3',
        dispositivo_identificador:detectedA3.slot||detectedA3.id,
      }:null;
      if(mode.origin==='PF'){
        const cpf=a3Cpf.replace(/\D/g,'');const nome=a3Nome.trim();
        if(cpf.length!==11||!nome)throw new Error('Informe CPF e nome completo para registrar o tipo A3.');
        c=await cadastrarPFA3(metadata?{cpf,nome,...metadata}:{cpf,nome,meio:'CARTAO'});
      }else{
        if(!mode.empresaId)throw new Error('Empresa não identificada.');
        const documento=(empresas.find(e=>e.id===mode.empresaId)?.cnpj||'').replace(/\D/g,'');
        c=await cadastrarA3(metadata?{
          empresa_id:String(mode.empresaId),titular_tipo:'PJ',documento_titular:documento,
          nome_titular:detectedA3.nome_titular||empresas.find(e=>e.id===mode.empresaId)?.razao_social||'',
          ...metadata,
        }:{
          empresa_id:String(mode.empresaId),meio:'CARTAO',titular_tipo:'PJ',documento_titular:documento,
        });
      }
      setA3Pin('');
      setMessage(detectedA3
        ?'Certificado A3 vinculado ao cartão/token detectado. Confira a validade e teste o acesso antes de usar no módulo NFS-e.'
        :'Tipo A3 cadastrado. O certificado permanece sem vínculo técnico e não poderá consultar NFS-e até ser associado a um cartão/token.');
      setMode(null);await load();await open(c);
    }catch(err){setError(err instanceof Error?err.message:'Não foi possível registrar o certificado A3.')}
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
      if(q&&!searchable.includes(q))return false;if(filter==='A1'&&!companyCerts.some(c=>c.tipo==='A1'))return false;if(filter==='A3'&&!companyCerts.some(c=>c.tipo==='A3'))return false;if(filter==='SEM'&&companyCerts.some(c=>c.apto_para_uso&&c.status==='ATIVO'))return false;if(filter==='VENCIDOS'&&!companyCerts.some(c=>c.status==='EXPIRADO'||isExpired(c.data_validade)))return false;if(filter==='VENCENDO'&&!companyCerts.some(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=30}))return false;return true;
    }).sort((a,b)=>{const valid=(cs:Certificado[])=>Math.min(...cs.filter(c=>c.data_validade).map(c=>new Date(c.data_validade as string).getTime()),Infinity);return valid(a.certs)-valid(b.certs)});
  },[empresas,certByEmpresa,search,filter]);

  const rowsPF=useMemo(()=>{
    const q=search.trim().toLowerCase();
    return pessoas.map(pessoa=>({pessoa, pessoaId:pessoa.id, certs:certByPessoa.get(pessoa.id)||[]})).filter(({pessoa,certs:items})=>{
      const primary=items.find(c=>c.status==='ATIVO'&&c.apto_para_uso&&days(c.data_validade)!==null&&!isExpired(c.data_validade))||items.find(c=>c.status==='ATIVO'&&!isExpired(c.data_validade))||items[0];
      const searchable=[pessoa.nome,pessoa.cpf,pessoa.email||'',primary?.nome_titular||'',primary?.numero_serie||'',...items.flatMap(c=>[c.tipo,c.emissor||''])].join(' ').toLowerCase();
      if(q&&!searchable.includes(q))return false;
      if(filter==='A1'&&!items.some(c=>c.tipo==='A1'))return false;
      if(filter==='A3'&&!items.some(c=>c.tipo==='A3'))return false;
      if(filter==='SEM'&&items.some(c=>c.apto_para_uso&&c.status==='ATIVO'))return false;
      if(filter==='VENCIDOS'&&!items.some(c=>c.status==='EXPIRADO'||isExpired(c.data_validade)))return false;
      if(filter==='VENCENDO'&&!items.some(c=>{const d=days(c.data_validade);return d!==null&&d>=0&&d<=30}))return false;
      return true;
    }).sort((a,b)=>{const av=Math.min(...a.certs.filter(c=>c.data_validade).map(c=>new Date(c.data_validade as string).getTime()),Infinity);const bv=Math.min(...b.certs.filter(c=>c.data_validade).map(c=>new Date(c.data_validade as string).getTime()),Infinity);return av-bv||a.pessoa.nome.localeCompare(b.pessoa.nome)});
  },[pessoas,certByPessoa,search,filter]);

  const entityCerts=selectedEntity?.origin==='PF'?(certByPessoa.get(selectedEntity.pessoaId||-1)||[]):(certByEmpresa.get(selectedEntity?.empresaId||-1)||[]);
  const entityName=selectedEntity?.name||selected?.nome_titular||selected?.razao_social||'Certificado';

  return <div className="page cert-digital-page">
    <div className="page-heading"><div><span className="eyebrow">INFRAESTRUTURA DE IDENTIDADE DIGITAL</span><h2>Certificados Digitais</h2><p>A1 e A3 centralizados para uso seguro pelos módulos do ÔMEGA.</p></div><div className="actions">{canAdmin&&<button className="button primary" onClick={()=>{setPersonType('PF');setFilter('TODOS');setSelected(null);setShowPfCreate(true)}} disabled={loading||busy}><Plus size={15}/> Adicionar certificado PF</button>}<button className="button secondary" onClick={()=>void load()} disabled={loading||busy}><RefreshCw size={15}/> Atualizar</button></div></div>
    {error&&<div className="form-error"><AlertTriangle size={15}/>{error}</div>}{message&&<div className="cert-success"><CheckCircle2 size={15}/>{message}</div>}
    <div className="metric-grid cert-metrics"><button className={`metric-card cert-filter ${filter==='TODOS'?'active':''}`} onClick={()=>setFilter('TODOS')}><ShieldCheck size={18}/><span>Certificados ativos</span><strong>{summary.certificados_ativos}</strong><small>A1 + A3 aptos para uso</small></button><button className={`metric-card cert-filter ${filter==='VENCENDO'?'active':''}`} onClick={()=>setFilter('VENCENDO')}><Clock3 size={18}/><span>Vencem em 30 dias</span><strong>{summary.vencem_30_dias}</strong><small>inclui os que vencem em 7 dias</small></button><button className={`metric-card cert-filter ${filter==='VENCIDOS'?'active':''}`} onClick={()=>setFilter('VENCIDOS')}><AlertTriangle size={18}/><span>Vencidos</span><strong>{summary.vencidos}</strong><small>exigem substituição</small></button><button className="metric-card"><KeyRound size={18}/><span>{personType==='PF'?'Pessoas sem certificado':'Empresas sem certificado'}</span><strong>{personType==='PF'?summary.pessoas_fisicas_sem_certificado:summary.empresas_sem_certificado}</strong><small>{personType==='PF'?'pessoas ativas':'empresas ativas'}</small></button></div>
    <section className="panel cert-toolbar-panel"><div className="cert-toolbar"><div className="cert-person-switch" role="tablist" aria-label="Tipo de titular"><button className={personType==='PJ'?'active':''} onClick={()=>{setPersonType('PJ');setFilter('TODOS');setSelected(null)}}>Pessoa Jurídica (PJ)</button><button className={personType==='PF'?'active':''} onClick={()=>{setPersonType('PF');setFilter('TODOS');setSelected(null)}}>Pessoa Física (PF)</button></div><div className="search-box"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder={personType==='PF'?'Pesquisar CPF, nome ou série...':'Pesquisar empresa, CNPJ, titular ou série...'}/></div><div className="cert-filters">{(['TODOS','A1','A3','VENCENDO','VENCIDOS','SEM'] as const).map(f=><button key={f} className={`filter-chip ${filter===f?'active':''}`} onClick={()=>setFilter(f)} >{f==='SEM'?'Sem certificado':f==='VENCENDO'?'A vencer':f==='VENCIDOS'?'Vencidos':f}</button>)}</div></div></section>

    <section className="panel cert-list-panel cert-list-full"><div className="panel-header"><div><span className="eyebrow">{personType==='PF'?'PESSOAS FÍSICAS':'EMPRESAS'}</span><h3>{personType==='PF'?rowsPF.length:rowsPJ.length} {personType==='PF'?'pessoa(s)':'empresa(s)'}</h3></div><span className="muted">ordenadas pela validade</span></div>
      {loading?<div className="empty"><div className="spinner"/><span>Carregando certificados...</span></div>:personType==='PJ'?<div className="table-wrap"><table><thead><tr><th>Empresa</th><th>Certificado</th><th>Titular / emissor</th><th>Validade</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{rowsPJ.map(({empresa,certs:companyCerts})=>{const primary=companyCerts.find(c=>c.status==='ATIVO'&&c.apto_para_uso&&days(c.data_validade)!==null&&(days(c.data_validade) as number)>=0)||companyCerts.find(c=>c.status==='ATIVO')||companyCerts[0];const [label,cls]=validity(primary);const selectedRow=companyCerts.some(c=>c.id===selected?.id&&selected?.origem==='PJ');return <tr key={empresa.id} className={selectedRow?'selected-row':''} onClick={()=>openEntity(empresa,'PJ')} title={primary?'Clique para abrir os detalhes e ações':'Clique para adicionar um certificado'}><td><strong>{empresa.razao_social}</strong><small>{empresa.cnpj}</small></td><td>{companyCerts.length?<div className="cert-type-list">{companyCerts.map(cert=><button key={cert.id} className="cert-inline-button" onClick={event=>{event.stopPropagation();void open(cert)}}><strong>{cert.tipo}</strong><small>{cert.meio_armazenamento}</small></button>)}</div>:<span className="badge neutral">Sem certificado</span>}</td><td>{primary?<><strong>{primary.nome_titular||'—'}</strong><small>{primary.emissor||'Emissor não informado'}</small></>:<span>—</span>}</td><td>{primary?<><strong>{fmtDate(primary.data_validade)}</strong><small>{days(primary.data_validade)!==null?`${days(primary.data_validade)} dias restantes`:label}</small></>:<span>—</span>}</td><td><span className={`badge ${cls}`}>{label}</span></td><td><div className="cert-row-actions">{primary&&<button className="icon-button" title="Abrir certificado" onClick={event=>{event.stopPropagation();void open(primary)}}><ArrowLeft size={15} style={{transform:'rotate(180deg)'}}/></button>}</div></td></tr>})}{!rowsPJ.length&&<tr><td colSpan={6}><div className="empty compact"><KeyRound size={25}/><strong>Nenhuma empresa encontrada</strong><span>Ajuste os filtros.</span></div></td></tr>}</tbody></table></div>:<div className="table-wrap"><table><thead><tr><th>Pessoa física</th><th>Certificado</th><th>Titular / emissor</th><th>Validade</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{rowsPF.map(({pessoaId,pessoa,certs:items})=>{const primary=items.find(c=>c.status==='ATIVO'&&c.apto_para_uso&&days(c.data_validade)!==null&&!isExpired(c.data_validade))||items.find(c=>c.status==='ATIVO'&&!isExpired(c.data_validade))||items[0];const [label,cls]=validity(primary);const selectedRow=items.some(c=>c.id===selected?.id&&selected?.origem==='PF');return <tr key={`pf-${pessoaId}`} className={selectedRow?'selected-row':''} onClick={()=>openEntity(pessoa,'PF')} title="Clique para abrir a pessoa e escolher o certificado"><td><strong>{pessoa.nome}</strong><small>CPF {maskDocument(pessoa.cpf)}</small></td><td>{items.length?<div className="cert-type-list">{items.map(cert=><button key={cert.id} className="cert-inline-button" onClick={event=>{event.stopPropagation();void open(cert)}}><strong>{cert.tipo}</strong><small>{cert.meio_armazenamento}</small></button>)}</div>:<span className="badge neutral">Sem certificado</span>}</td><td><strong>{primary?.nome_titular||pessoa.nome}</strong><small>{primary?.emissor||'Ainda não cadastrado'}</small></td><td>{primary?<><strong>{fmtDate(primary.data_validade)}</strong><small>{label}</small></>:<span>—</span>}</td><td>{primary?<span className={`badge ${cls}`}>{label}</span>:<span className="badge neutral">Sem certificado</span>}</td><td><div className="cert-row-actions">{primary&&<button className="icon-button" title="Abrir certificado" onClick={event=>{event.stopPropagation();void open(primary)}}><ArrowLeft size={15} style={{transform:'rotate(180deg)'}}/></button>}</div></td></tr>})}{!rowsPF.length&&<tr><td colSpan={6}><div className="empty compact"><KeyRound size={25}/><strong>Nenhuma pessoa física cadastrada</strong><span>Use “Adicionar A3” para cadastrar o certificado da pessoa física.</span></div></td></tr>}</tbody></table></div>}
    </section>

    {selectedEntity&&<div className="cert-detail-overlay" role="dialog" aria-modal="true" aria-label={`Detalhes do certificado de ${entityName}`} onMouseDown={e=>{if(e.target===e.currentTarget){setSelected(null);setSelectedEntity(null)}}}><div className="panel cert-detail-panel cert-detail-modal"><div className="panel-header"><div><span className="eyebrow">{selectedEntity?.origin==='PF'?'PESSOA FÍSICA':'EMPRESA'}</span><h3>{entityName}</h3></div><button className="icon-button" onClick={()=>{setSelected(null);setSelectedEntity(null)}}><X size={15}/></button></div>{canAdmin&&<div className="cert-entity-add-card"><div><span className="eyebrow">NOVO CERTIFICADO</span><strong>Escolha o tipo para {selectedEntity?.origin==='PF'?'esta pessoa':'esta empresa'}</strong></div><div className="cert-entity-add-actions"><button className="button secondary" onClick={()=>start('A1',selectedEntity!.origin,selectedEntity!.origin==='PJ'?empresas.find(e=>e.id===selectedEntity!.empresaId):pessoas.find(p=>p.id===selectedEntity!.pessoaId))}><KeyRound size={14}/> Adicionar A1</button><button className="button primary" onClick={()=>start('A3',selectedEntity!.origin,selectedEntity!.origin==='PJ'?empresas.find(e=>e.id===selectedEntity!.empresaId):pessoas.find(p=>p.id===selectedEntity!.pessoaId))}><Smartphone size={14}/> Adicionar A3</button></div></div>}{selected&&<><div className="cert-detail-tabs" role="tablist"><button className={detailTab==='SENHA'?'active':''} onClick={()=>void (password?setDetailTab('SENHA'):revealPassword())} disabled={selected.tipo!=='A1'||!canViewPassword}>{selected.tipo==='A1'?'Senha do certificado':'PIN do A3'}</button><button className={detailTab==='CERTIFICADO'?'active':''} onClick={()=>setDetailTab('CERTIFICADO')}>Certificado</button><button className={detailTab==='HISTORICO'?'active':''} onClick={()=>setDetailTab('HISTORICO')}>Histórico</button></div><div className="cert-detail-body">
      {detailTab==='CERTIFICADO'&&<><div className="cert-identity"><div className="cert-type-icon">{selected.tipo==='A1'?<KeyRound size={22}/>:<Smartphone size={22}/>}</div><div><strong>{selected.tipo} · {selected.meio_armazenamento}</strong><span>{selected.apto_para_uso?'Pronto para utilização':'Não apto para uso'}</span></div></div><div className="details cert-details"><div><span>Titular</span><strong>{selected.nome_titular||'—'}</strong></div><div><span>CPF/CNPJ</span><strong>{maskDocument(selected.documento_titular||selected.cpf)}</strong></div><div><span>Emissor</span><strong>{selected.emissor||'—'}</strong></div><div><span>Número de série</span><strong>{selected.numero_serie||'—'}</strong></div><div><span>Emissão</span><strong>{fmtDate(selected.data_emissao)}</strong></div><div><span>Validade</span><strong>{fmtDate(selected.data_validade)}</strong></div><div><span>Algoritmo</span><strong>{selected.algoritmo||'—'}</strong></div><div><span>Status</span><strong>{validity(selected)[0]}</strong></div></div>{selected.status==='NAO_VINCULADO'&&<div className="cert-warning"><AlertTriangle size={15}/><span>Este certificado está cadastrado, mas não está apto para uso.</span></div>}<div className="cert-actions">{canAdmin&&<><button className="button primary" onClick={()=>start(selected.tipo,(selected.origem||'PJ') as Origin,selected,selected.id)} disabled={busy}><RefreshCw size={14}/> Substituir</button>{selected.tipo==='A1'&&<button className="button secondary" onClick={()=>start('A3',(selected.origem||'PJ') as Origin,selected)} disabled={busy}><Plus size={14}/> Adicionar A3</button>}<button className="button secondary" onClick={()=>selected.tipo==='A3'?void testA3Local():void action(()=>testarCertificado(selected.id,(selected.origem||'PJ') as Origin),'Teste concluído.')} disabled={busy}><TestTube2 size={14}/> Testar acesso</button>{selected.tipo==='A1'&&<><button className="button secondary" onClick={()=>void baixarA1(selected.id,'certificado.p12',(selected.origem||'PJ') as Origin)} disabled={busy}><Download size={14}/> Baixar A1</button><button className="button secondary" onClick={()=>void revealPassword()} disabled={busy||passwordLoading}><KeyRound size={14}/> {passwordLoading?'Carregando senha...':'Ver senha'}</button></>}<button className="button danger" onClick={()=>{if(confirm('Desativar este certificado?'))void action(()=>desativarCertificado(selected.id,(selected.origem||'PJ') as Origin),'Certificado desativado.')}} disabled={busy}><Trash2 size={14}/> Desativar</button></>}{!canAdmin&&<button className="button secondary" onClick={()=>void action(()=>solicitarSubstituicao(selected.id,(selected.origem||'PJ') as Origin),'Solicitação de substituição registrada.')} disabled={busy}><RefreshCw size={14}/> Solicitar substituição</button>}</div><div className="cert-credential-note"><LockKeyhole size={15}/><div><strong>{selected.tipo==='A1'?'Senha protegida e recuperável':'PIN protegido no dispositivo'}</strong><span>{selected.tipo==='A1'?'A senha do A1 fica criptografada e pode ser recuperada inclusive em certificados vencidos ou substituídos, se ainda estiver armazenada.':'A chave privada e o PIN permanecem no cartão/token e nunca são enviados ao servidor.'}</span></div></div></>}
      {detailTab==='SENHA'&&<div className="cert-password-tab">{selected.tipo==='A1'&&canViewPassword?<>{password===null?<div className="cert-password-locked"><LockKeyhole size={24}/><strong>Senha protegida</strong><span>Clique em “Ver senha” para recuperá-la do armazenamento criptografado.</span><button className="button primary" onClick={()=>void revealPassword()} disabled={passwordLoading}>{passwordLoading?'Recuperando...':<><Eye size={14}/> Ver senha</>}</button></div>:<div className="cert-password-value"><label>Senha armazenada</label><div className="password-field"><input value={password} readOnly type="text" aria-label="Senha do certificado"/><button className="icon-button" title="Ocultar senha" onClick={()=>setPassword(null)}><EyeOff size={15}/></button></div><div className="cert-password-actions"><button className="button secondary" onClick={()=>void baixarSenhaA1(selected.id,(selected.origem||'PJ') as Origin)}><Download size={14}/> Baixar senha (.txt)</button><button className="button secondary" onClick={()=>{if(navigator.clipboard)void navigator.clipboard.writeText(password).then(()=>setMessage('Senha copiada para a área de transferência.'))}}><KeyRound size={14}/> Copiar senha</button></div><small>Não compartilhe esta credencial. O acesso fica registrado na auditoria.</small></div>}</>:<div className="cert-password-locked"><Smartphone size={25}/><strong>PIN do A3 não é armazenado</strong><span>O ÔMEGA nunca grava o PIN de cartão/token. O acesso é feito pelo OMEGA Bridge.</span></div>}</div>}
      {detailTab==='HISTORICO'&&<><div className="cert-related-panel"><div className="section-title-row"><div><span className="eyebrow">TODOS OS REGISTROS</span><h4>Certificados de {selected.origem==='PF'?'esta pessoa':'esta empresa'}</h4></div><span className="download-count">{entityCerts.length} registro(s)</span></div><div className="cert-related-list">{entityCerts.map(c=><button key={`${c.origem||'PJ'}-${c.id}`} className={`cert-related-item ${c.id===selected.id?'active':''}`} onClick={()=>void open(c)}><div><strong>{c.tipo} · {c.meio_armazenamento}</strong><span>{c.nome_titular||'Titular não informado'} · validade {fmtDate(c.data_validade)}</span></div><span className={`badge ${validity(c)[1]}`}>{validity(c)[0]}</span></button>)}</div></div><div className="cert-history"><div className="section-title-row"><div><span className="eyebrow">HISTÓRICO</span><h4>Eventos</h4></div></div>{history.length?history.map(h=><div className="history-item" key={h.id}><strong>{h.tipo_evento}</strong><span>{h.descricao}</span><small>{h.usuario||'Sistema'} · {fmtDate(h.criado_em)}</small></div>):<span className="muted">Nenhum evento registrado.</span>}</div></>}
    </div></>}</div></div>}

    {showPfCreate&&<div className="cert-detail-overlay" role="dialog" aria-modal="true" aria-label="Adicionar certificado de pessoa física" onMouseDown={e=>{if(e.target===e.currentTarget)setShowPfCreate(false)}}><div className="panel cert-detail-panel cert-detail-modal"><div className="panel-header"><div><span className="eyebrow">PESSOA FÍSICA</span><h3>Novo certificado</h3></div><button className="icon-button" onClick={()=>setShowPfCreate(false)}><X size={15}/></button></div><div className="cert-entity-add-card"><div><span className="eyebrow">ESCOLHA O TIPO</span><strong>Como deseja cadastrar o certificado?</strong></div><div className="cert-entity-add-actions"><button className="button secondary" onClick={()=>{setShowPfCreate(false);start('A1','PF')}}><KeyRound size={14}/> Certificado A1</button><button className="button primary" onClick={()=>{setShowPfCreate(false);start('A3','PF')}}><Smartphone size={14}/> Certificado A3</button></div></div><div className="cert-credential-note"><LockKeyhole size={15}/><div><strong>O CPF e o nome serão preenchidos no próximo passo</strong><span>Para A1, você selecionará o PFX/P12 e informará a senha. Para A3, o sistema apenas registra o tipo; o vínculo com cartão/token será configurado posteriormente.</span></div></div></div></div>}

    {mode&&<div className="cert-form-overlay" role="dialog" aria-modal="true"><div className="cert-form-dialog"><div className="panel-header"><div><span className="eyebrow">{mode.replaceId?'SUBSTITUIR':'ADICIONAR'} CERTIFICADO</span><h3>{mode.kind} · {mode.origin==='PF'?(mode.nome||'Pessoa Física'):(empresas.find(e=>e.id===mode.empresaId)?.razao_social||'Empresa')}</h3></div><button className="icon-button" onClick={()=>!busy&&setMode(null)}><X size={15}/></button></div>{mode.kind==='A1'?<form onSubmit={submitA1}><div className="cert-form-body">{mode.origin==='PF'&&<div className="cert-a3-grid"><label>CPF<input name="cpf" defaultValue={mode.cpf||''} placeholder="Somente números" required/></label><label>Nome completo<input name="nome" defaultValue={mode.nome||''} required/></label><label>E-mail<input name="email" type="email"/></label><label>Telefone<input name="telefone"/></label></div>}<div className={`upload-drop ${dragOver?'drag-over':''} ${selectedA1File?'has-file':''}`} onDragOver={e=>{e.preventDefault();setDragOver(true)}} onDragLeave={e=>{e.preventDefault();setDragOver(false)}} onDrop={e=>{e.preventDefault();setDragOver(false);const f=e.dataTransfer.files?.[0];if(!f)return;const n=f.name.toLowerCase();if(!n.endsWith('.pfx')&&!n.endsWith('.p12')){setSelectedA1File(null);const input=e.currentTarget.querySelector('input[type=\"file\"]') as HTMLInputElement|null;if(input)input.value='';setError('O arquivo precisa ser .PFX ou .P12.');return}if(f.size>10*1024*1024){setSelectedA1File(null);const input=e.currentTarget.querySelector('input[type=\"file\"]') as HTMLInputElement|null;if(input)input.value='';setError('O certificado deve ter no máximo 10 MB.');return}setSelectedA1File(f);setError('')}}><input name="arquivo" type="file" accept=".pfx,.p12,application/x-pkcs12" required={!selectedA1File} onChange={e=>{const f=e.target.files?.[0]||null;if(f){const n=f.name.toLowerCase();if(!n.endsWith('.pfx')&&!n.endsWith('.p12')){setSelectedA1File(null);e.currentTarget.value='';setError('O arquivo precisa ser .PFX ou .P12.');return}if(f.size>10*1024*1024){setSelectedA1File(null);e.currentTarget.value='';setError('O certificado deve ter no máximo 10 MB.');return}setSelectedA1File(f);setError('')}}} /><Upload size={25}/><strong>{selectedA1File?selectedA1File.name:'Arraste o certificado aqui'}</strong><span>{selectedA1File?`${(selectedA1File.size/1024/1024).toFixed(2)} MB · arquivo selecionado`:'ou clique para selecionar · PFX ou P12 · máximo 10 MB'}</span>{selectedA1File&&<button type="button" className="button small secondary" onClick={()=>setSelectedA1File(null)}>Escolher outro arquivo</button>}</div><label>Senha do certificado<input name="senha" type="password" autoComplete="new-password" required maxLength={200}/><small>Usada somente para validar e operar o PFX; a senha fica criptografada.</small></label></div><div className="form-actions"><button type="button" className="button secondary" onClick={()=>setMode(null)} disabled={busy}>Cancelar</button><button className="button primary" disabled={busy}>{busy?'Validando...':'Validar e salvar A1'}</button></div></form>:<form onSubmit={submitA3}><div className="cert-form-body">{mode.origin==='PF'?<div className="cert-a3-simple"><label>CPF<input value={a3Cpf} onChange={e=>setA3Cpf(e.target.value)} placeholder="Somente números" required/></label><label>Nome completo<input value={a3Nome} onChange={e=>setA3Nome(e.target.value)} required/></label></div>:<div className="cert-a3-detected"><strong>Empresa selecionada</strong><span>{empresas.find(e=>e.id===mode.empresaId)?.razao_social||'Empresa não identificada'}</span><span>CNPJ: {empresas.find(e=>e.id===mode.empresaId)?.cnpj||'—'}</span></div>}<div className="cert-a3-bridge-actions"><button type="button" className="button secondary" onClick={()=>void detectBridge()} disabled={busy||bridgeLoading}>{bridgeLoading?<><RefreshCw size={14}/> Detectando cartão...</>:<><Wifi size={14}/> Detectar cartão/token no Bridge</>}</button><span>{detectedA3?'Dispositivo detectado: os dados técnicos serão vinculados ao cadastro.':'Também é possível registrar apenas o tipo A3 e vincular o dispositivo depois.'}</span></div>{bridgeCerts.length>0&&<div className="cert-a3-bridge-list"><strong>Certificados compatíveis com este titular</strong>{bridgeCerts.map(cert=><button type="button" key={cert.thumbprint_sha256} className={detectedA3?.thumbprint_sha256===cert.thumbprint_sha256?'selected':''} onClick={()=>chooseBridgeCertificate(cert.thumbprint_sha256)}><span><b>{cert.nome_titular||cert.label||cert.token_label||'Certificado A3'}</b><small>{cert.issuer}</small><small>Validade: {fmtDate(cert.valid_to)} · Série: {cert.serial}</small></span><span>{detectedA3?.thumbprint_sha256===cert.thumbprint_sha256?'Selecionado':'Selecionar'}</span></button>)}</div>}<div className="cert-credential-note"><Smartphone size={16}/><div><strong>{detectedA3?'Vincular certificado A3 detectado':'Cadastro somente do tipo A3'}</strong><span>{detectedA3?'O ÔMEGA salvará o thumbprint SHA-256, emissor, validade e referência do dispositivo. A chave privada e o PIN permanecem no cartão/token; o PIN não é armazenado.':'Sem um cartão detectado, o registro fica pendente de vínculo e não poderá consultar NFS-e até ser associado a um dispositivo pelo Bridge.'}</span></div></div></div><div className="form-actions"><button type="button" className="button secondary" onClick={()=>setMode(null)} disabled={busy}>Cancelar</button><button className="button primary" disabled={busy}>{busy?'Salvando...':detectedA3?'Vincular e salvar A3':'Registrar tipo A3'}</button></div></form>}</div></div>}
  </div>;
}
