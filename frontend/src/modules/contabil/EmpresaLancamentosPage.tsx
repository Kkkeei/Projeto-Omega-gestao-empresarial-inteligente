import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { ArrowLeft, CalendarDays, CircleAlert, FileCheck2, FileText, Plus, RefreshCw } from 'lucide-react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { atualizarMovimentacaoCompetencia, criarMovimentacaoInterna, inativarMovimentacaoInterna, obterPainelEmpresaLancamentos } from './contabilApi';
import type { EmpresaLancamentosDetalhe, MovimentacaoCompetencia } from './types';
import './contabil.css';

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
function competenciaInput(value: number) { return `${Math.floor(value / 100)}-${String(value % 100).padStart(2, '0')}`; }
function deslocarCompetencia(value: number, delta: number) {
  const data = new Date(Math.floor(value / 100), (value % 100) - 1 + delta, 1);
  return data.getFullYear() * 100 + data.getMonth() + 1;
}

function formatarCnpj(value: string) {
  const digits = (value || '').replace(/\D/g, '');
  return digits.length === 14 ? digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5') : value;
}

export function EmpresaLancamentosPage() {
  const { id } = useParams();
  const empresaId = Number(id);
  const [searchParams, setSearchParams] = useSearchParams();
  const competencia = lerCompetencia(searchParams.get('competencia'));
  const [data, setData] = useState<EmpresaLancamentosDetalhe | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [nome, setNome] = useState('');
  const [categoriaId, setCategoriaId] = useState('');
  const [competenciaInicio, setCompetenciaInicio] = useState(competenciaInput(competencia));
  const [formError, setFormError] = useState('');
  const [savingNew, setSavingNew] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaId) return;
    setLoading(true); setError('');
    try { setData(await obterPainelEmpresaLancamentos(empresaId, competencia)); }
    catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível carregar as movimentações.'); }
    finally { setLoading(false); }
  }, [empresaId, competencia]);
  useEffect(() => { void carregar(); }, [carregar]);

  function selecionarCompetencia(value: string) {
    if (!value) return;
    const next = new URLSearchParams(searchParams);
    next.set('competencia', value);
    setSearchParams(next);
  }

  async function atualizar(item: MovimentacaoCompetencia, changes: Parameters<typeof atualizarMovimentacaoCompetencia>[2]) {
    setSavingId(item.movimentacao_id); setError('');
    try { await atualizarMovimentacaoCompetencia(item.movimentacao_id, competencia, changes); await carregar(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível atualizar a movimentação.'); }
    finally { setSavingId(null); }
  }

  async function marcarNaoAplicavel(item: MovimentacaoCompetencia) {
    const justificativa = window.prompt('Informe a justificativa para esta movimentação não ser aplicável nesta competência:');
    if (!justificativa?.trim()) return;
    await atualizar(item, { aplicavel: false, justificativa: justificativa.trim() });
  }

  async function reativarMovimentacao(item: MovimentacaoCompetencia) {
    // A reativação é limitada à competência aberta na tela. O backend limpa a
    // justificativa e o recarregamento atualiza card e resumo com a mesma fonte.
    await atualizar(item, { aplicavel: true });
  }

  async function encerrarMovimentacao(item: MovimentacaoCompetencia) {
    setSavingId(item.movimentacao_id);
    setError('');
    try {
      await inativarMovimentacaoInterna(item.movimentacao_id, competencia);
      await carregar();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível encerrar a movimentação.');
    } finally { setSavingId(null); }
  }

  async function salvarNova(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!nome.trim()) { setFormError('Informe o nome da movimentação.'); return; }
    const [ano, mes] = competenciaInicio.split('-').map(Number);
    if (!ano || mes < 1 || mes > 12) { setFormError('Informe uma competência válida.'); return; }
    setSavingNew(true); setFormError('');
    try {
      await criarMovimentacaoInterna(empresaId, {
        nome: nome.trim(), categoria_id: categoriaId ? Number(categoriaId) : null,
        competencia_inicio: ano * 100 + mes,
      });
      setFormOpen(false); setNome(''); await carregar();
    } catch (err) { setFormError(err instanceof Error ? err.message : 'Não foi possível criar a movimentação.'); }
    finally { setSavingNew(false); }
  }

  const empresa = data?.empresa;
  const grupos = useMemo(() => {
    const map = new Map<string, MovimentacaoCompetencia[]>();
    for (const item of data?.movimentacoes ?? []) {
      const key = item.categoria_nome || (item.origem === 'DOCUMENTACAO' ? 'Documentação' : 'Movimentações internas');
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return [...map.entries()];
  }, [data]);

  return <div className="page contabil-page">
    <div className="page-heading contabil-heading">
      <div>
        <div className="contabil-back-row">
          <Link to={`/contabil/lancamentos-conferencias?competencia=${competenciaInput(competencia)}`} className="contabil-back-link"><ArrowLeft size={15}/> Voltar ao painel</Link>
        </div>
        <span className="eyebrow">MÓDULO CONTÁBIL · LANÇAMENTOS E CONFERÊNCIAS</span>
        <h2>{empresa?.razao_social || 'Movimentações da empresa'}</h2>
        {empresa && <p>{empresa.nome_fantasia || '—'} · CNPJ {formatarCnpj(empresa.cnpj)}</p>}
      </div>
      <div className="contabil-period-chip" aria-label="Seletor de competência">
        <CalendarDays size={15}/><strong>Competência</strong>
        <button type="button" className="contabil-period-nav" aria-label="Competência anterior"
          onClick={() => selecionarCompetencia(competenciaInput(deslocarCompetencia(competencia, -1)))}>‹</button>
        <input type="month" aria-label="Selecionar competência" value={competenciaInput(competencia)} onChange={e => selecionarCompetencia(e.target.value)}/>
        <button type="button" className="contabil-period-nav" aria-label="Próxima competência"
          onClick={() => selecionarCompetencia(competenciaInput(deslocarCompetencia(competencia, 1)))}>›</button>
      </div>
    </div>

    {error && <div className="contabil-inline-error" role="alert"><CircleAlert size={16}/>{error}</div>}
    {loading && !data ? <div className="contabil-loading"><span className="spinner"/>Carregando movimentações...</div> : data && <>
      <div className="contabil-movement-summary">
        <div><small>Movimentações aplicáveis</small><strong>{data.resumo.total}</strong></div>
        <div><small>Concluídas</small><strong>{data.resumo.concluidas}</strong></div>
        <div><small>Pendentes</small><strong>{data.resumo.pendentes}</strong></div>
        <div><small>Aguardando documento</small><strong>{data.resumo.aguardando_documento}</strong></div>
        <div><small>Progresso</small><strong>{data.resumo.progresso_percentual}%</strong></div>
      </div>
      <div className="contabil-detail-toolbar">
        <div><strong>Movimentações da competência</strong><small>Marque o lançamento e, depois, a conferência de cada item.</small></div>
        <button className="button primary" onClick={() => { setCompetenciaInicio(competenciaInput(competencia)); setFormOpen(true); }}><Plus size={16}/> Nova movimentação</button>
      </div>
      {grupos.length === 0 ? <div className="contabil-empty"><FileText size={28}/><strong>Nenhuma movimentação cadastrada</strong><span>Cadastre uma movimentação interna ou configure documentos recorrentes na Documentação Contábil.</span></div> : grupos.map(([grupo, items]) => <section className="panel contabil-movement-group" key={grupo}>
        <header><span><FileCheck2 size={17}/><strong>{grupo}</strong></span><small>{items.length} movimentação(ões)</small></header>
        <div className="contabil-movement-list">{items.map(item => <article className={'contabil-movement-row' + (!item.aplicavel ? ' is-not-applicable' : '')} key={item.movimentacao_id}>
          <div className="contabil-movement-name"><strong>{item.nome}</strong><small>{item.origem === 'DOCUMENTACAO' ? (item.documento_disponivel ? `${item.quantidade_arquivos} arquivo(s) recebido(s)` : 'Aguardando documento') : 'Movimentação interna'}</small></div>
          <label className="contabil-check"><input type="checkbox" checked={item.lancado} disabled={!item.aplicavel || !item.documento_disponivel || savingId === item.movimentacao_id} onChange={e => void atualizar(item, { lancado: e.target.checked })}/><span>Lançado</span></label>
          <label className="contabil-check"><input type="checkbox" checked={item.conferido} disabled={!item.aplicavel || !item.documento_disponivel || !item.lancado || savingId === item.movimentacao_id} onChange={e => void atualizar(item, { conferido: e.target.checked })}/><span>Conferido</span></label>
          <span className={'contabil-movement-state ' + (item.concluida ? 'done' : !item.aplicavel ? 'off' : item.status_documento === 'AGUARDANDO_DOCUMENTO' ? 'waiting' : 'open')}>{!item.aplicavel ? 'Não aplicável' : item.concluida ? 'Concluída' : item.status_documento === 'AGUARDANDO_DOCUMENTO' ? 'Aguardando documento' : item.lancado ? 'Aguardando conferência' : 'Pendente'}</span>
          {item.aplicavel && <button className="contabil-text-action" disabled={savingId === item.movimentacao_id || item.lancado || item.conferido} onClick={() => void marcarNaoAplicavel(item)}>Não aplicável</button>}
          {item.origem === 'LANCAMENTOS_CONFERENCIAS' && item.aplicavel && <button className="contabil-text-action" disabled={savingId === item.movimentacao_id} onClick={() => void encerrarMovimentacao(item)}>Encerrar</button>}
          {!item.aplicavel && <><small className="contabil-not-applicable-reason">Justificativa: {item.justificativa_nao_aplicavel || '—'}</small><button className="contabil-text-action" disabled={savingId === item.movimentacao_id} onClick={() => void reativarMovimentacao(item)}>Tornar aplicável nesta competência</button></>}
          {savingId === item.movimentacao_id && <RefreshCw className="contabil-saving-icon" size={14}/>}
        </article>)}</div>
      </section>)}
    </>}

    {formOpen && <div className="contabil-modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) setFormOpen(false); }}>
      <form className="contabil-modal" onSubmit={salvarNova}>
        <header><div><span className="eyebrow">CADASTRO</span><h3>Nova movimentação</h3></div><button type="button" className="contabil-modal-close" onClick={() => setFormOpen(false)}>×</button></header>
        <label>Nome da movimentação<input value={nome} onChange={e => setNome(e.target.value)} placeholder="Ex.: Folha de pagamento" required maxLength={200}/></label>
        <label>Categoria<select value={categoriaId} onChange={e => setCategoriaId(e.target.value)}><option value="">Sem categoria</option>{data?.categorias.map(cat => <option key={cat.id} value={cat.id}>{cat.nome}</option>)}</select></label>
        <label>Competência inicial
          <div className="contabil-month-picker">
            <button type="button" className="icon-button" aria-label="Mês anterior" onClick={() => setCompetenciaInicio(current => {
              const [year, month] = current.split('-').map(Number); const date = new Date(year, month - 2, 1);
              return competenciaInput(date.getFullYear() * 100 + date.getMonth() + 1);
            })}>‹</button>
            <input type="month" value={competenciaInicio} onChange={e => setCompetenciaInicio(e.target.value)} required/>
            <button type="button" className="icon-button" aria-label="Próximo mês" onClick={() => setCompetenciaInicio(current => {
              const [year, month] = current.split('-').map(Number); const date = new Date(year, month, 1);
              return competenciaInput(date.getFullYear() * 100 + date.getMonth() + 1);
            })}>›</button>
          </div>
        </label>
        {formError && <p className="contabil-inline-error">{formError}</p>}
        <footer><button type="button" className="button secondary" onClick={() => setFormOpen(false)}>Cancelar</button><button type="submit" className="button primary" disabled={savingNew}>{savingNew ? 'Salvando...' : 'Criar movimentação'}</button></footer>
      </form>
    </div>}
  </div>;
}
