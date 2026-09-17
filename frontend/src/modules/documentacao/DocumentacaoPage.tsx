import {useEffect,useMemo,useState} from 'react';
import {Building2,Folder,Search,Filter,ArrowRight,Files,Plus} from 'lucide-react';
import {Link} from 'react-router-dom';
import {listarEmpresasDocumentacao,type EmpresaDocumento} from '../../services/api/documentacao';
import {Loading} from '../../components/ui/Loading';
import {ErrorState} from '../../components/ui/ErrorState';

function regimeClass(regime?:string|null){const v=(regime||'').toLowerCase();if(v.includes('simples'))return 'regime simples';if(v.includes('presumido'))return 'regime presumido';if(v.includes('real'))return 'regime real';return 'regime'}

export function DocumentacaoPage(){
 const [items,setItems]=useState<EmpresaDocumento[]>([]),[q,setQ]=useState(''),[regime,setRegime]=useState('TODOS'),[status,setStatus]=useState('TODOS'),[loading,setLoading]=useState(true),[err,setErr]=useState('');
 async function load(){setLoading(true);setErr('');try{const p=new URLSearchParams({page:'1',page_size:'200'});const r=await listarEmpresasDocumentacao(p);setItems(r.empresas)}catch(e){setErr(e instanceof Error?e.message:'Erro ao carregar documentação.')}finally{setLoading(false)}}
 useEffect(()=>{void load()},[]);
 const filtered=useMemo(()=>items.filter(e=>{const s=q.toLowerCase().trim();const mq=!s||`${e.razao_social} ${e.nome_fantasia||''} ${e.cnpj}`.toLowerCase().includes(s);const mr=regime==='TODOS'||(e.regime_tributario||'').toUpperCase()===regime;const ms=status==='TODOS'||(status==='ATIVA'?Boolean(e.ativo):!e.ativo);return mq&&mr&&ms}).sort((a,b)=>a.razao_social.localeCompare(b.razao_social,'pt-BR')),[items,q,regime,status]);
 const counts={todos:items.length,simples:items.filter(e=>(e.regime_tributario||'').toUpperCase()==='SIMPLES NACIONAL').length,presumido:items.filter(e=>(e.regime_tributario||'').toUpperCase()==='LUCRO PRESUMIDO').length,real:items.filter(e=>(e.regime_tributario||'').toUpperCase()==='LUCRO REAL').length};
 return <div className="page documentacao-page">
  <div className="page-heading"><div><span className="eyebrow">DOSSIÊ DIGITAL</span><h2><Folder size={25}/> Documentação</h2><p>Organize os documentos das empresas por pastas, versões e histórico.</p></div><div className="actions"><span className="doc-rule-note"><Files size={15}/> Uma pasta para cada tipo de documento</span></div></div>
  <div className="doc-regime-grid">
   <button className={`doc-regime-card ${regime==='TODOS'?'active':''}`} onClick={()=>setRegime('TODOS')}><span className="doc-regime-icon all"><Building2 size={20}/></span><div><strong>Todas</strong><small>{counts.todos} empresas</small></div></button>
   <button className={`doc-regime-card ${regime==='SIMPLES NACIONAL'?'active':''}`} onClick={()=>setRegime('SIMPLES NACIONAL')}><span className="doc-regime-icon simple"><Files size={20}/></span><div><strong>Simples Nacional</strong><small>{counts.simples} empresas</small></div></button>
   <button className={`doc-regime-card ${regime==='LUCRO PRESUMIDO'?'active':''}`} onClick={()=>setRegime('LUCRO PRESUMIDO')}><span className="doc-regime-icon presumed"><Files size={20}/></span><div><strong>Lucro Presumido</strong><small>{counts.presumido} empresas</small></div></button>
   <button className={`doc-regime-card ${regime==='LUCRO REAL'?'active':''}`} onClick={()=>setRegime('LUCRO REAL')}><span className="doc-regime-icon real"><Files size={20}/></span><div><strong>Lucro Real</strong><small>{counts.real} empresas</small></div></button>
  </div>
  <div className="doc-filters panel"><div className="empresa-search"><Search size={17}/><input value={q} placeholder="Pesquisar por razão social, nome fantasia ou CNPJ..." onChange={e=>setQ(e.target.value)}/></div><select value={status} onChange={e=>setStatus(e.target.value)}><option value="TODOS">Todas as situações</option><option value="ATIVA">Ativas</option><option value="INATIVA">Inativas</option></select><button className="button secondary" onClick={()=>{setQ('');setRegime('TODOS');setStatus('TODOS')}}><Filter size={14}/> Limpar</button></div>
  <div className="doc-list-head"><strong>{filtered.length} empresas encontradas</strong><span>Cards mais compactos para consulta rápida</span></div>
  {loading?<Loading text="Carregando empresas..."/>:err?<ErrorState message={err} onRetry={load}/>:<div className="doc-company-list">{filtered.map(e=><Link className="doc-company-row doc-company-row-clickable" key={e.id} to={`/documentacao/empresa/${e.id}`}><div className="doc-company-main"><span className="empresa-icon"><Building2 size={17}/></span><div className="doc-company-name"><strong>{e.razao_social}</strong><small>{e.nome_fantasia||'Sem nome fantasia'}</small></div></div><div className="doc-company-data"><span><b>CNPJ</b>{e.cnpj}</span><span><b>Regime</b><em className={regimeClass(e.regime_tributario)}>{e.regime_tributario||'Não informado'}</em></span><span><b>Status</b><em className={`status-pill ${e.ativo?'ok':'off'}`}><i/>{e.ativo?'Ativa':'Inativa'}</em></span><span className="doc-count"><b>Documentos</b><strong><Folder size={14}/>{e.documentos_count}</strong></span></div><span className="doc-open-hint"><ArrowRight size={13}/> Abrir documentação</span></Link>)}{filtered.length===0&&<div className="empty"><Folder size={32}/><strong>Nenhuma empresa encontrada</strong><span>Ajuste os filtros ou a pesquisa.</span></div>}</div>}
 </div>
}
