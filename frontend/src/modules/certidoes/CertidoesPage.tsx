import {useEffect,useMemo,useState} from 'react';
import {AlertTriangle, CheckCircle2, Download, ExternalLink, FileCheck2, FileText, History, Landmark, RefreshCw, Search, ShieldCheck, Play, Building2, CalendarDays} from 'lucide-react';
import {listarCertidoes,historicoCertidoes,listarEmpresasParaSelecao,consultarCertidaoEstadual,consultarCertidaoFederal,consultarCertidaoNarrativa,consultarTodasCertidoesEstaduais,abrirPdfCertidaoAutenticado} from '../../services/api/certidoes';
import type {Certidao,Empresa,CertidaoConsultaResultado} from '../../types';
import {Loading} from '../../components/ui/Loading';
import {StatusBadge} from '../../components/status/StatusBadge';
import './CertidoesHardening.css';

function formatarData(value?:string|null){
  if(!value) return '—';
  const parts=value.split('-');
  return parts.length===3?`${parts[2]}/${parts[1]}/${parts[0]}`:value;
}

function formatarDataHora(value?:string|null){
  if(!value) return '—';
  const d=new Date(value.replace(' ','T'));
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('pt-BR');
}

type CertType='federal'|'estadual'|'narrativa';

type TypeCard={key:CertType;title:string;short:string;desc:string;icon:typeof Landmark;className:string;method:string;typeName:string};
const TYPE_CARDS: TypeCard[] = [
  {key:'federal',title:'Federal · RFB/PGFN',short:'CND Federal',desc:'Receita Federal e PGFN',icon:Landmark,className:'blue',method:'Automação visual no Chrome',typeName:'Federal - RFB/PGFN'},
  {key:'estadual',title:'Estadual · SEFAZ-PE',short:'CND Estadual',desc:'Regularidade fiscal em Pernambuco',icon:ShieldCheck,className:'green',method:'Consulta via Playwright',typeName:'Estadual - SEFAZ'},
  {key:'narrativa',title:'Narrativa · Débito Fiscal',short:'Narrativa SEFAZ',desc:'Consulta autenticada por certificado',icon:FileText,className:'amber',method:'Sessão gráfica + certificado',typeName:'Narrativa - Débito Fiscal'},
];

function validadeCalculada(value?:string|null):string|null {
  if(!value)return null;
  const parts=value.slice(0,10).split('-').map(Number);
  if(parts.length!==3||!parts.every(Number.isFinite))return null;
  const [year,month,day]=parts;
  const validade=new Date(year,month-1,day);
  if(validade.getFullYear()!==year||validade.getMonth()!==month-1||validade.getDate()!==day)return null;
  const hoje=new Date();hoje.setHours(0,0,0,0);
  validade.setHours(0,0,0,0);
  const dias=Math.floor((validade.getTime()-hoje.getTime())/86400000);
  return dias<0?'VENCIDA':dias<=30?'PRÓXIMA DO VENCIMENTO':'VÁLIDA';
}
function statusDaCertidao(item?:{situacao?:string|null;status_validade?:string|null;data_validade?:string|null}|null):string {
  const situacao=(item?.situacao||'').trim();
  if(!situacao)return 'Ainda não consultada';
  const normalized=situacao.toUpperCase();
  const validade=item?.status_validade||validadeCalculada(item?.data_validade);
  if(validade==='VENCIDA')return normalized==='IRREGULAR'||normalized==='ERRO'? `${situacao} · VENCIDA`:'VENCIDA';
  if(validade==='PRÓXIMA DO VENCIMENTO'&&(normalized==='REGULAR'||normalized==='NEGATIVA'))return validade;
  if(!item?.data_validade&&(normalized==='REGULAR'||normalized==='NEGATIVA'))return `${situacao} · validade não identificada`;
  return situacao;
}
function classeSituacao(value?:string|null){
  const v=(value||'').toUpperCase();
  if(v.includes('VENCIDA')||v.includes('IRREGULAR')||v.includes('ERRO')) return 'bad';
  if(v.includes('POSITIVA COM EFEITOS')||v.includes('POSITIVA')||v.includes('PRÓXIMA DO VENCIMENTO')) return 'warn';
  if(v.includes('VALIDADE NÃO IDENTIFICADA')) return 'neutral';
  if(v==='REGULAR'||v==='NEGATIVA') return 'ok';
  return 'neutral';
}
function resultadoLote(lote:{resumo:Record<string,number>;resultados:CertidaoConsultaResultado[]}):string {
  const r=lote.resumo;
  if((r.erro||0)>0||(r.consultas_registradas||0)<(r.total||0))return 'ERRO · REVISAR LOTE';
  if((r.irregular||0)>0)return 'IRREGULAR';
  if((r.positiva_com_efeitos_de_negativa||0)>0)return 'POSITIVA COM EFEITOS DE NEGATIVA';
  if((r.regular||0)===(r.total||0)&&(r.total||0)>0)return 'REGULAR';
  return 'REVISAR RESULTADOS';
}

export function CertidoesPage(){
  const [emp,setEmp]=useState<Empresa[]>([]);
  const [empresaId,setEmpresaId]=useState('');
  const [tipoSelecionado,setTipoSelecionado]=useState<CertType>('federal');
  const [busca,setBusca]=useState('');
  const [items,setItems]=useState<Certidao[]>([]);
  const [hist,setHist]=useState<any[]>([]);
  const [loading,setLoading]=useState(true);
  const [consultando,setConsultando]=useState(false);
  const [err,setErr]=useState('');
  const [resultado,setResultado]=useState<CertidaoConsultaResultado|null>(null);
  const [lote,setLote]=useState<{resumo:Record<string,number>;resultados:CertidaoConsultaResultado[]}|null>(null);
  const [processandoLote,setProcessandoLote]=useState(false);

  const empresaSelecionada=emp.find(e=>e.id===Number(empresaId));
  const activeCompanies=useMemo(()=>emp.filter(e=>e.ativo),[emp]);
  const filteredCompanies=useMemo(()=>{
    const q=busca.trim().toLowerCase();
    if(!q) return activeCompanies;
    return activeCompanies.filter(e=>`${e.razao_social} ${e.nome_fantasia||''} ${e.cnpj}`.toLowerCase().includes(q));
  },[activeCompanies,busca]);
  const cardAtual=TYPE_CARDS.find(x=>x.key===tipoSelecionado)!;
  const busy=loading||consultando||processandoLote;

  async function carregarEmpresa(id:number){
    setLoading(true);
    try{
      const [r,h]=await Promise.all([listarCertidoes(id),historicoCertidoes(id)]);
      setItems(r.certidoes); setHist(h.historico);
    }catch(x){setErr(x instanceof Error?x.message:'Erro ao carregar as certidões da empresa.')}finally{setLoading(false)}
  }

  async function load(selectedId?:string){
    setLoading(true);setErr('');
    try{
      const a=await listarEmpresasParaSelecao();
      setEmp(a.empresas);
      const saved=selectedId ?? localStorage.getItem('omega_certidoes_empresa_id') ?? '';
      if(saved && a.empresas.some(e=>e.id===Number(saved)&&e.ativo)){
        setEmpresaId(saved); await carregarEmpresa(Number(saved));
      }else if(a.empresas.some(e=>e.ativo)){
        const first=a.empresas.find(e=>e.ativo)!;
        setEmpresaId(String(first.id)); localStorage.setItem('omega_certidoes_empresa_id',String(first.id));
        await carregarEmpresa(first.id);
      }else{
        setEmpresaId('');setItems([]);setHist([]);
      }
    }catch(x){setErr(x instanceof Error?x.message:'Erro ao carregar a Central de Certidões.')}finally{setLoading(false)}
  }

  useEffect(()=>{void load()},[]);

  async function selecionarEmpresa(id:string){
    setEmpresaId(id);setResultado(null);setLote(null);setErr('');
    if(id) localStorage.setItem('omega_certidoes_empresa_id',id); else localStorage.removeItem('omega_certidoes_empresa_id');
    if(!id){setItems([]);setHist([]);return;}
    await carregarEmpresa(Number(id));
  }

  async function executar(tipo:CertType,id?:number){
    const alvo=id ?? Number(empresaId);
    if(!alvo){setErr('Selecione uma empresa antes de consultar a certidão.');return;}
    setEmpresaId(String(alvo));localStorage.setItem('omega_certidoes_empresa_id',String(alvo));
    setTipoSelecionado(tipo);setConsultando(true);setErr('');setResultado(null);setLote(null);
    try{
      let r:CertidaoConsultaResultado;
      if(tipo==='federal') r=await consultarCertidaoFederal(alvo);
      else if(tipo==='estadual') r=await consultarCertidaoEstadual(alvo);
      else r=await consultarCertidaoNarrativa(alvo);
      setResultado(r);
      await carregarEmpresa(alvo);
    }catch(x){setErr(x instanceof Error?x.message:'Não foi possível concluir a emissão.')}finally{setConsultando(false)}
  }

  async function consultarTodas(){
    if(!activeCompanies.length) return;
    setTipoSelecionado('estadual');setProcessandoLote(true);setErr('');setResultado(null);setLote(null);
    try{const r=await consultarTodasCertidoesEstaduais();setLote(r);if(empresaId) await carregarEmpresa(Number(empresaId));}
    catch(x){setErr(x instanceof Error?x.message:'Não foi possível concluir o processamento em lote.')}finally{setProcessandoLote(false)}
  }

  function certAtual(typeName:string){return items.find(x=>x.tipo_certidao===typeName);}

  const pdfHistory=hist.filter(h=>h.pdf_path);

  function renderResult(){
    if(!resultado) return null;
    return <div className="panel cert-result-card">
      <div className="cert-result-top"><div><span className="eyebrow">ÚLTIMO RESULTADO</span><h3>{resultado.empresa||empresaSelecionada?.razao_social||'Empresa'}</h3><p>{resultado.cnpj||empresaSelecionada?.cnpj||'—'}</p></div><StatusBadge value={statusDaCertidao(resultado)}/></div>
      <div className="cert-result-grid">
        <div><span>Certidão</span><strong>{resultado.tipo_certidao||cardAtual.title}</strong></div>
        <div><span>Emissão</span><strong>{formatarData(resultado.data_emissao)}</strong></div>
        <div><span>Validade</span><strong>{formatarData(resultado.data_validade)}</strong></div>
        <div><span>Número</span><strong>{resultado.numero_certidao||'—'}</strong></div>
      </div>
      {resultado.mensagem&&<div className="result-message">{resultado.mensagem}</div>}
      {resultado.pdf_path&&<div className="result-actions"><button className="button primary" onClick={()=>void abrirPdfCertidaoAutenticado(resultado.pdf_path!,true)}><Download size={15}/> Baixar PDF</button><button className="button secondary" onClick={()=>void abrirPdfCertidaoAutenticado(resultado.pdf_path!)}><ExternalLink size={15}/> Visualizar PDF</button></div>}
    </div>
  }

  if(loading && !emp.length) return <div className="page"><Loading/></div>;

  return <div className="page cert-page">
    <div className="page-heading cert-page-heading">
      <div><span className="eyebrow">CENTRAL DE CERTIDÕES</span><h2>Certidões</h2><p>Consulte, emita, visualize e baixe os documentos fiscais de cada empresa.</p></div>
      <div className="heading-actions"><button className="button secondary" onClick={()=>load(empresaId||undefined)} disabled={busy}><RefreshCw size={15}/> Atualizar</button><button className="button secondary" onClick={consultarTodas} disabled={!activeCompanies.length||busy}><ShieldCheck size={15}/> Atualizar estaduais</button></div>
    </div>

    {err&&<div className="form-error"><AlertTriangle size={14}/><span>{err}</span></div>}

    <div className="cert-environment-notice"><AlertTriangle size={16}/><span><strong>Requisitos das consultas:</strong> a certidão estadual usa Playwright; a consulta federal e a narrativa dependem de Chrome/Chromium e sessão gráfica ativa na máquina do backend. Em servidor sem interface gráfica, esses dois fluxos não devem ser considerados disponíveis.</span></div>

    <section className="cert-type-section">
      <div className="section-title-row"><div><span className="eyebrow">1 · TIPO DE CERTIDÃO</span><h3>Escolha o que deseja emitir</h3></div><span className="section-hint">Emissão e histórico permanentes</span></div>
      <div className="cert-type-grid-v2">
        {TYPE_CARDS.map(card=>{const Icon=card.icon;const selected=tipoSelecionado===card.key;const item=certAtual(card.typeName);return <button key={card.key} className={`cert-type-card-v2 ${card.className} ${selected?'selected':''}`} onClick={()=>{setTipoSelecionado(card.key);setResultado(null);setErr('')}} disabled={busy}>
          <span className="type-card-top"><span className="type-icon-v2"><Icon size={23}/></span>{selected&&<span className="selected-check"><CheckCircle2 size={17}/> Selecionada</span>}</span>
          <span className="type-card-name">{card.short}</span><strong>{card.title}</strong><small>{card.desc}</small>
          <span className={`type-status ${classeSituacao(statusDaCertidao(item))}`}>{statusDaCertidao(item)}{item?.data_validade?` · validade ${formatarData(item.data_validade)}`:''}</span>
          <span className="type-card-footer"><em>{card.method}</em><span><Play size={12} fill="currentColor"/> Emitir agora</span></span>
        </button>})}
      </div>
    </section>

    <section className="company-section">
      <div className="section-title-row company-title-row"><div><span className="eyebrow">2 · EMPRESAS</span><h3>Selecione a empresa</h3></div><span className="company-counter">{filteredCompanies.length} disponíveis</span></div>
      <div className="company-toolbar-v2"><div className="company-search-v2"><Search size={17}/><input value={busca} onChange={e=>setBusca(e.target.value)} placeholder="Pesquisar por razão social, fantasia ou CNPJ..."/></div></div>
      <div className="company-cards-grid">
        {filteredCompanies.map(e=>{const selected=e.id===Number(empresaId);return <button key={e.id} className={`company-card-v2 ${selected?'selected':''}`} onClick={()=>void selecionarEmpresa(String(e.id))} disabled={busy}>
          <span className="company-card-icon"><Building2 size={19}/></span>
          <span className="company-card-body"><strong>{e.razao_social}</strong><small>{e.nome_fantasia&&e.nome_fantasia!==e.razao_social?e.nome_fantasia+' · ':''}{e.cnpj}</small><small>{[e.municipio,e.uf].filter(Boolean).join('/')||'Localização não informada'}</small></span>
          <span className="company-card-check">{selected?<CheckCircle2 size={19}/>:null}</span>
        </button>})}
        {!filteredCompanies.length&&<div className="empty-company"><Building2 size={25}/><strong>Nenhuma empresa encontrada</strong><span>Ajuste a pesquisa para continuar.</span></div>}
      </div>
    </section>

    {empresaSelecionada&&<section className="company-workspace">
      <div className="workspace-head"><div><span className="eyebrow">3 · EMPRESA SELECIONADA</span><h3>{empresaSelecionada.razao_social}</h3><p>{empresaSelecionada.cnpj}{empresaSelecionada.municipio?` · ${empresaSelecionada.municipio}/${empresaSelecionada.uf||''}`:''}</p></div><button className="button primary big" onClick={()=>void executar(tipoSelecionado)} disabled={busy}><Play size={16} fill="currentColor"/> Emitir {cardAtual.short}</button></div>

      {renderResult()}

      {(() => {
        const selected = certAtual(cardAtual.typeName);
        const Icon = cardAtual.icon;
        return <section className={`cert-selected-panel ${cardAtual.className}`}>
          <div className="cert-selected-head">
            <div className="cert-selected-title"><span className="type-icon-v2"><Icon size={20}/></span><div><span className="eyebrow">CERTIDÃO SELECIONADA</span><h3>{cardAtual.title}</h3><p>{cardAtual.desc}</p></div></div>
          </div>
          <div className="cert-selected-grid">
            <div><span>Situação</span><strong className={`selected-status ${classeSituacao(statusDaCertidao(selected))}`}>{statusDaCertidao(selected)}</strong></div>
            <div><span>Emissão</span><strong>{formatarData(selected?.data_emissao)}</strong></div>
            <div><span>Validade</span><strong>{formatarData(selected?.data_validade)}</strong></div>
            <div><span>Número</span><strong>{selected?.numero_certidao||'—'}</strong></div>
          </div>
          <div className="cert-selected-actions">{selected?.pdf_path?<><button className="button secondary small" onClick={()=>void abrirPdfCertidaoAutenticado(selected.pdf_path!,true)}><Download size={13}/> Baixar PDF</button><button className="button secondary small" onClick={()=>void abrirPdfCertidaoAutenticado(selected.pdf_path!)}><ExternalLink size={13}/> Visualizar PDF</button></>:<span className="cert-no-pdf">Nenhum PDF armazenado para esta certidão.</span>}</div>
        </section>;
      })()}

      <section className="downloads-panel panel">
        <div className="panel-header"><div><span className="eyebrow">DOCUMENTOS DISPONÍVEIS</span><h3>Certidões para download</h3></div><span className="download-count">{pdfHistory.length} PDF(s)</span></div>
        {pdfHistory.length===0?<div className="empty compact"><FileText size={26}/><strong>Nenhuma certidão armazenada ainda</strong><span>Ao emitir uma certidão, o PDF fica disponível aqui para visualizar e baixar novamente.</span></div>:<div className="downloads-list">
          {pdfHistory.map((h:any,index:number)=><div className="download-row" key={`${h.id}-${index}`}><div className="download-file-icon"><FileCheck2 size={19}/></div><div className="download-main"><strong>{h.tipo_certidao||'Certidão'}</strong><span>{h.nome_arquivo_original||'certidao.pdf'} · {formatarData(h.data_emissao)} · validade {formatarData(h.data_validade)}</span><small>{formatarDataHora(h.consultado_em)}</small></div><div className="download-status"><StatusBadge value={statusDaCertidao(h)}/></div><div className="download-actions"><button className="icon-button" title="Baixar PDF" onClick={()=>void abrirPdfCertidaoAutenticado(h.pdf_path,true)}><Download size={15}/></button><button className="icon-button" title="Visualizar PDF" onClick={()=>void abrirPdfCertidaoAutenticado(h.pdf_path)}><ExternalLink size={15}/></button></div></div>)}
        </div>}
      </section>

      <section className="history-panel panel"><div className="panel-header"><div><span className="eyebrow">HISTÓRICO</span><h3>Consultas realizadas</h3></div><History size={18}/></div>{hist.length===0?<div className="empty compact"><CalendarDays size={24}/><span>Nenhuma consulta registrada.</span></div>:<div className="history-list">{hist.slice(0,20).map((h:any,index:number)=><div className="history-item" key={`${h.id}-${index}`}><strong>{h.tipo_certidao||'Certidão'} · {h.situacao||'—'}</strong><span>{formatarData(h.data_emissao)} → validade {formatarData(h.data_validade)}</span><small>{formatarDataHora(h.consultado_em)}{h.numero_certidao?` · Nº ${h.numero_certidao}`:''}</small></div>)}</div>}</section>
    </section>}

    {lote&&<section className="panel batch-panel">
      <div className="panel-header"><div><span className="eyebrow">PROCESSAMENTO EM LOTE</span><h3>Resultado do processamento em lote</h3></div><StatusBadge value={resultadoLote(lote)}/></div>
      <div className="batch-grid">{Object.entries(lote.resumo).map(([k,v])=><div key={k}><strong>{v}</strong><span>{k.replace(/_/g,' ')}</span></div>)}</div>
      {lote.resultados.some(r=>r.situacao!=='REGULAR'||r.status_processamento!=='Sucesso')&&<div className="batch-result-list">
        <strong>Resultados que precisam de atenção</strong>
        {lote.resultados.filter(r=>r.situacao!=='REGULAR'||r.status_processamento!=='Sucesso').map((r,index)=><div className="batch-result-row" key={`${r.empresa_id||r.cnpj||'empresa'}-${index}`}>
          <div><b>{r.empresa||'Empresa não identificada'}</b><small>{r.cnpj||'CNPJ não informado'}</small></div>
          <StatusBadge value={statusDaCertidao(r)}/>
          <span>{r.mensagem||'Verifique a certidão e o histórico desta empresa.'}</span>
        </div>)}
      </div>}
    </section>}
  </div>
}
