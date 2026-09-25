import {useEffect, useMemo, useState} from 'react';
import {
  BadgeDollarSign,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock3,
  DollarSign,
  Eye,
  FileText,
  Filter,
  Plus,
  Search,
  X,
} from 'lucide-react';
import {Link, useNavigate} from 'react-router-dom';
import {Loading} from '../../components/ui/Loading';
import {ErrorState} from '../../components/ui/ErrorState';
import {
  gerarDeclaracao12Meses,
  gerarDeclaracaoAnual,
  gerarDeclaracaoPersonalizada,
  listarEmpresasFaturamento,
  visualizarDeclaracao,
  type Competencia,
  type FaturamentoEmpresa,
} from '../../services/api/faturamento';
import {FaturamentoEntryModal} from './FaturamentoEntryModal';
import {BancoBrasilDeclarationModal} from './BancoBrasilDeclarationModal';
import './Faturamento.css';

const REGIMES = [
  {value:'TODOS', label:'Todas', className:'all'},
  {value:'SIMPLES NACIONAL', label:'Simples Nacional', className:'simples'},
  {value:'LUCRO PRESUMIDO', label:'Lucro Presumido', className:'presumido'},
  {value:'LUCRO REAL', label:'Lucro Real', className:'real'},
];

const MESES=["","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];

function dinheiro(value:number|null|undefined){return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value||0));}
function nomeCompetencia(ano:number, mes:number){return `${MESES[mes]}/${ano}`;}
export function FaturamentoPage(){
  const [items,setItems]=useState<FaturamentoEmpresa[]>([]);
  const [competencia,setCompetencia]=useState<Competencia|null>(null);
  const [indicadores,setIndicadores]=useState({total_empresas:0,faturamentos_pendentes:0,faturamentos_informados:0,valor_competencia:0,regimes:{'TODOS':0,'SIMPLES NACIONAL':0,'LUCRO PRESUMIDO':0,'LUCRO REAL':0} as Record<string,number>});
  const [regime,setRegime]=useState('TODOS');
  const [q,setQ]=useState('');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [declaracaoOpen,setDeclaracaoOpen]=useState(false);
  const [empresaDeclaracao,setEmpresaDeclaracao]=useState<FaturamentoEmpresa|null>(null);
  const [modoDeclaracao,setModoDeclaracao]=useState<'inicio'|'anual'|'personalizada'>('inicio');
  const [anoDeclaracao,setAnoDeclaracao]=useState(new Date().getFullYear());
  const [inicio,setInicio]=useState(`${new Date().getFullYear()}-01`);
  const [fim,setFim]=useState(`${new Date().getFullYear()}-12`);
  const [busyDeclaration,setBusyDeclaration]=useState(false);
  const [informarEmpresa,setInformarEmpresa]=useState<FaturamentoEmpresa|null>(null);
  const [successMessage,setSuccessMessage]=useState('');
  const [bancoBrasilEmpresa,setBancoBrasilEmpresa]=useState<FaturamentoEmpresa|null>(null);
  const navigate=useNavigate();

  async function load(ano?:number,mes?:number){
    setLoading(true);setError('');
    try{
      const result=await listarEmpresasFaturamento({ano,mes});
      setItems(result.empresas);
      setIndicadores(result.indicadores);
      const comp=result.competencia;
      setCompetencia(comp);
    }catch(e){setError(e instanceof Error?e.message:'Erro ao carregar o faturamento.');}
    finally{setLoading(false);}
  }

  useEffect(()=>{void load();},[]);

  const visible=useMemo(()=>{
    const termo=q.trim().toLowerCase();
    return items.filter(item=>{
      const mr=regime==='TODOS'||(item.regime_tributario||'').toUpperCase()===regime;
      const texto=`${item.razao_social} ${item.nome_fantasia||''} ${item.cnpj} ${item.nire||''}`.toLowerCase();
      return mr&&(!termo||texto.includes(termo));
    });
  },[items,regime,q]);

  function abrirDeclaracao(empresa:FaturamentoEmpresa|null){
    setEmpresaDeclaracao(empresa);setModoDeclaracao('inicio');setDeclaracaoOpen(true);
  }

  async function gerar12(){
    if(!empresaDeclaracao)return;
    setBusyDeclaration(true);setError('');
    const pdfAba=window.open('about:blank','_blank');
    if(!pdfAba){setError('O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.');return;}
    try{const d=await gerarDeclaracao12Meses(empresaDeclaracao.id);await visualizarDeclaracao(d.id,pdfAba);setDeclaracaoOpen(false);}catch(e){pdfAba.close();setError(e instanceof Error?e.message:'Não foi possível gerar a declaração.');}finally{setBusyDeclaration(false);}
  }

  async function gerarAnual(){
    if(!empresaDeclaracao)return;
    setBusyDeclaration(true);setError('');
    const pdfAba=window.open('about:blank','_blank');
    if(!pdfAba){setError('O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.');return;}
    try{const d=await gerarDeclaracaoAnual(empresaDeclaracao.id,anoDeclaracao);await visualizarDeclaracao(d.id,pdfAba);setDeclaracaoOpen(false);}catch(e){pdfAba.close();setError(e instanceof Error?e.message:'Não foi possível gerar a declaração anual.');}finally{setBusyDeclaration(false);}
  }

  async function gerarPersonalizada(){
    if(!empresaDeclaracao)return;
    const [anoInicio,mesInicio]=inicio.split('-').map(Number);
    const [anoFim,mesFim]=fim.split('-').map(Number);
    if(!anoInicio||!mesInicio||!anoFim||!mesFim){setError('Informe corretamente o período.');return;}
    if(anoInicio*12+mesInicio>anoFim*12+mesFim){setError('O início não pode ser maior que o fim.');return;}
    setBusyDeclaration(true);setError('');
    const pdfAba=window.open('about:blank','_blank');
    if(!pdfAba){setError('O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.');return;}
    try{const d=await gerarDeclaracaoPersonalizada(empresaDeclaracao.id,{ano_inicio:anoInicio,mes_inicio:mesInicio,ano_fim:anoFim,mes_fim:mesFim});await visualizarDeclaracao(d.id,pdfAba);setDeclaracaoOpen(false);}catch(e){pdfAba.close();setError(e instanceof Error?e.message:'Não foi possível gerar a declaração personalizada.');}finally{setBusyDeclaration(false);}
  }

  function abrirInformar(item:FaturamentoEmpresa){
    setInformarEmpresa(item);
  }

  function statusLabel(item:FaturamentoEmpresa){
    const pendentes=item.meses_pendentes||[];
    if(pendentes.length===1)return `Pendente em ${MESES[pendentes[0]]}`;
    if(pendentes.length>1)return 'Pendente vários meses';
    return 'Informado';
  }

  return <div className="page faturamento-page">
    <div className="page-heading">
      <div>
        <span className="eyebrow">CONTROLE MENSAL</span>
        <h2><BadgeDollarSign size={25}/> Faturamento</h2>
        <p>Organize o faturamento das empresas por competência e mantenha o histórico das declarações.</p>
      </div>
      <button className="button fat-main-action" onClick={()=>abrirDeclaracao(null)}><FileText size={15}/> Gerar declaração</button>
    </div>

    <div className="fat-metrics-grid">
      <div className="fat-metric-card"><span className="fat-metric-icon blue"><Building2 size={18}/></span><div><strong>{indicadores.total_empresas}</strong><small>Total de empresas</small></div></div>
      <div className="fat-metric-card"><span className="fat-metric-icon amber"><Clock3 size={18}/></span><div><strong>{indicadores.faturamentos_pendentes}</strong><small>Faturamentos pendentes</small></div></div>
      <div className="fat-metric-card"><span className="fat-metric-icon green"><CheckCircle2 size={18}/></span><div><strong>{indicadores.faturamentos_informados}</strong><small>Faturamentos informados</small></div></div>
      <div className="fat-metric-card"><span className="fat-metric-icon purple"><DollarSign size={18}/></span><div><strong>{dinheiro(indicadores.valor_competencia)}</strong><small>Faturamento da competência</small><em>{competencia?.label||'—'}</em></div></div>
    </div>

    <div className="fat-regime-grid">
      {REGIMES.map(item=><button key={item.value} className={`fat-regime-card ${item.className} ${regime===item.value?'active':''}`} onClick={()=>setRegime(item.value)}>
        <span className="fat-regime-icon"><Building2 size={18}/></span>
        <div><strong>{item.label}</strong><small>{indicadores.regimes[item.value]||0} empresas</small></div>
      </button>)}
    </div>

    <div className="fat-filter-row panel">
      <div className="empresa-search"><Search size={17}/><input value={q} placeholder="Buscar por razão social, nome fantasia, CNPJ, IE ou NIRE..." onChange={e=>setQ(e.target.value)}/></div>
      <button className="button secondary" onClick={()=>{setQ('');setRegime('TODOS');}}><Filter size={14}/> Limpar</button>
    </div>

    <div className="doc-list-head"><strong>{visible.length} empresas encontradas</strong></div>

    {error&&<div className="form-error fat-global-error">{error}</div>}
    {successMessage&&<div className="fat-success-toast"><CheckCircle2 size={17}/><div><strong>{successMessage}</strong><span>O faturamento da empresa foi atualizado.</span></div><button className="icon-button" onClick={()=>setSuccessMessage('')}><X size={14}/></button></div>}

    {loading?<Loading text="Carregando empresas..."/>:error&&!items.length?<ErrorState message={error} onRetry={()=>void load()}/>:<div className="fat-company-table-wrap panel">
      <div className="table-wrap">
        <table className="fat-company-table">
          <thead><tr><th>Empresa</th><th>CNPJ</th><th>Regime</th><th>Status</th><th>Competência</th><th>Último faturamento</th><th>Ações</th></tr></thead>
          <tbody>
          {visible.map(item=>{
            const pendentes=(item.meses_pendentes||[]).length;
            const informado=item.status_competencia==='informado';
            const ultimo=item.ultima_competencia_ano&&item.ultima_competencia_mes?`${nomeCompetencia(item.ultima_competencia_ano,item.ultima_competencia_mes)}${item.ultimo_valor!=null?` · ${dinheiro(item.ultimo_valor)}`:''}`:'Nenhum lançamento';
            const regimeClass=(item.regime_tributario||'').toLowerCase().includes('simples')?'simples':(item.regime_tributario||'').toLowerCase().includes('presumido')?'presumido':(item.regime_tributario||'').toLowerCase().includes('real')?'real':'neutral';
            return <tr key={item.id} className="fat-company-row" onClick={()=>navigate(`/faturamento/empresa/${item.id}`)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();navigate(`/faturamento/empresa/${item.id}`);}}} tabIndex={0} role="link">
              <td><div className="fat-company-cell"><span className="fat-company-icon"><Building2 size={17}/></span><div><strong>{item.razao_social}</strong><small>{item.nome_fantasia&&item.nome_fantasia!==item.razao_social?item.nome_fantasia:'—'}</small></div></div></td>
              <td>{item.cnpj}</td>
              <td><span className={`fat-regime-badge ${regimeClass}`}>{item.regime_tributario||'Não informado'}</span></td>
              <td><span className={`fat-status ${pendentes>0?'pending':'done'}`}><i className="fat-status-dot"/>{statusLabel(item)}</span></td>
              <td>{competencia?.label||'—'}</td>
              <td><strong>{ultimo}</strong><small>{informado&&item.valor_competencia!=null?`Competência: ${dinheiro(item.valor_competencia)}`:'Nenhum valor informado'}</small></td>
              <td><div className="fat-row-actions" onClick={event=>event.stopPropagation()}><button className="button secondary" onClick={()=>abrirInformar(item)}><Plus size={13}/> Informar faturamento</button><button className="button secondary" onClick={()=>abrirDeclaracao(item)}><FileText size={13}/> Declaração</button><Link className="icon-button" title="Visualizar empresa" to={`/faturamento/empresa/${item.id}`} onClick={event=>event.stopPropagation()}><Eye size={15}/></Link></div></td>
            </tr>;
          })}
          {!visible.length&&<tr><td colSpan={7}><div className="empty compact"><BadgeDollarSign size={30}/><strong>Nenhuma empresa encontrada</strong><span>Ajuste o regime ou a pesquisa.</span></div></td></tr>}
          </tbody>
        </table>
      </div>
    </div>}



    {informarEmpresa&&competencia&&<FaturamentoEntryModal
      open={Boolean(informarEmpresa)}
      onClose={()=>setInformarEmpresa(null)}
      empresaId={informarEmpresa.id}
      empresaNome={informarEmpresa.razao_social}
      defaultYear={competencia.ano}
      defaultMonth={competencia.mes}
      initial={informarEmpresa.faturamento_competencia_id ? {
        id: informarEmpresa.faturamento_competencia_id,
        competencia_ano: competencia.ano,
        competencia_mes: competencia.mes,
        valor: informarEmpresa.valor_competencia ?? null,
        observacao: informarEmpresa.observacao_competencia ?? null,
        data_faturamento: informarEmpresa.data_faturamento_competencia ?? null,
        periodicidade: informarEmpresa.periodicidade_competencia ?? 'Mensal',
      } : null}
      onSaved={async message=>{
        setSuccessMessage(message);
        await load(competencia.ano,competencia.mes);
        window.setTimeout(()=>setSuccessMessage(''),3500);
      }}
    />}


    {declaracaoOpen&&<div className="fat-modal-backdrop" onMouseDown={()=>!busyDeclaration&&setDeclaracaoOpen(false)}>
      <div className="fat-modal declaration-modal" onMouseDown={e=>e.stopPropagation()}>
        <div className="fat-modal-header"><div><span className="fat-modal-icon"><FileText size={17}/></span><div><strong>Gerar declaração</strong><small>{empresaDeclaracao?empresaDeclaracao.razao_social:'Selecione a empresa e o período para gerar a declaração de faturamento.'}</small></div></div><button className="icon-button" onClick={()=>setDeclaracaoOpen(false)} disabled={busyDeclaration}><X size={15}/></button></div>
        {!empresaDeclaracao&&<div className="fat-modal-section"><label>Empresa<select onChange={e=>setEmpresaDeclaracao(items.find(i=>String(i.id)===e.target.value)||null)} value={empresaDeclaracao?.id?String(empresaDeclaracao.id):''}><option value="">Selecione a empresa</option>{items.map(item=><option key={item.id} value={item.id}>{item.razao_social}</option>)}</select></label></div>}
        {empresaDeclaracao&&modoDeclaracao==='inicio'&&<div className="fat-declaration-choice-grid">
          <button className="fat-declaration-choice active" onClick={()=>void gerar12()} disabled={busyDeclaration}><CalendarDays size={20}/><strong>Últimos 12 meses</strong><span>Gerar a declaração considerando as últimas 12 competências completas.</span></button>
          <button className="fat-declaration-choice" onClick={()=>setModoDeclaracao('anual')} disabled={busyDeclaration}><CalendarDays size={20}/><strong>Anual</strong><span>Gerar a declaração de um ano específico.</span></button>
          <button className="fat-declaration-choice" onClick={()=>setModoDeclaracao('personalizada')} disabled={busyDeclaration}><CalendarDays size={20}/><strong>Personalizado</strong><span>Escolha o período inicial e final da declaração.</span></button>
          <button className="fat-declaration-choice fat-declaration-choice-bb" onClick={()=>{setDeclaracaoOpen(false);setBancoBrasilEmpresa(empresaDeclaracao)}} disabled={busyDeclaration}><Building2 size={20}/><strong>Banco do Brasil</strong><span>Preenche e salva automaticamente o formulário oficial do Banco do Brasil e gera o PDF.</span></button>
        </div>}
        {empresaDeclaracao&&modoDeclaracao==='anual'&&<div className="fat-declaration-form"><button className="fat-back-mini" onClick={()=>setModoDeclaracao('inicio')}>← Voltar</button><div className="fat-declaration-form-title"><CalendarDays size={20}/><div><strong>Anual</strong><span>Selecione o ano para gerar a declaração.</span></div></div><label>Ano *<input type="number" value={anoDeclaracao} onChange={e=>setAnoDeclaracao(Number(e.target.value))}/></label><div className="fat-modal-actions"><button className="button secondary" onClick={()=>setDeclaracaoOpen(false)}>Cancelar</button><button className="button primary" onClick={()=>void gerarAnual()} disabled={busyDeclaration}>Gerar declaração</button></div></div>}
        {empresaDeclaracao&&modoDeclaracao==='personalizada'&&<div className="fat-declaration-form"><button className="fat-back-mini" onClick={()=>setModoDeclaracao('inicio')}>← Voltar</button><div className="fat-declaration-form-title"><CalendarDays size={20}/><div><strong>Personalizado</strong><span>Escolha o período para gerar a declaração.</span></div></div><div className="fat-two-inputs"><label>De *<input type="month" value={inicio} onChange={e=>setInicio(e.target.value)}/></label><label>Até *<input type="month" value={fim} onChange={e=>setFim(e.target.value)}/></label></div><div className="fat-modal-actions"><button className="button secondary" onClick={()=>setDeclaracaoOpen(false)}>Cancelar</button><button className="button primary" onClick={()=>void gerarPersonalizada()} disabled={busyDeclaration}>Gerar declaração</button></div></div>}
        {!empresaDeclaracao&&<div className="fat-modal-actions"><button className="button secondary" onClick={()=>setDeclaracaoOpen(false)}>Cancelar</button><button className="button primary" disabled={!empresaDeclaracao}>Continuar</button></div>}
      </div>
    </div>}

    {bancoBrasilEmpresa&&<BancoBrasilDeclarationModal
      open={Boolean(bancoBrasilEmpresa)}
      empresaId={bancoBrasilEmpresa.id}
      empresaNome={bancoBrasilEmpresa.razao_social}
      onClose={()=>setBancoBrasilEmpresa(null)}
    />}

  </div>
}
