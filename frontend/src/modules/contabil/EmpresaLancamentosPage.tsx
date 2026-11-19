import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  ArrowLeft, Building2, Check, CheckCheck, ChevronLeft, ChevronRight,
  CircleAlert, Clock3, FileText, Info, Pencil, Plus, Search, Trash2, X, RefreshCw,
} from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  atualizarDocumentoContabil,
  reativarDocumentoContabil,
  reativarMovimentacaoInterna,
  atualizarMovimentacaoCompetencia,
  criarMovimentacaoInterna,
  editarMovimentacaoInterna,
  inativarDocumentoContabil,
  inativarMovimentacaoInterna,
  obterDocumentacaoEmpresa,
  obterPainelEmpresaLancamentos,
} from './contabilApi';
import type { EmpresaDocumentacaoContabilResponse, EmpresaLancamentosDetalhe, MovimentacaoCompetencia } from './types';
import './contabil.css';

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const MOTIVOS_INATIVACAO = ['Conta encerrada', 'Contrato encerrado', 'Empresa deixou de utilizar o serviço', 'Substituição por outra movimentação', 'Outros'];

function competenciaAnterior() {
  const now = new Date();
  const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return prev.getFullYear() * 100 + prev.getMonth() + 1;
}
function lerCompetencia(value: string | null) {
  if (!value) return competenciaAnterior();
  const match = value.match(/^(\d{4})-(\d{2})$/);
  if (!match) return competenciaAnterior();
  const result = Number(match[1]) * 100 + Number(match[2]);
  return Number(match[2]) >= 1 && Number(match[2]) <= 12 ? result : competenciaAnterior();
}
function competenciaInput(value: number) {
  return `${Math.floor(value / 100)}-${String(value % 100).padStart(2, '0')}`;
}
function formatarCnpj(value: string) {
  const digits = (value || '').replace(/\D/g, '');
  return digits.length === 14 ? digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5') : value;
}
function statusMes(item: MovimentacaoCompetencia) {
  if (!item.ativa) return { label: 'Inativo', tone: 'neutral' };
  if (item.origem === 'LANCAMENTOS_CONFERENCIAS' && !item.recebido) return { label: 'Não recebido', tone: 'danger' };
  if (item.origem === 'DOCUMENTACAO' && !item.documento_disponivel) {
    return item.nao_recebido_confirmado
      ? { label: 'Não recebido', tone: 'danger' }
      : { label: 'Aguardando documento', tone: 'warning' };
  }
  if (item.concluida || item.lancado && item.conferido) return { label: 'Conferido', tone: 'success' };
  if (item.lancado) return { label: 'Lançado', tone: 'info' };
  return { label: 'Pendente', tone: 'warning' };
}

export function EmpresaLancamentosPage() {
  const { id } = useParams();
  const empresaId = Number(id);
  const [searchParams, setSearchParams] = useSearchParams();
  const competencia = lerCompetencia(searchParams.get('competencia'));
  const [data, setData] = useState<EmpresaLancamentosDetalhe | null>(null);
  const [documentacao, setDocumentacao] = useState<EmpresaDocumentacaoContabilResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [busca, setBusca] = useState('');
  const [filtroCategoria, setFiltroCategoria] = useState('TODAS');
  const [filtroStatus, setFiltroStatus] = useState('TODOS');
  const [formOpen, setFormOpen] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [editingItem, setEditingItem] = useState<MovimentacaoCompetencia | null>(null);
  const [nome, setNome] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [competenciaInicio, setCompetenciaInicio] = useState(competenciaInput(competencia));
  const [formError, setFormError] = useState('');
  const [savingForm, setSavingForm] = useState(false);
  const [inactivationItem, setInactivationItem] = useState<MovimentacaoCompetencia | null>(null);
  const [inactivationCompetence, setInactivationCompetence] = useState(competenciaInput(competencia));
  const [inactivationReason, setInactivationReason] = useState(MOTIVOS_INATIVACAO[0]);
  const [inactivationNote, setInactivationNote] = useState('');
  const [inactivationError, setInactivationError] = useState('');
  const [savingInactivation, setSavingInactivation] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaId) return;
    setLoading(true);
    setError('');
    try {
      setData(await obterPainelEmpresaLancamentos(empresaId, competencia));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar as movimentações.');
    } finally {
      setLoading(false);
    }
  }, [empresaId, competencia]);

  const carregarDocumentacao = useCallback(async () => {
    if (!empresaId) return;
    try {
      setDocumentacao(await obterDocumentacaoEmpresa(empresaId, competencia));
    } catch {
      // O painel continua utilizável mesmo se a consulta auxiliar do calendário falhar.
      setDocumentacao(null);
    }
  }, [empresaId, competencia]);

  useEffect(() => { void carregar(); }, [carregar]);
  useEffect(() => { void carregarDocumentacao(); }, [carregarDocumentacao]);

  function selecionarCompetencia(value: string) {
    const next = new URLSearchParams(searchParams);
    next.set('competencia', value);
    setSearchParams(next);
  }

  async function atualizar(item: MovimentacaoCompetencia, changes: Parameters<typeof atualizarMovimentacaoCompetencia>[2]) {
    setSavingId(item.movimentacao_id);
    setError('');
    try {
      await atualizarMovimentacaoCompetencia(item.movimentacao_id, competencia, changes);
      await carregar();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível atualizar a movimentação.');
    } finally {
      setSavingId(null);
    }
  }

  function abrirNovaMovimentacao() {
    setFormMode('create');
    setEditingItem(null);
    setNome('');
    setCategoriaId('');
    setCompetenciaInicio(competenciaInput(competencia));
    setFormError('');
    setFormOpen(true);
  }

  function abrirEdicao(item: MovimentacaoCompetencia) {
    setFormMode('edit');
    setEditingItem(item);
    setNome(item.nome);
    setCategoriaId(item.categoria_id ? String(item.categoria_id) : '');
    setCompetenciaInicio(competenciaInput(competencia));
    setFormError('');
    setFormOpen(true);
  }

  async function salvarFormulario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!nome.trim()) { setFormError('Informe o nome da movimentação.'); return; }
    if (!categoriaId) { setFormError('Selecione uma categoria.'); return; }
    setSavingForm(true);
    setFormError('');
    try {
      if (formMode === 'edit' && editingItem) {
        const categoria = Number(categoriaId);
        if (editingItem.origem === 'DOCUMENTACAO') {
          if (!editingItem.documento_origem_id) throw new Error('Não foi possível identificar o documento de origem.');
          const dadosDocumento = documentacao ?? await obterDocumentacaoEmpresa(empresaId, competencia);
          const documentoAtual = dadosDocumento.documentos.find(doc => doc.id === editingItem.documento_origem_id);
          if (!documentoAtual) throw new Error('Documento de origem não encontrado na competência selecionada.');
          await atualizarDocumentoContabil(editingItem.documento_origem_id, {
            nome: nome.trim(), categoria_id: categoria, observacao: documentoAtual.observacao ?? undefined,
          });
        } else {
          await editarMovimentacaoInterna(editingItem.movimentacao_id, { nome: nome.trim(), categoria_id: categoria });
        }
      } else {
        const [ano, mes] = competenciaInicio.split('-').map(Number);
        if (!ano || mes < 1 || mes > 12) throw new Error('Informe uma competência inicial válida.');
        await criarMovimentacaoInterna(empresaId, {
          nome: nome.trim(), categoria_id: Number(categoriaId), competencia_inicio: ano * 100 + mes,
        });
      }
      setFormOpen(false);
      setEditingItem(null);
      await Promise.all([carregar(), carregarDocumentacao()]);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Não foi possível salvar a movimentação.');
    } finally {
      setSavingForm(false);
    }
  }

  async function ativarMovimentacao(item: MovimentacaoCompetencia) {
    setSavingId(item.movimentacao_id);
    setError('');
    try {
      if (item.origem === 'DOCUMENTACAO') {
        if (!item.documento_origem_id) throw new Error('Não foi possível identificar o documento de origem.');
        await reativarDocumentoContabil(item.documento_origem_id);
      } else {
        await reativarMovimentacaoInterna(item.movimentacao_id);
      }
      await Promise.all([carregar(), carregarDocumentacao()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível ativar a movimentação.');
    } finally {
      setSavingId(null);
    }
  }

  function abrirInativacao(item: MovimentacaoCompetencia) {
    setInactivationItem(item);
    setInactivationCompetence(competenciaInput(competencia));
    setInactivationReason(MOTIVOS_INATIVACAO[0]);
    setInactivationNote('');
    setInactivationError('');
  }

  async function confirmarInativacao(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inactivationItem) return;
    const [ano, mes] = inactivationCompetence.split('-').map(Number);
    if (!ano || mes < 1 || mes > 12) {
      setInactivationError('Informe uma última competência ativa válida.');
      return;
    }
    const competenciaFim = ano * 100 + mes;
    const motivoCompleto = inactivationNote.trim()
      ? `${inactivationReason} — ${inactivationNote.trim()}`
      : inactivationReason;
    setSavingInactivation(true);
    setSavingId(inactivationItem.movimentacao_id);
    setInactivationError('');
    setError('');
    try {
      if (inactivationItem.origem === 'DOCUMENTACAO') {
        if (!inactivationItem.documento_origem_id) throw new Error('Não foi possível identificar o documento de origem.');
        await inativarDocumentoContabil(inactivationItem.documento_origem_id, {
          competencia_fim: competenciaFim,
          motivo: inactivationReason,
          observacao: inactivationNote.trim() || undefined,
        });
      } else {
        await inativarMovimentacaoInterna(inactivationItem.movimentacao_id, competenciaFim, motivoCompleto);
      }
      setInactivationItem(null);
      await Promise.all([carregar(), carregarDocumentacao()]);
    } catch (err) {
      setInactivationError(err instanceof Error ? err.message : 'Não foi possível inativar a movimentação.');
    } finally {
      setSavingId(null);
      setSavingInactivation(false);
    }
  }

  const empresa = data?.empresa;
  const categoriasOrdenadas = useMemo(() => {
    // Ordem fixa do catálogo de Lançamentos e Conferências, conforme a referência aprovada.
    const ordemCategorias = [
      'Contábil',
      'Departamento Pessoal',
      'Extratos Bancários',
      'Aplicações Financeiras',
      'Financiamentos / Empréstimos',
      'Consórcios',
      'Parcelamentos',
      'Administradoras de Cartões',
    ];
    const posicao = new Map(ordemCategorias.map((nome, index) => [nome, index]));
    return [...(data?.categorias ?? [])].sort((a, b) =>
      (posicao.get(a.nome) ?? 9999) - (posicao.get(b.nome) ?? 9999)
      || a.nome.localeCompare(b.nome, 'pt-BR'),
    );
  }, [data?.categorias]);

  const grupos = useMemo(() => {
    const map = new Map<string, MovimentacaoCompetencia[]>();
    const term = busca.trim().toLocaleLowerCase('pt-BR');
    const normalizarCategoria = (nome: string) =>
      nome.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLocaleLowerCase('pt-BR');
    // Usa exatamente a sequência do seletor de categoria como fonte da ordem dos grupos.
    const ordem = new Map(categoriasOrdenadas.map((cat, index) => [normalizarCategoria(cat.nome), index]));
    for (const item of data?.movimentacoes ?? []) {
      const categoria = item.categoria_nome || 'Sem categoria';
      if (filtroCategoria !== 'TODAS' && categoria !== filtroCategoria) continue;
      const status = statusMes(item);
      const statusKey = status.label === 'Conferido' ? 'CONFERIDO'
        : status.label === 'Lançado' ? 'LANCADO'
          : status.label === 'Aguardando documento' ? 'AGUARDANDO'
            : status.label === 'Não recebido' ? 'NAO_RECEBIDO'
              : 'PENDENTE';
      if (filtroStatus !== 'TODOS' && filtroStatus !== statusKey) continue;
      if (term && !`${item.nome} ${categoria}`.toLocaleLowerCase('pt-BR').includes(term)) continue;
      map.set(categoria, [...(map.get(categoria) ?? []), item]);
    }
    return [...map.entries()]
      .map(([categoria, items]) => [categoria, items.sort((a, b) => b.movimentacao_id - a.movimentacao_id)] as const)
      .sort(([a], [b]) =>
        (ordem.get(normalizarCategoria(a)) ?? 9999) - (ordem.get(normalizarCategoria(b)) ?? 9999)
        || a.localeCompare(b, 'pt-BR'),
      );
  }, [data?.movimentacoes, categoriasOrdenadas, busca, filtroCategoria, filtroStatus]);

  const movimentos = data?.movimentacoes ?? [];
  // Somente a inativação global exclui a movimentação do indicador mensal.
  // A conferência não participa da regra de conclusão do mês.
  const movimentosAtivos = movimentos.filter(item => item.ativa !== false);
  const documentosAtivos = movimentosAtivos.filter(item => item.origem === 'DOCUMENTACAO').length;
  const indisponiveis = movimentosAtivos.filter(item => item.origem === 'DOCUMENTACAO' && !item.documento_disponivel).length;
  const pendentesLancamento = movimentosAtivos.filter(item => !item.lancado && (item.origem === 'DOCUMENTACAO' ? item.documento_disponivel : item.recebido)).length;
  const lancados = movimentosAtivos.filter(item => item.lancado && !item.conferido).length;
  const conferidos = movimentosAtivos.filter(item => item.lancado && item.conferido).length;
  const statusAno = new Map((data?.competencias_ano ?? documentacao?.competencias_ano ?? []).map(item => [item.mes, item.status]));

  return <div className="page contabil-page lc-launch-page">
    <div className="lc-company-detail-heading">
      <div className="lc-company-backline">
        <Link to={`/contabil/lancamentos-conferencias?competencia=${competenciaInput(competencia)}`} className="contabil-back-link"><ArrowLeft size={15}/> Voltar para empresas</Link>
      </div>
      <div className="lc-company-head-main">
        <div className="lc-company-identity">
          <span className="contabil-company-icon large"><Building2 size={21}/></span>
          <div>
            <span className="eyebrow">DOCUMENTAÇÃO CONTÁBIL · LANÇAMENTOS E CONFERÊNCIAS</span>
            <h2>{empresa?.razao_social || 'Movimentações da empresa'}</h2>
            {empresa && <p>{formatarCnpj(empresa.cnpj)} <span>·</span> <strong>{empresa.regime_tributario || 'Regime não informado'}</strong></p>}
          </div>
        </div>
        <button type="button" className="lc-company-info-button" onClick={() => setInfoOpen(true)}><Info size={15}/> Informações da empresa</button>
      </div>
    </div>

    <section className="lc-month-selector" aria-label="Calendário anual de competências">
      <div className="lc-month-year">
        <button type="button" aria-label="Ano anterior" onClick={() => selecionarCompetencia(competenciaInput(competencia - 100))}><ChevronLeft size={16}/></button>
        <strong>{Math.floor(competencia / 100)}</strong>
        <button type="button" aria-label="Próximo ano" onClick={() => selecionarCompetencia(competenciaInput(competencia + 100))}><ChevronRight size={16}/></button>
      </div>
      <div className="lc-month-grid">
        {MESES.map((mes, index) => {
          const mesNumber = index + 1;
          const value = Math.floor(competencia / 100) * 100 + mesNumber;
          // Todos os meses usam o status anual calculado pelo backend com a
          // mesma regra de lançamentos ativos; não misturar com o status documental.
          const status = statusAno.get(mesNumber);
          // A competência em andamento é sempre o mês civil anterior.
          // Meses posteriores a ela ficam neutros (cinza), mesmo que a API
          // retorne SEM_RECEBIMENTO por já existirem obrigações futuras cadastradas.
          const isFutureCompetence = value > competenciaAnterior();
          const dotClass = isFutureCompetence ? 'future'
            : status === 'COMPLETA' ? 'complete'
              : status === 'PARCIAL' ? 'partial'
                : status === 'SEM_RECEBIMENTO' ? 'missing' : 'future';
          return <button type="button" key={mes} className={`lc-month-pill ${value === competencia ? 'active' : ''}`} aria-pressed={value === competencia}
            onClick={() => selecionarCompetencia(competenciaInput(value))}>
            <strong>{mes}</strong><i className={dotClass}/>
          </button>;
        })}
      </div>
    </section>

    {infoOpen && <div className="lc-info-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setInfoOpen(false); }}>
      <section className="lc-info-card" role="dialog" aria-modal="true" aria-labelledby="lc-info-title">
        <header><h3 id="lc-info-title">Informações da empresa</h3><button type="button" aria-label="Fechar" onClick={() => setInfoOpen(false)}><X size={18}/></button></header>
        <dl>
          <div><dt>Razão social</dt><dd>{empresa?.razao_social || '—'}</dd></div>
          <div><dt>Nome fantasia</dt><dd>{empresa?.nome_fantasia || '—'}</dd></div>
          <div><dt>CNPJ</dt><dd>{empresa ? formatarCnpj(empresa.cnpj) : '—'}</dd></div>
          <div><dt>Regime tributário</dt><dd>{empresa?.regime_tributario || 'Não informado'}</dd></div>
          <div><dt>Responsável</dt><dd>{empresa?.responsavel_nome || 'Não atribuído'}</dd></div>
        </dl>
        <footer><button type="button" className="button secondary" onClick={() => setInfoOpen(false)}>Fechar</button></footer>
      </section>
    </div>}

    {error && <div className="contabil-inline-error" role="alert"><CircleAlert size={16}/>{error}</div>}
    {loading && !data ? <div className="contabil-loading"><span className="spinner"/>Carregando movimentações...</div> : data && <>
      <section className="lc-company-metrics" aria-label="Resumo da competência">
        <article className="lc-metric-card blue"><FileText/><div><strong>{documentosAtivos}</strong><span>Documentações ativas</span><small>no mês selecionado</small></div></article>
        <article className="lc-metric-card red"><CircleAlert/><div><strong>{indisponiveis}</strong><span>Não disponíveis</span><small>sem documento</small></div></article>
        <article className="lc-metric-card orange"><Clock3/><div><strong>{pendentesLancamento}</strong><span>Pendentes de lançamento</span><small>aguardando execução</small></div></article>
        <article className="lc-metric-card purple"><CheckCheck/><div><strong>{lancados}</strong><span>Lançados</span><small>aguardando conferência</small></div></article>
        <article className="lc-metric-card green"><Check/><div><strong>{conferidos}</strong><span>Conferidos</span><small>mês concluído</small></div></article>
      </section>

      <div className="lc-movement-toolbar">
        <label className="lc-movement-search"><Search size={16}/><input value={busca} onChange={event => setBusca(event.target.value)} placeholder="Buscar por nome, conta, categoria..." aria-label="Buscar movimentações"/></label>
        <select value={filtroCategoria} onChange={event => setFiltroCategoria(event.target.value)} aria-label="Filtrar por categoria">
          <option value="TODAS">Todas as categorias</option>
          {categoriasOrdenadas.map(cat => <option key={cat.id} value={cat.nome}>{cat.nome}</option>)}
        </select>
        <select value={filtroStatus} onChange={event => setFiltroStatus(event.target.value)} aria-label="Filtrar por status">
          <option value="TODOS">Todos os status</option>
          <option value="NAO_RECEBIDO">Não recebido</option>
          <option value="PENDENTE">Pendente</option>
          <option value="AGUARDANDO">Aguardando documento</option>
          <option value="LANCADO">Lançado</option>
          <option value="CONFERIDO">Conferido</option>
        </select>
        <button type="button" className="button primary" onClick={abrirNovaMovimentacao}><Plus size={16}/> Nova movimentação</button>
      </div>

      <section className="lc-movement-board" aria-label="Movimentações da competência">
        <div className="lc-movement-column-head">
          <span>Movimentação</span><span>Categoria</span><span>Situação do documento</span><span>Lançado</span><span>Conferido</span><span>Status do mês</span><span>Ações</span>
        </div>
        {grupos.length === 0 ? <div className="contabil-empty"><FileText size={28}/><strong>Nenhuma movimentação cadastrada</strong><span>Cadastre uma movimentação interna ou configure documentos recorrentes na Documentação Contábil.</span></div> : grupos.map(([grupo, items]) => <div className="lc-movement-category-group" key={grupo}>
          <header><strong>{grupo} ({items.length})</strong></header>
          {items.map(item => {
            const status = statusMes(item);
            const isInternal = item.origem === 'LANCAMENTOS_CONFERENCIAS';
            const disabled = savingId === item.movimentacao_id || !item.ativa;
            const recebimentoOk = isInternal ? item.recebido : item.documento_disponivel;
            return <article className={`lc-movement-row ${!item.ativa ? 'is-archived' : ''}`} key={item.movimentacao_id}>
              <div className="lc-movement-title-cell">
                <span className="lc-movement-file-icon"><FileText size={16}/></span>
                <div><strong>{item.nome}</strong><small>{!item.ativa ? (isInternal ? 'Cadastro inativo — reative o cadastro da movimentação' : 'Documento de origem inativo — reative na Documentação Contábil') : isInternal ? 'Movimentação interna' : item.documento_disponivel ? `${item.quantidade_arquivos} arquivo(s) recebido(s)` : item.nao_recebido_confirmado ? 'Documento não recebido' : 'Aguardando documento'}</small></div>
              </div>
              <div className="lc-movement-category-cell"><span className="lc-category-pill">{item.categoria_nome || 'Sem categoria'}</span></div>
              <div className="lc-movement-receipt-cell">
                {isInternal ? <button type="button" className={`lc-receipt-toggle ${item.recebido ? 'received' : 'not-received'}`} disabled={disabled || item.lancado || item.conferido}
                    onClick={() => void atualizar(item, { recebido: !item.recebido })}>
                  <i>{item.recebido ? <Check size={11}/> : <X size={11}/>}</i><span>{item.recebido ? 'Recebido' : 'Não recebido'}</span>
                </button> : <span className={`lc-receipt-static ${item.documento_disponivel ? 'received' : item.nao_recebido_confirmado ? 'not-received' : 'waiting'}`}>
                  <i>{item.documento_disponivel ? <Check size={11}/> : <CircleAlert size={11}/>}</i>{item.documento_disponivel ? 'Recebido' : item.nao_recebido_confirmado ? 'Não recebido' : 'Aguardando documento'}
                </span>}
              </div>
              <label className="lc-row-check"><input type="checkbox" checked={item.lancado} disabled={disabled || !recebimentoOk} onChange={event => void atualizar(item, { lancado: event.target.checked })}/><span>Lançado</span></label>
              <label className="lc-row-check"><input type="checkbox" checked={item.conferido} disabled={disabled || !recebimentoOk || !item.lancado} onChange={event => void atualizar(item, { conferido: event.target.checked })}/><span>Conferido</span></label>
              <div className="lc-row-status">
                <span className={`lc-status-pill ${status.tone}`}><i/>{status.label}</span>
              </div>
              <div className="lc-row-actions">
                {!item.ativa && <button type="button" className="lc-activate-action" title={`Ativar movimentação ${item.nome}`} disabled={savingId === item.movimentacao_id} onClick={() => void ativarMovimentacao(item)}>{savingId === item.movimentacao_id ? 'Ativando...' : 'Ativar'}</button>}
                <button type="button" className="lc-icon-action" title="Editar" aria-label={`Editar ${item.nome}`} disabled={disabled} onClick={() => abrirEdicao(item)}><Pencil size={15}/></button>
                <button type="button" className="lc-icon-action danger" title="Inativar" aria-label={`Inativar ${item.nome}`} disabled={disabled} onClick={() => abrirInativacao(item)}><Trash2 size={15}/></button>
                {savingId === item.movimentacao_id && <RefreshCw size={13} className="contabil-saving-icon"/>}
              </div>
            </article>;
          })}
        </div>)}
      </section>
    </>}

    {formOpen && <div className="lc-drawer-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setFormOpen(false); }}>
      <aside className="lc-movement-drawer" role="dialog" aria-modal="true" aria-labelledby="lc-drawer-title">
        <header className="lc-drawer-header">
          <span className="lc-drawer-plus"><Plus size={20}/></span>
          <div><h3 id="lc-drawer-title">{formMode === 'create' ? 'Nova movimentação' : 'Editar movimentação'}</h3><p>{formMode === 'create' ? 'Cadastrar uma nova movimentação para controle de lançamentos e conferências.' : 'Atualize o nome e a categoria deste item.'}</p></div>
          <button type="button" aria-label="Fechar formulário" onClick={() => setFormOpen(false)}><X size={18}/></button>
        </header>
        <form className="lc-drawer-form" onSubmit={salvarFormulario}>
          <label>Nome da movimentação <b>*</b><input value={nome} onChange={event => setNome(event.target.value)} placeholder="Ex.: Banco Itaú CC 12345-6" required maxLength={200}/></label>
          <label>Categoria <b>*</b><select value={categoriaId} onChange={event => setCategoriaId(event.target.value)} required>
            <option value="">Selecione uma categoria</option>
            {categoriasOrdenadas.map(cat => <option key={cat.id} value={cat.id}>{cat.nome}</option>)}
          </select></label>
          {formMode === 'create' && <label>Mês de início <b>*</b><input type="month" value={competenciaInicio} onChange={event => setCompetenciaInicio(event.target.value)} required/></label>}
          {formError && <p className="lc-drawer-error" role="alert">{formError}</p>}
          <footer><button type="button" className="button secondary" onClick={() => setFormOpen(false)}>Cancelar</button><button type="submit" className="button primary" disabled={savingForm}>{savingForm ? 'Salvando...' : formMode === 'create' ? 'Salvar movimentação' : 'Salvar alterações'}</button></footer>
        </form>
      </aside>
    </div>}

    {inactivationItem && <div className="contabil-modal-backdrop" role="presentation"
      onMouseDown={event => { if (event.target === event.currentTarget && !savingInactivation) setInactivationItem(null); }}>
      <section className="contabil-form-modal" role="dialog" aria-modal="true" aria-labelledby="lc-inactivation-title">
        <header className="contabil-modal-header">
          <div>
            <span className="eyebrow">CONTROLE DE LANÇAMENTOS E CONFERÊNCIAS</span>
            <h3 id="lc-inactivation-title">Inativar movimentação</h3>
            <p>{inactivationItem.nome}</p>
          </div>
          <button type="button" className="icon-button" onClick={() => setInactivationItem(null)} disabled={savingInactivation} aria-label="Fechar"><X size={17}/></button>
        </header>
        <form onSubmit={confirmarInativacao}>
          <div className="contabil-upload-content">
            <div className="contabil-warning-box">
              <CircleAlert size={17}/>
              <span>A movimentação deixará de gerar competências após a última competência ativa informada. Os lançamentos, conferências e histórico anteriores serão preservados.</span>
            </div>
            <div className="contabil-form-grid">
              <label>Última competência ativa *<input type="month" min="1900-01" value={inactivationCompetence}
                onChange={event => setInactivationCompetence(event.target.value)} required /></label>
              <label>Motivo *<select value={inactivationReason} onChange={event => setInactivationReason(event.target.value)}>
                {MOTIVOS_INATIVACAO.map(item => <option key={item}>{item}</option>)}
              </select></label>
              <label className="span-2">Observação<textarea rows={3} value={inactivationNote}
                onChange={event => setInactivationNote(event.target.value)} placeholder="Informações adicionais (opcional)"/></label>
            </div>
            {inactivationError && <div className="contabil-inline-error" role="alert">{inactivationError}</div>}
            <div className="contabil-modal-footer">
              <span>A movimentação permanecerá disponível para consulta.</span>
              <div>
                <button type="button" className="button secondary" onClick={() => setInactivationItem(null)} disabled={savingInactivation}>Cancelar</button>
                <button type="submit" className="button danger" disabled={savingInactivation}>{savingInactivation ? 'Inativando...' : 'Confirmar inativação'}</button>
              </div>
            </div>
          </div>
        </form>
      </section>
    </div>}
  </div>;
}
