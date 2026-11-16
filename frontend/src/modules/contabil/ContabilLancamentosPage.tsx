import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  CircleHelp,
  FileCheck2,
  FileText,
  Filter,
  Search,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { listarPainelLancamentos, listarResponsaveisContabeis } from './contabilApi';
import type {
  DashboardLancamentosResponse,
  EmpresaLancamentos,
  IndicadorLancamentos,
  ResponsavelContabil,
} from './types';
import './contabil.css';

const REGIMES = [
  { key: 'TODOS', label: 'Todas', countKey: 'total_empresas', icon: Building2 },
  { key: 'SIMPLES NACIONAL', label: 'Simples Nacional', countKey: 'simples_nacional', icon: FileText },
  { key: 'LUCRO PRESUMIDO', label: 'Lucro Presumido', countKey: 'lucro_presumido', icon: FileCheck2 },
  { key: 'LUCRO REAL', label: 'Lucro Real', countKey: 'lucro_real', icon: CircleHelp },
] as const;

const INDICATOR_COLORS: Record<IndicadorLancamentos, string> = {
  VERDE: '#1b9a67',
  AZUL: '#3688d4',
  LARANJA: '#e2a12b',
  VERMELHO: '#d94b52',
  CINZA: '#c6cdd6',
};

function competenciaAnterior() {
  const agora = new Date();
  const anterior = new Date(agora.getFullYear(), agora.getMonth() - 1, 1);
  return anterior.getFullYear() * 100 + anterior.getMonth() + 1;
}

function lerCompetencia(value: string | null) {
  if (!value) return null;
  const match = value.match(/^(\d{4})-?(\d{2})$/);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  return year >= 1900 && year <= 2999 && month >= 1 && month <= 12 ? year * 100 + month : null;
}

function deslocarCompetencia(value: number, delta: number) {
  const data = new Date(Math.floor(value / 100), (value % 100) - 1 + delta, 1);
  return data.getFullYear() * 100 + data.getMonth() + 1;
}

function competenciaInput(value: number) {
  return `${Math.floor(value / 100)}-${String(value % 100).padStart(2, '0')}`;
}

function competenciaLabel(value: number) {
  const year = Math.floor(value / 100);
  const month = value % 100;
  return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' })
    .format(new Date(year, month - 1, 1));
}

function formatarCnpj(value: string) {
  const digits = (value || '').replace(/\D/g, '');
  if (digits.length !== 14) return value || '—';
  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

function classeRegime(value?: string | null) {
  const regime = (value || '').toUpperCase();
  if (regime.includes('SIMPLES')) return 'simple';
  if (regime.includes('PRESUMIDO')) return 'presumido';
  if (regime.includes('REAL')) return 'real';
  return 'default';
}

function formatSituacao(value: EmpresaLancamentos['situacao']) {
  switch (value) {
    case 'CONCLUIDO': return 'Concluído';
    case 'EM_ANDAMENTO': return 'Em andamento';
    case 'PENDENTE': return 'Pendente';
    case 'ATRASADO': return 'Atrasado';
    case 'SEM_MOVIMENTACOES': return 'Sem movimentações';
  }
}

function situacaoClass(value: EmpresaLancamentos['situacao']) {
  switch (value) {
    case 'CONCLUIDO': return 'done';
    case 'EM_ANDAMENTO': return 'working';
    case 'PENDENTE': return 'pending';
    case 'ATRASADO': return 'late';
    case 'SEM_MOVIMENTACOES': return 'none';
  }
}

function iniciais(nome?: string | null) {
  const partes = (nome || '').trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return '—';
  return partes.length === 1
    ? partes[0].slice(0, 1).toUpperCase()
    : `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

function ProgressRing({ empresa }: { empresa: EmpresaLancamentos }) {
  const semMovimentacoes = empresa.situacao === 'SEM_MOVIMENTACOES';
  const color = INDICATOR_COLORS[empresa.indicador] || INDICATOR_COLORS.CINZA;
  const percent = semMovimentacoes ? 0 : Math.max(0, Math.min(100, empresa.progresso_percentual || 0));
  return (
    <div className="lc-progress-wrap">
      <span
        className={`lc-progress-ring ${semMovimentacoes ? 'is-empty' : ''}`}
        style={{ background: semMovimentacoes ? '#e8edf2' : `conic-gradient(${color} ${percent}%, #e8edf2 0)` }}
        role="img"
        aria-label={semMovimentacoes ? 'Sem movimentações' : `${percent}% concluído`}
      >
        <i />
      </span>
      <span className="lc-progress-copy">
        <strong>{semMovimentacoes ? '—' : `${empresa.movimentacoes_concluidas}/${empresa.movimentacoes_total}`}</strong>
        <small>{semMovimentacoes ? 'Sem movimentações' : 'Movimentações'}</small>
      </span>
    </div>
  );
}

export function ContabilLancamentosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const competencia = lerCompetencia(searchParams.get('competencia')) ?? competenciaAnterior();
  const [data, setData] = useState<DashboardLancamentosResponse | null>(null);
  const [busca, setBusca] = useState('');
  const [regime, setRegime] = useState('TODOS');
  const [responsavel, setResponsavel] = useState('TODOS');
  const [responsaveis, setResponsaveis] = useState<ResponsavelContabil[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [responsaveisError, setResponsaveisError] = useState('');

  const carregar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await listarPainelLancamentos({
        competencia,
        busca: busca.trim() || undefined,
        regime,
        responsavel_id: responsavel === 'TODOS'
          ? null
          : responsavel === 'NAO_ATRIBUIDO'
            ? 'NAO_ATRIBUIDO'
            : Number(responsavel),
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar os lançamentos e conferências.');
    } finally {
      setLoading(false);
    }
  }, [busca, competencia, regime, responsavel]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void carregar(); }, busca ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [busca, carregar]);

  useEffect(() => {
    let active = true;
    void listarResponsaveisContabeis().then((result) => {
      if (active) setResponsaveis(result.responsaveis.filter((item) => item.ativo));
    }).catch((err: unknown) => {
      if (active) setResponsaveisError(err instanceof Error ? err.message : 'Não foi possível carregar os responsáveis.');
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => { void carregar(); }, 60000);
    const onFocus = () => { void carregar(); };
    window.addEventListener('focus', onFocus);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('focus', onFocus);
    };
  }, [carregar]);

  function selecionarCompetencia(value: string) {
    if (!value) return;
    const [year, month] = value.split('-').map(Number);
    const next = new URLSearchParams(searchParams);
    next.set('competencia', `${year}-${String(month).padStart(2, '0')}`);
    setSearchParams(next);
  }

  const resumo = data?.resumo;
  const empresas = data?.empresas ?? [];
  const responsaveisOrdenados = useMemo(
    () => [...responsaveis].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [responsaveis],
  );

  return (
    <main className="page contabil-page lc-dashboard">
      <header className="lc-page-heading">
        <div>
          <span className="lc-eyebrow">CONTÁBIL</span>
          <h1>Lançamentos e Conferências</h1>
          <p>Acompanhe os lançamentos e as conferências de todas as empresas.</p>
        </div>
        <div className="lc-competence" aria-label="Seletor de competência">
          <span className="lc-competence-label">Competência</span>
          <button type="button" aria-label="Competência anterior" onClick={() => selecionarCompetencia(competenciaInput(deslocarCompetencia(competencia, -1)))}>
            <ChevronLeft size={15} />
          </button>
          <input
            aria-label="Escolher competência"
            type="month"
            value={competenciaInput(competencia)}
            onChange={(event) => selecionarCompetencia(event.target.value)}
          />
          <button type="button" aria-label="Próxima competência" onClick={() => selecionarCompetencia(competenciaInput(deslocarCompetencia(competencia, 1)))}>
            <ChevronRight size={15} />
          </button>
        </div>
      </header>

      <section className="lc-regime-grid" aria-label="Filtrar por regime tributário">
        {REGIMES.map(({ key, label, countKey, icon: Icon }) => {
          const active = regime === key;
          const count = resumo?.[countKey] ?? 0;
          return (
            <button
              key={key}
              type="button"
              className={`lc-regime-card ${active ? 'is-active' : ''}`}
              aria-pressed={active}
              onClick={() => setRegime(key)}
            >
              <span className={`lc-regime-icon ${classeRegime(key)}`}><Icon size={17} /></span>
              <span className="lc-regime-copy">
                <strong>{label}</strong>
                <small>{count} {count === 1 ? 'empresa' : 'empresas'}</small>
              </span>
              {active && <CheckCircle2 className="lc-regime-check" size={15} />}
            </button>
          );
        })}
      </section>

      <section className="lc-filter-bar" aria-label="Pesquisa e filtros">
        <label className="lc-search-field">
          <Search size={17} />
          <input
            value={busca}
            onChange={(event) => setBusca(event.target.value)}
            placeholder="Pesquisar por nome da empresa, CNPJ etc..."
            aria-label="Pesquisar empresa por razão social, nome fantasia ou CNPJ"
          />
          {busca && <button type="button" onClick={() => setBusca('')} aria-label="Limpar pesquisa">×</button>}
        </label>
        <label className="lc-filter-select">
          <span><Filter size={12} /> Regime</span>
          <select value={regime} onChange={(event) => setRegime(event.target.value)}>
            <option value="TODOS">Todos os regimes</option>
            <option value="SIMPLES NACIONAL">Simples Nacional</option>
            <option value="LUCRO PRESUMIDO">Lucro Presumido</option>
            <option value="LUCRO REAL">Lucro Real</option>
          </select>
        </label>
        <label className="lc-filter-select lc-responsible-select">
          <span><Filter size={12} /> Responsável</span>
          <select value={responsavel} onChange={(event) => setResponsavel(event.target.value)}>
            <option value="TODOS">Todos os responsáveis</option>
            {responsaveisOrdenados.map((item) => <option key={item.id} value={String(item.id)}>{item.nome}</option>)}
            <option value="NAO_ATRIBUIDO">Não atribuído</option>
          </select>
        </label>
      </section>
      {(responsaveisError || error) && <p className="lc-inline-error" role="alert">{responsaveisError || error}</p>}

      <section className="lc-table-card" aria-label="Empresas e situação dos lançamentos">
        <div className="lc-table-topline">
          <div>
            <h2>Empresas</h2>
            <span>{loading && !data ? 'Carregando...' : `${data?.total ?? 0} ${data?.total === 1 ? 'empresa encontrada' : 'empresas encontradas'}`}</span>
          </div>
          <span className="lc-competence-caption">Referência: {competenciaLabel(competencia)}</span>
        </div>

        {error && !data ? (
          <div className="lc-state-box is-error">
            <CircleAlert size={25} />
            <strong>Não foi possível carregar o painel</strong>
            <span>{error}</span>
            <button type="button" onClick={() => void carregar()}>Tentar novamente</button>
          </div>
        ) : loading && !data ? (
          <div className="lc-state-box"><span className="lc-spinner" />Carregando empresas...</div>
        ) : empresas.length === 0 ? (
          <div className="lc-state-box">
            <Building2 size={27} />
            <strong>Nenhuma empresa encontrada</strong>
            <span>Ajuste a pesquisa ou os filtros para visualizar as empresas.</span>
          </div>
        ) : (
          <div className="lc-table-scroll">
            <table className="lc-table">
              <thead>
                <tr>
                  <th>Empresa</th>
                  <th>CNPJ</th>
                  <th>Regime</th>
                  <th>Movimentações</th>
                  <th>Situação do mês</th>
                  <th>Responsável</th>
                  <th className="lc-actions-head">Ações</th>
                </tr>
              </thead>
              <tbody>
                {empresas.map((empresa) => {
                  const status = situacaoClass(empresa.situacao);
                  return (
                    <tr key={empresa.id}>
                      <td>
                        <div className="lc-company">
                          <span className="lc-company-mark"><Building2 size={16} /></span>
                          <span className="lc-company-name">
                            <strong title={empresa.razao_social}>{empresa.razao_social}</strong>
                            <small title={empresa.nome_fantasia || ''}>{empresa.nome_fantasia || ' '}</small>
                          </span>
                        </div>
                      </td>
                      <td className="lc-cnpj">{formatarCnpj(empresa.cnpj)}</td>
                      <td><span className={`lc-regime-pill ${classeRegime(empresa.regime_tributario)}`}>{empresa.regime_tributario || 'Não informado'}</span></td>
                      <td><ProgressRing empresa={empresa} /></td>
                      <td>
                        <div className={`lc-status ${status}`}>
                          <strong><i />{formatSituacao(empresa.situacao)}</strong>
                          {empresa.situacao !== 'SEM_MOVIMENTACOES' && <small>{empresa.descricao_situacao}</small>}
                          {empresa.aguardando_documento > 0 && <small>{empresa.aguardando_documento} aguardando documento</small>}
                        </div>
                      </td>
                      <td>
                        {empresa.responsavel_id ? (
                          <span className="lc-owner">
                            <i>{iniciais(empresa.responsavel_nome)}</i>
                            <span>{empresa.responsavel_nome || 'Responsável'}</span>
                          </span>
                        ) : (
                          <span className="lc-owner is-unassigned"><i>—</i><span>Não atribuído</span></span>
                        )}
                      </td>
                      <td>
                        <Link className="lc-access-link" to={`/contabil/lancamentos-conferencias/empresa/${empresa.id}?competencia=${competenciaInput(competencia)}`}>
                          Acessar <ArrowRight size={14} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <footer className="lc-table-footer">
          <span>O progresso considera somente movimentações lançadas e conferidas.</span>
          <span>{empresas.length} de {data?.total ?? 0}</span>
        </footer>
      </section>
    </main>
  );
}
