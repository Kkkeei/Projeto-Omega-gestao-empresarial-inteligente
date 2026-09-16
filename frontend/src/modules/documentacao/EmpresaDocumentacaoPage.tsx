import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ArrowLeft,
  Building2,
  ChevronRight,
  Download,
  Eye,
  FileText,
  Folder,
  History,
  Upload,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import {
  baixarVersao,
  listarCategorias,
  listarDocumentos,
  listarVersoes,
  uploadDocumento,
  uploadNovaVersao,
  visualizarVersao,
  type CategoriaDocumento,
  type Documento,
  type Versao,
} from '../../services/api/documentacao';
import { apiFetch } from '../../services/api/client';
import { Loading } from '../../components/ui/Loading';

export function EmpresaDocumentacaoPage() {
  const { id } = useParams();
  const empresaId = Number(id);

  const [empresa, setEmpresa] = useState<any>(null);
  const [cats, setCats] = useState<CategoriaDocumento[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [docs, setDocs] = useState<Documento[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [modal, setModal] = useState<'upload' | 'version' | null>(null);
  const [docTarget, setDocTarget] = useState<Documento | null>(null);
  const [versions, setVersions] = useState<Versao[]>([]);
  const [error, setError] = useState('');

  const folders = useMemo(() => {
    const wanted = ['Pessoal (Sócio)', 'Societário', 'IRPF'];
    const activeRoots = cats.filter(
      (c) => c.ativo && c.categoria_pai_id === null && wanted.includes(c.nome),
    );
    return wanted
      .map((name) => activeRoots.find((c) => c.nome === name))
      .filter((c): c is CategoriaDocumento => Boolean(c));
  }, [cats]);

  const selectedFolder = selectedCategoryId
    ? folders.find((c) => c.id === selectedCategoryId) ?? null
    : null;

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [empresaData, categoriaData] = await Promise.all([
        apiFetch<any>(`/api/v1/empresas/${empresaId}`),
        listarCategorias(empresaId),
      ]);
      setEmpresa(empresaData);
      setCats(categoriaData.categorias);

      const wanted = ['Pessoal (Sócio)', 'Societário', 'IRPF'];
      const first = wanted
        .map((name) => categoriaData.categorias.find(
          (c: CategoriaDocumento) => c.ativo && c.categoria_pai_id === null && c.nome === name,
        ))
        .find(Boolean) as CategoriaDocumento | undefined;

      if (selectedCategoryId && categoriaData.categorias.some((c: CategoriaDocumento) => c.id === selectedCategoryId && c.ativo)) {
        // mantém a pasta selecionada
      } else if (first) {
        setSelectedCategoryId(first.id);
        setLoadingDocs(true);
        try {
          const result = await listarDocumentos(empresaId, first.id);
          setDocs(result.documentos);
        } finally {
          setLoadingDocs(false);
        }
      } else {
        setSelectedCategoryId(null);
        setDocs([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar documentação.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [empresaId]);

  async function selectFolder(categoryId: number) {
    if (selectedCategoryId === categoryId) return;
    setSelectedCategoryId(categoryId);
    setLoadingDocs(true);
    setError('');
    try {
      const result = await listarDocumentos(empresaId, categoryId);
      setDocs(result.documentos);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar documentos.');
      setDocs([]);
    } finally {
      setLoadingDocs(false);
    }
  }

  async function refreshSelectedFolder() {
    if (!selectedCategoryId) return;
    const result = await listarDocumentos(empresaId, selectedCategoryId);
    setDocs(result.documentos);
    await load();
  }

  async function openVersions(doc: Documento) {
    try {
      setDocTarget(doc);
      const result = await listarVersoes(doc.id);
      setVersions(result.versoes);
      setModal('version');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar versões.');
    }
  }

  if (loading && !empresa) {
    return (
      <div className="page">
        <Loading text="Carregando documentação..." />
      </div>
    );
  }

  if (error && !empresa) {
    return (
      <div className="page">
        <div className="panel empty"><strong>{error}</strong></div>
      </div>
    );
  }

  return (
    <div className="page documentacao-detail-page">
      <div className="doc-detail-back">
        <Link to="/documentacao"><ArrowLeft size={15} /> Voltar para documentação</Link>
      </div>

      <div className="page-heading">
        <div>
          <span className="eyebrow">DOSSIÊ EMPRESARIAL</span>
          <h2><Building2 size={24} /> {empresa?.razao_social}</h2>
          <p>{empresa?.nome_fantasia || 'Sem nome fantasia'} · {empresa?.cnpj}</p>
        </div>
        <div className="doc-company-status">
          <span className={`status-pill ${empresa?.ativo ? 'ok' : 'off'}`}><i />{empresa?.ativo ? 'Ativa' : 'Inativa'}</span>
          <span className="regime">{empresa?.regime_tributario || 'Regime não informado'}</span>
        </div>
      </div>

      {error && <div className="panel doc-inline-error"><strong>{error}</strong></div>}

      <section className="doc-category-section">
        <div className="section-title-row">
          <div>
            <span className="eyebrow">1 · TIPO DE DOCUMENTAÇÃO</span>
            <h3>Escolha a pasta para consultar</h3>
          </div>
          <span className="section-hint">Três áreas do dossiê empresarial</span>
        </div>

        <div className="doc-category-card-grid">
          {folders.map((folder) => {
            const selected = selectedCategoryId === folder.id;
            const count = folder.documentos_count ?? 0;
            const tone = folder.nome === 'Pessoal (Sócio)' ? 'blue' : folder.nome === 'Societário' ? 'green' : 'amber';
            return (
              <button
                key={folder.id}
                type="button"
                className={`doc-category-card ${tone} ${selected ? 'selected' : ''}`}
                onClick={() => void selectFolder(folder.id)}
              >
                <span className="doc-category-card-top">
                  <span className="doc-category-icon"><Folder size={23} /></span>
                  {selected && <span className="doc-category-selected">Selecionada</span>}
                </span>
                <span className="doc-category-kicker">PASTA</span>
                <strong>{folder.nome}</strong>
                <small>{count} documento{count === 1 ? '' : 's'}</small>
                <span className="doc-category-footer">
                  <span>{selected ? 'Documentos abaixo' : 'Clique para abrir'}</span>
                  <ChevronRight size={15} className={selected ? 'active' : ''} />
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="doc-selected-workspace panel">
        {!selectedFolder ? (
          <div className="doc-selected-empty">
            <Folder size={34} />
            <strong>Selecione uma pasta acima</strong>
            <span>Escolha Pessoal (Sócio), Societário ou IRPF para visualizar os documentos.</span>
          </div>
        ) : (
          <>
            <div className="doc-selected-head">
              <div className="doc-selected-title">
                <span className="doc-selected-folder-icon"><Folder size={20} /></span>
                <div>
                  <span className="eyebrow">2 · CONTEÚDO DA PASTA</span>
                  <h3>{selectedFolder.nome}</h3>
                  <p>{docs.length} arquivo(s) disponível(eis) nesta pasta.</p>
                </div>
              </div>
              <button className="button primary" onClick={() => setModal('upload')}>
                <Upload size={14} /> Adicionar documento
              </button>
            </div>

            {loadingDocs ? (
              <div className="doc-accordion-empty"><Loading text="Carregando documentos..." /></div>
            ) : docs.length === 0 ? (
              <div className="doc-selected-empty compact">
                <FileText size={28} />
                <strong>Nenhum documento nesta pasta</strong>
                <span>Use “Adicionar documento” para enviar o primeiro arquivo.</span>
                <button className="button secondary small" onClick={() => setModal('upload')}><Upload size={13} /> Adicionar documento</button>
              </div>
            ) : (
              <div className="doc-table">
                <div className="doc-table-head">
                  <span>Nome</span><span>Arquivo</span><span>Versões</span><span>Atualizado</span><span></span>
                </div>
                {docs.map((doc) => (
                  <div className="doc-table-row" key={doc.id}>
                    <div className="doc-table-name">
                      <span className="doc-file-icon"><FileText size={17} /></span>
                      <div><strong>{doc.nome}</strong><small>{doc.criado_em}</small></div>
                    </div>
                    <span>{doc.nome_arquivo || '—'}</span>
                    <span>{doc.versoes_count}</span>
                    <span>{doc.atualizado_em}</span>
                    <div className="doc-table-actions">
                      <button className="icon-button" title="Histórico" onClick={() => void openVersions(doc)}><History size={15} /></button>
                      {doc.ultima_versao_id && <>
                        <button className="icon-button" title="Visualizar" onClick={() => void visualizarVersao(doc.ultima_versao_id as number)}><Eye size={15} /></button>
                        <button className="icon-button" title="Baixar" onClick={() => void baixarVersao(doc.ultima_versao_id as number, doc.nome_arquivo || doc.nome)}><Download size={15} /></button>
                      </>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      <div className="doc-explorer-note panel">
        <Folder size={16} />
        <div><strong>Estrutura da documentação</strong><span>As três pastas do dossiê são Pessoal (Sócio), Societário e IRPF. Selecione uma delas nos cards acima para carregar os documentos abaixo, sem sair da página.</span></div>
      </div>

      {modal === 'upload' && selectedFolder && (
        <Modal title={`Adicionar documento · ${selectedFolder.nome}`} onClose={() => setModal(null)}>
          <UploadForm onCancel={() => setModal(null)} onSave={async (data) => {
            await uploadDocumento(empresaId, selectedFolder.id, data.nome, data.file, data.observacao);
            setModal(null);
            await refreshSelectedFolder();
          }} />
        </Modal>
      )}

      {modal === 'version' && docTarget && (
        <Modal title={`Histórico · ${docTarget.nome}`} onClose={() => setModal(null)}>
          <div className="version-list">
            {versions.length === 0 ? <span>Nenhuma versão registrada.</span> : versions.map((version) => (
              <div className="version-row" key={version.id}>
                <div><strong>Versão {version.versao}</strong><small>{version.nome_arquivo || 'Arquivo'} · {version.usuario_nome || 'Usuário'} · {version.criado_em}</small></div>
                <div className="download-actions">
                  <button className="icon-button" onClick={() => void visualizarVersao(version.id)} title="Visualizar"><Eye size={14} /></button>
                  <button className="icon-button" onClick={() => void baixarVersao(version.id, version.nome_arquivo || `documento_v${version.versao}`)} title="Baixar"><Download size={14} /></button>
                </div>
              </div>
            ))}
          </div>
          <div className="modal-actions"><button className="button secondary" onClick={() => setModal(null)}>Fechar</button></div>
          <InlineVersionForm documentId={docTarget.id} onDone={async () => {
            const versionResult = await listarVersoes(docTarget.id);
            setVersions(versionResult.versoes);
            await refreshSelectedFolder();
          }} />
        </Modal>
      )}
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-button" type="button" onClick={onClose}>
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function UploadForm({
  onCancel,
  onSave,
}: {
  onCancel: () => void;
  onSave: (data: { nome: string; file: File; observacao?: string }) => Promise<void>;
}) {
  const [nome, setNome] = useState('');
  const [observacao, setObservacao] = useState('');
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="modal-form">
      <label>
        Nome do documento
        <input
          value={nome}
          onChange={(event) => setNome(event.target.value)}
          placeholder="Ex.: Contrato Social"
        />
      </label>

      <label>
        Arquivo
        <input
          type="file"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <small>Limite padrão: 25 MB.</small>
      </label>

      <label>
        Observação
        <textarea
          value={observacao}
          onChange={(event) => setObservacao(event.target.value)}
        />
      </label>

      <div className="modal-actions">
        <button className="button secondary" type="button" onClick={onCancel}>
          Cancelar
        </button>
        <button
          className="button primary"
          type="button"
          disabled={!nome.trim() || !file}
          onClick={() => {
            if (!file) return;
            void onSave({
              nome: nome.trim(),
              file,
              observacao: observacao.trim() || undefined,
            });
          }}
        >
          Enviar documento
        </button>
      </div>
    </div>
  );
}

function InlineVersionForm({
  documentId,
  onDone,
}: {
  documentId: number;
  onDone: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);

  async function handleUpload() {
    if (!file || sending) return;

    setSending(true);
    try {
      await uploadNovaVersao(documentId, file);
      setFile(null);
      await onDone();
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="version-upload">
      <h4>Adicionar nova versão</h4>
      <input
        type="file"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <button
        className="button primary"
        type="button"
        disabled={!file || sending}
        onClick={() => void handleUpload()}
      >
        {sending ? 'Enviando...' : 'Enviar nova versão'}
      </button>
    </div>
  );
}
