import type {ReactNode} from 'react';
import {Navigate,useLocation} from 'react-router-dom';
import {useAuth} from './AuthContext';
import {Loading} from '../components/ui/Loading';

export function ProtectedRoute({children}:{children:ReactNode}){
  const {usuario,carregando}=useAuth();const loc=useLocation();
  if(carregando) return <div style={{minHeight:'100vh',display:'grid',placeItems:'center'}}><Loading text="Validando sessão..."/></div>;
  if(!usuario) return <Navigate to="/login" replace state={{from:loc.pathname}}/>;
  if(usuario.deve_trocar_senha && loc.pathname!=='/alterar-senha') return <Navigate to="/alterar-senha" replace/>;
  return <>{children}</>;
}
