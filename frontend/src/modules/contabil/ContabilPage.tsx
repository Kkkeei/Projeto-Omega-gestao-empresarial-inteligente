import { useEffect, useState } from 'react';
import { Building2, CheckCircle2, ChevronRight, CircleAlert, FileCheck2, FileText, Filter, Search, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { listarDashboardContabil, listarResponsaveisContabeis } from './contabilApi';
import { AtribuicaoModal } from './AtribuicaoModal';
import type { DashboardContabilResponse, EmpresaContabil, ResponsavelContabil } from './types';
import './contabil.css';

const REGIMES = [
  { key: 'TODOS', label: 'Todas', icon: Building2 },
  { key: 'SIMPLES NACIONAL', label: 'Simples Nacional', icon: FileText },
  { key: 'LUCRO PRESUMIDO', label: 'Lucro Presumido', icon: FileText },
  { key: 'LUCRO REAL', label: 'Lucro Real', icon: FileCheck2 },
] as const;

function competenciaAtual() {
  const now = new Date();
  return now.getFullYear() * 100 + now.getMonth() + 1;
}

function formatarCnpj(value: string) {
  const digits = (value || '').replace(/\D/g, '');
  if (digits.length !== 14) return value;
  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

function classeRegime(value?: string | null) {
  const regime = (value || '').toUpperCase();
  if (regime.includes('SIMPLES')) return 'simple';
  if (regime.includes('PRESUMIDO')) return 'presumido';
  if (regime.includes('REAL')) return 'real';
  return 'default';
}

function statusLabel(status: EmpresaContabil['status_documentacao']) {
  if (status === 'COMPLETA') return 'Documentação completa';
  if (status === 'PARCIAL') return 'Documentação parcialmente recebida';
  return 'Nenhum documento recebido';
}

function statusClass(status: EmpresaContabil['status_documentacao']) {
  if (status === 'COMPLETA') return 'complete';
  if (status === 'PARCIAL') return 'partial';
  return 'missing';
}

export function ContabilPage() {
  const [data, setData] = useState<DashboardContabilResponse | null>(null);
  const [busca, setBusca] = useState('');
  const [regime, setRegime] = useState('TODOS');
  const [responsavel, setResponsavel] = useState('TODOS');
  const [competencia] = useState(competenciaAtual());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalAtribuicao, setModalAtribuicao] = useState(false);
  const [responsaveis, setResponsaveis] = useState<ResponsavelContabil[]>([]);

  async function carregar() {
    setLoading(true);
    setError('');
    try {
      const result = await listarDashboardContabil({
        competencia,
        busca: busca.trim() || undefined,
        regime,
        responsavel_id: responsavel === 'TODOS' ? null : responsavel === 'NAO_ATRIBUIDO' ? 'NAO_ATRIBUIDO' : Number(responsavel),
        pagina: 1,
        por_pagina: 100,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar o painel contábil.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void listarResponsaveisContabeis().then((result) => setResponsaveis(result.responsaveis.filter((item) => item.ativo))).catch(() => setResponsaveis([]));
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void carregar(); }, busca ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [busca, regime, responsavel, competencia]);

  const resumo = data?.resumo;
  const companies = data?.empresas ?? [];
  const owners = responsaveis.map((item) => [item.id, item.nome] as const);

  return <div className="page contabil-page">
    <div className="page-heading contabil-heading">
      <div><span className="eyebrow">GESTÃO CONTÁBIL</span><h2>Contábil</h2><p>Acompanhe o recebimento mensal de documentos e a distribuição das empresas.</p></div>
      <div className="contabil-period-chip"><span className="contabil-live-dot" />Competência {String(competencia).slice(4, 6)}/{String(competencia).slice(0, 4)}</div>
    </div>

    <div className="contabil-regime-grid">
      {REGIMES.map(({ key, label, icon: Icon }) => {
        const active = regime === key;
        const count = key === 'TODOS' ? resumo?.total_empresas ?? 0
          : key === 'SIMPLES NACIONAL' ? resumo?.simples_nacional ?? 0
          : key === 'LUCRO PRESUMIDO' ? resumo?.lucro_presumido ?? 0
          : resumo?.lucro_real ?? 0;
        return <button key={key} className={'contabil-regime-card' + (active ? ' active' : '')} onClick={() => setRegime(key)}>
          <span className={'contabil-regime-icon ' + classeRegime(key)}><Icon size={19} /></span>
          <span className="contabil-regime-copy"><strong>{label}</strong><small>{count} empresas</small></span>
          {active && <span className="contabil-regime-selected"><CheckCircle2 size={15} /></span>}
        </button>;
      })}
      <button className="contabil-regime-card assign" onClick={() => setModalAtribuicao(true)}>
        <span className="contabil-regime-icon responsible"><Users size={19} /></span>
        <span className="contabil-regime-copy"><strong>Atribuir Responsável</strong><small>Distribua a carteira de empresas</small></span>
        <ChevronRight size={17} className="contabil-card-arrow" />
      </button>
    </div>

    <div className="contabil-toolbar">
      <label className="contabil-search"><Search size={17} /><input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Pesquisar por razão social, nome fantasia ou CNPJ..." /></label>
      <label className="contabil-select"><span>Regime</span><select value={regime} onChange={(event) => setRegime(event.target.value)}>
        <option value="TODOS">Todos os regimes</option><option value="SIMPLES NACIONAL">Simples Nacional</option><option value="LUCRO PRESUMIDO">Lucro Presumido</option><option value="LUCRO REAL">Lucro Real</option>
      </select></label>
      <label className="contabil-select"><span>Responsável</span><select value={responsavel} onChange={(event) => setResponsavel(event.target.value)}>
        <option value="TODOS">Todos os responsáveis</option><option value="NAO_ATRIBUIDO">Não atribuído</option>
        {owners.map(([id, name]) => <option key={id} value={String(id)}>{name}</option>)}
      </select></label>
      <button className="button secondary contabil-clear" onClick={() => { setBusca(''); setRegime('TODOS'); setResponsavel('TODOS'); }}><Filter size={14} />Limpar</button>
    </div>

    <section className="panel contabil-table-panel">
      <div className="contabil-table-heading"><div><strong>Empresas</strong><small>{loading ? 'Atualizando dados...' : (data?.total ?? 0) + ' empresas encontradas'}</small></div><button className="button secondary" onClick={() => void carregar()} disabled={loading}>Atualizar</button></div>
      {error ? <div className="contabil-error-state"><CircleAlert size={22} /><strong>Não foi possível carregar o Contábil</strong><span>{error}</span><small>A interface está preparada; implemente a rota /api/v1/contabil/dashboard no backend.</small><button className="button secondary" onClick={() => void carregar()}>Tentar novamente</button></div>
      : loading && !data ? <div className="contabil-loading"><span className="spinner" />Carregando empresas...</div>
      : companies.length === 0 ? <div className="contabil-empty"><Building2 size={30} /><strong>Nenhuma empresa encontrada</strong><span>Ajuste os filtros ou verifique se há empresas cadastradas.</span></div>
      : <div className="table-wrap"><table className="contabil-table">
        <thead><tr><th>Empresa</th><th>CNPJ</th><th>Regime</th><th>Documentos</th><th>Situação do mês</th><th>Responsável</th><th>Ações</th></tr></thead>
        <tbody>{companies.map((empresa) => <tr key={empresa.id}>
          <td><div className="contabil-company-cell"><span className="contabil-company-icon"><Building2 size={16} /></span><span><strong>{empresa.razao_social}</strong><small>{empresa.nome_fantasia || '—'}</small></span></div></td>
          <td className="contabil-cnpj">{formatarCnpj(empresa.cnpj)}</td>
          <td><span className={'contabil-regime-tag ' + classeRegime(empresa.regime_tributario)}>{empresa.regime_tributario || 'Não informado'}</span></td>
          <td><div className="contabil-doc-count"><span className={'contabil-progress ' + statusClass(empresa.status_documentacao)} style={{ background: 'conic-gradient(' + (empresa.status_documentacao === 'COMPLETA' ? '#22895e' : empresa.status_documentacao === 'PARCIAL' ? '#d69b31' : '#d8dee7') + ' ' + (empresa.documentos_total ? Math.min(100, empresa.documentos_recebidos / empresa.documentos_total * 100) : 0) + '%, #e5e9ef 0)' }}><i /></span><span><strong>{empresa.documentos_recebidos}/{empresa.documentos_total}</strong><small>documentos</small></span></div></td>
          <td><span className={'contabil-status-text ' + statusClass(empresa.status_documentacao)}><i />{statusLabel(empresa.status_documentacao)}</span></td>
          <td>{empresa.responsavel_id ? <span className="contabil-owner"><i>{(empresa.responsavel_nome || 'U').slice(0, 1).toUpperCase()}</i>{empresa.responsavel_nome}</span> : <span className="contabil-unassigned">Não atribuído</span>}</td>
          <td><Link className="contabil-access-link" to={'/contabil/documentacao/empresa/' + empresa.id}>Acessar <ChevronRight size={14} /></Link></td>
        </tr>)}</tbody>
      </table></div>}
      <div className="contabil-table-footer"><span>Os indicadores consideram as obrigações da competência selecionada.</span><span>{companies.length} de {data?.total ?? 0}</span></div>
    </section>
    {modalAtribuicao && <AtribuicaoModal onClose={() => setModalAtribuicao(false)} onSaved={() => { setModalAtribuicao(false); void carregar(); }} />}
  </div>;
}
