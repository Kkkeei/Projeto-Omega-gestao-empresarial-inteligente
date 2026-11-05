import { useEffect, useMemo, useState } from 'react';
import { Building2, CheckCircle2, Search, Users, X } from 'lucide-react';
import { listarEmpresasParaAtribuicao, listarResponsaveisContabeis, salvarAtribuicoes } from './contabilApi';
import type { AtribuicaoAlteracao, EmpresaContabil, ResponsavelContabil } from './types';

export function AtribuicaoModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [responsaveis, setResponsaveis] = useState<ResponsavelContabil[]>([]);
  const [empresas, setEmpresas] = useState<EmpresaContabil[]>([]);
  const [responsavelId, setResponsavelId] = useState<number | null>(null);
  const [selecionadas, setSelecionadas] = useState<number[]>([]);
  const [transferencias, setTransferencias] = useState<number[]>([]);
  const [pendente, setPendente] = useState<EmpresaContabil | null>(null);
  const [busca, setBusca] = useState('');
  const [regime, setRegime] = useState('TODOS');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function carregar() {
    setLoading(true);
    setError('');
    try {
      const [users, companies] = await Promise.all([listarResponsaveisContabeis(), listarEmpresasParaAtribuicao()]);
      const ativos = users.responsaveis.filter((item) => item.ativo);
      setResponsaveis(ativos);
      setEmpresas(companies.empresas);
      if (ativos.length) {
        setResponsavelId(ativos[0].id);
        setSelecionadas(companies.empresas.filter((item) => item.responsavel_id === ativos[0].id).map((item) => item.id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar responsáveis e empresas.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void carregar(); }, []);

  function selecionarResponsavel(id: number) {
    setResponsavelId(id);
    setSelecionadas(empresas.filter((item) => item.responsavel_id === id).map((item) => item.id));
    setTransferencias([]);
    setPendente(null);
  }

  function alternarEmpresa(empresa: EmpresaContabil) {
    if (responsavelId === null) return;
    if (selecionadas.includes(empresa.id)) {
      setSelecionadas((current) => current.filter((id) => id !== empresa.id));
      setTransferencias((current) => current.filter((id) => id !== empresa.id));
      return;
    }
    if (empresa.responsavel_id && empresa.responsavel_id !== responsavelId) {
      setPendente(empresa);
      return;
    }
    setSelecionadas((current) => [...current, empresa.id]);
  }

  function confirmarTransferencia() {
    if (!pendente || responsavelId === null) return;
    setSelecionadas((current) => [...current, pendente.id]);
    setTransferencias((current) => [...current, pendente.id]);
    setPendente(null);
  }

  const filtradas = useMemo(() => empresas.filter((empresa) => {
    const termo = busca.toLocaleLowerCase('pt-BR').trim();
    const corresponde = !termo || (empresa.razao_social + ' ' + (empresa.nome_fantasia || '') + ' ' + empresa.cnpj).toLocaleLowerCase('pt-BR').includes(termo);
    const regimeOk = regime === 'TODOS' || (empresa.regime_tributario || '').toUpperCase() === regime;
    return corresponde && regimeOk;
  }), [empresas, busca, regime]);

  async function salvar() {
    if (responsavelId === null || saving) return;
    const changes: AtribuicaoAlteracao[] = [];
    empresas.forEach((empresa) => {
      const marcada = selecionadas.includes(empresa.id);
      if (marcada && empresa.responsavel_id !== responsavelId) {
        changes.push({
          empresa_id: empresa.id,
          responsavel_id: responsavelId,
          confirmar_transferencia: transferencias.includes(empresa.id),
          motivo: transferencias.includes(empresa.id) ? 'Transferência confirmada pela tela Contábil' : 'Atribuição pela tela Contábil',
        });
      } else if (!marcada && empresa.responsavel_id === responsavelId) {
        changes.push({
          empresa_id: empresa.id,
          responsavel_id: null,
          confirmar_transferencia: false,
          motivo: 'Retirada da carteira pela tela Contábil',
        });
      }
    });
    if (!changes.length) { onClose(); return; }
    setSaving(true);
    setError('');
    try {
      await salvarAtribuicoes(changes);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível salvar as atribuições.');
    } finally {
      setSaving(false);
    }
  }

  return <div className="contabil-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="contabil-assignment-modal" role="dialog" aria-modal="true" aria-labelledby="contabil-assignment-title">
      <header className="contabil-modal-header">
        <div><span className="eyebrow">DISTRIBUIÇÃO DA CARTEIRA</span><h3 id="contabil-assignment-title">Atribuir responsáveis</h3><p>Selecione um responsável e marque as empresas que ficarão sob seu acompanhamento.</p></div>
        <button className="icon-button" aria-label="Fechar" onClick={onClose}><X size={17} /></button>
      </header>
      {error && <div className="contabil-inline-error">{error}</div>}
      {loading ? <div className="contabil-loading"><span className="spinner" />Carregando responsáveis e empresas...</div> :
      <div className="contabil-assignment-body">
        <aside className="contabil-responsible-list">
          <div className="contabil-subheading"><strong>Responsáveis</strong><small>{responsaveis.length} ativos</small></div>
          {responsaveis.map((item) => <button key={item.id} className={'contabil-responsible-option' + (responsavelId === item.id ? ' active' : '')} onClick={() => selecionarResponsavel(item.id)}>
            <i>{item.nome.slice(0, 1).toUpperCase()}</i><span><strong>{item.nome}</strong><small>{item.empresas_atribuidas} empresas</small></span>{responsavelId === item.id && <CheckCircle2 size={16} />}
          </button>)}
          {!responsaveis.length && <div className="contabil-mini-empty"><Users size={20} />Nenhum usuário ativo disponível. Cadastre ou ative usuários no módulo Usuários.</div>}
        </aside>
        <div className="contabil-assignment-companies">
          <div className="contabil-subheading"><strong>Empresas</strong><small>{selecionadas.length} selecionadas</small></div>
          <div className="contabil-assignment-filters">
            <label className="contabil-search compact"><Search size={15} /><input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Pesquisar empresa ou CNPJ..." /></label>
            <select value={regime} onChange={(event) => setRegime(event.target.value)}><option value="TODOS">Todos os regimes</option><option value="SIMPLES NACIONAL">Simples Nacional</option><option value="LUCRO PRESUMIDO">Lucro Presumido</option><option value="LUCRO REAL">Lucro Real</option></select>
          </div>
          {pendente && <div className="contabil-transfer-confirm">
            <div><strong>Transferir empresa?</strong><span>{pendente.razao_social} está atribuída a {pendente.responsavel_nome || 'outro responsável'}.</span></div>
            <button className="button secondary" onClick={() => setPendente(null)}>Cancelar</button>
            <button className="button primary" onClick={confirmarTransferencia}>Confirmar transferência</button>
          </div>}
          <div className="contabil-assignment-company-list">
            {filtradas.map((empresa) => {
              const checked = selecionadas.includes(empresa.id);
              const ownerConflict = Boolean(empresa.responsavel_id && empresa.responsavel_id !== responsavelId);
              return <label key={empresa.id} className={'contabil-assignment-company' + (ownerConflict ? ' conflict' : '')}>
                <input type="checkbox" checked={checked} disabled={responsavelId === null} onChange={() => alternarEmpresa(empresa)} />
                <span className="contabil-company-icon"><Building2 size={15} /></span>
                <span className="contabil-assignment-company-name"><strong>{empresa.razao_social}</strong><small>{empresa.cnpj} · {empresa.regime_tributario || 'Regime não informado'}</small></span>
                {ownerConflict && !checked && <span className="contabil-owner-conflict">Com {empresa.responsavel_nome}</span>}
                {checked && <span className="contabil-owner-selected">{transferencias.includes(empresa.id) ? 'Transferência' : 'Selecionada'}</span>}
              </label>;
            })}
            {!filtradas.length && <div className="contabil-mini-empty">Nenhuma empresa corresponde à pesquisa.</div>}
          </div>
        </div>
      </div>}
      <footer className="contabil-modal-footer"><span>As alterações só serão gravadas ao salvar.</span><div><button className="button secondary" onClick={onClose}>Cancelar</button><button className="button primary" disabled={loading || saving || responsavelId === null || Boolean(pendente)} onClick={() => void salvar()}>{saving ? 'Salvando...' : 'Salvar atribuições'}</button></div></footer>
    </section>
  </div>;
}
