import {createContext,useContext,useEffect,useMemo,useState,ReactNode} from 'react';
import {apiFetch} from '../services/api/client';

export type Usuario={id:number;nome:string;email:string;perfil:'ADMIN'|'USUARIO';deve_trocar_senha:boolean;ultimo_login?:string|null};
type LoginResponse={access_token:string;token_type:string;usuario:Usuario};
type AuthContextValue={usuario:Usuario|null;carregando:boolean;login:(email:string,senha:string)=>Promise<Usuario>;logout:()=>Promise<void>;recarregarUsuario:()=>Promise<Usuario|null>};
const AuthContext=createContext<AuthContextValue|null>(null);
const TOKEN_KEY='omega_access_token';

export function getToken(){return localStorage.getItem(TOKEN_KEY);}
export function clearToken(){localStorage.removeItem(TOKEN_KEY);}

export function AuthProvider({children}:{children:ReactNode}){
  const [usuario,setUsuario]=useState<Usuario|null>(null);
  const [carregando,setCarregando]=useState(true);

  async function recarregarUsuario(){
    const token=getToken();
    if(!token){setUsuario(null);return null;}
    try{const u=await apiFetch<Usuario>('/api/v1/auth/me');setUsuario(u);return u;}
    catch{clearToken();setUsuario(null);return null;}
  }

  useEffect(()=>{void recarregarUsuario().finally(()=>setCarregando(false));},[]);

  async function login(email:string,senha:string){
    const r=await apiFetch<LoginResponse>('/api/v1/auth/login',{method:'POST',body:JSON.stringify({email,senha})});
    localStorage.setItem(TOKEN_KEY,r.access_token);setUsuario(r.usuario);return r.usuario;
  }

  async function logout(){
    try{if(getToken()) await apiFetch('/api/v1/auth/logout',{method:'POST'});}catch{/* expiração já encerra a sessão */}
    clearToken();setUsuario(null);window.location.href='/login';
  }

  const value=useMemo(()=>({usuario,carregando,login,logout,recarregarUsuario}),[usuario,carregando]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(){
  const ctx=useContext(AuthContext);if(!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider');return ctx;
}
