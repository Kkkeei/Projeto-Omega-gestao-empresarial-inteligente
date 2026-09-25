import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Building2,
  CalendarDays,
  CheckCircle2,
  Edit3,
  FileText,
  Info,
  Plus,
  Save,
  X,
} from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ErrorState } from "../../components/ui/ErrorState";
import { Loading } from "../../components/ui/Loading";
import {
  atualizarObservacaoEmpresaFaturamento,
  gerarDeclaracao12Meses,
  gerarDeclaracaoAnual,
  gerarDeclaracaoPersonalizada,
  visualizarDeclaracao,
  baixarDeclaracao,
  obterEmpresaFaturamento,
  type DeclaracaoFaturamento,
  type EmpresaFaturamento,
  type MesFaturamento,
} from "../../services/api/faturamento";
import { FaturamentoEntryModal } from "./FaturamentoEntryModal";
import { BancoBrasilDeclarationModal } from "./BancoBrasilDeclarationModal";
import "./Faturamento.css";

const MESES = [
  "",
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

function dinheiro(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value || 0));
}
function competenciaLabel(ano: number, mes: number) {
  return `${MESES[mes]}/${ano}`;
}
function periodoLabel(valor?: string | null) {
  if (!valor) return "—";
  const [ano, mes] = valor.split("-").map(Number);
  return `${String(mes).padStart(2, "0")}/${ano}`;
}
function anoAtual() {
  return new Date().getFullYear();
}
function mesAnterior() {
  const hoje = new Date();
  return hoje.getMonth() === 0 ? 12 : hoje.getMonth();
}
function anoCompetenciaAnterior() {
  const hoje = new Date();
  return hoje.getMonth() === 0 ? hoje.getFullYear() - 1 : hoje.getFullYear();
}

export function EmpresaFaturamentoPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const empresaId = Number(id);
  const [data, setData] = useState<EmpresaFaturamento | null>(null);
  const [ano, setAno] = useState(anoCompetenciaAnterior());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyDeclaration, setBusyDeclaration] = useState(false);
  const [selectedMes, setSelectedMes] = useState(mesAnterior());
  const [informarOpen, setInformarOpen] = useState(false);
  const [informarInicial, setInformarInicial] = useState<MesFaturamento | null>(
    null,
  );
  const [success, setSuccess] = useState("");
  const [obsEditing, setObsEditing] = useState(false);
  const [obsEmpresa, setObsEmpresa] = useState("");
  const [showAllDeclarations, setShowAllDeclarations] = useState(false);
  const [bancoBrasilOpen, setBancoBrasilOpen] = useState(false);
  const [anoDeclaracao, setAnoDeclaracao] = useState(anoAtual());
  const [inicioDeclaracao, setInicioDeclaracao] = useState(`${anoAtual()}-01`);
  const [fimDeclaracao, setFimDeclaracao] = useState(`${anoAtual()}-12`);
  const openedFromQuery = useRef(false);

  async function load(targetYear = ano) {
    setLoading(true);
    setError("");
    try {
      const result = await obterEmpresaFaturamento(empresaId, targetYear);
      setData(result);
      setObsEmpresa(result.empresa.observacoes || "");
      const current = result.competencias.find(
        (item) => item.competencia_mes === selectedMes,
      );
      if (!current)
        setSelectedMes(
          targetYear === anoCompetenciaAnterior() ? mesAnterior() : 1,
        );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Erro ao carregar faturamento.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(ano);
  }, [empresaId, ano]);

  useEffect(() => {
    if (
      !openedFromQuery.current &&
      searchParams.get("open") === "informar" &&
      !loading &&
      data
    ) {
      openedFromQuery.current = true;
      setInformarInicial(
        data.competencias.find(
          (item) => item.competencia_mes === selectedMes,
        ) || null,
      );
      setInformarOpen(true);
    }
  }, [searchParams, loading, data, selectedMes]);

  function selecionarMes(mes: number) {
    setSelectedMes(mes);
    const item =
      data?.competencias.find((x) => x.competencia_mes === mes) || null;
    setInformarInicial(item);
    setInformarOpen(true);
  }

  function abrirNovoFaturamento() {
    const item =
      data?.competencias.find((x) => x.competencia_mes === selectedMes) || null;
    setInformarInicial(item);
    setInformarOpen(true);
  }

  async function salvarObservacao() {
    setSaving(true);
    setError("");
    try {
      await atualizarObservacaoEmpresaFaturamento(empresaId, obsEmpresa);
      setObsEditing(false);
      setSuccess("Observação da empresa salva com sucesso.");
      await load(ano);
      window.setTimeout(() => setSuccess(""), 3000);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Não foi possível salvar a observação.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function gerar12() {
    setBusyDeclaration(true);
    setError("");
    const pdfAba = window.open("about:blank", "_blank");
    if (!pdfAba) {
      setError(
        "O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.",
      );
      return;
    }
    try {
      const d = await gerarDeclaracao12Meses(empresaId);
      await visualizarDeclaracao(d.id, pdfAba);
      await load(ano);
    } catch (e) {
      pdfAba.close();
      setError(
        e instanceof Error ? e.message : "Não foi possível gerar a declaração.",
      );
    } finally {
      setBusyDeclaration(false);
    }
  }
  async function gerarAnual() {
    setBusyDeclaration(true);
    setError("");
    const pdfAba = window.open("about:blank", "_blank");
    if (!pdfAba) {
      setError(
        "O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.",
      );
      return;
    }
    try {
      const d = await gerarDeclaracaoAnual(empresaId, anoDeclaracao);
      await visualizarDeclaracao(d.id, pdfAba);
      await load(ano);
    } catch (e) {
      pdfAba.close();
      setError(
        e instanceof Error
          ? e.message
          : "Não foi possível gerar a declaração anual.",
      );
    } finally {
      setBusyDeclaration(false);
    }
  }
  async function gerarPersonalizada() {
    const [ai, mi] = inicioDeclaracao.split("-").map(Number);
    const [af, mf] = fimDeclaracao.split("-").map(Number);
    if (!ai || !mi || !af || !mf || ai * 12 + mi > af * 12 + mf) {
      setError("Informe corretamente o período da declaração.");
      return;
    }
    setBusyDeclaration(true);
    setError("");
    const pdfAba = window.open("about:blank", "_blank");
    if (!pdfAba) {
      setError(
        "O navegador bloqueou a abertura do PDF. Permita pop-ups para a ÔMEGA.",
      );
      return;
    }
    try {
      const d = await gerarDeclaracaoPersonalizada(empresaId, {
        ano_inicio: ai,
        mes_inicio: mi,
        ano_fim: af,
        mes_fim: mf,
      });
      await visualizarDeclaracao(d.id, pdfAba);
      await load(ano);
    } catch (e) {
      pdfAba.close();
      setError(
        e instanceof Error
          ? e.message
          : "Não foi possível gerar a declaração personalizada.",
      );
    } finally {
      setBusyDeclaration(false);
    }
  }

  function navegarAno(delta: number) {
    setAno((current) => current + delta);
  }

  if (loading)
    return (
      <div className="page">
        <Loading />
      </div>
    );
  if (error && !data)
    return (
      <div className="page">
        <ErrorState message={error} onRetry={() => void load(ano)} />
      </div>
    );
  if (!data) return null;

  const resumo = data.resumo;
  const declarations = showAllDeclarations
    ? data.declaracoes
    : data.declaracoes.slice(0, 3);
  const ultimo = resumo.ultimo_faturamento;
  const primeiro = resumo.primeiro_faturamento;

  return (
    <div className="page faturamento-page">
      <Link to="/faturamento" className="back-link">
        <ArrowLeft size={15} /> Voltar para Faturamento
      </Link>
      <div className="fat-company-detail-heading">
        <div className="fat-company-detail-identification">
          <span className="fat-company-detail-icon">
            <Building2 size={19} />
          </span>
          <div>
            <span className="eyebrow">EMPRESA</span>
            <h2>{data.empresa.razao_social}</h2>
            <div className="fat-detail-meta">
              {data.empresa.cnpj} ·{" "}
              {data.empresa.regime_tributario || "Regime não informado"}
            </div>
          </div>
        </div>
        <Link className="button secondary" to={`/empresas/${empresaId}`}>
          <Info size={14} /> Informações da empresa
        </Link>
      </div>

      {error && <div className="form-error">{error}</div>}
      {success && (
        <div className="fat-success-toast">
          <CheckCircle2 size={17} />
          <div>
            <strong>{success}</strong>
            <span>Os dados da empresa foram atualizados.</span>
          </div>
          <button className="icon-button" onClick={() => setSuccess("")}>
            <X size={14} />
          </button>
        </div>
      )}

      <div className="fat-detail-summary">
        <div className="fat-detail-metric">
          <span className="fat-detail-metric-icon green">
            <CheckCircle2 size={17} />
          </span>
          <div>
            <strong>{resumo.meses_informados}</strong>
            <small>Meses informados</small>
            <em>de 12 no ano de {ano}</em>
            <div className="fat-progress">
              <i style={{ width: `${resumo.percentual_informado}%` }} />
            </div>
            <b>{Math.round(resumo.percentual_informado)}%</b>
          </div>
        </div>
        <div className="fat-detail-metric">
          <span className="fat-detail-metric-icon blue">
            <Plus size={17} />
          </span>
          <div>
            <strong>{dinheiro(resumo.valor_total)}</strong>
            <small>Total faturado em {ano}</small>
          </div>
        </div>
        <div className="fat-detail-metric">
          <span className="fat-detail-metric-icon purple">
            <CalendarDays size={17} />
          </span>
          <div>
            <strong>{dinheiro(resumo.media_mensal)}</strong>
            <small>Média mensal</small>
          </div>
        </div>
        <div className="fat-detail-metric">
          <span className="fat-detail-metric-icon blue">
            <CalendarDays size={17} />
          </span>
          <div>
            <strong>
              {ultimo
                ? competenciaLabel(
                    ultimo.competencia_ano,
                    ultimo.competencia_mes,
                  )
                : "—"}
            </strong>
            <small>Último faturamento</small>
            <em>{ultimo ? dinheiro(ultimo.valor) : "Nenhum registro"}</em>
          </div>
        </div>
        <div className="fat-detail-metric">
          <span className="fat-detail-metric-icon purple">
            <CalendarDays size={17} />
          </span>
          <div>
            <strong>
              {primeiro
                ? competenciaLabel(
                    primeiro.competencia_ano,
                    primeiro.competencia_mes,
                  )
                : "—"}
            </strong>
            <small>Primeiro faturamento</small>
            <em>{primeiro ? dinheiro(primeiro.valor) : "Nenhum registro"}</em>
          </div>
        </div>
      </div>

      <section className="panel fat-billing-section">
        <div className="fat-section-heading">
          <div>
            <span className="eyebrow">1 · INFORMAR FATURAMENTO</span>
            <h3>
              Acompanhe os meses do ano, informe ou edite os valores de
              faturamento.
            </h3>
          </div>
          <div className="fat-section-actions">
            <button className="button primary" onClick={abrirNovoFaturamento}>
              <Plus size={14} /> Informar faturamento
            </button>
          </div>
        </div>
        <div className="fat-year-toolbar">
          <button
            className="icon-button"
            onClick={() => navegarAno(-1)}
            title="Ano anterior"
          >
            ‹
          </button>
          <span className="fat-year-label">
            <CalendarDays size={17} />
            <strong>{ano}</strong>
          </span>
          <button
            className="icon-button"
            onClick={() => navegarAno(1)}
            title="Próximo ano"
          >
            ›
          </button>
          <span className="fat-year-help">
            Clique em um mês para abrir o lançamento. No formulário você escolhe
            Mensal, Trimestral, Semestral, Anual ou Personalizado.
          </span>
        </div>
        <div className="fat-month-grid">
          {data.competencias.map((item) => (
            <button
              key={item.competencia_mes}
              className={`fat-month-card ${selectedMes === item.competencia_mes ? "active" : ""}`}
              onClick={() => selecionarMes(item.competencia_mes)}
            >
              <div className="fat-month-top">
                <strong>
                  {MESES[item.competencia_mes].slice(0, 3)}/{ano}
                </strong>
                <span className={item.informado ? "informed" : "pending"}>
                  {item.informado ? "✓ Informado" : "! Pendente"}
                </span>
              </div>
              <strong className="fat-month-value">
                {item.informado ? dinheiro(item.valor) : "—"}
              </strong>
              <span className="fat-month-edit">
                <Edit3 size={13} />
              </span>
            </button>
          ))}
        </div>
        <div className="fat-observation-box">
          <div>
            <span className="fat-observation-icon">
              <FileText size={17} />
            </span>
            <div>
              <strong>Observações da empresa</strong>
              <small>
                {data.empresa.observacoes || "Não há observações cadastradas."}
              </small>
            </div>
          </div>
          <button
            className="button secondary"
            onClick={() => setObsEditing((current) => !current)}
          >
            <Plus size={13} /> {obsEditing ? "Fechar" : "Adicionar observação"}
          </button>
        </div>
        {obsEditing && (
          <div className="fat-observation-editor">
            <textarea
              value={obsEmpresa}
              onChange={(e) => setObsEmpresa(e.target.value)}
              placeholder="Digite uma observação importante sobre a empresa..."
            />
            <div>
              <button
                className="button secondary"
                onClick={() => {
                  setObsEditing(false);
                  setObsEmpresa(data.empresa.observacoes || "");
                }}
              >
                Cancelar
              </button>
              <button
                className="button primary"
                onClick={() => void salvarObservacao()}
                disabled={saving}
              >
                <Save size={13} /> Salvar observação
              </button>
            </div>
          </div>
        )}
      </section>

      <div className="fat-declarations-layout">
        <section className="panel">
          <div className="fat-section-heading simple">
            <div>
              <span className="eyebrow">2 · DECLARAÇÕES</span>
              <h3>
                Emita a declaração de faturamento da empresa no período
                desejado.
              </h3>
            </div>
          </div>
          <div className="fat-declaration-cards">
            <div className="fat-declaration-card featured">
              <CalendarDays size={20} />
              <strong>Últimos 12 meses</strong>
              <span>
                Gera a declaração com base nas 12 últimas competências
                completas.
              </span>
              <button
                className="button primary"
                onClick={() => void gerar12()}
                disabled={busyDeclaration}
              >
                Gerar agora
              </button>
              <small>Período calculado automaticamente</small>
            </div>
            <div className="fat-declaration-card">
              <CalendarDays size={20} />
              <strong>Declaração anual</strong>
              <span>Selecione um ano específico para gerar a declaração.</span>
              <label>
                Selecionar ano
                <input
                  type="number"
                  value={anoDeclaracao}
                  onChange={(e) => setAnoDeclaracao(Number(e.target.value))}
                />
              </label>
              <button
                className="button secondary"
                onClick={() => void gerarAnual()}
                disabled={busyDeclaration}
              >
                Gerar declaração
              </button>
              <small>
                Período: 01/{anoDeclaracao} a 12/{anoDeclaracao}
              </small>
            </div>
            <div className="fat-declaration-card">
              <CalendarDays size={20} />
              <strong>Período personalizado</strong>
              <span>Escolha o mês inicial e o mês final da declaração.</span>
              <div className="fat-two-inputs">
                <label>
                  De
                  <input
                    type="month"
                    value={inicioDeclaracao}
                    onChange={(e) => setInicioDeclaracao(e.target.value)}
                  />
                </label>
                <label>
                  Até
                  <input
                    type="month"
                    value={fimDeclaracao}
                    onChange={(e) => setFimDeclaracao(e.target.value)}
                  />
                </label>
              </div>
              <button
                className="button secondary"
                onClick={() => void gerarPersonalizada()}
                disabled={busyDeclaration}
              >
                Gerar declaração
              </button>
            </div>
            <div className="fat-declaration-card fat-bb-card">
              <Building2 size={20} />
              <strong>Banco do Brasil</strong>
              <span>
                Preenche, salva e gera automaticamente a relação oficial de
                faturamento do BB.
              </span>
              <button
                className="button secondary"
                onClick={() => setBancoBrasilOpen(true)}
                disabled={busyDeclaration}
              >
                Configurar e gerar
              </button>
              <small>Período calculado automaticamente</small>
            </div>
          </div>
        </section>

        <aside className="panel fat-history-side">
          <div className="fat-section-heading simple">
            <div>
              <span className="eyebrow">HISTÓRICO DE DECLARAÇÕES</span>
              <h3>Últimas declarações emitidas</h3>
            </div>
          </div>
          <div className="fat-history-list">
            {!declarations.length && (
              <div className="empty compact">
                <FileText size={22} />
                <span>Nenhuma declaração gerada ainda.</span>
              </div>
            )}
            {declarations.map((d: DeclaracaoFaturamento) => (
              <div className="fat-history-item" key={d.id}>
                <span className="fat-history-icon">
                  <FileText size={15} />
                </span>
                <div>
                  <strong>
                    {d.tipo === "Personalizada" ? "Período: " : d.tipo + ": "}
                    {d.periodo_inicio.replace("-", "/")}
                    {d.tipo !== "Anual" &&
                      ` a ${d.periodo_fim.replace("-", "/")}`}
                  </strong>
                  <small>
                    Emitida em {periodoLabel(d.data_geracao.slice(0, 7))} por{" "}
                    {d.usuario_nome || "Usuário"}
                  </small>
                </div>
                <button
                  className="button secondary"
                  onClick={() => void baixarDeclaracao(d.id)}
                >
                  <FileText size={12} /> Baixar
                </button>
              </div>
            ))}
          </div>
          {data.declaracoes.length > 3 && (
            <button
              className="fat-see-all"
              onClick={() => setShowAllDeclarations((current) => !current)}
            >
              {showAllDeclarations ? "Recolher" : "Ver todos"}
            </button>
          )}
        </aside>
      </div>

      <FaturamentoEntryModal
        open={informarOpen}
        onClose={() => setInformarOpen(false)}
        empresaId={empresaId}
        empresaNome={data.empresa.razao_social}
        defaultYear={ano}
        defaultMonth={selectedMes}
        initial={informarInicial}
        existingFaturamentos={data.faturamentos}
        onSaved={async (message) => {
          setSuccess(message);
          await load(ano);
          window.setTimeout(() => setSuccess(""), 3500);
        }}
      />

      <BancoBrasilDeclarationModal
        open={bancoBrasilOpen}
        empresaId={empresaId}
        empresaNome={data.empresa.razao_social}
        onClose={async () => {
          setBancoBrasilOpen(false);
          await load(ano);
        }}
      />
    </div>
  );
}
