import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCw, Edit3, Power, History, ShieldCheck, X } from "lucide-react";
import { buscarEmpresa, sincronizarEmpresa, atualizarEmpresa, inativarEmpresa, alterarRegime, historicoEmpresa } from "../../services/api/empresas";
import type { Empresa, Historico } from "../../types";
import { Loading } from "../../components/ui/Loading";
import { ErrorState } from "../../components/ui/ErrorState";

type EmpresaEditPayload = Partial<Pick<Empresa,
  "nome_fantasia" | "inscricao_estadual" | "inscricao_municipal" | "email" | "nire" |
  "data_entrada" | "data_abertura" | "natureza_juridica" | "porte" | "capital_social" |
  "cnae_principal" | "cnaes_secundarios" | "logradouro" | "numero" | "complemento" |
  "bairro" | "municipio" | "codigo_ibge" | "uf" | "cep" | "telefone" | "responsavel" |
  "segmento" | "grupo_empresarial" | "observacoes"
>>;

export function EmpresaDetailPage() {
  const { id } = useParams();
  const eid = Number(id);
  const [e, setE] = useState<Empresa | null>(null);
  const [h, setH] = useState<Historico[]>([]);
  const [err, setErr] = useState("");
  const [edit, setEdit] = useState(false);
  const [sync, setSync] = useState(false);
  const [saving, setSaving] = useState(false);
  const [regimeOpen, setRegimeOpen] = useState(false);
  const [regimeSaving, setRegimeSaving] = useState(false);

  const load = async () => {
    try {
      setErr("");
      const [empresa, historico] = await Promise.all([buscarEmpresa(eid), historicoEmpresa(eid)]);
      setE(empresa);
      setH(historico.historico);
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Erro ao carregar empresa.");
    }
  };

  useEffect(() => { if (eid) load(); }, [eid]);

  if (err && !e) return <ErrorState message={err} onRetry={load} />;
  if (!e) return <Loading />;

  async function sincronizar() {
    setSync(true); setErr("");
    try { const r = await sincronizarEmpresa(e.id); setE(r.empresa); await load(); }
    catch (x) { setErr(x instanceof Error ? x.message : "Falha na sincronização."); }
    finally { setSync(false); }
  }

  async function salvar(payload: EmpresaEditPayload) {
    setSaving(true); setErr("");
    try { setE(await atualizarEmpresa(e.id, payload)); setEdit(false); await load(); }
    catch (x) { setErr(x instanceof Error ? x.message : "Falha ao atualizar."); }
    finally { setSaving(false); }
  }

  async function inativar() {
    const dataSaida = window.prompt("Informe a data de saída (AAAA-MM-DD):");
    if (!dataSaida) return;
    const observacao = window.prompt("Observação (opcional):") || "";
    setErr("");
    try { setE(await inativarEmpresa(e.id, dataSaida, observacao)); await load(); }
    catch (x) { setErr(x instanceof Error ? x.message : "Falha ao inativar."); }
  }

  async function regime(novo: string, mes: number, ano: number, observacao: string) {
    setRegimeSaving(true); setErr("");
    try { setE(await alterarRegime(e.id, novo, mes, ano, observacao)); setRegimeOpen(false); await load(); }
    catch (x) { setErr(x instanceof Error ? x.message : "Falha ao alterar regime."); }
    finally { setRegimeSaving(false); }
  }

  return (
    <div className="page">
      <div className="page-heading">
        <div>
          <Link className="back-link" to="/empresas"><ArrowLeft size={15} /> Empresas</Link>
          <span className="eyebrow">DOSSIÊ EMPRESARIAL DIGITAL</span>
          <h2>{e.razao_social}</h2>
          <p>{e.nome_fantasia || "Sem nome fantasia"} · CNPJ {e.cnpj}</p>
        </div>
        <div className="actions">
          <button className="button secondary" onClick={() => setEdit(!edit)}><Edit3 size={15} /> {edit ? "Cancelar edição" : "Editar"}</button>
          <button className="button secondary" onClick={sincronizar} disabled={sync}><RefreshCw size={15} /> {sync ? "Sincronizando..." : "Sincronizar"}</button>
          {e.ativo ? <button className="button danger" onClick={inativar}><Power size={15} /> Inativar</button> : null}
        </div>
      </div>

      {err && <div className="form-error">{err}</div>}

      {edit ? <Editor empresa={e} onSave={salvar} saving={saving} onCancel={() => setEdit(false)} /> : (
        <>
          <div className="detail-grid">
            <div className="panel">
              <div className="panel-header"><div><span className="eyebrow">CADASTRO</span><h3>Dados da empresa</h3></div><span className={`badge ${e.ativo ? "success" : "neutral"}`}>{e.ativo ? "ATIVA" : "INATIVA"}</span></div>
              <div className="details">
                {[
                  ["CNPJ", e.cnpj], ["Inscrição Estadual", e.inscricao_estadual], ["Inscrição Municipal", e.inscricao_municipal], ["E-mail", e.email], ["NIRE", e.nire], ["Regime Tributário", e.regime_tributario], ["Data de Entrada", e.data_entrada], ["Data de Saída", e.data_saida], ["Data de Abertura", e.data_abertura], ["CNAE Principal", e.cnae_principal], ["Capital Social", e.capital_social != null ? `R$ ${Number(e.capital_social).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : null], ["Endereço", [e.logradouro, e.numero, e.complemento].filter(Boolean).join(", ")], ["Bairro", e.bairro], ["Município", e.municipio], ["UF", e.uf], ["CEP", e.cep], ["Telefone", e.telefone],
                ].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value || "—"}</strong></div>)}
              </div>
            </div>

            <div className="side-stack">
              <div className="panel"><div className="panel-header"><div><span className="eyebrow">REGIME</span><h3>Controle tributário</h3></div><ShieldCheck size={18} /></div><div className="side-content"><strong>{e.regime_tributario || "Não informado"}</strong><p>O regime fica bloqueado na edição cadastral. Para alterá-lo, use a ação específica e informe mês/ano da mudança.</p><button className="button secondary" onClick={() => setRegimeOpen(true)}>Alterar regime tributário</button></div></div>
              <div className="panel"><div className="panel-header"><div><span className="eyebrow">HISTÓRICO</span><h3>Últimos eventos</h3></div><History size={18} /></div><div className="history-list">{h.slice(0, 8).map(x => <div className="history-item" key={x.id}><strong>{x.tipo_evento}</strong><span>{x.descricao || "—"}</span><small>{x.criado_em} · {x.origem || "—"}</small></div>)}</div></div>
            </div>
          </div>
        </>
      )}

      {regimeOpen && <RegimeModal
        atual={e.regime_tributario || "Não informado"}
        onClose={() => setRegimeOpen(false)}
        onSave={regime}
        saving={regimeSaving}
      />}
    </div>
  );
}

function RegimeModal({ atual, onClose, onSave, saving }: {
  atual: string;
  onClose: () => void;
  onSave: (regime: string, mes: number, ano: number, observacao: string) => void;
  saving: boolean;
}) {
  const hoje = new Date();
  const [novo, setNovo] = useState("");
  const [mes, setMes] = useState(String(hoje.getMonth() + 1).padStart(2, "0"));
  const [ano, setAno] = useState(String(hoje.getFullYear()));
  const [observacao, setObservacao] = useState("");
  const opcoes = ["Simples Nacional", "Lucro Presumido", "Lucro Real"];
  const confirmar = () => {
    const m = Number(mes); const a = Number(ano);
    if (!novo || novo === atual || m < 1 || m > 12 || a < 2000 || a > 2100) return;
    onSave(novo, m, a, observacao.trim());
  };
  return <div className="modal-backdrop" onMouseDown={onClose}>
    <div className="modal-card regime-modal" onMouseDown={e => e.stopPropagation()}>
      <div className="modal-head"><div><span className="eyebrow">ALTERAÇÃO TRIBUTÁRIA</span><h3>Alterar regime da empresa</h3></div><button className="icon-button" onClick={onClose} title="Fechar"><X size={15}/></button></div>
      <div className="regime-modal-body">
        <div className="regime-current"><span>Regime atual</span><strong>{atual}</strong></div>
        <label> Novo regime
          <select value={novo} onChange={e => setNovo(e.target.value)}>
            <option value="">Selecione</option>
            {opcoes.map(x => <option key={x} value={x} disabled={x === atual}>{x}</option>)}
          </select>
        </label>
        <div className="regime-date-grid">
          <label>Mês de início<select value={mes} onChange={e=>setMes(e.target.value)}>{Array.from({length:12},(_,i)=>{const v=String(i+1).padStart(2,'0');return <option key={v} value={v}>{v}</option>})}</select></label>
          <label>Ano de início<input inputMode="numeric" maxLength={4} value={ano} onChange={e=>setAno(e.target.value.replace(/\D/g,'').slice(0,4))}/></label>
        </div>
        <label>Observação <span className="optional">(opcional)</span><textarea value={observacao} onChange={e=>setObservacao(e.target.value)} placeholder="Ex.: alteração por opção tributária para 2027." /></label>
        <div className="regime-note">A alteração será registrada no histórico da empresa com o regime anterior, o novo regime e a data de início.</div>
      </div>
      <div className="modal-actions"><button className="button secondary" onClick={onClose}>Cancelar</button><button className="button primary" onClick={confirmar} disabled={saving || !novo || novo === atual}>{saving ? 'Salvando...' : 'Confirmar alteração'}</button></div>
    </div>
  </div>;
}

function Editor({ empresa, onSave, saving, onCancel }: { empresa: Empresa; onSave: (p: EmpresaEditPayload) => void; saving: boolean; onCancel: () => void }) {
  const [p, setP] = useState<EmpresaEditPayload>({
    nome_fantasia: empresa.nome_fantasia ?? "", inscricao_estadual: empresa.inscricao_estadual ?? "", inscricao_municipal: empresa.inscricao_municipal ?? "", email: empresa.email ?? "", nire: empresa.nire ?? "", data_entrada: empresa.data_entrada ?? "", data_abertura: empresa.data_abertura ?? "", natureza_juridica: empresa.natureza_juridica ?? "", porte: empresa.porte ?? "", capital_social: empresa.capital_social ?? null, cnae_principal: empresa.cnae_principal ?? "", cnaes_secundarios: empresa.cnaes_secundarios ?? "", logradouro: empresa.logradouro ?? "", numero: empresa.numero ?? "", complemento: empresa.complemento ?? "", bairro: empresa.bairro ?? "", municipio: empresa.municipio ?? "", codigo_ibge: empresa.codigo_ibge ?? "", uf: empresa.uf ?? "", cep: empresa.cep ?? "", telefone: empresa.telefone ?? "", responsavel: empresa.responsavel ?? "", segmento: empresa.segmento ?? "", grupo_empresarial: empresa.grupo_empresarial ?? "", observacoes: empresa.observacoes ?? "",
  });
  const set = <K extends keyof EmpresaEditPayload>(key: K, value: EmpresaEditPayload[K]) => setP(x => ({ ...x, [key]: value }));
  const fields: Array<[keyof EmpresaEditPayload, string]> = [["nome_fantasia", "Nome Fantasia"], ["inscricao_estadual", "Inscrição Estadual"], ["inscricao_municipal", "Inscrição Municipal"], ["email", "E-mail"], ["nire", "NIRE"], ["data_entrada", "Data de Entrada"], ["data_abertura", "Data de Abertura"], ["cnae_principal", "CNAE Principal"], ["logradouro", "Endereço"], ["numero", "Número"], ["complemento", "Complemento"], ["bairro", "Bairro"], ["municipio", "Município"], ["uf", "UF"], ["cep", "CEP"], ["telefone", "Telefone"]];
  return <div className="panel form-panel"><div className="panel-header"><div><span className="eyebrow">ATUALIZAÇÃO CADASTRAL</span><h3>Editar dados</h3></div></div><div className="form-grid">{fields.map(([k, label]) => <label key={String(k)}>{label}<input type={k === "data_entrada" || k === "data_abertura" ? "date" : k === "email" ? "email" : "text"} value={String(p[k] ?? "")} onChange={x => set(k, x.target.value)} /></label>)}<label>Capital Social<input type="number" step="0.01" value={p.capital_social ?? ""} onChange={x => set("capital_social", x.target.value === "" ? null : Number(x.target.value))} /></label><label>Regime Tributário<input disabled value={empresa.regime_tributario || "Não informado"} /><small className="field-help">Bloqueado. Use “Alterar regime tributário”.</small></label></div><div className="form-actions"><button className="button secondary" onClick={onCancel}>Cancelar</button><button className="button primary" disabled={saving} onClick={() => onSave(p)}>{saving ? "Salvando..." : "Salvar alterações"}</button></div></div>;
}
