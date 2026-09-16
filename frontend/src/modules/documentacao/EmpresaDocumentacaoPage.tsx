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
  const [selected, setSelected] = useState<number | null>(null);
  const [docs, setDocs] = useState<Documento[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<'upload' | 'version' | null>(null);
  const [docTarget, setDocTarget] = useState<Documento | null>(null);
  const [versions, setVersions] = useState<Versao[]>([]);
  const [error, setError] = useState('');

  const roots = useMemo(
    () => cats.filter((c) => c.ativo && c.categoria_pai_id === null),
    [cats],
  );

  const current = selected ? cats.find((c) => c.id === selected) ?? null : null;

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

      if (selected) {
        const result = await listarDocumentos(empresaId, selected);
        setDocs(result.documentos);
      } else {
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

  useEffect(() => {
    if (!selected) {
      setDocs([]);
      return;
    }

    void listarDocumentos(empresaId, selected)
      .then((result) => setDocs(result.documentos))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Erro ao carregar documentos.');
      });
  }, [empresaId, selected]);

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
        <div className="panel empty">
          <strong>{error}</strong>
        </div>
      </div>
    );
  }

  return (
    <div className="page documentacao-detail-page">
      <div className="doc-detail-back">
        <Link to="/documentacao">
          <ArrowLeft size={15} />
          Voltar para documentação
        </Link>
      </div>

      <div className="page-heading">
        <div>
          <span className="eyebrow">DOSSIÊ EMPRESARIAL</span>
          <h2>
            <Building2 size={24} />
            {empresa?.razao_social}
          </h2>
          <p>
            {empresa?.nome_fantasia || 'Sem nome fantasia'} · {empresa?.cnpj}
          </p>
        </div>

        <div className="actions">
          {current && (
            <button className="button primary" onClick={() => setModal('upload')}>
              <Upload size={14} /> Enviar documento
            </button>
          )}
        </div>
      </div>

      {!selected ? (
        <>
          <div className="explorer-shell panel">
            <div className="explorer-toolbar">
              <div className="explorer-path">
                <button type="button" onClick={() => setSelected(null)}><Folder size={15}/> Documentação</button>
                <ChevronRight size={13}/>
                <span>{empresa?.razao_social}</span>
              </div>
              <div className="explorer-hint">3 pastas de documentação</div>
            </div>
            <div className="explorer-table-head">
              <span>Nome</span><span>Tipo</span><span>Documentos</span><span></span>
            </div>
            <div className="explorer-folder-list">
              {roots.map((category) => (
                <button
                  key={category.id}
                  type="button"
                  className="explorer-folder-row"
                  onClick={() => setSelected(category.id)}
                >
                  <span className="explorer-name"><span className="explorer-folder-icon"><Folder size={18}/></span><strong>{category.nome}</strong></span>
                  <span className="explorer-type">Pasta de arquivos</span>
                  <span className="explorer-count">{category.documentos_count}</span>
                  <ChevronRight size={16}/>
                </button>
              ))}
            </div>
          </div>

          <div className="doc-folder-help panel">
            <Folder size={17} />
            <span><strong>Estrutura fixa</strong> — o dossiê utiliza apenas as pastas Pessoal (Sócio), Societário e IRPF. Os documentos ficam dentro da pasta correspondente, com histórico de versões.</span>
          </div>
        </>
      ) : (
        <>
          <div className="doc-breadcrumb">
            <button type="button" onClick={() => setSelected(null)}>
              <Folder size={15} /> Documentação
            </button>
            <ChevronRight size={13} />
            <strong>{current?.nome}</strong>
          </div>

          <div className="doc-category-header panel">
            <div>
              <span className="doc-folder-icon">
                <Folder size={20} />
              </span>
              <div>
                <strong>{current?.nome}</strong>
                <small>{current?.descricao || 'Documentos desta pasta'}</small>
              </div>
            </div>

            <div className="actions">
              <button className="button primary" onClick={() => setModal('upload')}>
                <Upload size={13} /> Enviar documento
              </button>
            </div>
          </div>

          <div className="panel doc-list-panel">
            <div className="section-title-row">
              <div>
                <h3>
                  <FileText size={17} /> Documentos
                </h3>
                <span>{docs.length} documento(s) nesta pasta</span>
              </div>
            </div>

            {docs.length === 0 ? (
              <div className="empty">
                <Folder size={28} />
                <strong>Nenhum documento nesta pasta</strong>
                <span>Envie o primeiro arquivo para esta categoria.</span>
              </div>
            ) : (
              <div className="doc-items">
                {docs.map((doc) => (
                  <div className="doc-item" key={doc.id}>
                    <span className="doc-file-icon">
                      <FileText size={18} />
                    </span>

                    <div className="doc-item-main">
                      <strong>{doc.nome}</strong>
                      <small>
                        {doc.nome_arquivo || 'Sem arquivo'} · {doc.versoes_count} versão(ões)
                      </small>
                    </div>

                    <div className="doc-item-actions">
                      <button
                        className="icon-button"
                        title="Histórico"
                        onClick={() => void openVersions(doc)}
                      >
                        <History size={15} />
                      </button>

                      {doc.ultima_versao_id && (
                        <>
                          <button
                            className="icon-button"
                            onClick={() => void visualizarVersao(doc.ultima_versao_id as number)}
                            title="Visualizar"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            className="icon-button"
                            onClick={() =>
                              void baixarVersao(
                                doc.ultima_versao_id as number,
                                doc.nome_arquivo || doc.nome,
                              )
                            }
                            title="Baixar"
                          >
                            <Download size={15} />
                          </button>
                        </>
                      )}

                      <button
                        className="button secondary small"
                        onClick={() => {
                          setDocTarget(doc);
                          void openVersions(doc);
                        }}
                      >
                        Nova versão
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {modal === 'upload' && current && (
        <Modal title={`Enviar documento · ${current.nome}`} onClose={() => setModal(null)}>
          <UploadForm
            onCancel={() => setModal(null)}
            onSave={async (data) => {
              await uploadDocumento(
                empresaId,
                current.id,
                data.nome,
                data.file,
                data.observacao,
              );
              setModal(null);
              const result = await listarDocumentos(empresaId, current.id);
              setDocs(result.documentos);
              await load();
            }}
          />
        </Modal>
      )}

      {modal === 'version' && docTarget && (
        <Modal title={`Histórico · ${docTarget.nome}`} onClose={() => setModal(null)}>
          <div className="version-list">
            {versions.length === 0 ? (
              <span>Nenhuma versão registrada.</span>
            ) : (
              versions.map((version) => (
                <div className="version-row" key={version.id}>
                  <div>
                    <strong>Versão {version.versao}</strong>
                    <small>
                      {version.nome_arquivo || 'Arquivo'} · {version.usuario_nome || 'Usuário'} ·{' '}
                      {version.criado_em}
                    </small>
                  </div>

                  <div className="download-actions">
                    <button
                      className="icon-button"
                      onClick={() => void visualizarVersao(version.id)}
                      title="Visualizar"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      className="icon-button"
                      onClick={() =>
                        void baixarVersao(
                          version.id,
                          version.nome_arquivo || `documento_v${version.versao}`,
                        )
                      }
                      title="Baixar"
                    >
                      <Download size={14} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="modal-actions">
            <button className="button secondary" onClick={() => setModal(null)}>
              Fechar
            </button>
          </div>

          <InlineVersionForm
            documentId={docTarget.id}
            onDone={async () => {
              const versionResult = await listarVersoes(docTarget.id);
              setVersions(versionResult.versoes);

              if (current) {
                const documentResult = await listarDocumentos(empresaId, current.id);
                setDocs(documentResult.documentos);
              }
            }}
          />
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
