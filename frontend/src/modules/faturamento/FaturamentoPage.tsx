import {useEffect, useMemo, useState} from 'react';
import {AlertCircle, BadgeDollarSign, Building2, CheckCircle2, Eye, Filter, Plus, Search, X} from 'lucide-react';
import {useNavigate} from 'react-router-dom';
import {Loading} from '../../components/ui/Loading';
import {ErrorState} from '../../components/ui/ErrorState';
import {
  criarFaturamento,
  listarEmpresasFaturamento,
  type FaturamentoEmpresa,
} from '../../services/api/faturamento';
import './Faturamento.css';

const REGIMES = [
  {value:'TODOS', label:'Todos os regimes', shortLabel:'Todas'},
  {value:'SIMPLES NACIONAL', label:'Simples Nacional', shortLabel:'Simples Nacional'},
  {value:'LUCRO PRESUMIDO', label:'Lucro Presumido', shortLabel:'Lucro Presumido'},
  {value:'LUCRO REAL', label:'Lucro Real', shortLabel:'Lucro Real'},
];

const MESES = [
  '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function dinheiro(value:number|null|undefined){
  return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value||0));
}

function numero(text:string){
  const value=text.trim().replace(/\s/g,'');
  return Number(value.includes(',') ? value.replace(/\./g,'').replace(',','.') : value);
}

function countRegime(items:FaturamentoEmpresa[], regime:string){
  if(regime==='TODOS') return items.length;
  return items.filter(item=>(item.regime_tributario||'').toUpperCase()===regime).length;
}

function competenciaLabel(ano:number, mes:number){
  return `${MESES[mes]}/${ano}`;
}

export function FaturamentoPage(){
  const navigate=useNavigate();
  const [items,setItems]=useState<FaturamentoEmpresa[]>([]);
  const [competencia,setCompetencia]=useState<{label:string;nome:string;ano:number;mes:number}|null>(null);
  const [regime,setRegime]=useState('TODOS');
  const [q,setQ]=useState('');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [lancamentoEmpresa,setLancamentoEmpresa]=useState<FaturamentoEmpresa|null>(null);
  const [competenciaForm,setCompetenciaForm]=useState('');
  const [valorForm,setValorForm]=useState('');
  const [observacaoForm,setObservacaoForm]=useState('');
  const [saving,setSaving]=useState(false);

  async function load(){
    setLoading(true);
    setError('');
    try{
      const result=await listarEmpresasFaturamento();
      setItems(result.empresas);
      setCompetencia(result.competencia_pendente);
      setCompetenciaForm(`${result.competencia_pendente.ano}-${String(result.competencia_pendente.mes).padStart(2,'0')}`);
    }catch(e){
      setError(e instanceof Error?e.message:'Erro ao carregar o faturamento.');
    }finally{
      setLoading(false);
    }
  }

  useEffect(()=>{void load()},[]);

  const visible=useMemo(()=>{
    const termo=q.trim().toLowerCase();
    return items
      .filter(item=>{
        const matchesReg=regime==='TODOS'||(item.regime_tributario||'').toUpperCase()===regime;
        const texto=`${item.razao_social} ${item.nome_fantasia||''} ${item.cnpj}`.toLowerCase();
        return matchesReg && (!termo||texto.includes(termo));
      })
      .sort((a,b)=>a.razao_social.localeCompare(b.razao_social,'pt-BR'));
  },[items,regime,q]);

  const total=items.length;
  const pendentes=items.filter(item=>item.status_competencia==='pendente').length;
  const informadas=total-pendentes;
  const totalCompetencia=items.reduce((sum,item)=>sum+Number(item.valor_competencia||0),0);

  function abrirLancamento(item:FaturamentoEmpresa){
    setLancamentoEmpresa(item);
    const competenciaAtual=competencia||{
      ano:new Date().getFullYear(),
      mes:new Date().getMonth()===0?12:new Date().getMonth(),
    };
    setCompetenciaForm(`${competenciaAtual.ano}-${String(competenciaAtual.mes).padStart(2,'0')}`);
    setValorForm(item.valor_competencia!=null?String(item.valor_competencia.toFixed(2)).replace('.',','):'');
    setObservacaoForm('');
    setError('');
  }

  function fecharLancamento(){
    if(saving)return;
    setLancamentoEmpresa(null);
    setValorForm('');
    setObservacaoForm('');
    setError('');
  }

  async function salvarLancamento(){
    if(!lancamentoEmpresa)return;
    const [anoText,mesText]=competenciaForm.split('-');
    const ano=Number(anoText);
    const mes=Number(mesText);
    const valor=numero(valorForm);
    if(!ano||mes<1||mes>12||ano<2000||ano>2100){setError('Selecione uma competência válida.');return;}
    if(!Number.isFinite(valor)||valor<0){setError('Informe um valor de faturamento válido.');return;}
    setSaving(true);
    setError('');
    try{
      await criarFaturamento({
        empresa_id:lancamentoEmpresa.id,
        competencia_ano:ano,
        competencia_mes:mes,
        valor,
        observacao:observacaoForm.trim(),
      });
      fecharLancamento();
      await load();
    }catch(e){
      setError(e instanceof Error?e.message:'Não foi possível salvar o faturamento.');
    }finally{
      setSaving(false);
    }
  }

  return <div className="page faturamento-page">
    <div className="page-heading faturamento-heading">
      <div>
        <span className="eyebrow">CONTROLE MENSAL</span>
        <h2><BadgeDollarSign size={25}/> Faturamento</h2>
        <p>Organize o faturamento das empresas por competência e mantenha o histórico das declarações.</p>
      </div>
    </div>

    <div className="empresa-metrics faturamento-metrics">
      <div className="empresa-metric active"><span><Building2 size={19}/></span><div><strong>{total}</strong><small>Total de empresas</small></div></div>
      <div className="empresa-metric"><span><AlertCircle size={19}/></span><div><strong>{pendentes}</strong><small>Faturamentos pendentes</small></div></div>
      <div className="empresa-metric"><span><CheckCircle2 size={19}/></span><div><strong>{informadas}</strong><small>Competências informadas</small></div></div>
      <div className="empresa-metric"><span><BadgeDollarSign size={19}/></span><div><strong>{dinheiro(totalCompetencia)}</strong><small>{competencia?`Informado em ${competencia.label}`:'Competência atual'}</small></div></div>
    </div>

    <div className="fat-regime-grid">
      {REGIMES.map(item=><button key={item.value} className={`fat-regime-card ${regime===item.value?'active':''}`} onClick={()=>setRegime(item.value)}>
        <span><BadgeDollarSign size={17}/></span>
        <div><strong>{item.shortLabel}</strong><small>{countRegime(items,item.value)} empresas</small></div>
      </button>)}
    </div>

    <div className="empresa-filters panel faturamento-filters">
      <div className="empresa-search"><Search size={17}/><input value={q} placeholder="Buscar por razão social, nome fantasia, CNPJ, IE ou NIRE..." onChange={e=>setQ(e.target.value)}/></div>
      <button className="button secondary" onClick={()=>{setQ('');setRegime('TODOS')}}><Filter size={14}/> Limpar</button>
    </div>

    <div className="empresa-list-head faturamento-list-head">
      <strong>{visible.length} empresas encontradas</strong>
      <div className="faturamento-list-tools">
        <span>{competencia?`Competência de controle: ${competencia.label}`:'—'}</span>
      </div>
    </div>

    {loading?<Loading text="Carregando empresas..."/>:error?<ErrorState message={error} onRetry={load}/>:<div className="faturamento-empresa-list">
      {visible.map(item=>{
        const pending=item.status_competencia==='pendente';
        const ultima=item.ultima_competencia_mes&&item.ultima_competencia_ano?`${String(item.ultima_competencia_mes).padStart(2,'0')}/${item.ultima_competencia_ano}`:'Nenhum lançamento';
        return <article className="faturamento-empresa-row" key={item.id}>
          <div className="faturamento-empresa-main">
            <span className="empresa-icon"><Building2 size={18}/></span>
            <div className="faturamento-empresa-name">
              <strong>{item.razao_social}</strong>
              <small>{item.nome_fantasia&&item.nome_fantasia!==item.razao_social?item.nome_fantasia:'Sem nome fantasia'}</small>
            </div>
          </div>
          <div className="faturamento-empresa-field">
            <span>CNPJ</span>
            <strong>{item.cnpj}</strong>
          </div>
          <div className="faturamento-empresa-field">
            <span>REGIME</span>
            <span className="regime">{item.regime_tributario||'Não informado'}</span>
          </div>
          <div className="faturamento-empresa-field">
            <span>STATUS</span>
            <span className={`fat-status ${pending?'pending':'done'}`}><i className="fat-status-dot"/>{pending?'Pendente':'Informado'}</span>
          </div>
          <div className="faturamento-empresa-field faturamento-last-field">
            <span>ÚLTIMO FATURAMENTO</span>
            <strong>{ultima}</strong>
            <small>{item.ultimo_valor!=null?dinheiro(item.ultimo_valor):'Nenhum valor informado'}</small>
          </div>
          <div className="faturamento-empresa-actions">
            <button className="button secondary small" onClick={()=>abrirLancamento(item)}><Plus size={13}/> Informar faturamento</button>
            <button className="icon-button" title="Abrir histórico" onClick={()=>navigate(`/faturamento/empresa/${item.id}`)}><Eye size={15}/></button>
          </div>
        </article>;
      })}
      {!visible.length&&<div className="panel empty"><BadgeDollarSign size={30}/><strong>Nenhuma empresa encontrada</strong><span>Ajuste o regime ou a pesquisa.</span></div>}
    </div>}

    {lancamentoEmpresa&&<div className="modal-backdrop faturamento-modal-backdrop" onMouseDown={fecharLancamento}>
      <div className="modal-card faturamento-launch-modal" onMouseDown={e=>e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <span className="eyebrow">NOVO FATURAMENTO</span>
            <h3>Informar faturamento</h3>
          </div>
          <button className="icon-button" onClick={fecharLancamento} disabled={saving} aria-label="Fechar"><X size={15}/></button>
        </div>
        <div className="faturamento-modal-company">
          <span className="empresa-icon"><Building2 size={17}/></span>
          <div><strong>{lancamentoEmpresa.razao_social}</strong><small>{lancamentoEmpresa.cnpj} · {lancamentoEmpresa.regime_tributario||'Regime não informado'}</small></div>
        </div>
        <div className="modal-form faturamento-modal-form">
          <div className="faturamento-form-highlight">
            <span>Competência</span>
            <strong>{competenciaForm?(() => {const [a,m]=competenciaForm.split('-').map(Number);return a&&m?competenciaLabel(a,m):'Selecione o mês e o ano';})():'Selecione o mês e o ano'}</strong>
            <small>Você pode informar qualquer competência ainda não registrada.</small>
          </div>
          <label>Competência do faturamento<input type="month" value={competenciaForm} onChange={e=>setCompetenciaForm(e.target.value)}/></label>
          <label>Valor do faturamento<input autoFocus inputMode="decimal" placeholder="R$ 0,00" value={valorForm} onChange={e=>setValorForm(e.target.value)}/></label>
          <label>Observação <span className="optional">(opcional)</span><textarea value={observacaoForm} onChange={e=>setObservacaoForm(e.target.value)} placeholder="Ex.: faturamento informado pelo cliente por e-mail."/></label>
          {error&&<div className="modal-error">{error}</div>}
        </div>
        <div className="modal-actions faturamento-modal-actions">
          <button className="button secondary" onClick={fecharLancamento} disabled={saving}>Cancelar</button>
          <button className="button primary" onClick={()=>void salvarLancamento()} disabled={saving}><Plus size={14}/>{saving?'Salvando...':'Salvar faturamento'}</button>
        </div>
      </div>
    </div>}
  </div>;
}
