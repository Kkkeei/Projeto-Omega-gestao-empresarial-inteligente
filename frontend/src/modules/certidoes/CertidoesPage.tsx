import {useEffect,useState} from 'react';
import {FileCheck2,RefreshCw,History,ExternalLink,Play,AlertTriangle} from 'lucide-react';
import {listarCertidoes,listarTiposCertidao,historicoCertidoes,listarEmpresasParaSelecao,consultarCertidaoEstadual,consultarCertidaoFederal,consultarCertidaoNarrativa,consultarTodasCertidoesEstaduais,pdfUrl} from '../../services/api/certidoes';
import type {Certidao,TipoCertidao,Empresa,CertidaoConsultaResultado} from '../../types';
import {Loading} from '../../components/ui/Loading';
import {ErrorState} from '../../components/ui/ErrorState';
import {StatusBadge} from '../../components/status/StatusBadge';

function classeSituacao(value:string){
  const v=value.toUpperCase();
  if(v==='REGULAR') return 'success';
  if(v==='POSITIVA COM EFEITOS DE NEGATIVA') return 'warning';
  if(v==='IRREGULAR') return 'danger';
  return 'neutral';
}

export function CertidoesPage(){
  const [emp,setEmp]=useState<Empresa[]>([]),[tipos,setTipos]=useState<TipoCertidao[]>([]),[empresaId,setEmpresaId]=useState('');
  const [items,setItems]=useState<Certidao[]>([]),[hist,setHist]=useState<any[]>([]),[loading,setLoading]=useState(true),[consultando,setConsultando]=useState(false),[consultandoFederal,setConsultandoFederal]=useState(false),[consultandoNarrativa,setConsultandoNarrativa]=useState(false),[err,setErr]=useState('');
  const [resultado,setResultado]=useState<CertidaoConsultaResultado|null>(null);
  const [lote,setLote]=useState<{resumo:Record<string,number>;resultados:CertidaoConsultaResultado[]}|null>(null);
  const [processandoLote,setProcessandoLote]=useState(false);

  const load=async(selectedId?:string)=>{
    setLoading(true);setErr('');
    try{
      const [a,b]=await Promise.all([listarEmpresasParaSelecao(),listarTiposCertidao()]);
      setEmp(a.empresas);setTipos(b.tipos);

      const saved=selectedId ?? localStorage.getItem('omega_certidoes_empresa_id') ?? '';
      const valido=saved && a.empresas.some(e=>e.id===Number(saved) && e.ativo);
      if(valido){
        setEmpresaId(saved);
        const [r,h]=await Promise.all([listarCertidoes(Number(saved)),historicoCertidoes(Number(saved))]);
        setItems(r.certidoes);setHist(h.historico);
      }else{
        setEmpresaId('');
        setItems((await listarCertidoes()).certidoes);
        setHist([]);
      }
    }catch(x){setErr(x instanceof Error?x.message:'Erro ao carregar certidões.')}
    finally{setLoading(false)}
  };
  useEffect(()=>{load()},[]);

  async function selecionar(id:string){
    setEmpresaId(id);setResultado(null);setErr('');
    if(id) localStorage.setItem('omega_certidoes_empresa_id',id);
    else localStorage.removeItem('omega_certidoes_empresa_id');
    if(!id){setItems([]);setHist([]);return;}
    setLoading(true);
    try{const r=await listarCertidoes(Number(id));setItems(r.certidoes);setHist((await historicoCertidoes(Number(id))).historico)}
    catch(x){setErr(x instanceof Error?x.message:'Erro ao carregar certidões da empresa.')}finally{setLoading(false)}
  }


  async function consultarFederal(){
    if(!empresaId){setErr('Selecione uma empresa antes de consultar a Certidão Federal.');return;}
    setConsultandoFederal(true);setErr('');setResultado(null);setLote(null);
    try{
      const r=await consultarCertidaoFederal(Number(empresaId));
      setResultado(r);
      const atual=await listarCertidoes(Number(empresaId));
      setItems(atual.certidoes);
      setHist((await historicoCertidoes(Number(empresaId))).historico);
    }catch(x){setErr(x instanceof Error?x.message:'Não foi possível concluir a Certidão Federal RFB/PGFN.')}
    finally{setConsultandoFederal(false)}
  }

  async function consultarNarrativa(){
    if(!empresaId){setErr('Selecione uma empresa antes de consultar a Certidão Narrativa.');return;}
    setConsultandoNarrativa(true);setErr('');setResultado(null);setLote(null);
    try{
      const r=await consultarCertidaoNarrativa(Number(empresaId));
      setResultado(r);
      const atual=await listarCertidoes(Number(empresaId));
      setItems(atual.certidoes);
      setHist((await historicoCertidoes(Number(empresaId))).historico);
    }catch(x){setErr(x instanceof Error?x.message:'Não foi possível concluir a Certidão Narrativa de Débito Fiscal.')}
    finally{setConsultandoNarrativa(false)}
  }

  async function consultarTodas(){
    setProcessandoLote(true);setErr('');setResultado(null);setLote(null);
    try{
      const r=await consultarTodasCertidoesEstaduais();
      setLote(r);
      if(empresaId){
        const atual=await listarCertidoes(Number(empresaId));
        setItems(atual.certidoes);
        setHist((await historicoCertidoes(Number(empresaId))).historico);
      }
    }catch(x){
      setErr(x instanceof Error?x.message:'Não foi possível concluir o processamento em lote.');
    }finally{
      setProcessandoLote(false);
    }
  }

  async function consultar(){
    if(!empresaId){setErr('Selecione uma empresa antes de consultar a Certidão Estadual.');return;}
    setConsultando(true);setErr('');setResultado(null);
    try{const r=await consultarCertidaoEstadual(Number(empresaId));setResultado(r);const atual=await listarCertidoes(Number(empresaId));setItems(atual.certidoes);setHist((await historicoCertidoes(Number(empresaId))).historico)}
    catch(x){setErr(x instanceof Error?x.message:'Não foi possível concluir a consulta na SEFAZ-PE.')}finally{setConsultando(false)}
  }

  const empresaSelecionada=emp.find(e=>e.id===Number(empresaId));

  return <div className="page">
    <div className="page-heading"><div><span className="eyebrow">REGULARIDADE FISCAL</span><h2>Certidão Estadual</h2><p>Consulta integrada ao e-Fisco da SEFAZ Pernambuco, com PDF e histórico preservados.</p></div><div className="heading-actions"><button className="button secondary" onClick={load} disabled={loading||consultando||consultandoFederal||consultandoNarrativa||processandoLote}><RefreshCw size={15}/> Atualizar</button><button className="button secondary" onClick={consultarTodas} disabled={loading||consultando||consultandoFederal||consultandoNarrativa||processandoLote}>{processandoLote?'Processando todas...':'Consultar todas as empresas'}</button></div></div>

    {err&&<div className="form-error"><AlertTriangle size={14}/> {err}</div>}

    <div className="panel automation-run">
      <div><span className="eyebrow">CENTRAL DE CERTIDÕES</span><h3>Consultar Certidão Estadual</h3><p>Selecione uma empresa e execute a consulta automática. A situação fiscal nunca é presumida.</p></div>
      <div className="run-grid"><label>Empresa<select value={empresaId} onChange={e=>selecionar(e.target.value)}><option value="">Selecione uma empresa</option>{emp.filter(e=>e.ativo).map(e=><option key={e.id} value={e.id}>{e.razao_social} — {e.cnpj}</option>)}</select></label><label>Tipo de Certidão<input value="Estadual - SEFAZ" disabled /></label><button className="button primary run-button" onClick={consultar} disabled={!empresaId||consultando||consultandoFederal||consultandoNarrativa}><Play size={15}/>{consultando?'Consultando SEFAZ-PE...':'Consultar Estadual'}</button><button className="button secondary run-button" onClick={consultarFederal} disabled={!empresaId||consultando||consultandoFederal||consultandoNarrativa}>{consultandoFederal?'Consultando RFB/PGFN...':'Consultar Federal'}</button><button className="button secondary run-button" onClick={consultarNarrativa} disabled={!empresaId||consultando||consultandoFederal||consultandoNarrativa}>{consultandoNarrativa?'Lendo documento...':'Certidão Narrativa / Débito Fiscal'}</button></div>
    </div>

    {consultando&&<Loading text="Acessando o e-Fisco, emitindo e analisando a certidão..."/>}
    {consultandoFederal&&<Loading text="Acessando a Receita Federal/PGFN, consultando o CNPJ e tentando obter o documento..."/>}
    {consultandoNarrativa&&<Loading text="Abrindo SEFAZ-PE, autenticando com certificado digital e lendo o documento exibido no Chrome..."/>}
    {processandoLote&&<Loading text="Consultando todas as empresas ativas na SEFAZ-PE. O lote continua mesmo se uma empresa apresentar erro..."/>}

    {!processandoLote&&lote&&<div className="panel result-card"><div className="panel-header"><div><span className="eyebrow">PROCESSAMENTO EM LOTE</span><h3>Certidões Estaduais</h3><p>{lote.resumo.consultas_registradas||0} de {lote.resumo.total||0} consultas registradas no banco.</p></div></div><div className="details cert-result-details"><div><span>Regular</span><strong>{lote.resumo.regular||0}</strong></div><div><span>Positiva com efeitos</span><strong>{lote.resumo.positiva_com_efeitos_de_negativa||0}</strong></div><div><span>Irregular</span><strong>{lote.resumo.irregular||0}</strong></div><div><span>Aguardando intervenção</span><strong>{lote.resumo.aguardando_intervencao||0}</strong></div><div><span>Erro</span><strong>{lote.resumo.erro||0}</strong></div></div></div>}

    {!consultando&&resultado&&<div className="panel result-card">
      <div className="panel-header"><div><span className="eyebrow">RESULTADO DA CONSULTA</span><h3>{resultado.empresa||empresaSelecionada?.razao_social||'Empresa'}</h3><p>{resultado.cnpj}</p></div><span className={`badge ${classeSituacao(resultado.situacao)}`}>{resultado.situacao==='AGUARDANDO_INTERVENCAO'?'🟠 AGUARDANDO INTERVENÇÃO':resultado.situacao==='ERRO'?'⚠ ERRO':resultado.situacao}</span></div>
      <div className="details cert-result-details">
        <div><span>Tipo da certidão</span><strong>{resultado.tipo_certidao||'—'}</strong></div><div><span>Status da automação</span><strong>{resultado.status_processamento||'—'}</strong></div>
        <div><span>Data de emissão</span><strong>{resultado.data_emissao||'—'}</strong></div><div><span>Data de validade</span><strong>{resultado.data_validade||'—'}</strong></div>
        <div><span>Pendência</span><strong>{resultado.pendencia?'SIM':'NÃO'}</strong></div><div><span>Arquivo original</span><strong>{resultado.nome_arquivo_original||'—'}</strong></div>
      </div>
      {resultado.pendencia&&<div className="pendency-box"><strong>🔴 Pendência identificada</strong><p>{resultado.pendencia_detalhes||'A certidão indica irregularidade. Consulte o documento para verificar os detalhes.'}</p></div>}
      {resultado.mensagem&&<div className="result-message">{resultado.mensagem}</div>}
      {resultado.tipo_certidao==='Narrativa de Débito Fiscal - SEFAZ'&&resultado.texto_extraido&&<div className="document-reading-box"><strong>Leitura do documento no navegador</strong><pre>{resultado.texto_extraido}</pre></div>}
      {resultado.pdf_path&&<div className="form-actions result-actions"><button className="button primary" onClick={()=>window.open(pdfUrl(resultado.pdf_path!), '_blank','noopener,noreferrer')}><ExternalLink size={15}/> Visualizar Certidão</button></div>}
    </div>}

    {loading?<Loading text="Carregando certidões..."/>:<>
      <div className="panel table-panel"><div className="table-meta"><span>{items.length} certidão(ões) atual(is)</span><span>SEFAZ-PE integrada · histórico preservado</span></div>{items.length===0?<div className="empty"><FileCheck2 size={35}/><strong>{empresaId?'Nenhuma certidão registrada':'Selecione uma empresa'}</strong><span>{empresaId?'Execute a consulta estadual para obter a primeira certidão.':'Escolha uma empresa acima para consultar a situação fiscal estadual.'}</span></div>:<div className="table-wrap"><table><thead><tr><th>Tipo</th><th>Empresa</th><th>Situação</th><th>Emissão</th><th>Validade</th><th>Documento</th></tr></thead><tbody>{items.map(c=><tr key={c.id}><td><strong>{c.tipo_certidao||`Tipo ${c.tipo_certidao_id}`}</strong></td><td>{emp.find(e=>e.id===c.empresa_id)?.razao_social||`Empresa #${c.empresa_id}`}</td><td><StatusBadge value={c.situacao}/></td><td>{c.data_emissao||'—'}</td><td>{c.data_validade||'—'}{c.status_validade&&<small>{c.status_validade}</small>}</td><td>{c.pdf_path?<button className="icon-button" title="Visualizar PDF" onClick={()=>window.open(pdfUrl(c.pdf_path!), '_blank','noopener,noreferrer')}><ExternalLink size={14}/></button>:'—'}</td></tr>)}</tbody></table></div>}</div>
      {empresaId&&<div className="panel history-panel"><div className="panel-header"><div><span className="eyebrow">HISTÓRICO</span><h3>Consultas da Certidão Estadual</h3></div><History size={18}/></div>{hist.length===0?<div className="empty compact"><span>Nenhuma consulta anterior registrada.</span></div>:<div className="history-list">{hist.map(x=><div className="history-item" key={x.id}><strong>{x.situacao}</strong><span>{x.tipo_certidao} · Emissão: {x.data_emissao||'—'} · Validade: {x.data_validade||'—'}</span><small>{x.consultado_em} · {x.status_processamento||'—'} · {x.origem||'—'} {x.pdf_path?'· PDF armazenado':''}</small>{x.pdf_path&&<button className="button ghost" onClick={()=>window.open(pdfUrl(x.pdf_path),'_blank','noopener,noreferrer')}>Visualizar PDF</button>}</div>)}</div>}</div>}
    </>}
  </div>
}
