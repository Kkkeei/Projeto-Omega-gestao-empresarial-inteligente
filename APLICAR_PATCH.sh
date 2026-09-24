#!/usr/bin/env bash
set -euo pipefail
PROJETO="${1:-.}"
DEST="$PROJETO/frontend/src/modules/faturamento"
PAGE="$DEST/FaturamentoPage.tsx"
CSS="$DEST/Faturamento.css"
MODAL="$DEST/BancoBrasilDeclarationModal.tsx"

[[ -f "$PAGE" ]] || { echo "ERRO: $PAGE não encontrado"; exit 1; }
[[ -f "$CSS" ]] || { echo "ERRO: $CSS não encontrado"; exit 1; }

BACKUP="$PROJETO/backup_faturamento_bb_v12_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP"
cp "$PAGE" "$BACKUP/FaturamentoPage.tsx"
cp "$CSS" "$BACKUP/Faturamento.css"
[[ -f "$MODAL" ]] && cp "$MODAL" "$BACKUP/BancoBrasilDeclarationModal.tsx"

# Recupera automaticamente a última cópia feita pelo patch V11, se existir.
# Isso desfaz somente o frontend quebrado pelo patch anterior antes de aplicar
# a alteração cirúrgica desta versão.
LATEST_BACKUP=$(find "$PROJETO" -maxdepth 1 -type d -name 'backup_frontend_faturamento_*' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)
if [[ -n "${LATEST_BACKUP:-}" && -f "$LATEST_BACKUP/FaturamentoPage.tsx" && -f "$LATEST_BACKUP/Faturamento.css" ]]; then
  cp "$LATEST_BACKUP/FaturamentoPage.tsx" "$PAGE"
  cp "$LATEST_BACKUP/Faturamento.css" "$CSS"
  [[ -f "$LATEST_BACKUP/BancoBrasilDeclarationModal.tsx" ]] && cp "$LATEST_BACKUP/BancoBrasilDeclarationModal.tsx" "$MODAL"
  echo "Base restaurada do backup anterior: $LATEST_BACKUP"
fi

python3 - "$PAGE" "$CSS" "$MODAL" <<'PY'
from pathlib import Path
import re, sys

page_path, css_path, modal_path = map(Path, sys.argv[1:])
page = page_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')

# 1) Importa o modal sem depender de novas funções da API.
if "./BancoBrasilDeclarationModal" not in page:
    marker = "import {FaturamentoEntryModal} from './FaturamentoEntryModal';"
    if marker not in page:
        raise SystemExit("ERRO: não encontrei o import de FaturamentoEntryModal; patch abortado para não corromper a página.")
    page = page.replace(marker, marker + "\nimport {BancoBrasilDeclarationModal} from './BancoBrasilDeclarationModal';", 1)

# 2) Estado do modal BB.
if "bancoBrasilEmpresa" not in page:
    marker = "  const [successMessage,setSuccessMessage]=useState('');"
    if marker not in page:
        raise SystemExit("ERRO: não encontrei o bloco de estados esperado; patch abortado.")
    page = page.replace(marker, marker + "\n  const [bancoBrasilEmpresa,setBancoBrasilEmpresa]=useState<FaturamentoEmpresa|null>(null);", 1)

# 3) Quarto card sem alterar os outros três.
if "fat-declaration-choice-bb" not in page:
    old = """          <button className=\"fat-declaration-choice\" onClick={()=>setModoDeclaracao('personalizada')} disabled={busyDeclaration}><CalendarDays size={20}/><strong>Personalizado</strong><span>Escolha o período inicial e final da declaração.</span></button>\n"""
    new = old + """          <button className=\"fat-declaration-choice fat-declaration-choice-bb\" onClick={()=>{setDeclaracaoOpen(false);setBancoBrasilEmpresa(empresaDeclaracao)}} disabled={busyDeclaration}><Building2 size={20}/><strong>Banco do Brasil</strong><span>Gerar a relação de faturamento do Banco do Brasil.</span></button>\n"""
    if old not in page:
        raise SystemExit("ERRO: bloco dos três cards não encontrado; patch abortado.")
    page = page.replace(old, new, 1)

# 4) Renderiza o modal BB no final do componente.
if "open={Boolean(bancoBrasilEmpresa)}" not in page:
    marker = "\n  </div>\n}"
    insert = """\n    {bancoBrasilEmpresa&&<BancoBrasilDeclarationModal\n      open={Boolean(bancoBrasilEmpresa)}\n      empresaId={bancoBrasilEmpresa.id}\n      empresaNome={bancoBrasilEmpresa.razao_social}\n      onClose={()=>setBancoBrasilEmpresa(null)}\n    />}\n"""
    if marker not in page:
        raise SystemExit("ERRO: final do componente não encontrado; patch abortado.")
    page = page.replace(marker, insert + marker, 1)

page_path.write_text(page, encoding='utf-8')

# 5) CSS: 4 colunas no desktop + responsivo + esconder apenas o seletor antigo da competência.
append = r'''

/* PATCH BB V12 — não altera a lógica do faturamento; apenas o layout e o novo card. */
.fat-competencia-select { display: none !important; }
.fat-declaration-choice-grid { grid-template-columns: repeat(4, minmax(0, 1fr)) !important; }
.fat-declaration-choice-bb { border-color: #d8c52a; background: linear-gradient(180deg,#fffef4 0%,#fff 100%); }
.fat-declaration-choice-bb:hover,
.fat-declaration-choice-bb.active { border-color: #c7ab00; background: #fffdf0; }
.fat-declaration-choice-bb svg { color: #b28e00; }
.fat-bb-modal { width: min(760px, 100%); }
.fat-bb-percentuais { margin-bottom: 12px; }
.fat-input-suffix { display: flex; align-items: stretch; }
.fat-input-suffix input { flex: 1; min-width: 0; border-top-right-radius: 0; border-bottom-right-radius: 0; }
.fat-input-suffix span { min-width: 34px; display: grid; place-items: center; border: 1px solid #d6dde7; border-left: 0; background: #f7f9fc; color: #64738a; border-top-right-radius: 7px; border-bottom-right-radius: 7px; font-size: 9px; }
.fat-bb-percentual-total { display:flex; align-items:center; justify-content:space-between; padding:10px 11px; border-radius:8px; border:1px solid #e3e8ee; background:#fbfcfe; margin-top:8px; }
.fat-bb-percentual-total strong { color:#1671df; }
.fat-bb-percentual-total.invalid { border-color:#f0c9c9; background:#fff8f8; }
.fat-bb-percentual-total.invalid strong { color:#c0392b; }
.fat-bb-progress { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; min-height:190px; color:#65738a; font-size:10px; text-align:center; }
.fat-bb-success { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px; min-height:160px; color:#2d6f51; text-align:center; }
.fat-bb-success svg { color:#10a56c; }
@media(max-width:1050px){ .fat-declaration-choice-grid { grid-template-columns:repeat(2,minmax(0,1fr)) !important; } }
@media(max-width:650px){ .fat-declaration-choice-grid { grid-template-columns:1fr !important; } }
'''
if "PATCH BB V12" not in css:
    css += append
css_path.write_text(css, encoding='utf-8')
PY

cat > "$MODAL" <<'TSX'
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
TSX

chmod +x "$PROJETO/" 2>/dev/null || true

echo "PATCH V12 aplicado. Backup: $BACKUP"
