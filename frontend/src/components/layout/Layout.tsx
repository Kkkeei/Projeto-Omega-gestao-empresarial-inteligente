import {NavLink,Outlet,useLocation} from 'react-router-dom';
import {LayoutDashboard,Building2,FileCheck2,AlertTriangle,ChevronRight,LogOut,Users,ShieldCheck,Folder,BadgeDollarSign,ReceiptText,KeyRound,FileText,BookOpen} from 'lucide-react';
import {useAuth} from '../../auth/AuthContext';
import type { LucideIcon } from 'lucide-react';

type NavItem = readonly [path: string, label: string, icon: LucideIcon];
type NavSection = { title: string; links: readonly NavItem[] };

const sections: readonly NavSection[] = [
  { title: 'GERAL', links: [['/', 'Dashboard', LayoutDashboard], ['/empresas', 'Empresas', Building2]] },
  { title: 'CONTÁBIL', links: [['/contabil/documentacao', 'Contábil', BookOpen]] },
  { title: 'FISCAL', links: [['/nfse', 'NFS-e', FileText], ['/impostos', 'Impostos', ReceiptText], ['/certidoes', 'Certidões', FileCheck2], ['/certificados', 'Certificados', KeyRound]] },
  { title: 'GESTÃO E DOCUMENTOS', links: [['/documentacao', 'Dossiê Digital', Folder], ['/pendencias', 'Pendências', AlertTriangle], ['/faturamento', 'Faturamento', BadgeDollarSign]] },
];

export function Layout(){
  const loc=useLocation(); const {usuario,logout}=useAuth();
  const contabilActive=loc.pathname.startsWith('/contabil');
  const title=contabilActive ? (loc.pathname.startsWith('/contabil/lancamentos-conferencias')?'Lançamentos e Conferências':'Contábil')
    : sections.flatMap(section=>section.links).find(x=>x[0]===loc.pathname)?.[1]
      || (loc.pathname==='/usuarios'?'Usuários':loc.pathname==='/alterar-senha'?'Alterar senha':loc.pathname.startsWith('/documentacao/')?'Dossiê Digital':loc.pathname.startsWith('/faturamento/')?'Faturamento':loc.pathname.startsWith('/impostos/')?'Impostos':'ÔMEGA');
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><img className="brand-logo" src="/omega-logo-white.svg" alt="Grupo Ômega — Gestão de Empresas" /></div>
      <nav className="nav" aria-label="Navegação principal">
        {sections.map(section=><section className="nav-section" key={section.title}>
          <div className="nav-section-title">{section.title}</div>
          {section.links.map(([to,label,Icon])=>{
            const accounting=to==='/contabil/documentacao';
            const active=to==='/'?loc.pathname==='/':accounting?contabilActive:loc.pathname===to||loc.pathname.startsWith(to+'/');
            return <div key={to}><NavLink to={to} end={to==='/'} className={()=>'nav-link '+(active?'active':'')}>
              <Icon size={17}/><span>{label}</span><ChevronRight size={14} className="nav-arrow"/>
            </NavLink>{accounting&&contabilActive&&<div className="nav-sublist">
              <NavLink to="/contabil/documentacao" end className={({isActive})=>'nav-sub-link '+(isActive||loc.pathname.startsWith('/contabil/documentacao/empresa/')?'active':'')}>Documentação</NavLink>
              <NavLink to="/contabil/lancamentos-conferencias" className={({isActive})=>'nav-sub-link '+(isActive?'active':'')}>Lançamentos e Conferências</NavLink>
            </div>}</div>;
          })}
        </section>)}
        {usuario?.perfil==='ADMIN'&&<section className="nav-section"><div className="nav-section-title">ADMINISTRAÇÃO</div><NavLink to="/usuarios" className={({isActive})=>'nav-link '+(isActive?'active':'')}><Users size={17}/><span>Usuários</span><ChevronRight size={14} className="nav-arrow"/></NavLink></section>}
      </nav>
      <div className="sidebar-user"><span className="user-avatar">{(usuario?.nome||'U').slice(0,1).toUpperCase()}</span><div><strong>{usuario?.nome}</strong><small>{usuario?.perfil==='ADMIN'?'Administrador':'Usuário'}</small></div><button className="icon-button dark" title="Sair" onClick={()=>void logout()}><LogOut size={15}/></button></div>
      <div className="sidebar-note"><span>Dossiê empresarial</span><strong>Histórico permanente</strong><small>A situação atual é importante. O histórico nunca é perdido.</small></div>
    </aside>
    <main className="main-content"><header className="topbar"><div><span className="eyebrow">PLATAFORMA ÔMEGA</span><h1>{title}</h1></div><div className="topbar-user"><span className="top-user-badge"><ShieldCheck size={13}/> Sessão segura</span><div className="top-user-info"><strong>{usuario?.nome}</strong><span>{usuario?.email}</span></div><button className="icon-button" onClick={()=>void logout()} title="Sair"><LogOut size={15}/></button></div></header><Outlet/></main>
  </div>;
}
