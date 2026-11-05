import { BookOpenCheck, Clock3 } from 'lucide-react';
import { Link } from 'react-router-dom';

export function ContabilLancamentosPage() {
  return <div className="page contabil-page">
    <div className="page-heading">
      <div><span className="eyebrow">MÓDULO CONTÁBIL</span><h2>Lançamentos e Conferências</h2><p>Área independente para processamento, conferência e fechamento contábil.</p></div>
      <Link className="button secondary" to="/contabil/documentacao">Voltar à documentação</Link>
    </div>
    <section className="panel contabil-roadmap-card">
      <span><BookOpenCheck size={24} /></span>
      <div><h3>Etapa planejada</h3><p>Esta área será desenvolvida separadamente da recepção de documentos. O desenho funcional prevê recebimento para processamento, controle de lançamentos, conferências e fechamento mensal.</p><small><Clock3 size={13} /> A implementação será iniciada em uma etapa própria.</small></div>
    </section>
  </div>;
}
