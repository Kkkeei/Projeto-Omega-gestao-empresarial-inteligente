import {useEffect,useMemo,useState} from 'react';
import {AlertTriangle,Building2,CalendarDays,CheckCircle2,ChevronLeft,ChevronRight,ClipboardCheck,FileText,LockKeyhole,RefreshCw,Search,ShieldCheck} from 'lucide-react';
import {useNavigate} from 'react-router-dom';
import {ErrorState} from '../../components/ui/ErrorState';
import {Loading} from '../../components/ui/Loading';
import {obterDashboardDctfweb,type DashboardDctfweb,type EmpresaDctfweb,type ObrigacaoDctfweb} from '../../services/api/dctfweb';
import './Dctfweb.css';

const MESES=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
function competenciaAnterior(){const d=new Date();d.setDate(1);d.setMonth(d.getMonth()-1);return {ano:d.getFullYear(),mes:d.getMonth()+1};}
function dinheiro(v:number|null|undefined){return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0));}
function regimeKey(v:string){return v.toUpperCase().includes('REAL')?'LUCRO REAL':'LUCRO PRESUMIDO';}
function statusTexto(o:ObrigacaoDctfweb){if(o.status==='PENDENTE')return 'Pendente';if(o.status==='CREDOR')return 'Credor';if(o.status==='SEM_MOVIMENTACAO')return '—';if(o.status==='PAGO')return `Pago · ${dinheiro(o.valor)}`;return dinheiro(o.valor);}
function statusClasse(o:ObrigacaoDctfweb){return o.status==='PENDENTE'?'pending':o.status==='CREDOR'?'credit':o.status==='SEM_MOVIMENTACAO'?'no-movement':o.status==='PAGO'?'paid':'reported';}

export function DctfwebPage(){
 const init=competenciaAnterior();const [ano,setAno]=useState(init.ano);const [mes,setMes]=useState(init.mes);
 const [data,setData]=useState<DashboardDctfweb|null>(null);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
 const [busca,setBusca]=useState('');const [regime,setRegime]=useState('TODOS');const [situacao,setSituacao]=useState('TODAS');const [somentePendencias,setSomentePendencias]=useState(false);
 const [conferencia,setConferencia]=useState(false);const navigate=useNavigate();
 async function load(){setLoading(true);setError('');setData(null);try{setData(await obterDashboardDctfweb(ano,mes));}catch(e){setError(e instanceof Error?e.message:'Não foi possível consultar a DCTFWeb.');}finally{setLoading(false);}}
 useEffect(()=>{void load();},[ano,mes]);
 function mudarMes(delta:number){const d=new Date(ano,mes-1+delta,1);setAno(d.getFullYear());setMes(d.getMonth()+1);setConferencia(false);}
 const filtradas=useMemo(()=>{const q=busca.trim().toLowerCase();return (data?.empresas||[]).filter(e=>{
  const matchBusca=!q||[e.razao_social,e.nome_fantasia||'',e.cnpj].some(v=>v.toLowerCase().includes(q));
  const matchRegime=regime==='TODOS'||regimeKey(e.regime_tributario)===regime;
  const matchSituacao=situacao==='TODAS'||(situacao==='COMPLETA'&&e.status_geral==='COMPLETA')||(situacao==='PENDENTE'&&e.pendentes>0)||(situacao==='CREDOR'&&e.obrigacoes.some(o=>o.status==='CREDOR'))||(situacao==='SEM_MOVIMENTACAO'&&e.obrigacoes.some(o=>o.status==='SEM_MOVIMENTACAO'));
  return matchBusca&&matchRegime&&matchSituacao&&(!somentePendencias||e.pendentes>0);
 });},[data,busca,regime,situacao,somentePendencias]);
 const grupos=[{key:'LUCRO PRESUMIDO',label:'Empresas — Lucro Presumido',icon:'presumido'},{key:'LUCRO REAL',label:'Empresas — Lucro Real',icon:'real'}];
 function abrirEmpresa(e:EmpresaDctfweb){const pendente=e.obrigacoes.find(o=>!o.finalizada);if(pendente)navigate(`/impostos/empresa/${e.id}/tributo/${pendente.tributo_id}?ano=${ano}&mes=${mes}`);else navigate(`/impostos/empresa/${e.id}?ano=${ano}&mes=${mes}`);}
 if(loading&&!data)return <div className="page"><Loading/></div>;
 if(error&&!data)return <div className="page"><ErrorState message={error} onRetry={()=>void load()}/></div>;
 if(!data)return null;
 const i=data.indicadores;const semObrigacoes=i.total_obrigacoes===0;
 return <div className="page dctf-page">
  <div className="page-heading dctf-heading"><div><span className="eyebrow">FECHAMENTO FISCAL FEDERAL</span><h2><ClipboardCheck size={23}/> DCTFWeb</h2><p>Confira os tributos federais de empresas do Lucro Presumido e Lucro Real antes da próxima etapa.</p></div><button className="button secondary" onClick={()=>void load()} disabled={loading}><RefreshCw size={14}/> Atualizar</button></div>
  <div className="dctf-toolbar">
   <div className="dctf-competencia"><CalendarDays size={17}/><span>Competência</span><button aria-label="Competência anterior" onClick={()=>mudarMes(-1)}><ChevronLeft size={17}/></button><strong>{MESES[mes-1]}/{ano}</strong><button aria-label="Próxima competência" onClick={()=>mudarMes(1)}><ChevronRight size={17}/></button></div>
   <label className="dctf-search"><Search size={15}/><input value={busca} onChange={e=>setBusca(e.target.value)} placeholder="Buscar empresa, nome fantasia ou CNPJ"/></label>
   <select aria-label="Filtrar por regime" value={regime} onChange={e=>setRegime(e.target.value)}><option value="TODOS">Todos os regimes</option><option value="LUCRO PRESUMIDO">Lucro Presumido</option><option value="LUCRO REAL">Lucro Real</option></select>
   <select aria-label="Filtrar por situação" value={situacao} onChange={e=>{setSituacao(e.target.value);setSomentePendencias(false)}}><option value="TODAS">Todas as situações</option><option value="COMPLETA">Completa</option><option value="PENDENTE">Pendente</option><option value="CREDOR">Credor</option><option value="SEM_MOVIMENTACAO">Sem movimentação</option></select>
   <button className="button ghost" onClick={()=>{setBusca('');setRegime('TODOS');setSituacao('TODAS');setSomentePendencias(false);}}>Limpar</button>
  </div>
  <section className={`dctf-close-card ${semObrigacoes?'empty':i.liberada?'released':'blocked'}`}>
   <div className="dctf-close-main"><div className="dctf-close-title"><span className="dctf-state-icon">{semObrigacoes?<AlertTriangle size={19}/>:i.liberada?<CheckCircle2 size={19}/>:<LockKeyhole size={19}/>}</span><div><span className="eyebrow">FECHAMENTO DA DCTFWEB</span><h3>{semObrigacoes?'Nenhuma obrigação encontrada':i.liberada?'Fechamento concluído':'Fechamento em andamento'}</h3><p>{semObrigacoes?'Não há obrigações federais elegíveis para esta competência. Confira os vínculos e a vigência dos tributos.':i.liberada?'Todas as obrigações esperadas foram finalizadas. A competência está liberada para conferência interna.':`${i.pendentes} obrigação(ões) pendente(s) em ${i.empresas_com_pendencias} empresa(s).`}</p></div></div>
    <div className="dctf-progress-label"><strong>{i.finalizadas} / {i.total_obrigacoes}</strong><span>{i.percentual}%</span></div><div className="dctf-progress"><span style={{width:`${i.percentual}%`}}/></div>
   </div>
   <div className="dctf-close-action">{semObrigacoes?<><AlertTriangle size={24}/><strong>Sem liberação automática</strong><span>É necessário existir ao menos uma obrigação esperada.</span></>:i.liberada?<><ShieldCheck size={25}/><strong>Pronta para conferência</strong><span>Esta etapa não transmite a declaração à Receita Federal.</span><button className="button primary" onClick={()=>setConferencia(v=>!v)}><ClipboardCheck size={15}/>{conferencia?'Ocultar conferência':'Conferir DCTFWeb'}</button></>:<><LockKeyhole size={24}/><strong>DCTFWeb bloqueada</strong><span>Existem obrigações ainda não finalizadas.</span><button className="button secondary" onClick={()=>{setSomentePendencias(true);setSituacao('PENDENTE');}}><AlertTriangle size={14}/> Ver pendências</button></>}</div>
  </section>
  {conferencia&&i.liberada&&<section className="dctf-review panel"><div><CheckCircle2 size={20}/><div><strong>Conferência interna — {data.competencia.label}</strong><p>Os valores abaixo são lidos da aba Impostos. Revise-os no sistema antes de qualquer transmissão oficial.</p></div></div><button className="button secondary" onClick={()=>setConferencia(false)}>Fechar conferência</button></section>}
  <div className="dctf-kpis">
   <div className="dctf-kpi"><span className="dctf-kpi-icon"><Building2 size={17}/></span><div><small>Empresas</small><strong>{i.total_empresas}</strong><span>Lucro Presumido e Real</span></div></div>
   <div className="dctf-kpi"><span className="dctf-kpi-icon"><FileText size={17}/></span><div><small>Obrigações federais</small><strong>{i.total_obrigacoes}</strong><span>Esperadas na competência</span></div></div>
   <div className="dctf-kpi"><span className="dctf-kpi-icon success"><CheckCircle2 size={17}/></span><div><small>Finalizadas</small><strong>{i.finalizadas}<em> / {i.total_obrigacoes}</em></strong><span>Registro final válido</span></div></div>
   <div className="dctf-kpi"><span className="dctf-kpi-icon danger"><AlertTriangle size={17}/></span><div><small>Pendentes</small><strong>{i.pendentes}</strong><span>{i.empresas_com_pendencias} empresa(s) com pendências</span></div></div>
  </div>
  {grupos.map(g=>{const companies=filtradas.filter(e=>regimeKey(e.regime_tributario)===g.key);return <section className="dctf-table-section" key={g.key}><div className="dctf-table-heading"><div><span className={`dctf-regime-mark ${g.icon}`}><Building2 size={16}/></span><div><h3>{g.label}</h3><small>{companies.length} empresa(s) na visualização</small></div></div><span className="dctf-table-competence">{data.competencia.label}</span></div>
   {companies.length===0?<div className="dctf-empty">Nenhuma empresa corresponde aos filtros neste regime.</div>:<div className="dctf-table-wrap"><table className="dctf-table"><thead><tr><th>Empresa</th><th>CNPJ</th>{data.tributos.map(t=><th key={t.id}>{t.sigla||t.nome}</th>)}<th>Status</th></tr></thead><tbody>{companies.map(e=><tr key={e.id} className={e.pendentes?'has-pending':''}><td><button className="dctf-company-link" onClick={()=>abrirEmpresa(e)}>{e.razao_social}<small>{e.nome_fantasia||'Abrir impostos da empresa'}</small></button></td><td className="dctf-cnpj">{e.cnpj}</td>{data.tributos.map(t=>{const o=e.obrigacoes.find(x=>x.tributo_id===t.id);return <td key={t.id}>{!o?<span className="dctf-not-applicable" title="Tributo não vinculado a esta empresa nesta competência">Não vinculado</span>:<span className={`dctf-tax-status ${statusClasse(o)}`} title={o.status==='SEM_MOVIMENTACAO'?'Sem movimentação informado':o.status==='PENDENTE'?'Registro mensal não finalizado':o.status==='CREDOR'?'Apuração credora':o.status==='PAGO'?'Pagamento registrado':o.status==='VALOR_INFORMADO'?'Registro final informado; pagamento pode estar pendente':undefined}>{statusTexto(o)}</span>}</td>})}<td><span className={`dctf-company-status ${e.status_geral.toLowerCase()}`}>{e.status_geral==='COMPLETA'?<CheckCircle2 size={13}/>:<AlertTriangle size={13}/>} {e.status_geral==='COMPLETA'?'Completa':'Pendente'}</span></td></tr>)}</tbody></table></div>}
  </section>})}
  <p className="dctf-footnote">Os dados são provenientes da aba Impostos. A liberação é apenas para conferência interna; não há transmissão oficial implementada nesta etapa.</p>
 </div>;
}
