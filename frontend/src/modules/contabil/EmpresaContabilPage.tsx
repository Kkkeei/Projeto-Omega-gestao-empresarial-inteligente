import { useEffect, useMemo, useState, type DragEvent, type FormEvent } from 'react';
import { ArrowLeft, Building2, CircleAlert, Download, FileText, Folder, FolderPlus, Pencil, Plus, Search, Trash2, Upload, X } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import {
  atualizarDocumentoContabil,
  baixarArquivoContabil,
  criarCategoriaContabil,
  criarDocumentoContabil,
  excluirArquivoContabil,
  enviarArquivosContabeis,
  inativarDocumentoContabil,
  listarArquivosContabeis,
  obterDocumentacaoEmpresa,
  renomearArquivoContabil,
} from './contabilApi';
import type { ArquivoContabil, CategoriaContabil, DocumentoContabil, EmpresaDocumentacaoContabilResponse, StatusObrigacao } from './types';
import './contabil.css';

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const MOTIVOS = ['Conta encerrada', 'Contrato encerrado', 'Empresa deixou de utilizar o serviço', 'Substituição por outra documentação', 'Outros'];
const ALLOWED = ['pdf', 'jpg', 'jpeg', 'png', 'xlsx'];

function competencia(ano: number, mes: number) { return ano * 100 + mes; }
function competenciaAtual() { const now = new Date(); return competencia(now.getFullYear(), now.getMonth() + 1); }
function mesInput(value: number) { return String(Math.floor(value / 100)) + '-' + String(value % 100).padStart(2, '0'); }
function inputCompetencia(value: string) { const [ano, mes] = value.split('-').map(Number); return competencia(ano, mes); }
function formatarCnpj(value: string) {
  const digits = (value || '').replace(/\D/g, '');
  return digits.length === 14 ? digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5') : value;
}
function dataHora(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('pt-BR');
}
function tamanhoArquivo(size: number) {
  if (size < 1024 * 1024) return Math.max(1, Math.round(size / 1024)) + ' KB';
  return (size / (1024 * 1024)).toFixed(1).replace('.', ',') + ' MB';
}
function statusTexto(status: StatusObrigacao) {
  if (status === 'RECEBIDO') return 'Recebido';
  if (status === 'PENDENTE') return 'Pendente';
  if (status === 'FUTURO') return 'Futura';
  return 'Não recebido';
}
function statusClasse(status: StatusObrigacao) {
  if (status === 'RECEBIDO') return 'complete';
  if (status === 'PENDENTE') return 'partial';
  if (status === 'FUTURO') return 'future';
  return 'missing';
}

export function EmpresaContabilPage() {
  const { id } = useParams();
  const empresaId = Number(id);
  const now = new Date();
  const [ano, setAno] = useState(now.getFullYear());
  const [mes, setMes] = useState(now.getMonth() + 1);
  const [data, setData] = useState<EmpresaDocumentacaoContabilResponse | null>(null);
  const [pasta, setPasta] = useState<number | null>(null);
  const [busca, setBusca] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState<'documento' | 'upload' | 'inativar' | 'categoria' | null>(null);
  const [documentoAlvo, setDocumentoAlvo] = useState<DocumentoContabil | null>(null);
  const [arquivos, setArquivos] = useState<ArquivoContabil[]>([]);
  const [formNome, setFormNome] = useState('');
  const [formCategoria, setFormCategoria] = useState('');
  const [formInicio, setFormInicio] = useState(mesInput(competenciaAtual()));
  const [formObs, setFormObs] = useState('');
  const [categoriaNome, setCategoriaNome] = useState('');
  const [categoriaDescricao, setCategoriaDescricao] = useState('');
  const [fimCompetencia, setFimCompetencia] = useState(mesInput(competenciaAtual()));
  const [motivo, setMotivo] = useState(MOTIVOS[0]);
  const [observacaoInativacao, setObservacaoInativacao] = useState('');
  const [arquivosNovos, setArquivosNovos] = useState<File[]>([]);
  const [dragAtivo, setDragAtivo] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [arquivoEditando, setArquivoEditando] = useState<number | null>(null);
  const [nomeArquivoEditado, setNomeArquivoEditado] = useState('');
  const [arquivoExcluir, setArquivoExcluir] = useState<ArquivoContabil | null>(null);
  const [erroModal, setErroModal] = useState('');

  async function carregar() {
    if (!empresaId) return;
    setLoading(true);
    setError('');
    try {
      const result = await obterDocumentacaoEmpresa(empresaId, competencia(ano, mes));
      setData(result);
      if (pasta !== null && !result.categorias.some((item) => item.id === pasta)) setPasta(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar a documentação da empresa.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void carregar(); }, [empresaId, ano, mes]);

  const docsVisiveis = useMemo(() => (data?.documentos ?? []).filter((item) => {
    const buscaOk = !busca.trim() || (item.nome + ' ' + (item.categoria_nome || '') + ' ' + (item.observacao || '')).toLocaleLowerCase('pt-BR').includes(busca.toLocaleLowerCase('pt-BR').trim());
    return buscaOk && (pasta === null || item.categoria_id === pasta);
  }), [data, busca, pasta]);

  const resumoPasta = (category: CategoriaContabil) => {
    if (category.documentos_count > 0 && category.obrigacoes_recebidas >= category.documentos_count) return { label: 'Completo', className: 'complete' };
    if (category.obrigacoes_pendentes > 0) return { label: category.obrigacoes_pendentes + ' pendentes', className: 'partial' };
    if (category.documentos_count === 0) return { label: 'Sem documentos', className: 'future' };
    return { label: category.obrigacoes_recebidas + ' recebidos', className: 'missing' };
  };

  function abrirNovoDocumento() {
    setDocumentoAlvo(null);
    setFormNome('');
    setFormCategoria(data?.categorias[0] ? String(data.categorias[0].id) : '');
    setFormInicio(mesInput(competencia(ano, mes)));
    setFormObs('');
    setErroModal('');
    setModal('documento');
  }

  function abrirEdicao(item: DocumentoContabil) {
    setDocumentoAlvo(item);
    setFormNome(item.nome);
    setFormCategoria(String(item.categoria_id));
    setFormInicio(mesInput(item.competencia_inicio));
    setFormObs(item.observacao || '');
    setErroModal('');
    setModal('documento');
  }

  async function abrirUpload(item: DocumentoContabil) {
    setDocumentoAlvo(item);
    setArquivosNovos([]);
    setArquivoExcluir(null);
    setArquivoEditando(null);
    setErroModal('');
    setModal('upload');
    try {
      const result = await listarArquivosContabeis(item.obrigacao_id);
      setArquivos(result.arquivos);
    } catch (err) {
      setArquivos([]);
      setErroModal(err instanceof Error ? err.message : 'Não foi possível listar os arquivos.');
    }
  }

  function validarArquivos(list: File[]) {
    const valid: File[] = [];
    const failures: string[] = [];
    list.forEach((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      if (!ALLOWED.includes(ext)) failures.push(file.name + ': formato não permitido');
      else if (file.size > 25 * 1024 * 1024) failures.push(file.name + ': excede 25 MB');
      else valid.push(file);
    });
    setArquivosNovos((current) => [...current, ...valid]);
    setErroModal(failures.join('; '));
  }

  function dropFiles(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragAtivo(false);
    validarArquivos(Array.from(event.dataTransfer.files));
  }

  async function salvarDocumento(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!formNome.trim() || !formCategoria) { setErroModal('Informe o nome e a categoria.'); return; }
    setSalvando(true);
    setErroModal('');
    try {
      if (documentoAlvo) {
        await atualizarDocumentoContabil(documentoAlvo.id, { nome: formNome.trim(), categoria_id: Number(formCategoria), observacao: formObs || undefined });
      } else {
        await criarDocumentoContabil(empresaId, { nome: formNome.trim(), categoria_id: Number(formCategoria), competencia_inicio: inputCompetencia(formInicio), observacao: formObs || undefined });
      }
      setModal(null);
      await carregar();
    } catch (err) {
      setErroModal(err instanceof Error ? err.message : 'Não foi possível salvar a documentação.');
    } finally {
      setSalvando(false);
    }
  }

  async function salvarCategoria(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!categoriaNome.trim()) { setErroModal('Informe o nome da pasta.'); return; }
    setSalvando(true);
    setErroModal('');
    try {
      await criarCategoriaContabil(empresaId, { nome: categoriaNome.trim(), descricao: categoriaDescricao || undefined });
      setModal(null);
      setCategoriaNome('');
      setCategoriaDescricao('');
      await carregar();
    } catch (err) {
      setErroModal(err instanceof Error ? err.message : 'Não foi possível criar a pasta.');
    } finally {
      setSalvando(false);
    }
  }

  async function enviarArquivos() {
    if (!documentoAlvo || !arquivosNovos.length || salvando) return;
    setSalvando(true);
    setErroModal('');
    try {
      const result = await enviarArquivosContabeis(documentoAlvo.obrigacao_id, arquivosNovos);
      setArquivos(result.arquivos);
      setArquivosNovos([]);
      await carregar();
    } catch (err) {
      setErroModal(err instanceof Error ? err.message : 'Falha ao enviar os arquivos.');
    } finally {
      setSalvando(false);
    }
  }

  async function salvarNomeArquivo(file: ArquivoContabil) {
    if (!nomeArquivoEditado.trim()) { setErroModal('Informe o nome do arquivo.'); return; }
    try {
      const updated = await renomearArquivoContabil(file.id, nomeArquivoEditado.trim());
      setArquivos((current) => current.map((item) => item.id === file.id ? updated : item));
      setArquivoEditando(null);
      setNomeArquivoEditado('');
    } catch (err) { setErroModal(err instanceof Error ? err.message : 'Não foi possível renomear o arquivo.'); }
  }

  async function confirmarExclusaoArquivo() {
    if (!arquivoExcluir) return;
    try {
      await excluirArquivoContabil(arquivoExcluir.id, 'Exclusão solicitada pela interface Contábil');
      setArquivos((current) => current.filter((item) => item.id !== arquivoExcluir.id));
      setArquivoExcluir(null);
      await carregar();
    } catch (err) { setErroModal(err instanceof Error ? err.message : 'Não foi possível excluir o arquivo.'); }
  }

  async function confirmarInativacao(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!documentoAlvo) return;
    setSalvando(true);
    setErroModal('');
    try {
      await inativarDocumentoContabil(documentoAlvo.id, {
        competencia_fim: inputCompetencia(fimCompetencia),
        motivo,
        observacao: observacaoInativacao || undefined,
      });
      setModal(null);
      await carregar();
    } catch (err) {
      setErroModal(err instanceof Error ? err.message : 'Não foi possível inativar a documentação.');
    } finally { setSalvando(false); }
  }

  const selectedLabel = String(mes).padStart(2, '0') + '/' + ano;
  const categories = data?.categorias ?? [];
  const allCount = categories.reduce((sum, item) => sum + item.documentos_count, 0);

  return <div className="page contabil-page contabil-company-page">
    <Link className="contabil-back-link" to="/contabil/documentacao"><ArrowLeft size={14} />Voltar para empresas</Link>
    <div className="contabil-company-header">
      <div className="contabil-company-title"><span className="contabil-company-icon large"><Building2 size={21} /></span><div>
        <span className="eyebrow">DOCUMENTAÇÃO CONTÁBIL</span>
        <h2>{data?.empresa.razao_social || (loading ? 'Carregando empresa...' : 'Empresa')}</h2>
        <p>{data?.empresa.cnpj ? formatarCnpj(data.empresa.cnpj) : ''} <span>·</span> <b>{data?.empresa.regime_tributario || 'Regime não informado'}</b></p>
      </div></div>
      <button className="button secondary" onClick={() => void carregar()} disabled={loading}>Atualizar dados</button>
    </div>

    <div className="contabil-timeline">
      <div className="contabil-year-control"><button className="icon-button" onClick={() => setAno((current) => current - 1)} aria-label="Ano anterior">‹</button><strong>{ano}</strong><button className="icon-button" onClick={() => setAno((current) => current + 1)} aria-label="Próximo ano">›</button></div>
      <div className="contabil-month-grid">{MESES.map((name, index) => {
        const month = index + 1;
        const selected = mes === month;
        const period = competencia(ano, month);
        const statusMap = data?.competencias_ano?.find((item) => item.mes === month)?.status;
        const status = period > competenciaAtual() ? 'future' : statusMap === 'COMPLETA' ? 'complete' : statusMap === 'PARCIAL' ? 'partial' : statusMap === 'SEM_RECEBIMENTO' ? 'missing' : 'future';
        return <button key={name} className={'contabil-month-card' + (selected ? ' active' : '')} onClick={() => setMes(month)}>
          <strong>{name}</strong><i className={status} />
        </button>;
      })}</div>
      <div className="contabil-timeline-legend"><span><i className="complete" />Completa</span><span><i className="partial" />Competência atual pendente</span><span><i className="missing" />Competência anterior pendente</span><span><i className="future" />Futura</span></div>
    </div>

    <div className="contabil-folder-toolbar"><div><span className="eyebrow">DOCUMENTAÇÕES CADASTRADAS</span><h3>Pastas da empresa</h3></div><div className="actions"><button className="button secondary" onClick={() => { setCategoriaNome(''); setCategoriaDescricao(''); setErroModal(''); setModal('categoria'); }}><FolderPlus size={14} />Cadastrar pasta</button><button className="button primary" onClick={abrirNovoDocumento}><Plus size={14} />Cadastrar documentação</button></div></div>
    <div className="contabil-folder-grid">
      <button className={'contabil-folder-card all' + (pasta === null ? ' active' : '')} onClick={() => setPasta(null)}>
        <span className="contabil-folder-icon"><Folder size={19} /></span><strong>Tudo</strong><small>{allCount} documentações</small><span className="contabil-folder-state">{data?.resumo.pendentes ? data.resumo.pendentes + ' pendentes' : 'Visão geral'}</span>
      </button>
      {categories.map((category) => {
        const state = resumoPasta(category);
        return <button key={category.id} className={'contabil-folder-card' + (pasta === category.id ? ' active' : '')} onClick={() => setPasta(category.id)}>
          <span className="contabil-folder-icon"><Folder size={19} /></span><strong>{category.nome}</strong><small>{category.documentos_count} documentações</small><span className={'contabil-folder-state ' + state.className}>{state.label}</span>
        </button>;
      })}
    </div>

    <section className="panel contabil-documents-panel">
      <div className="contabil-documents-heading"><div><span className="eyebrow">COMPETÊNCIA SELECIONADA</span><h3>Documentos — {selectedLabel}</h3><small>{docsVisiveis.length} itens nesta visualização</small></div>
        <label className="contabil-search compact"><Search size={15} /><input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Pesquisar nesta pasta..." /></label>
      </div>
      {error && <div className="contabil-inline-error">{error}<button className="button secondary" onClick={() => void carregar()}>Tentar novamente</button></div>}
      {loading ? <div className="contabil-loading"><span className="spinner" />Carregando documentação...</div>
      : !docsVisiveis.length ? <div className="contabil-empty"><FileText size={28} /><strong>Nenhuma documentação nesta competência</strong><span>Cadastre uma documentação para iniciar o acompanhamento mensal.</span><button className="button secondary" onClick={abrirNovoDocumento}><Plus size={14} />Cadastrar documentação</button></div>
      : <div className="table-wrap"><table className="contabil-table contabil-doc-table">
        <thead><tr><th>Documento / Detalhes</th><th>Categoria</th><th>Status</th><th>Arquivos / Último upload</th><th>Ações</th></tr></thead>
        <tbody>{docsVisiveis.map((item) => <tr key={item.id} onDoubleClick={() => void abrirUpload(item)}>
          <td><div className="contabil-document-cell"><span className="contabil-file-icon"><FileText size={15} /></span><span><strong>{item.nome}</strong><small>{item.observacao || 'Sem informações complementares'}</small></span></div></td>
          <td><span className="contabil-category-tag">{item.categoria_nome}</span></td>
          <td><span className={'contabil-status-text ' + statusClasse(item.status)}><i />{statusTexto(item.status)}</span></td>
          <td><button className="contabil-file-summary" onClick={() => void abrirUpload(item)}><strong>{item.quantidade_arquivos} arquivo(s)</strong><small>{dataHora(item.ultimo_upload)}</small></button></td>
          <td><div className="actions"><button className="icon-button" title="Enviar e consultar arquivos" onClick={() => void abrirUpload(item)}><Upload size={14} /></button><button className="icon-button" title="Editar cadastro" onClick={() => abrirEdicao(item)}><Pencil size={14} /></button><button className="icon-button danger" title="Inativar documentação" onClick={() => { setDocumentoAlvo(item); setFimCompetencia(mesInput(competencia(ano, mes))); setMotivo(MOTIVOS[0]); setObservacaoInativacao(''); setErroModal(''); setModal('inativar'); }}><Trash2 size={14} /></button></div></td>
        </tr>)}</tbody>
      </table></div>}
    </section>

    {modal && <div className="contabil-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !salvando) setModal(null); }}>
      <section className={'contabil-form-modal' + (modal === 'upload' ? ' upload' : '')} role="dialog" aria-modal="true">
        <header className="contabil-modal-header"><div><span className="eyebrow">{modal === 'upload' ? 'RECEBIMENTO DE ARQUIVOS' : 'CONTROLE DE DOCUMENTAÇÃO'}</span><h3>{modal === 'documento' ? (documentoAlvo ? 'Editar documentação' : 'Nova documentação') : modal === 'upload' ? 'Arquivos recebidos' : modal === 'categoria' ? 'Cadastrar pasta' : 'Inativar documentação'}</h3><p>{documentoAlvo?.nome || data?.empresa.razao_social}</p></div><button className="icon-button" onClick={() => setModal(null)} aria-label="Fechar"><X size={17} /></button></header>
        {erroModal && <div className="contabil-inline-error">{erroModal}</div>}

        {modal === 'documento' && <form onSubmit={(event) => void salvarDocumento(event)}>
          <div className="contabil-form-grid"><label>Nome da documentação *<input value={formNome} onChange={(event) => setFormNome(event.target.value)} required placeholder="Ex.: Banco Sicoob CC 159.522-9" /></label>
            <label>Categoria *<select value={formCategoria} onChange={(event) => setFormCategoria(event.target.value)} required><option value="">Selecione</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            {!documentoAlvo && <label>Mês e ano de início *<input type="month" value={formInicio} onChange={(event) => setFormInicio(event.target.value)} required /></label>}
            <label className="span-2">Observação<textarea value={formObs} onChange={(event) => setFormObs(event.target.value)} rows={3} placeholder="Informações complementares (opcional)" /></label>
          </div>
          {documentoAlvo && <div className="contabil-form-note">A competência inicial e o histórico de recebimentos serão preservados nesta edição.</div>}
          <div className="contabil-modal-footer"><span>O cadastro gera obrigações mensais a partir do início.</span><div><button type="button" className="button secondary" onClick={() => setModal(null)}>Cancelar</button><button className="button primary" disabled={salvando}>{salvando ? 'Salvando...' : 'Salvar'}</button></div></div>
        </form>}

        {modal === 'categoria' && <form onSubmit={(event) => void salvarCategoria(event)}>
          <div className="contabil-form-grid"><label>Nome da pasta *<input value={categoriaNome} onChange={(event) => setCategoriaNome(event.target.value)} required placeholder="Ex.: Folha de pagamento" /></label><label className="span-2">Descrição<textarea rows={3} value={categoriaDescricao} onChange={(event) => setCategoriaDescricao(event.target.value)} placeholder="Descrição opcional" /></label></div>
          <div className="contabil-modal-footer"><span>Pastas com histórico não poderão ser excluídas definitivamente.</span><div><button type="button" className="button secondary" onClick={() => setModal(null)}>Cancelar</button><button className="button primary" disabled={salvando}>{salvando ? 'Salvando...' : 'Criar pasta'}</button></div></div>
        </form>}

        {modal === 'inativar' && <form onSubmit={(event) => void confirmarInativacao(event)}>
          <div className="contabil-warning-box"><CircleAlert size={17} /><span>A documentação deixará de gerar novas obrigações após a competência final. O histórico e os arquivos anteriores serão preservados.</span></div>
          <div className="contabil-form-grid"><label>Última competência ativa *<input type="month" value={fimCompetencia} onChange={(event) => setFimCompetencia(event.target.value)} required /></label><label>Motivo *<select value={motivo} onChange={(event) => setMotivo(event.target.value)}>{MOTIVOS.map((item) => <option key={item}>{item}</option>)}</select></label><label className="span-2">Observação<textarea rows={3} value={observacaoInativacao} onChange={(event) => setObservacaoInativacao(event.target.value)} placeholder="Informações adicionais (opcional)" /></label></div>
          <div className="contabil-modal-footer"><span>O cadastro permanecerá disponível para consulta.</span><div><button type="button" className="button secondary" onClick={() => setModal(null)}>Cancelar</button><button className="button danger" disabled={salvando}>{salvando ? 'Inativando...' : 'Inativar'}</button></div></div>
        </form>}

        {modal === 'upload' && <div className="contabil-upload-content">
          <div className={'contabil-dropzone' + (dragAtivo ? ' active' : '')} onDragOver={(event) => { event.preventDefault(); setDragAtivo(true); }} onDragLeave={() => setDragAtivo(false)} onDrop={dropFiles}>
            <Upload size={25} /><strong>Arraste os arquivos aqui ou clique para selecionar</strong><span>PDF, JPG, PNG ou XLSX · máximo de 25 MB por arquivo</span>
            <label className="button secondary">Selecionar arquivos<input type="file" accept=".pdf,.jpg,.jpeg,.png,.xlsx" multiple hidden onChange={(event) => { if (event.target.files) validarArquivos(Array.from(event.target.files)); event.target.value = ''; }} /></label>
          </div>
          {arquivosNovos.length > 0 && <div className="contabil-pending-files"><strong>Arquivos prontos para envio ({arquivosNovos.length})</strong>{arquivosNovos.map((file, index) => <div key={file.name + index}><FileText size={14} /><span>{file.name}<small>{tamanhoArquivo(file.size)}</small></span><button className="icon-button" onClick={() => setArquivosNovos((current) => current.filter((_, i) => i !== index))}><X size={13} /></button></div>)}<button className="button primary" onClick={() => void enviarArquivos()} disabled={salvando}>{salvando ? 'Enviando...' : 'Enviar arquivos'}</button></div>}
          <div className="contabil-upload-list"><div className="contabil-subheading"><strong>Arquivos carregados</strong><small>{arquivos.length} arquivos</small></div>
            {!arquivos.length ? <div className="contabil-mini-empty">Ainda não há arquivos recebidos nesta competência.</div> : arquivos.map((file) => <div className="contabil-upload-file" key={file.id}>
              <span className="contabil-file-icon"><FileText size={15} /></span>
              <span className="contabil-upload-file-name">{arquivoEditando === file.id ? <input value={nomeArquivoEditado} onChange={(event) => setNomeArquivoEditado(event.target.value)} /> : <strong>{file.nome_original}</strong>}<small>{tamanhoArquivo(file.tamanho)} · {dataHora(file.enviado_em)} · {file.enviado_por_nome || 'Usuário'}</small></span>
              {arquivoEditando === file.id ? <><button className="button secondary small" onClick={() => void salvarNomeArquivo(file)}>Salvar</button><button className="icon-button" onClick={() => setArquivoEditando(null)}><X size={13} /></button></> : <><button className="icon-button" title="Baixar" onClick={() => void baixarArquivoContabil(file.id, file.nome_original)}><Download size={14} /></button><button className="icon-button" title="Renomear" onClick={() => { setArquivoEditando(file.id); setNomeArquivoEditado(file.nome_original); }}><Pencil size={14} /></button><button className="icon-button danger" title="Excluir" onClick={() => setArquivoExcluir(file)}><Trash2 size={14} /></button></>}
            </div>)}
          </div>
          {arquivoExcluir && <div className="contabil-delete-confirm"><span>Excluir <strong>{arquivoExcluir.nome_original}</strong>? O registro será preservado no histórico.</span><button className="button secondary" onClick={() => setArquivoExcluir(null)}>Cancelar</button><button className="button danger" onClick={() => void confirmarExclusaoArquivo()}>Confirmar exclusão</button></div>}
          <div className="contabil-modal-footer"><span>Envios e alterações ficam vinculados ao usuário e à competência.</span><div><button className="button secondary" onClick={() => { setModal(null); void carregar(); }}>Fechar</button></div></div>
        </div>}
      </section>
    </div>}
  </div>;
}
