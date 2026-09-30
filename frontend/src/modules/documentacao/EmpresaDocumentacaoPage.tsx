import { useEffect, useMemo, useState, type DragEvent, type ReactNode } from 'react';
import {
  ArrowLeft,
  Building2,
  Download,
  Eye,
  FileText,
  Folder,
  History,
  Pencil,
  Plus,
  FolderPlus,
  ChevronRight,
  ChevronLeft,
  ArrowUp,
  Home,
  FolderOpen,
  Trash2,
  Upload,
  Move,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import {
  arquivarCategoria,
  arquivarDocumento,
  atualizarCategoria,
  baixarVersao,
  criarCategoria,
  moverCategoria,
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
  const [modal, setModal] = useState<'upload' | 'version' | 'category' | 'editCategory' | 'moveCategory' | null>(null);
  const [docTarget, setDocTarget] = useState<Documento | null>(null);
  const [categoryTarget, setCategoryTarget] = useState<CategoriaDocumento | null>(null);
  const [versions, setVersions] = useState<Versao[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<{ kind: 'document' | 'category'; id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [dropFile, setDropFile] = useState<File | null>(null);
  const [categoryParentId, setCategoryParentId] = useState<number | null>(null);
  const [dragCategoryId, setDragCategoryId] = useState<number | null>(null);
  const [dropCategoryId, setDropCategoryId] = useState<number | null>(null);

  const activeCategories = useMemo(
    () => cats
      .filter((c) => c.ativo)
      .sort((a, b) => {
        const parentA = a.categoria_pai_id ?? 0;
        const parentB = b.categoria_pai_id ?? 0;
        return parentA - parentB || a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR');
      }),
    [cats],
  );

  const selectedFolder = selectedCategoryId
    ? activeCategories.find((c) => c.id === selectedCategoryId) ?? null
    : null;

  const visibleFolders = useMemo(
    () => activeCategories
      .filter((c) => (selectedCategoryId === null ? c.categoria_pai_id === null : c.categoria_pai_id === selectedCategoryId))
      .sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR')),
    [activeCategories, selectedCategoryId],
  );

  const parentFolder = useMemo(
    () => selectedFolder?.categoria_pai_id
      ? activeCategories.find((c) => c.id === selectedFolder.categoria_pai_id) ?? null
      : null,
    [activeCategories, selectedFolder],
  );

  const selectedPath = useMemo(() => {
    const path: CategoriaDocumento[] = [];
    let current = selectedFolder;
    const seen = new Set<number>();
    while (current && !seen.has(current.id)) {
      path.unshift(current);
      seen.add(current.id);
      current = current.categoria_pai_id
        ? activeCategories.find((item) => item.id === current?.categoria_pai_id) ?? null
        : null;
    }
    return path;
  }, [activeCategories, selectedFolder]);

  async function load(preferredCategoryId: number | null = null) {
    setLoading(true);
    setError('');
    try {
      const [empresaData, categoriaData] = await Promise.all([
        apiFetch<any>(`/api/v1/empresas/${empresaId}`),
        listarCategorias(empresaId),
      ]);
      setEmpresa(empresaData);
      setCats(categoriaData.categorias);

      const wantedId = preferredCategoryId ?? null;

      setSelectedCategoryId(wantedId);
      if (wantedId) {
        setLoadingDocs(true);
        try {
          const result = await listarDocumentos(empresaId, wantedId);
          setDocs(result.documentos);
        } finally {
          setLoadingDocs(false);
        }
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

  async function goToCategory(categoryId: number | null) {
    if (categoryId === null) {
      setSelectedCategoryId(null);
      setDocs([]);
      setLoadingDocs(false);
      return;
    }
    await selectFolder(categoryId);
  }

  async function refreshSelectedFolder() {
    if (!selectedCategoryId) return;
    const result = await listarDocumentos(empresaId, selectedCategoryId);
    setDocs(result.documentos);
    await load(selectedCategoryId);
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

  function openEditCategory() {
    if (!selectedFolder) return;
    setCategoryTarget(selectedFolder);
    setModal('editCategory');
  }

  function openDeleteCategory() {
    if (!selectedFolder) return;
    setDeleteTarget({ kind: 'category', id: selectedFolder.id, name: selectedFolder.nome });
  }

  async function confirmDelete() {
    if (!deleteTarget || deleting) return;
    setDeleting(true);
    setError('');
    try {
      if (deleteTarget.kind === 'document') {
        await arquivarDocumento(deleteTarget.id);
        setDeleteTarget(null);
        await refreshSelectedFolder();
      } else {
        await arquivarCategoria(deleteTarget.id);
        setDeleteTarget(null);
        await load();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível excluir o item.');
    } finally {
      setDeleting(false);
    }
  }

  function beginCategoryDrag(event: DragEvent<HTMLElement>, categoryId: number) {
    event.stopPropagation();
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/omega-category-id', String(categoryId));
    setDragCategoryId(categoryId);
    setDropCategoryId(null);
  }

  function overCategoryDrop(event: DragEvent<HTMLElement>, targetCategoryId: number) {
    if (!dragCategoryId || dragCategoryId === targetCategoryId) return;
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'move';
    setDropCategoryId(targetCategoryId);
  }

  function leaveCategoryDrop(event: DragEvent<HTMLElement>, targetCategoryId: number) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null) && dropCategoryId === targetCategoryId) {
      setDropCategoryId(null);
    }
  }

  async function dropCategoryInto(event: DragEvent<HTMLElement>, targetCategoryId: number) {
    event.preventDefault();
    event.stopPropagation();
    const draggedId = dragCategoryId ?? Number(event.dataTransfer.getData('text/omega-category-id') || 0);
    setDropCategoryId(null);
    setDragCategoryId(null);
    if (!draggedId || draggedId === targetCategoryId) return;
    setError('');
    try {
      await moverCategoria(draggedId, targetCategoryId);
      await load(selectedCategoryId ?? targetCategoryId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível mover a pasta.');
    }
  }

  function endCategoryDrag() {
    setDragCategoryId(null);
    setDropCategoryId(null);
  }

  async function moveSelectedFolder(targetParentId: number | null) {
    if (!selectedFolder) return;
    const sourceId = selectedFolder.id;
    setError('');
    try {
      await moverCategoria(sourceId, targetParentId);
      setModal(null);
      await load(sourceId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível mover a pasta.');
    }
  }

  function prepareDroppedFile(file: File) {
    const maxSize = 25 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('O arquivo excede o limite de 25 MB.');
      return;
    }
    setError('');
    setDropFile(file);
    setModal('upload');
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0];
    if (file) prepareDroppedFile(file);
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

      <div className="page-heading doc-company-heading">
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

      <section className="doc-folder-area">
        <div className="doc-folder-toolbar explorer-toolbar">
          <div className="doc-explorer-nav">
            <button
              className="doc-explorer-nav-button"
              type="button"
              disabled={selectedCategoryId === null}
              title="Voltar para a pasta anterior"
              onClick={() => void goToCategory(parentFolder?.id ?? null)}
            >
              <ChevronLeft size={15} />
            </button>
            <button
              className="doc-explorer-nav-button"
              type="button"
              disabled={selectedCategoryId === null}
              title="Subir um nível"
              onClick={() => void goToCategory(parentFolder?.id ?? null)}
            >
              <ArrowUp size={14} />
            </button>
            <button
              className="doc-explorer-nav-button"
              type="button"
              title="Ir para a raiz"
              onClick={() => void goToCategory(null)}
            >
              <Home size={14} />
            </button>
          </div>

          <div
            className={`doc-folder-breadcrumb ${dragCategoryId ? 'drag-root-target' : ''}`}
            onDragOver={(event) => {
              if (dragCategoryId) {
                event.preventDefault();
                event.dataTransfer.dropEffect = 'move';
              }
            }}
            onDrop={(event) => {
              if (dragCategoryId) {
                event.preventDefault();
                const draggedId = dragCategoryId;
                setDragCategoryId(null);
                setDropCategoryId(null);
                void moverCategoria(draggedId, null)
                  .then(() => load(selectedCategoryId ?? null))
                  .catch((err) => setError(err instanceof Error ? err.message : 'Não foi possível mover a pasta.'));
              }
            }}
          >
            <button className="doc-breadcrumb-home" type="button" onClick={() => void goToCategory(null)} title="Raiz">
              <Home size={13} />
              <span>Documentação</span>
            </button>
            {selectedPath.map((item, index) => (
              <span className="doc-breadcrumb-item" key={item.id}>
                <ChevronRight size={12} />
                <button type="button" onClick={() => void goToCategory(item.id)} title={`Abrir ${item.nome}`}>
                  {item.nome}
                </button>
              </span>
            ))}
          </div>

          <div className="doc-folder-toolbar-actions">
            <button className="button secondary small" type="button" onClick={() => { setCategoryParentId(null); setModal('category'); }}>
              <Plus size={13} /> Nova pasta
            </button>
            {selectedFolder && (
              <button className="button primary small" type="button" onClick={() => { setCategoryParentId(selectedFolder.id); setModal('category'); }}>
                <FolderPlus size={13} /> Nova subpasta
              </button>
            )}
          </div>
        </div>

        <div className="doc-explorer-frame panel">
          <div className="doc-explorer-location">
            <div>
              <span className="eyebrow">NAVEGAÇÃO DE PASTAS</span>
              <strong>{selectedFolder?.nome || 'Documentação'}</strong>
              <small>{selectedFolder ? 'Abra uma subpasta para navegar dentro dela.' : 'Pastas principais da empresa.'}</small>
            </div>
            {selectedFolder && (
              <span className="doc-explorer-location-count">
                {visibleFolders.length} {visibleFolders.length === 1 ? 'subpasta' : 'subpastas'}
              </span>
            )}
          </div>

          <div className="doc-explorer-list">
            {visibleFolders.map((folder) => {
              const childCount = activeCategories.filter((c) => c.categoria_pai_id === folder.id).length;
              const selected = selectedCategoryId === folder.id;
              return (
                <button
                  key={folder.id}
                  type="button"
                  draggable
                  onDragStart={(event) => beginCategoryDrag(event, folder.id)}
                  onDragEnd={endCategoryDrag}
                  onDragOver={(event) => overCategoryDrop(event, folder.id)}
                  onDragLeave={(event) => leaveCategoryDrop(event, folder.id)}
                  onDrop={(event) => void dropCategoryInto(event, folder.id)}
                  className={`doc-explorer-folder ${selected ? 'selected' : ''} ${dropCategoryId === folder.id ? 'drop-target' : ''} ${dragCategoryId === folder.id ? 'dragging' : ''}`}
                  onClick={() => void selectFolder(folder.id)}
                  title="Abrir pasta"
                >
                  <span className="doc-explorer-folder-icon"><FolderOpen size={20} /></span>
                  <span className="doc-explorer-folder-main">
                    <strong>{folder.nome}</strong>
                    <small>{childCount ? `${childCount} ${childCount === 1 ? 'subpasta' : 'subpastas'} · ` : ''}{folder.documentos_count ?? 0} documento(s)</small>
                  </span>
                  <ChevronRight size={16} className="doc-explorer-folder-chevron" />
                </button>
              );
            })}
            {visibleFolders.length === 0 && (
              <div className="doc-explorer-empty">
                <Folder size={30} />
                <strong>{selectedFolder ? 'Nenhuma subpasta nesta pasta' : 'Nenhuma pasta criada'}</strong>
                <span>{selectedFolder ? 'Use “Nova subpasta” para criar uma pasta dentro deste nível.' : 'Use “Nova pasta” para começar a organizar a documentação.'}</span>
              </div>
            )}
          </div>

          <div className="doc-folder-actions-row">
            <div className="doc-folder-selection-text">
              {selectedFolder ? (
                <>
                  <strong>{selectedFolder.nome}</strong>
                  <span>{selectedFolder.descricao || 'Pasta de documentação da empresa'}</span>
                </>
              ) : (
                <span>Navegue pelas pastas usando a barra de caminho acima.</span>
              )}
            </div>
            {selectedFolder && (
              <div className="doc-folder-actions">
                <button className="icon-button" type="button" title="Mover pasta" onClick={() => { setCategoryTarget(selectedFolder); setModal('moveCategory'); }}>
                  <Move size={15} />
                </button>
                <button className="icon-button" type="button" title="Editar pasta" onClick={openEditCategory}>
                  <Pencil size={15} />
                </button>
                <button className="icon-button danger-icon" type="button" title="Excluir pasta" onClick={openDeleteCategory}>
                  <Trash2 size={15} />
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="doc-selected-workspace panel">
        {!selectedFolder ? (
          <div className="doc-selected-empty">
            <Folder size={34} />
            <strong>Selecione uma pasta acima</strong>
            <span>Clique em uma das pastas para visualizar os documentos.</span>
          </div>
        ) : (
          <>
            <div className="doc-selected-head">
              <div className="doc-selected-title">
                <span className="doc-selected-folder-icon"><Folder size={20} /></span>
                <div>
                  <span className="eyebrow">CONTEÚDO DA PASTA</span>
                  <h3>{selectedFolder.nome}</h3>
                  <p>{docs.length} arquivo(s) disponível(eis) nesta pasta.</p>
                </div>
              </div>
              <button className="button primary" type="button" onClick={() => setModal('upload')}>
                <Upload size={14} /> Adicionar documento
              </button>
            </div>

            {loadingDocs ? (
              <div className="doc-accordion-empty"><Loading text="Carregando documentos..." /></div>
            ) : (
              <>
                <div
                  className={`doc-drop-zone ${dragActive ? 'drag-active' : ''} ${docs.length ? 'with-documents' : ''}`}
                  onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
                  onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; }}
                  onDragLeave={(event) => {
                    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragActive(false);
                  }}
                  onDrop={handleDrop}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setModal('upload'); }}
                  onClick={() => setModal('upload')}
                  aria-label={`Arraste um documento para a pasta ${selectedFolder.nome}`}
                >
                  <span className="doc-drop-icon"><Upload size={23} /></span>
                  <strong>{dragActive ? 'Solte o documento aqui' : 'Arraste o documento para esta pasta'}</strong>
                  <span>{dragActive ? `O arquivo será salvo em ${selectedFolder.nome}.` : 'ou clique para selecionar um arquivo do computador'}</span>
                  <small>Até 25 MB · o arquivo será vinculado automaticamente à pasta atual</small>
                </div>

                {docs.length === 0 ? (
                  <div className="doc-selected-empty compact">
                    <FileText size={28} />
                    <strong>Nenhum documento nesta pasta</strong>
                    <span>Use a área acima ou “Adicionar documento” para enviar o primeiro arquivo.</span>
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
                      <button className="icon-button" type="button" title="Histórico" onClick={() => void openVersions(doc)}><History size={15} /></button>
                      {doc.ultima_versao_id && <>
                        <button className="icon-button" type="button" title="Visualizar" onClick={() => void visualizarVersao(doc.ultima_versao_id as number)}><Eye size={15} /></button>
                        <button className="icon-button" type="button" title="Baixar" onClick={() => void baixarVersao(doc.ultima_versao_id as number, doc.nome_arquivo || doc.nome)}><Download size={15} /></button>
                      </>}
                      <button className="icon-button danger-icon" type="button" title="Excluir documento" onClick={() => setDeleteTarget({ kind: 'document', id: doc.id, name: doc.nome })}><Trash2 size={15} /></button>
                    </div>
                  </div>
                ))}
              </div>
                )}
              </>
            )}
          </>
        )}
      </section>

      <div className="doc-explorer-note panel">
        <Folder size={16} />
        <div><strong>Estrutura da documentação</strong><span>Crie pastas e subpastas por empresa. Cada nível mantém seus próprios documentos, nomes e histórico, sem misturar os arquivos.</span></div>
      </div>

      {modal === 'category' && (
        <Modal title={categoryParentId ? `Criar subpasta · ${selectedFolder?.nome || 'Pasta atual'}` : 'Criar nova pasta'} onClose={() => setModal(null)}>
          <CategoryForm
            existingNames={activeCategories.filter((category) => (category.categoria_pai_id ?? null) === categoryParentId).map((category) => category.nome)}
            parentId={categoryParentId}
            onCancel={() => setModal(null)}
            onSave={async (data) => {
              const created = await criarCategoria(empresaId, { ...data, categoria_pai_id: categoryParentId });
              setModal(null);
              await load(created.id);
            }}
          />
        </Modal>
      )}

      {modal === 'editCategory' && categoryTarget && (
        <Modal title={`Editar pasta · ${categoryTarget.nome}`} onClose={() => setModal(null)}>
          <CategoryEditForm
            category={categoryTarget}
            existingNames={activeCategories.filter((category) =>
              (category.categoria_pai_id ?? null) === (categoryTarget.categoria_pai_id ?? null)
              && category.id !== categoryTarget.id
            ).map((category) => category.nome)}
            onCancel={() => setModal(null)}
            onSave={async (data) => {
              await atualizarCategoria(categoryTarget.id, data);
              setModal(null);
              await load(categoryTarget.id);
            }}
          />
        </Modal>
      )}

      {modal === 'upload' && selectedFolder && (
        <Modal title={`Adicionar documento · ${selectedFolder.nome}`} onClose={() => { setDropFile(null); setModal(null); }}>
          <UploadForm
            initialFile={dropFile}
            onCancel={() => { setDropFile(null); setModal(null); }}
            onSave={async (data) => {
              await uploadDocumento(empresaId, selectedFolder.id, data.nome, data.file, data.observacao);
              setDropFile(null);
              setModal(null);
              await refreshSelectedFolder();
            }}
          />
        </Modal>
      )}

      {modal === 'moveCategory' && categoryTarget && (
        <Modal title={`Mover pasta · ${categoryTarget.nome}`} onClose={() => setModal(null)}>
          <MoveCategoryForm
            source={categoryTarget}
            categories={activeCategories}
            onCancel={() => setModal(null)}
            onMove={(targetId) => moveSelectedFolder(targetId)}
          />
        </Modal>
      )}

      {modal === 'version' && docTarget && (
        <Modal title={`Histórico · ${docTarget.nome}`} onClose={() => setModal(null)}>
          <div className="version-list">
            {versions.length === 0 ? <span>Nenhuma versão registrada.</span> : versions.map((version) => (
              <div className="version-row" key={version.id}>
                <div><strong>Versão {version.versao}</strong><small>{version.nome_arquivo || 'Arquivo'} · {version.usuario_nome || 'Usuário'} · {version.criado_em}</small></div>
                <div className="download-actions">
                  <button className="icon-button" type="button" onClick={() => void visualizarVersao(version.id)} title="Visualizar"><Eye size={14} /></button>
                  <button className="icon-button" type="button" onClick={() => void baixarVersao(version.id, version.nome_arquivo || `documento_v${version.versao}`)} title="Baixar"><Download size={14} /></button>
                </div>
              </div>
            ))}
          </div>
          <div className="modal-actions"><button className="button secondary" type="button" onClick={() => setModal(null)}>Fechar</button></div>
          <InlineVersionForm documentId={docTarget.id} onDone={async () => {
            const versionResult = await listarVersoes(docTarget.id);
            setVersions(versionResult.versoes);
            await refreshSelectedFolder();
          }} />
        </Modal>
      )}

      {deleteTarget && (
        <Modal
          title={deleteTarget.kind === 'document' ? 'Excluir documento' : 'Excluir pasta'}
          onClose={() => { if (!deleting) setDeleteTarget(null); }}
        >
          <div className="delete-confirm">
            <div className="delete-confirm-icon"><Trash2 size={22} /></div>
            <h4>Tem certeza que deseja excluir?</h4>
            <p>Você está prestes a excluir <strong>“{deleteTarget.name}”</strong>. O item será arquivado e deixará de aparecer na documentação. O histórico físico será preservado para auditoria.</p>
            {deleteTarget.kind === 'category' && <p className="delete-warning">Os documentos desta pasta também serão arquivados.</p>}
            <div className="modal-actions">
              <button className="button secondary" type="button" disabled={deleting} onClick={() => setDeleteTarget(null)}>Cancelar</button>
              <button className="button danger" type="button" disabled={deleting} onClick={() => void confirmDelete()}><Trash2 size={13} /> {deleting ? 'Excluindo...' : 'Excluir'}</button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-button" type="button" onClick={onClose}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function MoveCategoryForm({
  source,
  categories,
  onCancel,
  onMove,
}: {
  source: CategoriaDocumento;
  categories: CategoriaDocumento[];
  onCancel: () => void;
  onMove: (targetId: number | null) => Promise<void>;
}) {
  const [targetId, setTargetId] = useState<number | null>(source.categoria_pai_id ?? null);
  const [saving, setSaving] = useState(false);

  const descendants = useMemo(() => {
    const ids = new Set<number>();
    const pending = [source.id];
    while (pending.length) {
      const current = pending.pop()!;
      categories.forEach((category) => {
        if (category.categoria_pai_id === current && !ids.has(category.id)) {
          ids.add(category.id);
          pending.push(category.id);
        }
      });
    }
    return ids;
  }, [categories, source.id]);

  const options = useMemo(() => {
    const sorted = [...categories].sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR'));
    const children = new Map<number | null, CategoriaDocumento[]>();
    sorted.forEach((category) => {
      const key = category.categoria_pai_id ?? null;
      const list = children.get(key) ?? [];
      list.push(category);
      children.set(key, list);
    });

    const result: Array<{ id: number | null; label: string; disabled: boolean }> = [
      { id: null, label: 'Pastas principais (raiz)', disabled: source.categoria_pai_id === null },
    ];
    const walk = (parentId: number | null, depth: number) => {
      for (const category of children.get(parentId) ?? []) {
        if (category.id === source.id || descendants.has(category.id)) continue;
        result.push({
          id: category.id,
          label: `${'— '.repeat(depth)}${category.nome}`,
          disabled: false,
        });
        walk(category.id, depth + 1);
      }
    };
    walk(null, 0);
    return result;
  }, [categories, descendants, source]);

  return (
    <div className="modal-form move-folder-form">
      <div className="move-folder-preview">
        <span className="doc-file-icon"><Folder size={18} /></span>
        <div>
          <strong>{source.nome}</strong>
          <small>Escolha onde esta pasta ficará. As subpastas e documentos acompanham a estrutura.</small>
        </div>
      </div>
      <label>
        Mover para
        <select value={targetId === null ? '' : String(targetId)} onChange={(event) => setTargetId(event.target.value ? Number(event.target.value) : null)}>
          {options.map((option) => (
            <option key={option.id === null ? 'root' : option.id} value={option.id === null ? '' : option.id} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <small>Você também pode arrastar a pasta diretamente sobre outra pasta ou subpasta.</small>
      <div className="modal-actions">
        <button className="button secondary" type="button" disabled={saving} onClick={onCancel}>Cancelar</button>
        <button className="button primary" type="button" disabled={saving || targetId === (source.categoria_pai_id ?? null)} onClick={async () => { setSaving(true); try { await onMove(targetId); } finally { setSaving(false); } }}>
          <Move size={13} /> {saving ? 'Movendo...' : 'Mover pasta'}
        </button>
      </div>
    </div>
  );
}

function CategoryForm({ onCancel, onSave, existingNames, parentId }: {
  onCancel: () => void;
  onSave: (data: { nome: string; descricao?: string; categoria_pai_id?: number | null }) => Promise<void>;
  existingNames: string[];
  parentId: number | null;
}) {
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [saving, setSaving] = useState(false);
  const duplicated = existingNames.some((value) => value.trim().toLocaleLowerCase() === nome.trim().toLocaleLowerCase());

  async function handleSave() {
    if (!nome.trim() || duplicated || saving) return;
    setSaving(true);
    try {
      await onSave({ nome: nome.trim(), descricao: descricao.trim() || undefined, categoria_pai_id: parentId });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-form">
      <label>
        Nome da pasta
        <input value={nome} onChange={(event) => setNome(event.target.value)} placeholder="Ex.: Licitações" autoFocus />
        {duplicated && <small className="form-error">Já existe uma pasta com esse nome.</small>}
      </label>
      <label>
        Descrição (opcional)
        <textarea value={descricao} onChange={(event) => setDescricao(event.target.value)} placeholder="Ex.: Documentos de licitações e contratos" />
      </label>
      <div className="modal-actions">
        <button className="button secondary" type="button" onClick={onCancel}>Cancelar</button>
        <button className="button primary" type="button" disabled={!nome.trim() || duplicated || saving} onClick={() => void handleSave()}>{saving ? 'Criando...' : 'Criar pasta'}</button>
      </div>
    </div>
  );
}

function CategoryEditForm({ category, onCancel, onSave, existingNames }: {
  category: CategoriaDocumento;
  onCancel: () => void;
  onSave: (data: { nome: string; descricao?: string }) => Promise<void>;
  existingNames: string[];
}) {
  const [nome, setNome] = useState(category.nome);
  const [descricao, setDescricao] = useState(category.descricao || '');
  const [saving, setSaving] = useState(false);
  const duplicated = existingNames.some((value) => value.trim().toLocaleLowerCase() === nome.trim().toLocaleLowerCase());

  async function handleSave() {
    if (!nome.trim() || duplicated || saving) return;
    setSaving(true);
    try {
      await onSave({ nome: nome.trim(), descricao: descricao.trim() || undefined });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-form">
      <div className="doc-edit-folder-preview"><Folder size={19} /><div><strong>{category.nome}</strong><small>Esta alteração afeta apenas o nome e a descrição da pasta.</small></div></div>
      <label>
        Nome da pasta
        <input value={nome} onChange={(event) => setNome(event.target.value)} autoFocus />
        {duplicated && <small className="form-error">Já existe outra pasta com esse nome.</small>}
      </label>
      <label>
        Descrição (opcional)
        <textarea value={descricao} onChange={(event) => setDescricao(event.target.value)} placeholder="Descrição da pasta" />
      </label>
      <div className="modal-actions">
        <button className="button secondary" type="button" onClick={onCancel}>Cancelar</button>
        <button className="button primary" type="button" disabled={!nome.trim() || duplicated || saving} onClick={() => void handleSave()}>{saving ? 'Salvando...' : 'Salvar alterações'}</button>
      </div>
    </div>
  );
}

function UploadForm({ initialFile, onCancel, onSave }: {
  initialFile?: File | null;
  onCancel: () => void;
  onSave: (data: { nome: string; file: File; observacao?: string }) => Promise<void>;
}) {
  const [nome, setNome] = useState(initialFile ? initialFile.name.replace(/\.[^.]+$/, '') : '');
  const [observacao, setObservacao] = useState('');
  const [file, setFile] = useState<File | null>(initialFile ?? null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (!initialFile) return;
    setFile(initialFile);
    setNome(initialFile.name.replace(/\.[^.]+$/, ''));
  }, [initialFile]);

  function acceptFile(nextFile: File) {
    if (nextFile.size > 25 * 1024 * 1024) return;
    setFile(nextFile);
    setNome(nextFile.name.replace(/\.[^.]+$/, ''));
  }

  return (
    <div className="modal-form">
      <label>Nome do documento<input value={nome} onChange={(event) => setNome(event.target.value)} placeholder="Ex.: Contrato Social" /></label>
      <div
        className={`doc-modal-drop ${dragging ? 'drag-active' : ''}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; }}
        onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }}
        onDrop={(event) => { event.preventDefault(); setDragging(false); const next = event.dataTransfer.files?.[0]; if (next) acceptFile(next); }}
      >
        <Upload size={20} />
        <strong>{dragging ? 'Solte o arquivo aqui' : file ? file.name : 'Arraste o arquivo para cá'}</strong>
        <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · pronto para envio` : 'ou clique no campo abaixo para selecionar'}</span>
        <input type="file" onChange={(event) => { const next = event.target.files?.[0]; if (next) acceptFile(next); }} />
      </div>
      <label>Observação<textarea value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
      <div className="modal-actions">
        <button className="button secondary" type="button" onClick={onCancel}>Cancelar</button>
        <button className="button primary" type="button" disabled={!nome.trim() || !file} onClick={() => { if (file) void onSave({ nome: nome.trim(), file, observacao: observacao.trim() || undefined }); }}>Enviar documento</button>
      </div>
    </div>
  );
}

function InlineVersionForm({ documentId, onDone }: { documentId: number; onDone: () => Promise<void> }) {
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
      <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      <button className="button primary" type="button" disabled={!file || sending} onClick={() => void handleUpload()}>{sending ? 'Enviando...' : 'Enviar nova versão'}</button>
    </div>
  );
}
