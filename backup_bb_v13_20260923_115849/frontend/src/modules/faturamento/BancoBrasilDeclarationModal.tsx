import {useEffect, useState} from 'react';
import {Building2, CheckCircle2, FileText, X} from 'lucide-react';
import {gerarDeclaracaoBancoBrasil, visualizarDeclaracao} from './api';

type Props = {
  open: boolean;
  empresaId: number;
  empresaNome: string;
  onClose: () => void;
  onGenerated?: () => Promise<void> | void;
};

export function BancoBrasilDeclarationModal({open, empresaId, empresaNome, onClose, onGenerated}: Props) {
  const [aVista, setAVista] = useState(20);
  const [aPrazo, setAPrazo] = useState(80);
  const [gerando, setGerando] = useState(false);
  const [error, setError] = useState('');
  const [gerada, setGerada] = useState<{id: number; nome_arquivo: string} | null>(null);

  useEffect(() => {
    if (!open) {
      setAVista(20);
      setAPrazo(80);
      setGerando(false);
      setError('');
      setGerada(null);
    }
  }, [open]);

  const total = Number(aVista || 0) + Number(aPrazo || 0);

  async function gerar() {
    setError('');
    if (total !== 100) {
      setError('Percentual à vista + percentual a prazo deve totalizar 100%.');
      return;
    }
    setGerando(true);
    try {
      const declaracao = await gerarDeclaracaoBancoBrasil(empresaId, {
        percentual_a_vista: Number(aVista),
        percentual_a_prazo: Number(aPrazo),
      });
      setGerada({id: declaracao.id, nome_arquivo: declaracao.nome_arquivo});
      await onGenerated?.();
    } catch (erro) {
      setError(erro instanceof Error ? erro.message : 'Não foi possível gerar a declaração do Banco do Brasil.');
    } finally {
      setGerando(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fat-modal-backdrop" onMouseDown={() => !gerando && onClose()}>
      <div className="fat-modal fat-bb-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="fat-modal-header">
          <div>
            <span className="fat-modal-icon"><Building2 size={17}/></span>
            <div><strong>Banco do Brasil</strong><small>{empresaNome}</small></div>
          </div>
          <button className="icon-button" onClick={onClose} disabled={gerando}><X size={15}/></button>
        </div>

        {!gerada && !gerando && (
          <div className="fat-modal-body">
            <div className="fat-form-highlight">
              <span>Percentuais usados no formulário do Banco do Brasil</span>
              <strong>À vista + a prazo deve totalizar 100%.</strong>
            </div>

            <div className="fat-two-inputs fat-bb-percentuais">
              <label>
                Percentual à vista *
                <div className="fat-input-suffix">
                  <input type="number" min="0" max="100" step="0.01" value={aVista} onChange={(e) => setAVista(Number(e.target.value || 0))}/>
                  <span>%</span>
                </div>
              </label>
              <label>
                Percentual a prazo *
                <div className="fat-input-suffix">
                  <input type="number" min="0" max="100" step="0.01" value={aPrazo} onChange={(e) => setAPrazo(Number(e.target.value || 0))}/>
                  <span>%</span>
                </div>
              </label>
            </div>

            <div className={`fat-bb-percentual-total ${total === 100 ? '' : 'invalid'}`}>
              <span>Total</span>
              <strong>{total.toFixed(2).replace('.', ',')}%</strong>
            </div>
            {error && <div className="fat-entry-error form-error"><X size={14}/>{error}</div>}
          </div>
        )}

        {gerando && (
          <div className="fat-bb-progress">
            <Building2 size={28}/>
            <strong>Gerando declaração do Banco do Brasil...</strong>
            <span>O ÔMEGA está preenchendo e salvando o formulário oficial.</span>
          </div>
        )}

        {!gerando && gerada && (
          <div className="fat-bb-success">
            <CheckCircle2 size={34}/>
            <strong>Declaração gerada com sucesso</strong>
            <span>{gerada.nome_arquivo}</span>
          </div>
        )}

        {!gerando && gerada && error && <div className="fat-entry-error form-error">{error}</div>}

        {!gerando && (
          <div className="fat-modal-actions">
            <button className="button secondary" onClick={onClose}>Fechar</button>
            {gerada ? (
              <button className="button primary" onClick={() => void visualizarDeclaracao(gerada.id)}><FileText size={13}/> Abrir PDF</button>
            ) : (
              <button className="button primary" onClick={() => void gerar()} disabled={total !== 100}>Gerar declaração</button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
