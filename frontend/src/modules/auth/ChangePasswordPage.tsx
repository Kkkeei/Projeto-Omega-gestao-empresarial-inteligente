import {FormEvent,useState} from 'react';
import {LockKeyhole,ShieldCheck} from 'lucide-react';
import {apiFetch} from '../../services/api/client';
import {useAuth} from '../../auth/AuthContext';
import {useNavigate} from 'react-router-dom';

export function ChangePasswordPage(){
  const {usuario}=useAuth();const navigate=useNavigate();
  const [atual,setAtual]=useState('');const [nova,setNova]=useState('');const [confirmacao,setConfirmacao]=useState('');const [erro,setErro]=useState('');const [ok,setOk]=useState('');const [loading,setLoading]=useState(false);
  async function submit(e:FormEvent){e.preventDefault();setErro('');setOk('');if(nova!==confirmacao){setErro('As senhas novas não conferem.');return;}setLoading(true);try{await apiFetch('/api/v1/auth/alterar-senha',{method:'POST',body:JSON.stringify({senha_atual:atual,nova_senha:nova})});setOk('Senha alterada. Faça login novamente.');localStorage.removeItem('omega_access_token');setTimeout(()=>navigate('/login'),700);}catch(x){setErro(x instanceof Error?x.message:'Não foi possível alterar a senha.')}finally{setLoading(false)}}
  return <main className="login-page"><section className="login-card login-card-centered"><div><span className="eyebrow">PRIMEIRO ACESSO</span><h2>Defina sua nova senha</h2><p>{usuario?.nome||'Usuário'}, por segurança, altere a senha inicial antes de continuar.</p></div>{erro&&<div className="form-error">{erro}</div>}{ok&&<div className="form-success">{ok}</div>}<form onSubmit={submit} className="login-form"><label>Senha atual<div className="login-input"><LockKeyhole size={17}/><input type="password" value={atual} onChange={e=>setAtual(e.target.value)} required/></div></label><label>Nova senha<div className="login-input"><LockKeyhole size={17}/><input type="password" value={nova} onChange={e=>setNova(e.target.value)} minLength={8} required/></div></label><label>Confirme a nova senha<div className="login-input"><ShieldCheck size={17}/><input type="password" value={confirmacao} onChange={e=>setConfirmacao(e.target.value)} minLength={8} required/></div></label><button className="button primary login-submit" disabled={loading}>{loading?'Salvando...':'Alterar senha e continuar'}</button></form></section></main>;
}
