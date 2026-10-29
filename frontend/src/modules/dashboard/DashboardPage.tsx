import { useEffect, useState } from 'react';
import { Activity, ArrowDownRight, ArrowRight, BadgeDollarSign, Building2, FileText, FolderOpen, Plus, RefreshCw, ReceiptText, ShieldCheck, AlertTriangle, KeyRound } from 'lucide-react';
import { Link } from 'react-router-dom';
import { buscarResumoDashboard } from '../../services/api/dashboard';
import type { DashboardResumo } from '../../types';
import { Loading } from '../../components/ui/Loading';
import { ErrorState } from '../../components/ui/ErrorState';

export function DashboardPage() {
  const [data, setData] = useState<DashboardResumo | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function load() {
    setError('');
    setLoading(true);
    try { setData(await buscarResumoDashboard()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Erro ao carregar o painel.'); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  if (error) return <div className="page"><ErrorState message={error} onRetry={() => void load()} /></div>;
  if (loading || !data) return <div className="page"><Loading text="Carregando resumo empresarial..." /></div>;

  const total = data.empresas_total ?? data.empresas ?? 0;
  const ativas = data.empresas_ativas ?? 0;
  const inativas = data.empresas_inativas ?? Math.max(0, total - ativas);
  const pendencias = data.pendencias_abertas ?? 0;
  const hoje = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date());
  const metrics = [
    { label: 'Empresas cadastradas', value: total, note: 'Base empresarial', icon: Building2, to: '/empresas', tone: 'blue' },
    { label: 'Empresas ativas', value: ativas, note: 'Cadastros em atividade', icon: ShieldCheck, to: '/empresas', tone: 'green' },
    { label: 'Empresas inativas', value: inativas, note: 'Cadastros inativos', icon: ArrowDownRight, to: '/empresas', tone: 'slate' },
    { label: 'Pendências abertas', value: pendencias, note: 'Itens que precisam de atenção', icon: AlertTriangle, to: '/pendencias', tone: pendencias ? 'amber' : 'green' },
  ];
  const shortcuts = [
    { label: 'Empresas', description: 'Cadastro e dados empresariais', to: '/empresas', icon: Building2, tone: 'blue' },
    { label: 'Faturamento', description: 'Notas e rotinas de faturamento', to: '/faturamento', icon: BadgeDollarSign, tone: 'green' },
    { label: 'Impostos', description: 'Tributos e acompanhamento fiscal', to: '/impostos', icon: ReceiptText, tone: 'violet' },
    { label: 'Documentação', description: 'Arquivos e documentos', to: '/documentacao', icon: FolderOpen, tone: 'amber' },
    { label: 'NFS-e', description: 'Área de notas de serviço', to: '/nfse', icon: FileText, tone: 'blue' },
    { label: 'Certificados', description: 'Certificados cadastrados', to: '/certificados', icon: KeyRound, tone: 'slate' },
  ];

  return <main className="page omega-dashboard">
    <header className="omega-dashboard-header">
      <div className="omega-dashboard-title">
        <span className="eyebrow">VISÃO GERAL</span>
        <h2>Bom dia. Vamos organizar o ÔMEGA.</h2>
        <p>Um resumo da sua operação empresarial, com acesso rápido às áreas de trabalho.</p>
        <span className="omega-dashboard-date"><Activity size={14} aria-hidden="true" /> {hoje}</span>
      </div>
      <div className="omega-dashboard-actions">
        <button className="button secondary" type="button" onClick={() => void load()}><RefreshCw size={16} aria-hidden="true" /> Atualizar</button>
        <Link className="button primary" to="/empresas"><Plus size={16} aria-hidden="true" /> Nova empresa</Link>
      </div>
    </header>

    <section className="omega-dashboard-metrics" aria-label="Indicadores empresariais">
      {metrics.map(({ label, value, note, icon: Icon, to, tone }) => <Link className="omega-dashboard-metric" to={to} key={label}>
        <span className={`omega-dashboard-metric-icon tone-${tone}`}><Icon size={20} strokeWidth={1.9} aria-hidden="true" /></span>
        <span className="omega-dashboard-metric-copy">
          <span className="omega-dashboard-metric-label">{label}</span>
          <strong>{value.toLocaleString('pt-BR')}</strong>
          <small>{note}</small>
        </span>
        <ArrowRight className="omega-dashboard-arrow" size={16} aria-hidden="true" />
      </Link>)}
    </section>

    <section className="omega-dashboard-main-grid">
      <article className="panel omega-dashboard-panel omega-dashboard-company-panel">
        <div className="omega-dashboard-panel-heading">
          <div><span className="eyebrow">BASE EMPRESARIAL</span><h3>Resumo dos cadastros</h3><p>Indicadores calculados a partir dos dados retornados pelo sistema.</p></div>
          <span className="omega-dashboard-panel-symbol"><Building2 size={20}/></span>
        </div>
        <div className="omega-dashboard-company-stats">
          <div><span>Empresas ativas</span><strong>{ativas.toLocaleString('pt-BR')}</strong></div>
          <div><span>Empresas inativas</span><strong>{inativas.toLocaleString('pt-BR')}</strong></div>
          <div><span>Total cadastrado</span><strong>{total.toLocaleString('pt-BR')}</strong></div>
        </div>
        <div className="omega-dashboard-panel-footer"><span>Os dados são apresentados conforme o retorno atual da API.</span><Link className="text-link" to="/empresas">Abrir cadastro <ArrowRight size={14}/></Link></div>
      </article>

      <article className="panel omega-dashboard-panel omega-dashboard-pending-panel">
        <div className="omega-dashboard-panel-heading">
          <div><span className="eyebrow">ACOMPANHAMENTO</span><h3>Pendências</h3><p>Consulte os itens registrados para acompanhamento.</p></div>
          <span className={`omega-dashboard-panel-symbol ${pendencias ? 'tone-amber' : 'tone-green'}`}><AlertTriangle size={20}/></span>
        </div>
        <div className="omega-dashboard-pending-number"><strong>{pendencias.toLocaleString('pt-BR')}</strong><span>pendência(s) aberta(s)</span></div>
        <Link className="omega-dashboard-pending-link" to="/pendencias">Acessar central de pendências <ArrowRight size={15}/></Link>
      </article>
    </section>

    <section className="omega-dashboard-shortcuts">
      <div className="omega-dashboard-section-heading"><div><span className="eyebrow">ÁREAS DO SISTEMA</span><h3>Acesse seu trabalho</h3><p>Atalhos para os módulos disponíveis no menu principal.</p></div></div>
      <div className="omega-dashboard-shortcut-grid">
        {shortcuts.map(({ label, description, to, icon: Icon, tone }) => <Link to={to} className="omega-dashboard-shortcut" key={to}>
          <span className={`omega-dashboard-shortcut-icon tone-${tone}`}><Icon size={19}/></span>
          <span className="omega-dashboard-shortcut-copy"><strong>{label}</strong><small>{description}</small></span>
          <ArrowRight size={16} className="omega-dashboard-arrow"/>
        </Link>)}
      </div>
    </section>
  </main>;
}
