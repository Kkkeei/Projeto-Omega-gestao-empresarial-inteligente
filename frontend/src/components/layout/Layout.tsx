import {NavLink,Outlet,useLocation} from 'react-router-dom';
import {LayoutDashboard,Building2,FileCheck2,AlertTriangle,ChevronRight,LogOut,Users,ShieldCheck,Folder,BadgeDollarSign,ReceiptText,KeyRound,FileText,BookOpen} from 'lucide-react';
import {useAuth} from '../../auth/AuthContext';

const links=[
  ['/','Dashboard',LayoutDashboard],
  ['/empresas','Empresas',Building2],
  ['/certidoes','Certidões',FileCheck2],
  ['/certificados','Certificados',KeyRound],
  ['/nfse','NFS-e',FileText],
  ['/documentacao','Dossiê Digital',Folder],
  ['/pendencias','Pendências',AlertTriangle],
  ['/faturamento','Faturamento',BadgeDollarSign],
  ['/impostos','Impostos',ReceiptText],
] as const;

export function Layout(){
  const loc=useLocation();
  const {usuario,logout}=useAuth();
  const contabilActive=loc.pathname.startsWith('/contabil');
  const title=contabilActive
    ? (loc.pathname.startsWith('/contabil/lancamentos-conferencias')?'Lançamentos e Conferências':'Contábil')
    : links.find(x=>x[0]===loc.pathname)?.[1]
      || (loc.pathname==='/usuarios'?'Usuários':loc.pathname==='/alterar-senha'?'Alterar senha':loc.pathname.startsWith('/documentacao/')?'Dossiê Digital':loc.pathname.startsWith('/faturamento/')?'Faturamento':loc.pathname.startsWith('/impostos/')?'Impostos':'ÔMEGA');

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">Ω</div><div><strong>ÔMEGA</strong><span>GESTÃO EMPRESARIAL</span></div></div>
      <nav className="nav">
        {links.slice(0,5).map(([to,label,Icon])=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>'nav-link '+(isActive?'active':'')}><Icon size={17}/><span>{label}</span><ChevronRight size={14} className="nav-arrow"/></NavLink>)}
        <NavLink to="/contabil/documentacao" className={()=>'nav-link '+(contabilActive?'active':'')}><BookOpen size={17}/><span>Contábil</span><ChevronRight size={14} className="nav-arrow"/></NavLink>
        {contabilActive&&<div className="nav-sublist">
          <NavLink to="/contabil/documentacao" end className={({isActive})=>'nav-sub-link '+(isActive||loc.pathname.startsWith('/contabil/documentacao/empresa/')?'active':'')}>Documentação</NavLink>
          <NavLink to="/contabil/lancamentos-conferencias" className={({isActive})=>'nav-sub-link '+(isActive?'active':'')}>Lançamentos e Conferências</NavLink>
        </div>}
        {links.slice(5).map(([to,label,Icon])=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>'nav-link '+(isActive?'active':'')}><Icon size={17}/><span>{label}</span><ChevronRight size={14} className="nav-arrow"/></NavLink>)}
        {usuario?.perfil==='ADMIN'&&<NavLink to="/usuarios" className={({isActive})=>'nav-link '+(isActive?'active':'')}><Users size={17}/><span>Usuários</span><ChevronRight size={14} className="nav-arrow"/></NavLink>}
      </nav>
      <div className="sidebar-user"><span className="user-avatar">{(usuario?.nome||'U').slice(0,1).toUpperCase()}</span><div><strong>{usuario?.nome}</strong><small>{usuario?.perfil==='ADMIN'?'Administrador':'Usuário'}</small></div><button className="icon-button dark" title="Sair" onClick={()=>void logout()}><LogOut size={15}/></button></div>
      <div className="sidebar-note"><span>Dossiê empresarial</span><strong>Histórico permanente</strong><small>A situação atual é importante. O histórico nunca é perdido.</small></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><span className="eyebrow">PLATAFORMA ÔMEGA</span><h1>{title}</h1></div><div className="topbar-user"><span className="top-user-badge"><ShieldCheck size={13}/> Sessão segura</span><div className="top-user-info"><strong>{usuario?.nome}</strong><span>{usuario?.email}</span></div><button className="icon-button" onClick={()=>void logout()} title="Sair"><LogOut size={15}/></button></div></header>
      <Outlet/>
    </main>
  </div>;
}
