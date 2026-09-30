import {useEffect,useMemo,useState} from 'react';
import {AlertTriangle, CheckCircle2, Download, ExternalLink, FileCheck2, FileText, History, Landmark, RefreshCw, Search, ShieldCheck, Play, Building2, CalendarDays} from 'lucide-react';
import {listarCertidoes,listarTiposCertidao,historicoCertidoes,listarEmpresasParaSelecao,consultarCertidaoEstadual,consultarCertidaoFederal,consultarCertidaoNarrativa,consultarTodasCertidoesEstaduais,pdfUrl,pdfDownloadUrl} from '../../services/api/certidoes';
import type {Certidao,TipoCertidao,Empresa,CertidaoConsultaResultado} from '../../types';
import {Loading} from '../../components/ui/Loading';
import {StatusBadge} from '../../components/status/StatusBadge';

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
  {key:'federal',title:'Federal · RFB/PGFN',short:'CND Federal',desc:'Receita Federal e PGFN',icon:Landmark,className:'blue',method:'Emissão integrada',typeName:'Federal - RFB/PGFN'},
  {key:'estadual',title:'Estadual · SEFAZ-PE',short:'CND Estadual',desc:'Regularidade fiscal em Pernambuco',icon:ShieldCheck,className:'green',method:'Emissão integrada',typeName:'Estadual - SEFAZ'},
  {key:'narrativa',title:'Narrativa · Débito Fiscal',short:'Narrativa SEFAZ',desc:'Consulta autenticada por certificado',icon:FileText,className:'amber',method:'Emissão integrada',typeName:'Narrativa - Débito Fiscal'},
];

function classeSituacao(value?:string|null){
  const v=(value||'').toUpperCase();
  if(v==='REGULAR'||v==='NEGATIVA') return 'ok';
  if(v.includes('POSITIVA COM EFEITOS')) return 'warn';
  if(v==='IRREGULAR'||v==='VENCIDA'||v==='ERRO') return 'bad';
  return 'neutral';
}

export function CertidoesPage(){
  const [emp,setEmp]=useState<Empresa[]>([]);
  const [tipos,setTipos]=useState<TipoCertidao[]>([]);
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
      const [a,b]=await Promise.all([listarEmpresasParaSelecao(),listarTiposCertidao()]);
      setEmp(a.empresas);setTipos(b.tipos);
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

  const currentCards=TYPE_CARDS.map(card=>({card,item:certAtual(card.typeName)}));
  const pdfHistory=hist.filter(h=>h.pdf_path);

  function renderResult(){
    if(!resultado) return null;
    return <div className="panel cert-result-card">
      <div className="cert-result-top"><div><span className="eyebrow">ÚLTIMO RESULTADO</span><h3>{resultado.empresa||empresaSelecionada?.razao_social||'Empresa'}</h3><p>{resultado.cnpj||empresaSelecionada?.cnpj||'—'}</p></div><StatusBadge value={resultado.situacao}/></div>
      <div className="cert-result-grid">
        <div><span>Certidão</span><strong>{resultado.tipo_certidao||cardAtual.title}</strong></div>
        <div><span>Emissão</span><strong>{formatarData(resultado.data_emissao)}</strong></div>
        <div><span>Validade</span><strong>{formatarData(resultado.data_validade)}</strong></div>
        <div><span>Número</span><strong>{resultado.numero_certidao||'—'}</strong></div>
      </div>
      {resultado.mensagem&&<div className="result-message">{resultado.mensagem}</div>}
      {resultado.pdf_path&&<div className="result-actions"><a className="button primary" href={pdfDownloadUrl(resultado.pdf_path)}><Download size={15}/> Baixar PDF</a><button className="button secondary" onClick={()=>window.open(pdfUrl(resultado.pdf_path!), '_blank','noopener,noreferrer')}><ExternalLink size={15}/> Visualizar PDF</button></div>}
    </div>
  }

  if(loading && !emp.length) return <div className="page"><Loading/></div>;

  return <div className="page cert-page">
    <div className="page-heading cert-page-heading">
      <div><span className="eyebrow">CENTRAL DE CERTIDÕES</span><h2>Certidões</h2><p>Consulte, emita, visualize e baixe os documentos fiscais de cada empresa.</p></div>
      <div className="heading-actions"><button className="button secondary" onClick={()=>load(empresaId||undefined)} disabled={busy}><RefreshCw size={15}/> Atualizar</button><button className="button secondary" onClick={consultarTodas} disabled={!activeCompanies.length||busy}><ShieldCheck size={15}/> Atualizar estaduais</button></div>
    </div>

    {err&&<div className="form-error"><AlertTriangle size={14}/><span>{err}</span></div>}


    <section className="cert-type-section">
      <div className="section-title-row"><div><span className="eyebrow">1 · TIPO DE CERTIDÃO</span><h3>Escolha o que deseja emitir</h3></div><span className="section-hint">Emissão e histórico permanentes</span></div>
      <div className="cert-type-grid-v2">
        {TYPE_CARDS.map(card=>{const Icon=card.icon;const selected=tipoSelecionado===card.key;const item=certAtual(card.typeName);return <button key={card.key} className={`cert-type-card-v2 ${card.className} ${selected?'selected':''}`} onClick={()=>{setTipoSelecionado(card.key);setResultado(null);setErr('')}} disabled={busy}>
          <span className="type-card-top"><span className="type-icon-v2"><Icon size={23}/></span>{selected&&<span className="selected-check"><CheckCircle2 size={17}/> Selecionada</span>}</span>
          <span className="type-card-name">{card.short}</span><strong>{card.title}</strong><small>{card.desc}</small>
          <span className={`type-status ${classeSituacao(item?.situacao)}`}>{item?.situacao||'Ainda não consultada'}{item?.data_validade?` · validade ${formatarData(item.data_validade)}`:''}</span>
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
            <button className="button primary" onClick={()=>void executar(tipoSelecionado)} disabled={busy}><Play size={14} fill="currentColor"/> Emitir {cardAtual.short}</button>
          </div>
          <div className="cert-selected-grid">
            <div><span>Situação</span><strong className={`selected-status ${classeSituacao(selected?.situacao)}`}>{selected?.situacao||'Ainda não consultada'}</strong></div>
            <div><span>Emissão</span><strong>{formatarData(selected?.data_emissao)}</strong></div>
            <div><span>Validade</span><strong>{formatarData(selected?.data_validade)}</strong></div>
            <div><span>Número</span><strong>{selected?.numero_certidao||'—'}</strong></div>
          </div>
          <div className="cert-selected-actions">{selected?.pdf_path?<><a className="button secondary small" href={pdfDownloadUrl(selected.pdf_path)}><Download size={13}/> Baixar PDF</a><button className="button secondary small" onClick={()=>window.open(pdfUrl(selected.pdf_path!), '_blank','noopener,noreferrer')}><ExternalLink size={13}/> Visualizar PDF</button></>:<span className="cert-no-pdf">Nenhum PDF armazenado para esta certidão.</span>}</div>
        </section>;
      })()}

      <section className="downloads-panel panel">
        <div className="panel-header"><div><span className="eyebrow">DOCUMENTOS DISPONÍVEIS</span><h3>Certidões para download</h3></div><span className="download-count">{pdfHistory.length} PDF(s)</span></div>
        {pdfHistory.length===0?<div className="empty compact"><FileText size={26}/><strong>Nenhuma certidão armazenada ainda</strong><span>Ao emitir uma certidão, o PDF fica disponível aqui para visualizar e baixar novamente.</span></div>:<div className="downloads-list">
          {pdfHistory.map((h:any,index:number)=><div className="download-row" key={`${h.id}-${index}`}><div className="download-file-icon"><FileCheck2 size={19}/></div><div className="download-main"><strong>{h.tipo_certidao||'Certidão'}</strong><span>{h.nome_arquivo_original||'certidao.pdf'} · {formatarData(h.data_emissao)} · validade {formatarData(h.data_validade)}</span><small>{formatarDataHora(h.consultado_em)}</small></div><div className="download-status"><StatusBadge value={h.situacao}/></div><div className="download-actions"><a className="icon-button" title="Baixar PDF" href={pdfDownloadUrl(h.pdf_path)}><Download size={15}/></a><button className="icon-button" title="Visualizar PDF" onClick={()=>window.open(pdfUrl(h.pdf_path),'_blank','noopener,noreferrer')}><ExternalLink size={15}/></button></div></div>)}
        </div>}
      </section>

      <section className="history-panel panel"><div className="panel-header"><div><span className="eyebrow">HISTÓRICO</span><h3>Consultas realizadas</h3></div><History size={18}/></div>{hist.length===0?<div className="empty compact"><CalendarDays size={24}/><span>Nenhuma consulta registrada.</span></div>:<div className="history-list">{hist.slice(0,20).map((h:any,index:number)=><div className="history-item" key={`${h.id}-${index}`}><strong>{h.tipo_certidao||'Certidão'} · {h.situacao||'—'}</strong><span>{formatarData(h.data_emissao)} → validade {formatarData(h.data_validade)}</span><small>{formatarDataHora(h.consultado_em)}{h.numero_certidao?` · Nº ${h.numero_certidao}`:''}</small></div>)}</div>}</section>
    </section>}

    {lote&&<section className="panel batch-panel"><div className="panel-header"><div><span className="eyebrow">PROCESSAMENTO EM LOTE</span><h3>Certidões estaduais emitidas</h3></div><StatusBadge value="REGULAR"/></div><div className="batch-grid">{Object.entries(lote.resumo).map(([k,v])=><div key={k}><strong>{v}</strong><span>{k}</span></div>)}</div></section>}
  </div>
}
