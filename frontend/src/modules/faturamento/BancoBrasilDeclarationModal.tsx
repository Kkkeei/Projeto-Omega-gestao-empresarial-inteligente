import {useEffect, useState} from 'react';
import {Building2, CheckCircle2, FileText, LoaderCircle, X} from 'lucide-react';
import {gerarDeclaracaoBancoBrasil, visualizarDeclaracao, type BancoBrasilConfig} from './api';

type Props = {
  open: boolean;
  empresaId: number;
  empresaNome: string;
  onClose: () => void;
  onGenerated?: () => Promise<void> | void;
};

const DEFAULT_CONFIG: BancoBrasilConfig = {
  percentual_a_vista: 20,
  percentual_a_prazo: 80,
  percentual_cartao: null,
  percentual_cheque: null,
  percentual_boleto: null,
  prazo_medio_dias: null,
};

export function BancoBrasilDeclarationModal({open,empresaId,empresaNome,onClose,onGenerated}: Props){
  const [config,setConfig]=useState<BancoBrasilConfig>(DEFAULT_CONFIG);
  const [gerando,setGerando]=useState(false);
  const [error,setError]=useState('');
  const [gerada,setGerada]=useState<{id:number;nome_arquivo:string}|null>(null);

  useEffect(()=>{
    if(!open){
      setConfig(DEFAULT_CONFIG);
      setGerando(false);
      setError('');
      setGerada(null);
    }
  },[open]);

  if(!open)return null;
  const soma=Number(config.percentual_a_vista||0)+Number(config.percentual_a_prazo||0);

  function atualizar(campo:'percentual_a_vista'|'percentual_a_prazo',valor:string){
    const numero=Number(valor.replace(',','.'));
    setConfig(current=>({...current,[campo]:Number.isFinite(numero)?numero:0}));
  }

  async function abrirPdf(){
    if(!gerada)return;
    setError('');
    try{
      await visualizarDeclaracao(gerada.id);
    }catch(e){
      setError(e instanceof Error?e.message:'Não foi possível abrir o PDF da declaração.');
    }
  }

  async function gerar(){
    setError('');
    if(Math.abs(soma-100)>0.01){setError('Percentual à vista + percentual a prazo deve totalizar 100%.');return;}
    setGerando(true);
    try{
      const declaracao=await gerarDeclaracaoBancoBrasil(empresaId,{...config,percentual_cartao:null,percentual_cheque:null,percentual_boleto:null,prazo_medio_dias:null});
      setGerada({id:declaracao.id,nome_arquivo:declaracao.nome_arquivo});
      setGerando(false);
      // A atualização do histórico da página da empresa não pode bloquear o
      // modal de sucesso. O PDF já foi gerado; a atualização da tela é paralela.
      void Promise.resolve(onGenerated?.()).catch(()=>undefined);
    }catch(e){
      setError(e instanceof Error?e.message:'Não foi possível gerar a declaração do Banco do Brasil.');
    }finally{setGerando(false);}
  }

  return <div className="fat-modal-backdrop" onMouseDown={()=>!gerando&&onClose()}>
    <div className="fat-modal fat-bb-modal" onMouseDown={event=>event.stopPropagation()}>
      <div className="fat-modal-header"><div><span className="fat-modal-icon"><Building2 size={17}/></span><div><strong>Banco do Brasil</strong><small>{empresaNome}</small></div></div><button className="icon-button" onClick={onClose} disabled={gerando}><X size={15}/></button></div>
      {!gerando&&!gerada&&<div className="fat-modal-body">
        <div className="fat-form-highlight"><span>Percentuais da declaração</span><strong>À vista + a prazo deve totalizar 100%.</strong></div>
        <div className="fat-entry-two-fields">
          <label>Percentual à vista *<input type="number" step="0.01" min="0" max="100" value={config.percentual_a_vista} onChange={event=>atualizar('percentual_a_vista',event.target.value)}/></label>
          <label>Percentual a prazo *<input type="number" step="0.01" min="0" max="100" value={config.percentual_a_prazo} onChange={event=>atualizar('percentual_a_prazo',event.target.value)}/></label>
        </div>
        <div className={`fat-form-highlight compact ${Math.abs(soma-100)>0.01?'invalid':''}`}><span>Total da divisão</span><strong>{soma.toFixed(2).replace('.',',')}%</strong></div>
        {error&&<div className="fat-entry-error form-error"><X size={14}/>{error}</div>}
      </div>}
      {gerando&&<div className="fat-bb-progress"><LoaderCircle size={28} className="spin"/><strong>Gerando declaração do Banco do Brasil...</strong><span>O ÔMEGA está preenchendo o formulário oficial e preparando o PDF.</span><small>Isso pode levar alguns segundos porque depende do site do Banco do Brasil.</small></div>}
      {!gerando&&gerada&&<div className="fat-bb-success"><CheckCircle2 size={34}/><strong>Declaração gerada com sucesso</strong><span>{gerada.nome_arquivo}</span></div>}
      {!gerando&&error&&<div className="fat-entry-error form-error"><X size={14}/>{error}</div>}
      {!gerando&&<div className="fat-modal-actions"><button className="button secondary" onClick={onClose}>Fechar</button>{gerada?<button className="button primary" onClick={()=>void abrirPdf()}><FileText size={13}/> Abrir PDF</button>:<button className="button primary" onClick={()=>void gerar()} disabled={Math.abs(soma-100)>0.01}>Gerar declaração</button>}</div>}
    </div>
  </div>;
}
