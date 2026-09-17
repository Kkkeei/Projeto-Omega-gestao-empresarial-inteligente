import {useEffect,useState} from 'react';
import {ArrowLeft,Download,Edit3,FileText,History,Save, X} from 'lucide-react';
import {Link,useParams} from 'react-router-dom';
import {ErrorState} from '../../components/ui/ErrorState';
import {Loading} from '../../components/ui/Loading';
import {
  atualizarFaturamento,
  criarFaturamento,
  declaracaoDownloadUrl,
  declaracaoVisualizacaoUrl,
  gerarDeclaracao12Meses,
  gerarDeclaracaoAnual,
  gerarDeclaracaoPersonalizada,
  obterEmpresaFaturamento,
  type EmpresaFaturamento,
  type Faturamento,
} from '../../services/api/faturamento';
import './Faturamento.css';

const MESES=['','Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

function dinheiro(value:number|null|undefined){return new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(value||0));}
function competencia(item:Faturamento){return `${MESES[item.competencia_mes]}/${item.competencia_ano}`;}
function dataHora(value:string){return new Date(value.replace(' ','T')).toLocaleString('pt-BR');}
function anoAtual(){return new Date().getFullYear();}

export function EmpresaFaturamentoPage(){
  const {id}=useParams();
  const empresaId=Number(id);
  const [data,setData]=useState<EmpresaFaturamento|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [saving,setSaving]=useState(false);
  const [valor,setValor]=useState('');
  const [observacao,setObservacao]=useState('');
  const hojeInicial=new Date();
  const mesPendenteInicial=hojeInicial.getMonth()===0?12:hojeInicial.getMonth();
  const anoPendenteInicial=hojeInicial.getMonth()===0?hojeInicial.getFullYear()-1:hojeInicial.getFullYear();
  const [competenciaAno,setCompetenciaAno]=useState(anoPendenteInicial);
  const [competenciaMes,setCompetenciaMes]=useState(mesPendenteInicial);
  const [editId,setEditId]=useState<number|null>(null);
  const [editValor,setEditValor]=useState('');
  const [editObs,setEditObs]=useState('');
  const [modoDeclaracao,setModoDeclaracao]=useState<'anual'|'personalizada'|null>(null);
  const [anoDeclaracao,setAnoDeclaracao]=useState(anoAtual());
  const [inicio,setInicio]=useState(`${anoAtual()}-01`);
  const [fim,setFim]=useState(`${anoAtual()}-12`);
  const [busyDeclaration,setBusyDeclaration]=useState(false);

  async function load(){
    setLoading(true);setError('');
    try{setData(await obterEmpresaFaturamento(empresaId));}
    catch(e){setError(e instanceof Error?e.message:'Erro ao carregar faturamento.');}
    finally{setLoading(false)}
  }
  useEffect(()=>{void load()},[empresaId]);

  function numero(text:string){const v=text.trim().replace(/\s/g,'');return Number(v.includes(',')?v.replace(/\./g,'').replace(',','.'):v)}

  async function salvar(){
    if(!data)return;
    const n=numero(valor);
    if(!Number.isFinite(n)||n<0){setError('Informe um valor de faturamento válido.');return;}
    setSaving(true);setError('');
    try{
      await criarFaturamento({empresa_id:empresaId,competencia_ano:competenciaAno,competencia_mes:competenciaMes,valor:n,observacao});
      setValor('');setObservacao('');await load();
    }catch(e){setError(e instanceof Error?e.message:'Não foi possível salvar o faturamento.')}
    finally{setSaving(false)}
  }

  function iniciarEdicao(item:Faturamento){setEditId(item.id);setEditValor(String(item.valor.toFixed(2)).replace('.',','));setEditObs(item.observacao||'');}

  async function salvarEdicao(){
    if(editId==null)return;
    const n=numero(editValor);
    if(!Number.isFinite(n)||n<0){setError('Informe um valor válido.');return;}
    setSaving(true);setError('');
    try{await atualizarFaturamento(editId,{valor:n,observacao:editObs});setEditId(null);await load();}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível atualizar o faturamento.')}
    finally{setSaving(false)}
  }

  async function gerar12(){
    setBusyDeclaration(true);setError('');
    try{const d=await gerarDeclaracao12Meses(empresaId);window.open(declaracaoVisualizacaoUrl(d.id),'_blank','noopener,noreferrer');await load();}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível gerar a declaração.')}
    finally{setBusyDeclaration(false)}
  }

  async function gerarAnual(){
    setBusyDeclaration(true);setError('');
    try{const d=await gerarDeclaracaoAnual(empresaId,anoDeclaracao);window.open(declaracaoVisualizacaoUrl(d.id),'_blank','noopener,noreferrer');setModoDeclaracao(null);await load();}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível gerar a declaração anual.')}
    finally{setBusyDeclaration(false)}
  }

  function parseMes(value:string){const [ano,mes]=value.split('-').map(Number);return {ano,mes};}

  async function gerarPersonalizada(){
    const a=parseMes(inicio);const b=parseMes(fim);
    if(!a.ano||!a.mes||!b.ano||!b.mes){setError('Informe corretamente o período.');return;}
    if(a.ano*12+a.mes>b.ano*12+b.mes){setError('O início não pode ser maior que o fim.');return;}
    setBusyDeclaration(true);setError('');
    try{const d=await gerarDeclaracaoPersonalizada(empresaId,{ano_inicio:a.ano,mes_inicio:a.mes,ano_fim:b.ano,mes_fim:b.mes});window.open(declaracaoVisualizacaoUrl(d.id),'_blank','noopener,noreferrer');setModoDeclaracao(null);await load();}
    catch(e){setError(e instanceof Error?e.message:'Não foi possível gerar a declaração personalizada.')}
    finally{setBusyDeclaration(false)}
  }

  if(loading)return <div className="page"><Loading/></div>;
  if(error&&!data)return <div className="page"><ErrorState message={error} onRetry={load}/></div>;
  if(!data)return null;

  return <div className="page faturamento-page">
    <Link to="/faturamento" className="back-link"><ArrowLeft size={15}/> Voltar para Faturamento</Link>

    <div className="fat-detail-head">
      <div><span className="eyebrow">EMPRESA</span><h2>{data.empresa.razao_social}</h2><div className="fat-detail-meta">{data.empresa.cnpj} · {data.empresa.regime_tributario||'Regime não informado'}</div></div>
    </div>

    {error&&<div className="form-error">{error}</div>}

    <div className="fat-summary">
      <div className="metric-card"><span>Faturamentos registrados</span><strong>{data.resumo.quantidade_lancamentos}</strong><small>competências informadas</small></div>
      <div className="metric-card"><span>Total histórico</span><strong>{dinheiro(data.resumo.valor_total)}</strong><small>soma dos registros</small></div>
      <div className="metric-card"><span>Último faturamento</span><strong>{data.resumo.ultimo_faturamento?dinheiro(data.resumo.ultimo_faturamento.valor):'—'}</strong><small>{data.resumo.ultimo_faturamento?`${MESES[data.resumo.ultimo_faturamento.competencia_mes]}/${data.resumo.ultimo_faturamento.competencia_ano}`:'Nenhum registro'}</small></div>
    </div>

    <section className="panel form-panel">
      <div className="form-section"><span className="eyebrow">1 · INFORMAR FATURAMENTO</span><h3>Registrar competência</h3><p>Escolha mês e ano, informe o valor e registre uma observação quando necessário.</p></div>
      <div className="form-grid faturamento-entry-grid">
        <label>Competência mês<select value={competenciaMes} onChange={e=>setCompetenciaMes(Number(e.target.value))}>{MESES.slice(1).map((m,i)=><option key={m} value={i+1}>{m}</option>)}</select></label>
        <label>Competência ano<input type="number" value={competenciaAno} onChange={e=>setCompetenciaAno(Number(e.target.value))}/></label>
        <label>Faturamento<input inputMode="decimal" placeholder="R$ 0,00" value={valor} onChange={e=>setValor(e.target.value)}/></label>
        <label>Observação <span className="optional">(opcional)</span><input value={observacao} onChange={e=>setObservacao(e.target.value)} placeholder="Ex.: informado pelo cliente por e-mail."/></label>
      </div>
      <div className="form-actions"><button className="button primary" onClick={()=>void salvar()} disabled={saving}><Save size={14}/> {saving?'Salvando...':'Salvar faturamento'}</button></div>
    </section>

    <section className="panel fat-declaration-section">
      <div className="panel-header"><div><span className="eyebrow">2 · DECLARAÇÕES</span><h3>Gerar declaração</h3></div><FileText size={18}/></div>
      <div className="fat-declaration-body">
        <div className="fat-action-grid">
          <button className="fat-action-card" onClick={()=>void gerar12()} disabled={busyDeclaration}><strong>Últimos 12 meses</strong><span>Considera as 12 competências completas anteriores ao mês atual.</span><b>Gerar agora</b></button>
          <button className={`fat-action-card ${modoDeclaracao==='anual'?'active':''}`} onClick={()=>setModoDeclaracao(modoDeclaracao==='anual'?null:'anual')} disabled={busyDeclaration}><strong>Declaração anual</strong><span>Gera janeiro a dezembro do ano escolhido.</span><b>Escolher ano</b></button>
          <button className={`fat-action-card ${modoDeclaracao==='personalizada'?'active':''}`} onClick={()=>setModoDeclaracao(modoDeclaracao==='personalizada'?null:'personalizada')} disabled={busyDeclaration}><strong>Período personalizado</strong><span>Escolha o mês inicial e o mês final da declaração.</span><b>Definir período</b></button>
        </div>

        {modoDeclaracao==='anual'&&<div className="fat-declaration-form-card"><div><span className="eyebrow">DECLARAÇÃO ANUAL</span><h4>Selecione o ano da declaração</h4><p>O sistema considerará janeiro a dezembro do ano escolhido.</p></div><div className="fat-declaration-form-row"><label>Ano<input type="number" min="2000" max="2100" value={anoDeclaracao} onChange={e=>setAnoDeclaracao(Number(e.target.value))}/></label><div className="fat-declaration-form-actions"><button className="button secondary" onClick={()=>setModoDeclaracao(null)}><X size={13}/> Cancelar</button><button className="button primary" disabled={busyDeclaration} onClick={()=>void gerarAnual()}>Gerar declaração</button></div></div></div>}

        {modoDeclaracao==='personalizada'&&<div className="fat-declaration-form-card"><div><span className="eyebrow">DECLARAÇÃO PERSONALIZADA</span><h4>Defina o período</h4><p>Selecione a primeira e a última competência que deverão aparecer na declaração.</p></div><div className="fat-declaration-form-row period"><label>Competência inicial<input type="month" value={inicio} onChange={e=>setInicio(e.target.value)}/></label><label>Competência final<input type="month" value={fim} onChange={e=>setFim(e.target.value)}/></label><div className="fat-declaration-form-actions"><button className="button secondary" onClick={()=>setModoDeclaracao(null)}><X size={13}/> Cancelar</button><button className="button primary" disabled={busyDeclaration} onClick={()=>void gerarPersonalizada()}>Gerar declaração</button></div></div></div>}
      </div>
    </section>

    <section className="panel fat-history-section">
      <div className="panel-header"><div><span className="eyebrow">3 · LANÇAMENTOS</span><h3>Histórico mensal</h3></div><span className="muted">{data.faturamentos.length} registro(s)</span></div>
      {data.faturamentos.length===0?<div className="empty compact"><History size={24}/><strong>Nenhum faturamento informado</strong><span>Cadastre a primeira competência acima.</span></div>:<div className="table-wrap"><table><thead><tr><th>Competência</th><th>Valor</th><th>Observação</th><th>Atualizado em</th><th></th></tr></thead><tbody>{data.faturamentos.map(item=>{
        const edit=editId===item.id;
        return <tr key={item.id}>
          <td><strong>{competencia(item)}</strong></td>
          <td>{edit?<input value={editValor} onChange={e=>setEditValor(e.target.value)}/>:dinheiro(item.valor)}</td>
          <td>{edit?<input value={editObs} onChange={e=>setEditObs(e.target.value)}/>:item.observacao||'—'}</td>
          <td>{new Date(item.atualizado_em.replace(' ','T')).toLocaleString('pt-BR')}</td>
          <td><div className="fat-table-actions">{edit?<><button className="icon-button" title="Salvar" onClick={()=>void salvarEdicao()}><Save size={14}/></button><button className="icon-button" title="Cancelar" onClick={()=>setEditId(null)}><X size={14}/></button></>:<button className="icon-button" title="Editar" onClick={()=>iniciarEdicao(item)}><Edit3 size={14}/></button>}</div></td>
        </tr>;
      })}</tbody></table></div>}
    </section>

    <section className="panel history-panel fat-history-section">
      <div className="panel-header"><div><span className="eyebrow">4 · HISTÓRICO DE DECLARAÇÕES</span><h3>Declarações geradas</h3></div><History size={18}/></div>
      {data.declaracoes.length===0?<div className="empty compact"><FileText size={24}/><span>Nenhuma declaração gerada ainda.</span></div>:<div className="table-wrap"><table className="fat-declaration-history"><thead><tr><th>Data</th><th>Tipo</th><th>Período</th><th>Total</th><th>Usuário</th><th>Ações</th></tr></thead><tbody>{data.declaracoes.map(d=><tr key={d.id}><td>{dataHora(d.data_geracao)}</td><td><strong>{d.tipo}</strong></td><td>{d.periodo_inicio} → {d.periodo_fim}</td><td>{dinheiro(d.valor_total)}</td><td>{d.usuario_nome||'—'}</td><td><div className="fat-declaration-links"><button className="button secondary" onClick={()=>window.open(declaracaoVisualizacaoUrl(d.id),'_blank','noopener,noreferrer')}><FileText size={12}/> Visualizar</button><a className="button secondary" href={declaracaoDownloadUrl(d.id)}><Download size={12}/> Baixar</a></div></td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}
