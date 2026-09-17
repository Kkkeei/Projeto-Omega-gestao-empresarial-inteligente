import {BrowserRouter,Routes,Route} from 'react-router-dom';
import {Layout} from '../components/layout/Layout';
import {DashboardPage} from '../modules/dashboard/DashboardPage';
import {EmpresasPage} from '../modules/empresas/EmpresasPage';
import {EmpresaDetailPage} from '../modules/empresas/EmpresaDetailPage';
import {CertidoesPage} from '../modules/certidoes/CertidoesPage';
import {PendenciasPage} from '../modules/pendencias/PendenciasPage';
import {DocumentacaoPage} from '../modules/documentacao/DocumentacaoPage';
import {EmpresaDocumentacaoPage} from '../modules/documentacao/EmpresaDocumentacaoPage';
import {LoginPage} from '../modules/auth/LoginPage';
import {RegisterPage} from '../modules/auth/RegisterPage';
import {ForgotPasswordPage} from '../modules/auth/ForgotPasswordPage';
import {ResetPasswordPage} from '../modules/auth/ResetPasswordPage';
import {ChangePasswordPage} from '../modules/auth/ChangePasswordPage';
import {UsuariosPage} from '../modules/usuarios/UsuariosPage';
import {AuthProvider,useAuth} from '../auth/AuthContext';
import {ProtectedRoute} from '../auth/ProtectedRoute';
import type {ReactNode} from 'react';
import {FaturamentoPage} from '../modules/faturamento/FaturamentoPage';
import {EmpresaFaturamentoPage} from '../modules/faturamento/EmpresaFaturamentoPage';

function AdminOnly({children}:{children:ReactNode}){const {usuario}=useAuth();return usuario?.perfil==='ADMIN'?<>{children}</>:<div className="page"><div className="panel empty"><strong>Acesso restrito</strong><span>Seu perfil não possui permissão para administrar usuários.</span></div></div>}

export function App(){return <AuthProvider><BrowserRouter><Routes><Route path="/login" element={<LoginPage/>}/><Route path="/registrar" element={<RegisterPage/>}/><Route path="/esqueci-senha" element={<ForgotPasswordPage/>}/><Route path="/redefinir-senha" element={<ResetPasswordPage/>}/><Route path="/alterar-senha" element={<ProtectedRoute><ChangePasswordPage/></ProtectedRoute>}/><Route element={<ProtectedRoute><Layout/></ProtectedRoute>}><Route path="/" element={<DashboardPage/>}/><Route path="/empresas" element={<EmpresasPage/>}/><Route path="/empresas/:id" element={<EmpresaDetailPage/>}/><Route path="/certidoes" element={<CertidoesPage/>}/>
<Route path="/documentacao" element={<DocumentacaoPage/>}/>
<Route path="/documentacao/empresa/:id" element={<EmpresaDocumentacaoPage/>}/><Route path="/pendencias" element={<PendenciasPage/>}/><Route path="/faturamento" element={<FaturamentoPage/>}/><Route path="/faturamento/empresa/:id" element={<EmpresaFaturamentoPage/>}/><Route path="/usuarios" element={<AdminOnly><UsuariosPage/></AdminOnly>}/></Route></Routes></BrowserRouter></AuthProvider>}
