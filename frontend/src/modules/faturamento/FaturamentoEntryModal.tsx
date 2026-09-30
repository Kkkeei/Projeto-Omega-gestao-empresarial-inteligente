import {useEffect, useMemo, useState} from 'react';
import {CalendarDays, Save, X} from 'lucide-react';
import {
  atualizarFaturamento,
  criarFaturamento,
  criarFaturamentosLote,
  type Faturamento,
} from '../../services/api/faturamento';

type Periodicidade = 'Mensal' | 'Trimestral' | 'Semestral' | 'Anual' | 'Personalizado';

type CompetenciaExistente = Pick<Faturamento, 'id' | 'competencia_ano' | 'competencia_mes' | 'valor' | 'observacao' | 'data_faturamento' | 'periodicidade'>;

type Props = {
  open: boolean;
  onClose: () => void;
  empresaId: number;
  empresaNome: string;
  defaultYear: number;
  defaultMonth: number;
  initial?: CompetenciaExistente | null;
  existingFaturamentos?: CompetenciaExistente[];
  onSaved?: (message: string) => void | Promise<void>;
};

const MESES = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

function pad2(value: number) { return String(value).padStart(2, '0'); }
function dateForMonth(year: number, month: number) { return `${year}-${pad2(month)}-01`; }
function monthKey(year: number, month: number) { return `${year}-${pad2(month)}`; }
function parseDateYearMonth(value: string) {
  const [year, month] = value.split('-').map(Number);
  return {year, month};
}
function parseMoney(text: string) {
  const clean = text.trim().replace(/\s/g, '');
  return Number(clean.includes(',') ? clean.replace(/\./g, '').replace(',', '.') : clean);
}
function lastDayOfMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}
function clampMonthRange(start: string, end: string) {
  const a = parseDateYearMonth(start);
  const b = parseDateYearMonth(end);
  if (!a.year || !a.month || !b.year || !b.month || a.year * 12 + a.month > b.year * 12 + b.month) return [] as Array<{year: number; month: number}>;
  const items: Array<{year: number; month: number}> = [];
  let year = a.year;
  let month = a.month;
  while (year * 12 + month <= b.year * 12 + b.month && items.length < 12) {
    items.push({year, month});
    month += 1;
    if (month === 13) { month = 1; year += 1; }
  }
  return items;
}
function quarterRange(year: number, month: number) {
  const start = Math.floor((month - 1) / 3) * 3 + 1;
  return {start: monthKey(year, start), end: monthKey(year, start + 2)};
}
function semesterRange(year: number, month: number) {
  const start = month <= 6 ? 1 : 7;
  return {start: monthKey(year, start), end: monthKey(year, start + 5)};
}

export function FaturamentoEntryModal({
  open,
  onClose,
  empresaId,
  empresaNome,
  defaultYear,
  defaultMonth,
  initial,
  existingFaturamentos = [],
  onSaved,
}: Props) {
  const [periodicidade, setPeriodicidade] = useState<Periodicidade>('Mensal');
  const [dataFaturamento, setDataFaturamento] = useState(dateForMonth(defaultYear, defaultMonth));
  const [valor, setValor] = useState('');
  const [observacao, setObservacao] = useState('');
  const [periodoInicio, setPeriodoInicio] = useState(monthKey(defaultYear, 1));
  const [periodoFim, setPeriodoFim] = useState(monthKey(defaultYear, 12));
  const [itens, setItens] = useState<Array<{year: number; month: number; valor: string; observacao: string}>>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    const initialDate = initial?.data_faturamento || dateForMonth(initial?.competencia_ano ?? defaultYear, initial?.competencia_mes ?? defaultMonth);
    setPeriodicidade((initial?.periodicidade as Periodicidade) || 'Mensal');
    setDataFaturamento(initialDate);
    setValor(initial?.valor == null ? '' : String(initial.valor.toFixed(2)).replace('.', ','));
    setObservacao(initial?.observacao || '');
    setPeriodoInicio(monthKey(defaultYear, 1));
    setPeriodoFim(monthKey(defaultYear, 12));
    setItens([]);
    setError('');
  }, [open, initial?.id, initial?.competencia_ano, initial?.competencia_mes, initial?.data_faturamento, initial?.periodicidade, defaultYear, defaultMonth]);

  useEffect(() => {
    if (!open || periodicidade === 'Mensal') return;
    const ranges = periodicidade === 'Anual'
      ? {start: monthKey(defaultYear, 1), end: monthKey(defaultYear, 12)}
      : periodicidade === 'Trimestral'
        ? quarterRange(defaultYear, defaultMonth)
        : periodicidade === 'Semestral'
          ? semesterRange(defaultYear, defaultMonth)
          : {start: periodoInicio, end: periodoFim};
    setPeriodoInicio(ranges.start);
    setPeriodoFim(ranges.end);
    const generated = clampMonthRange(ranges.start, ranges.end).map(item => {
      const existing = existingFaturamentos.find(x => x.competencia_ano === item.year && x.competencia_mes === item.month);
      return {
        year: item.year,
        month: item.month,
        valor: existing?.valor == null ? '' : String(existing.valor.toFixed(2)).replace('.', ','),
        observacao: existing?.observacao || '',
      };
    });
    setItens(generated);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, periodicidade]);

  const intervalo = useMemo(() => clampMonthRange(periodoInicio, periodoFim), [periodoInicio, periodoFim]);
  const dataCompetencia = parseDateYearMonth(dataFaturamento);
  const existingForDate = existingFaturamentos.find(x => x.competencia_ano === dataCompetencia.year && x.competencia_mes === dataCompetencia.month);

  if (!open) return null;

  function alterarPeriodicidade(next: Periodicidade) {
    setError('');
    setPeriodicidade(next);
    if (next === 'Mensal') {
      setPeriodoInicio(monthKey(defaultYear, defaultMonth));
      setPeriodoFim(monthKey(defaultYear, defaultMonth));
      return;
    }
    if (next === 'Anual') {
      setPeriodoInicio(monthKey(defaultYear, 1));
      setPeriodoFim(monthKey(defaultYear, 12));
    } else if (next === 'Trimestral') {
      const range = quarterRange(defaultYear, defaultMonth);
      setPeriodoInicio(range.start); setPeriodoFim(range.end);
    } else if (next === 'Semestral') {
      const range = semesterRange(defaultYear, defaultMonth);
      setPeriodoInicio(range.start); setPeriodoFim(range.end);
    }
  }

  function alterarPeriodo(field: 'inicio' | 'fim', value: string) {
    if (field === 'inicio') setPeriodoInicio(value); else setPeriodoFim(value);
    const start = field === 'inicio' ? value : periodoInicio;
    const end = field === 'fim' ? value : periodoFim;
    const generated = clampMonthRange(start, end).map(item => {
      const existing = existingFaturamentos.find(x => x.competencia_ano === item.year && x.competencia_mes === item.month);
      return {
        year: item.year,
        month: item.month,
        valor: existing?.valor == null ? '' : String(existing.valor.toFixed(2)).replace('.', ','),
        observacao: existing?.observacao || '',
      };
    });
    setItens(generated);
  }

  function atualizarItem(index: number, field: 'valor' | 'observacao', value: string) {
    setItens(current => current.map((item, itemIndex) => itemIndex === index ? {...item, [field]: value} : item));
  }

  async function salvar() {
    setError('');
    setSaving(true);
    try {
      if (periodicidade === 'Mensal') {
        if (!dataCompetencia.year || dataCompetencia.month < 1 || dataCompetencia.month > 12) throw new Error('Selecione uma data válida.');
        const n = parseMoney(valor);
        if (!Number.isFinite(n) || n < 0) throw new Error('Informe um valor de faturamento válido.');
        if (initial?.id && (initial.competencia_ano !== dataCompetencia.year || initial.competencia_mes !== dataCompetencia.month)) {
          throw new Error(`Para editar este lançamento, a data deve continuar em ${MESES[initial.competencia_mes]}/${initial.competencia_ano}. Para trocar a competência, informe um novo faturamento.`);
        }
        const dateObject = new Date(dataFaturamento + 'T12:00:00');
        const maxDay = lastDayOfMonth(dataCompetencia.year, dataCompetencia.month);
        if (dateObject.getDate() > maxDay) throw new Error('A data selecionada não é válida para esta competência.');
        if (initial?.id) {
          await atualizarFaturamento(initial.id, {
            valor: n,
            observacao,
            data_faturamento: dataFaturamento,
            periodicidade: 'Mensal',
          });
        } else {
          await criarFaturamento({
            empresa_id: empresaId,
            competencia_ano: dataCompetencia.year,
            competencia_mes: dataCompetencia.month,
            valor: n,
            observacao,
            data_faturamento: dataFaturamento,
            periodicidade: 'Mensal',
          });
        }
      } else {
        const preenchidos = itens.filter(item => item.valor.trim() !== '').map(item => {
          const n = parseMoney(item.valor);
          if (!Number.isFinite(n) || n < 0) throw new Error(`Valor inválido em ${MESES[item.month]}/${item.year}.`);
          return {
            competencia_ano: item.year,
            competencia_mes: item.month,
            valor: n,
            observacao: item.observacao,
            data_faturamento: null,
            periodicidade,
          };
        });
        if (!preenchidos.length) throw new Error('Informe ao menos uma competência para salvar.');
        await criarFaturamentosLote(empresaId, preenchidos);
      }
      await onSaved?.('Faturamento salvo com sucesso.');
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Não foi possível salvar o faturamento.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fat-modal-backdrop" onMouseDown={() => !saving && onClose()}>
      <div className="fat-modal fat-entry-modal" onMouseDown={e => e.stopPropagation()}>
        <div className="fat-modal-header">
          <div>
            <span className="fat-modal-icon"><CalendarDays size={17}/></span>
            <div><strong>{initial?.id ? 'Editar faturamento' : 'Informar faturamento'}</strong><small>{empresaNome}</small></div>
          </div>
          <button className="icon-button" onClick={onClose} disabled={saving}><X size={15}/></button>
        </div>

        <div className="fat-entry-type-tabs">
          {(['Mensal', 'Trimestral', 'Semestral', 'Anual', 'Personalizado'] as Periodicidade[]).map(item => (
            <button type="button" key={item} className={periodicidade === item ? 'active' : ''} onClick={() => alterarPeriodicidade(item)} disabled={saving}>{item}</button>
          ))}
        </div>

        {periodicidade === 'Mensal' ? (
          <div className="fat-modal-body">
            <div className="fat-entry-two-fields">
              <label>Data do faturamento *<input type="date" value={dataFaturamento} onChange={e => setDataFaturamento(e.target.value)} /></label>
              <div className="fat-form-highlight compact"><span>Competência</span><strong>{dataCompetencia.year && MESES[dataCompetencia.month] ? `${MESES[dataCompetencia.month]}/${dataCompetencia.year}` : '—'}</strong></div>
            </div>
            {existingForDate && !initial?.id && <div className="fat-entry-info">Já existe faturamento informado nesta competência. Ao salvar, a plataforma atualizará o lançamento existente.</div>}
            <label>Valor do faturamento *<input autoFocus inputMode="decimal" placeholder="R$ 0,00" value={valor} onChange={e => setValor(e.target.value)} /></label>
            <label>Observação <span className="fat-label-help">Opcional</span><textarea value={observacao} onChange={e => setObservacao(e.target.value)} placeholder="Observação sobre este faturamento..." /></label>
          </div>
        ) : (
          <div className="fat-modal-body">
            <div className="fat-form-highlight"><span>Período do lançamento</span><strong>{intervalo.length ? `${MESES[intervalo[0].month]}/${intervalo[0].year} a ${MESES[intervalo[intervalo.length - 1].month]}/${intervalo[intervalo.length - 1].year}` : 'Selecione um período válido'}</strong><small>O valor é registrado competência por competência para preservar os dados mensais da plataforma.</small></div>
            {periodicidade === 'Anual' && <label>Ano-base *<input type="number" value={defaultYear} readOnly /></label>}
            {periodicidade !== 'Anual' && <div className="fat-period-picker"><label>De *<input type="month" value={periodoInicio} onChange={e => alterarPeriodo('inicio', e.target.value)} /></label><label>Até *<input type="month" value={periodoFim} onChange={e => alterarPeriodo('fim', e.target.value)} /></label></div>}
            <div className="fat-batch-table-wrap">
              <table className="fat-batch-table"><thead><tr><th>Competência</th><th>Valor do faturamento</th><th>Observação</th></tr></thead>
                <tbody>{itens.map((item, index) => <tr key={`${item.year}-${item.month}`}><td><strong>{MESES[item.month]}/{item.year}</strong></td><td><input inputMode="decimal" placeholder="R$ 0,00" value={item.valor} onChange={e => atualizarItem(index, 'valor', e.target.value)} /></td><td><input value={item.observacao} onChange={e => atualizarItem(index, 'observacao', e.target.value)} placeholder="—" /></td></tr>)}</tbody>
              </table>
            </div>
          </div>
        )}

        {error && <div className="form-error fat-entry-error">{error}</div>}
        <div className="fat-modal-actions"><button className="button secondary" onClick={onClose} disabled={saving}>Cancelar</button><button className="button primary" onClick={() => void salvar()} disabled={saving}><Save size={13}/>{saving ? 'Salvando...' : 'Salvar faturamento'}</button></div>
      </div>
    </div>
  );
}
