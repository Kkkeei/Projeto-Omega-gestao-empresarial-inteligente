import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, ArrowRight, Building2, FileText, FileWarning, Plus, RefreshCw, Search, ShieldCheck, Workflow } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buscarResumoDashboard } from '../../services/api/dashboard';
import type { DashboardResumo } from '../../types';
import { Loading } from '../../components/ui/Loading';
import { ErrorState } from '../../components/ui/ErrorState';

export function DashboardPage() {
  const [data, setData] = useState<DashboardResumo | null>(null);
  const [error, setError] = useState('');
  async function load() {
    setError('');
    try { setData(await buscarResumoDashboard()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro ao carregar o painel.'); }
  }
  useEffect(() => { void load(); }, []);
  if (error) return <div className="page"><ErrorState message={error} onRetry={() => void load()} /></div>;
  if (!data) return <div className="page"><Loading /></div>;
  const metrics = [
    { label: 'Empresas cadastradas', value: data.empresas_total ?? data.empresas ?? 0, hint: 'Base empresarial', icon: Building2, to: '/empresas', tone: 'blue' },
    { label: 'Empresas ativas', value: data.empresas_ativas ?? 0, hint: 'Cadastros ativos', icon: ShieldCheck, to: '/empresas', tone: 'green' },
    { label: 'Empresas regulares', value: data.empresas_regulares ?? 0, hint: 'Com certidão regular', icon: ShieldCheck, to: '/certidoes', tone: 'green' },
    { label: 'Pendências abertas', value: data.pendencias_abertas ?? 0, hint: 'Precisam de atenção', icon: AlertTriangle, to: '/pendencias', tone: 'amber' },
    { label: 'Certidões vencidas', value: data.certidoes_vencidas ?? 0, hint: 'Verificar regularidade', icon: FileWarning, to: '/certidoes', tone: 'red' },
    { label: 'Vencem em até 30 dias', value: data.certidoes_proximas_vencimento ?? 0, hint: 'Antecipe a renovação', icon: FileWarning, to: '/certidoes', tone: 'amber' },
  ];
  const total = data.empresas_total ?? data.empresas ?? 0;
  const inativas = data.empresas_inativas ?? Math.max(0, total - (data.empresas_ativas ?? 0));
  const hoje = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date());
  return <main className="page omega-dashboard">
    <header className="omega-dashboard-header">
      <div className="omega-dashboard-title">
        <span className="eyebrow">PLATAFORMA DE GESTÃO EMPRESARIAL</span>
        <h2>Painel de controle</h2>
        <p>Acompanhe a situação das empresas, obrigações e rotinas do ÔMEGA em um só lugar.</p>
        <span className="omega-dashboard-date"><Activity size={14} aria-hidden="true" /> Resumo operacional · {hoje}</span>
      </div>
      <div className="omega-dashboard-actions">
        <button className="button secondary" type="button" onClick={() => void load()}><RefreshCw size={16} aria-hidden="true" /> Atualizar painel</button>
        <Link className="button primary" to="/empresas"><Plus size={16} aria-hidden="true" /> Nova empresa</Link>
      </div>
    </header>
    <section aria-label="Indicadores principais" className="omega-dashboard-metrics">
      {metrics.map(({ label, value, hint, icon: Icon, to, tone }) => <Link className="omega-dashboard-metric" to={to} key={label}>
        <span className={`omega-dashboard-metric-icon tone-${tone}`}><Icon size={21} strokeWidth={2} aria-hidden="true" /></span>
        <span className="omega-dashboard-metric-copy"><span className="omega-dashboard-metric-label">{label}</span><strong>{value.toLocaleString('pt-BR')}</strong><small>{hint}</small></span>
        <ArrowRight className="omega-dashboard-arrow" size={16} aria-hidden="true" />
      </Link>)}
    </section>
    <section className="omega-dashboard-lower">
      <article className="panel omega-dashboard-panel">
        <div className="omega-dashboard-panel-heading"><div><span className="eyebrow">CADASTRO</span><h3>Visão das empresas</h3></div><Link className="text-link" to="/empresas">Abrir empresas <ArrowRight size={13} /></Link></div>
        <div className="omega-dashboard-company-stats">
          <div><span>Ativas</span><strong>{(data.empresas_ativas ?? 0).toLocaleString('pt-BR')}</strong></div>
          <div><span>Inativas</span><strong>{inativas.toLocaleString('pt-BR')}</strong></div>
          <div><span>Total</span><strong>{total.toLocaleString('pt-BR')}</strong></div>
        </div>
        <div className="omega-dashboard-note">Os indicadores refletem os registros disponíveis no banco de dados do ÔMEGA.</div>
      </article>
      <article className="panel omega-dashboard-panel">
        <div className="omega-dashboard-panel-heading"><div><span className="eyebrow">PRIORIDADES</span><h3>O que merece atenção</h3></div><AlertTriangle size={19} aria-hidden="true" /></div>
        <Link className="omega-dashboard-priority" to="/pendencias"><span><AlertTriangle size={17} aria-hidden="true" /> Pendências abertas</span><strong>{data.pendencias_abertas ?? 0}</strong></Link>
        <Link className="omega-dashboard-priority" to="/certidoes"><span><FileWarning size={17} aria-hidden="true" /> Certidões vencidas</span><strong>{data.certidoes_vencidas ?? 0}</strong></Link>
        <Link className="omega-dashboard-priority" to="/certidoes"><span><ShieldCheck size={17} aria-hidden="true" /> Certidões a vencer</span><strong>{data.certidoes_proximas_vencimento ?? 0}</strong></Link>
        <div className="omega-dashboard-priority"><span><Workflow size={17} aria-hidden="true" /> Automações em andamento</span><strong>{data.automacoes_em_andamento ?? 0}</strong></div>
      </article>
    </section>
    <section className="panel omega-dashboard-quick">
      <div><span className="eyebrow">ATALHOS</span><h3>Ações frequentes</h3><p>Vá direto às tarefas mais utilizadas.</p></div>
      <div className="omega-dashboard-quick-actions">
        <Link to="/empresas"><Building2 size={17} aria-hidden="true" /> Gerenciar empresas</Link>
        <Link to="/certidoes"><Search size={17} aria-hidden="true" /> Consultar certidões</Link>
        <Link to="/pendencias"><AlertTriangle size={17} aria-hidden="true" /> Tratar pendências</Link>
        <Link to="/nfse"><FileText size={17} aria-hidden="true" /> NFS-e</Link>
        <Link to="/documentacao"><FileText size={17} aria-hidden="true" /> Documentação</Link>
      </div>
    </section>
  </main>;
}
