import {NavLink,Outlet,useLocation} from 'react-router-dom';
import {LayoutDashboard,Building2,FileCheck2,AlertTriangle,LogOut,Users,ShieldCheck,Folder,BadgeDollarSign,ReceiptText,KeyRound,FileText,ChevronDown,Workflow} from 'lucide-react';
import {useAuth} from '../../auth/AuthContext';

const groups=[
  {label:'VISÃO GERAL',links:[['/','Painel de trabalho',LayoutDashboard]]},
  {label:'GESTÃO EMPRESARIAL',links:[['/empresas','Empresas',Building2],['/documentacao','Documentação',Folder]]},
  {label:'ROTINAS FISCAIS',links:[['/impostos','Impostos',ReceiptText],['/faturamento','Faturamento',BadgeDollarSign],['/nfse','Notas de serviço',FileText]]},
  {label:'REGULARIDADE E ACESSO',links:[['/certidoes','Certidões',FileCheck2],['/certificados','Certificados',KeyRound],['/pendencias','Pendências',AlertTriangle]]},
] as const;

function tituloDaRota(path:string){
  if(path==='/') return 'Painel de trabalho';
  if(path==='/usuarios') return 'Usuários e acessos';
  if(path==='/alterar-senha') return 'Segurança da conta';
  if(path.startsWith('/documentacao')) return 'Documentação';
  if(path.startsWith('/faturamento')) return 'Faturamento';
  if(path.startsWith('/impostos')) return 'Impostos';
  if(path.startsWith('/empresas')) return 'Empresas';
  if(path.startsWith('/certidoes')) return 'Certidões';
  if(path.startsWith('/certificados')) return 'Certificados';
  if(path.startsWith('/nfse')) return 'Notas de serviço';
  if(path.startsWith('/pendencias')) return 'Pendências';
  return 'ÔMEGA';
}

export function Layout(){
  const loc=useLocation();
  const {usuario,logout}=useAuth();
  const title=tituloDaRota(loc.pathname);
  return <div className="app-shell">
    <aside className="sidebar">
      <NavLink to="/" className="brand" aria-label="ÔMEGA — início">
        <div className="brand-mark"><span>Ω</span></div>
        <div className="brand-copy"><strong>ômega<span>.</span></strong><span>GESTÃO EMPRESARIAL</span></div>
      </NavLink>
      <div className="sidebar-context"><span className="context-mark"><Workflow size={15}/></span><div><strong>Central de operações</strong><small>Ambiente de trabalho</small></div><ChevronDown size={14}/></div>
      <nav className="nav" aria-label="Navegação principal">
        {groups.map(group=><div className="nav-group" key={group.label}>
          <span className="nav-group-label">{group.label}</span>
          {group.links.map(([to,label,Icon])=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>`nav-link ${isActive?'active':''}`}>
            <Icon size={17} strokeWidth={1.8}/><span>{label}</span>
          </NavLink>)}
        </div>)}
        {usuario?.perfil==='ADMIN'&&<div className="nav-group"><span className="nav-group-label">ADMINISTRAÇÃO</span><NavLink to="/usuarios" className={({isActive})=>`nav-link ${isActive?'active':''}`}><Users size={17} strokeWidth={1.8}/><span>Usuários e acessos</span></NavLink></div>}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-note"><span className="note-icon"><ShieldCheck size={15}/></span><div><strong>Seus dados, sob controle</strong><small>Área de trabalho protegida por autenticação.</small></div></div>
        <div className="sidebar-user"><span className="user-avatar">{(usuario?.nome||'U').slice(0,1).toUpperCase()}</span><div className="sidebar-user-copy"><strong>{usuario?.nome||'Usuário'}</strong><small>{usuario?.perfil==='ADMIN'?'Administrador':'Acesso operacional'}</small></div><button className="icon-button dark" title="Sair da conta" aria-label="Sair da conta" onClick={()=>void logout()}><LogOut size={16}/></button></div>
      </div>
    </aside>
    <main className="main-content">
      <header className="topbar">
        <div className="topbar-title"><span className="breadcrumb-root">ÔMEGA <span>/</span> Workspace</span><h1>{title}</h1></div>
        <div className="topbar-user"><span className="top-user-badge"><span className="secure-dot"/><ShieldCheck size={14}/> Ambiente seguro</span><div className="top-user-info"><strong>{usuario?.nome}</strong><span>{usuario?.email}</span></div><button className="icon-button" onClick={()=>void logout()} title="Sair" aria-label="Sair"><LogOut size={16}/></button></div>
      </header>
      <div className="workspace-content"><Outlet/></div>
    </main>
  </div>;
}
