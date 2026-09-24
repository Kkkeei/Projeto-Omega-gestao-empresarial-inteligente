import {useEffect, useState} from 'react';
import {Building2, CheckCircle2, FileText, X} from 'lucide-react';
import {
  gerarDeclaracaoBancoBrasil,
  obterConfigBancoBrasil,
  salvarConfigBancoBrasil,
  visualizarDeclaracao,
  type BancoBrasilConfig,
} from './api';

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
};

export function BancoBrasilDeclarationModal({
  open,
  empresaId,
  empresaNome,
  onClose,
  onGenerated,
}: Props) {
  const [config, setConfig] = useState<BancoBrasilConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [error, setError] = useState('');
  const [gerada, setGerada] = useState<{ id: number; nome_arquivo: string } | null>(null);

  useEffect(() => {
    if (!open) {
      setConfig(DEFAULT_CONFIG);
      setLoading(false);
      setGerando(false);
      setError('');
      setGerada(null);
      return;
    }

    let ativo = true;
    setLoading(true);
    setError('');
    setGerada(null);

    void obterConfigBancoBrasil(empresaId)
      .then((dados) => {
        if (!ativo) return;
        setConfig({
          percentual_a_vista: Number(dados.percentual_a_vista ?? 20),
          percentual_a_prazo: Number(dados.percentual_a_prazo ?? 80),
        });
      })
      .catch((erro) => {
        if (!ativo) return;
        setError(erro instanceof Error ? erro.message : 'Não foi possível carregar as configurações do Banco do Brasil.');
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });

    return () => {
      ativo = false;
    };
  }, [open, empresaId]);

  function atualizarPercentual(campo: 'percentual_a_vista' | 'percentual_a_prazo', valor: string) {
    const numero = valor === '' ? 0 : Number(valor);
    setConfig((atual) => ({ ...atual, [campo]: Number.isFinite(numero) ? numero : 0 }));
    setError('');
  }

  const totalPercentual = Number(config.percentual_a_vista || 0) + Number(config.percentual_a_prazo || 0);

  async function gerar() {
    setError('');

    if (totalPercentual !== 100) {
      setError('Percentual à vista + percentual a prazo deve totalizar 100%.');
      return;
    }

    setGerando(true);
    try {
      const configSalva = await salvarConfigBancoBrasil(empresaId, {
        percentual_a_vista: Number(config.percentual_a_vista),
        percentual_a_prazo: Number(config.percentual_a_prazo),
      });
      setConfig(configSalva);

      const declaracao = await gerarDeclaracaoBancoBrasil(empresaId, {
        percentual_a_vista: Number(configSalva.percentual_a_vista),
        percentual_a_prazo: Number(configSalva.percentual_a_prazo),
      });

      setGerada({ id: declaracao.id, nome_arquivo: declaracao.nome_arquivo });
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
            <span className="fat-modal-icon"><Building2 size={17} /></span>
            <div>
              <strong>Banco do Brasil</strong>
              <small>{empresaNome}</small>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} disabled={gerando}>
            <X size={15} />
          </button>
        </div>

        <div className="fat-bb-config-body">
          {loading ? (
            <div className="fat-bb-loading">Carregando configurações...</div>
          ) : gerada ? (
            <div className="fat-bb-success-box">
              <CheckCircle2 size={28} />
              <strong>Declaração gerada com sucesso</strong>
              <span>{gerada.nome_arquivo}</span>
            </div>
          ) : (
            <>
              <div className="fat-form-highlight">
                <span>Percentuais para o preenchimento do Banco do Brasil</span>
                <strong>À vista + a prazo deve totalizar 100%.</strong>
              </div>

              <div className="fat-two-inputs fat-bb-percentuais">
                <label>
                  Percentual à vista *
                  <div className="fat-input-suffix">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={config.percentual_a_vista}
                      onChange={(event) => atualizarPercentual('percentual_a_vista', event.target.value)}
                    />
                    <span>%</span>
                  </div>
                </label>

                <label>
                  Percentual a prazo *
                  <div className="fat-input-suffix">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={config.percentual_a_prazo}
                      onChange={(event) => atualizarPercentual('percentual_a_prazo', event.target.value)}
                    />
                    <span>%</span>
                  </div>
                </label>
              </div>

              <div className={`fat-bb-percentual-total ${totalPercentual === 100 ? 'ok' : 'invalid'}`}>
                <span>Total</span>
                <strong>{totalPercentual.toFixed(2).replace('.', ',')}%</strong>
              </div>

              {error && <div className="fat-entry-error form-error"><X size={14} />{error}</div>}
            </>
          )}
        </div>

        {!loading && (
          <div className="fat-modal-actions">
            <button className="button secondary" onClick={onClose} disabled={gerando}>Cancelar</button>
            {gerada ? (
              <button className="button primary" onClick={() => void visualizarDeclaracao(gerada.id)}>
                <FileText size={13} /> Abrir PDF
              </button>
            ) : (
              <button className="button primary" onClick={() => void gerar()} disabled={gerando || loading}>
                {gerando ? 'Gerando...' : 'Gerar declaração'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
