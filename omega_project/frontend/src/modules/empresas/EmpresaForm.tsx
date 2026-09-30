import { useState } from "react";
import { ArrowLeft, Search, Save } from "lucide-react";
import { cadastrarEmpresa, consultarCnpj } from "../../services/api/empresas";
import type { Empresa } from "../../types";

type Props = { onCreated: (e: Empresa) => void; onCancel: () => void };
const clean = (v: string) => v.replace(/\D/g, "").slice(0, 14);
const fmt = (v: string) => v.length === 14 ? v.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5") : v;
const isoDate = (value: unknown) => typeof value === "string" ? value.slice(0, 10) : "";

export function EmpresaForm({ onCreated, onCancel }: Props) {
  const [p, setP] = useState<Record<string, string>>({ cnpj: "", razao_social: "", regime_tributario: "", data_entrada: new Date().toISOString().slice(0, 10), data_abertura: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (k: string, v: string) => setP(x => ({ ...x, [k]: v }));

  async function consulta() {
    const cnpj = clean(p.cnpj);
    if (cnpj.length !== 14) { setError("Informe um CNPJ válido com 14 dígitos para consultar."); return; }
    setError(""); setLoading(true);
    try {
      const d = await consultarCnpj(cnpj);
      setP(x => ({
        ...x,
        razao_social: d.razao_social ?? x.razao_social,
        nome_fantasia: d.nome_fantasia ?? x.nome_fantasia ?? "",
        data_abertura: isoDate(d.data_inicio_atividade ?? d.data_abertura),
        capital_social: d.capital_social != null ? String(d.capital_social) : x.capital_social ?? "",
        cnae_principal: d.cnae_fiscal != null ? String(d.cnae_fiscal) : x.cnae_principal ?? "",
        logradouro: d.logradouro ?? x.logradouro ?? "", numero: d.numero ?? x.numero ?? "", complemento: d.complemento ?? x.complemento ?? "", bairro: d.bairro ?? x.bairro ?? "", municipio: d.municipio ?? x.municipio ?? "", uf: d.uf ?? x.uf ?? "", cep: d.cep ?? x.cep ?? "", telefone: d.ddd_telefone_1 ?? d.ddd_telefone_2 ?? x.telefone ?? "", natureza_juridica: d.natureza_juridica ?? x.natureza_juridica ?? "", porte: d.porte ?? x.porte ?? "",
      }));
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível consultar o CNPJ."); }
    finally { setLoading(false); }
  }

  async function save(event: React.FormEvent) {
    event.preventDefault(); setError(""); setLoading(true);
    try { onCreated(await cadastrarEmpresa({ ...p, cnpj: clean(p.cnpj), capital_social: p.capital_social ? Number(p.capital_social) : undefined })); }
    catch (e) { setError(e instanceof Error ? e.message : "Erro ao cadastrar empresa."); }
    finally { setLoading(false); }
  }

  return <div className="page"><div className="page-heading"><div><button className="back-link button ghost" onClick={onCancel}><ArrowLeft size={15} /> Empresas</button><span className="eyebrow">CADASTRO RÁPIDO</span><h2>Nova empresa</h2><p>Informe o CNPJ e consulte os dados oficiais antes de concluir o cadastro.</p></div></div><form className="panel form-panel" onSubmit={save}><div className="form-section"><h3>Consulta automática do Cartão CNPJ</h3><p>Ao consultar, a <strong>Data de Abertura</strong> é preenchida automaticamente a partir da data de início da atividade informada pela fonte cadastral.</p></div><div className="form-grid"><label>CNPJ<div className="input-with-button"><input required value={fmt(p.cnpj)} onChange={e => set("cnpj", clean(e.target.value))} placeholder="00.000.000/0001-00" /><button type="button" className="button secondary" onClick={consulta} disabled={loading}><Search size={15} /> {loading ? "Consultando..." : "Consultar"}</button></div></label><label>Razão Social<input required value={p.razao_social || ""} onChange={e => set("razao_social", e.target.value)} /></label><label>Nome Fantasia<input value={p.nome_fantasia || ""} onChange={e => set("nome_fantasia", e.target.value)} /></label><label>Inscrição Estadual<input value={p.inscricao_estadual || ""} onChange={e => set("inscricao_estadual", e.target.value)} /></label><label>Inscrição Municipal<input value={p.inscricao_municipal || ""} onChange={e => set("inscricao_municipal", e.target.value)} /></label><label>E-mail<input type="email" value={p.email || ""} onChange={e => set("email", e.target.value)} /></label><label>NIRE<input value={p.nire || ""} onChange={e => set("nire", e.target.value)} /></label><label>Regime Tributário<select value={p.regime_tributario || ""} onChange={e => set("regime_tributario", e.target.value)}><option value="">Selecione</option><option>Lucro Real</option><option>Lucro Presumido</option><option>Simples Nacional</option></select></label><label>Data de Entrada<input type="date" value={p.data_entrada || ""} onChange={e => set("data_entrada", e.target.value)} /></label><label>Data de Abertura<input type="date" value={p.data_abertura || ""} readOnly className="readonly-field" /><small className="field-help">Preenchida automaticamente pela consulta do CNPJ.</small></label><label>CNAE Principal<input value={p.cnae_principal || ""} onChange={e => set("cnae_principal", e.target.value)} /></label><label>Capital Social<input type="number" step="0.01" value={p.capital_social || ""} onChange={e => set("capital_social", e.target.value)} /></label><label className="span-2">Endereço<input value={p.logradouro || ""} onChange={e => set("logradouro", e.target.value)} /></label><label>Número<input value={p.numero || ""} onChange={e => set("numero", e.target.value)} /></label><label>Complemento<input value={p.complemento || ""} onChange={e => set("complemento", e.target.value)} /></label><label>Bairro<input value={p.bairro || ""} onChange={e => set("bairro", e.target.value)} /></label><label>Município<input value={p.municipio || ""} onChange={e => set("municipio", e.target.value)} /></label><label>UF<input value={p.uf || ""} onChange={e => set("uf", e.target.value)} /></label><label>CEP<input value={p.cep || ""} onChange={e => set("cep", e.target.value)} /></label><label>Telefone<input value={p.telefone || ""} onChange={e => set("telefone", e.target.value)} /></label></div>{error && <div className="form-error">{error}</div>}<div className="form-actions"><button type="button" className="button secondary" onClick={onCancel}>Cancelar</button><button className="button primary" disabled={loading}><Save size={15} />{loading ? "Salvando..." : "Cadastrar empresa"}</button></div></form></div>;
}
