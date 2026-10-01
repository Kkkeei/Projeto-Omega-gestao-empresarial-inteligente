import { useEffect, useMemo, useState, type DragEvent, type ReactNode, type Dispatch, type SetStateAction } from 'react';
import {
  ArrowLeft,
  ArrowLeft as ChevronBack,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Download,
  Eye,
  File,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  History,
  Home,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  ArrowUp,
  X,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import {
  arquivarCategoria,
  arquivarDocumento,
  atualizarCategoria,
  baixarVersao,
  criarCategoria,
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
  const [currentFolderId, setCurrentFolderId] = useState<number | null>(null);
  const [navigationHistory, setNavigationHistory] = useState<(number | null)[]>([]);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [docs, setDocs] = useState<Documento[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<'upload' | 'version' | 'category' | 'editCategory' | null>(null);
  const [categoryMode, setCategoryMode] = useState<'root' | 'subfolder'>('root');
  const [docTarget, setDocTarget] = useState<Documento | null>(null);
  const [categoryTarget, setCategoryTarget] = useState<CategoriaDocumento | null>(null);
  const [versions, setVersions] = useState<Versao[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<{ kind: 'document' | 'category'; id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [dropFile, setDropFile] = useState<File | null>(null);

  const foldersByParent = useMemo(() => {
    const map = new Map<number | null, CategoriaDocumento[]>();
    for (const category of cats.filter((item) => item.ativo)) {
      const key = category.categoria_pai_id ?? null;
      const list = map.get(key) ?? [];
      list.push(category);
      map.set(key, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR'));
    }
    return map;
  }, [cats]);

  const currentFolder = currentFolderId ? cats.find((folder) => folder.id === currentFolderId) ?? null : null;
  const currentChildren = foldersByParent.get(currentFolderId) ?? [];
  const rootFolders = foldersByParent.get(null) ?? [];

  const breadcrumb = useMemo(() => {
    const result: CategoriaDocumento[] = [];
    let cursor = currentFolder;
    while (cursor) {
      result.unshift(cursor);
      cursor = cursor.categoria_pai_id ? cats.find((item) => item.id === cursor?.categoria_pai_id) ?? null : null;
    }
    return result;
  }, [currentFolder, cats]);

  const visibleFolders = currentChildren.filter((folder) => folder.nome.toLocaleLowerCase().includes(search.toLocaleLowerCase().trim()));
  const visibleDocuments = docs.filter((doc) => `${doc.nome} ${doc.nome_arquivo ?? ''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase().trim()));

  async function loadAll(preferredFolderId?: number | null, options?: { keepHistory?: boolean }) {
    setLoading(true);
    setError('');
    try {
      const [empresaData, categoriaData] = await Promise.all([
        apiFetch<any>(`/api/v1/empresas/${empresaId}`),
        listarCategorias(empresaId),
      ]);
      setEmpresa(empresaData);
      setCats(categoriaData.categorias);

      const requested = preferredFolderId !== undefined ? preferredFolderId : currentFolderId;
      const nextCurrent = requested && categoriaData.categorias.some((folder: CategoriaDocumento) => folder.id === requested && folder.ativo)
        ? requested
        : null;
      setCurrentFolderId(nextCurrent);
      if (!options?.keepHistory) setNavigationHistory([]);

      if (nextCurrent) {
        await loadDocuments(nextCurrent);
      } else {
        setDocs([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar documentação.');
    } finally {
      setLoading(false);
    }
  }

  async function loadDocuments(categoryId: number | null) {
    if (!categoryId) {
      setDocs([]);
      return;
    }
    setLoadingDocs(true);
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

  useEffect(() => {
    void loadAll(null);
  }, [empresaId]);

  async function navigateToFolder(folderId: number | null, addToHistory = true) {
    if (folderId === currentFolderId) return;
    if (addToHistory) setNavigationHistory((history) => [...history, currentFolderId]);
    setCurrentFolderId(folderId);
    setSearch('');
    setError('');
    await loadDocuments(folderId);
  }

  async function goBack() {
    const next = navigationHistory.length ? navigationHistory[navigationHistory.length - 1] : null;
    setNavigationHistory((history) => history.slice(0, -1));
    setCurrentFolderId(next ?? null);
    setSearch('');
    await loadDocuments(next ?? null);
  }

  async function goUp() {
    if (!currentFolder) return;
    await navigateToFolder(currentFolder.categoria_pai_id ?? null, true);
  }

  async function refresh() {
    setRefreshing(true);
    try {
      await loadAll(currentFolderId, { keepHistory: true });
    } finally {
      setRefreshing(false);
    }
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
    if (!currentFolder) return;
    setCategoryTarget(currentFolder);
    setModal('editCategory');
  }

  function openDeleteCategory() {
    if (!currentFolder) return;
    setDeleteTarget({ kind: 'category', id: currentFolder.id, name: currentFolder.nome });
  }

  async function confirmDelete() {
    if (!deleteTarget || deleting) return;
    setDeleting(true);
    setError('');
    try {
      if (deleteTarget.kind === 'document') {
        await arquivarDocumento(deleteTarget.id);
        setDeleteTarget(null);
        await loadDocuments(currentFolderId);
        await loadAll(currentFolderId, { keepHistory: true });
      } else {
        const parentId = cats.find((folder) => folder.id === deleteTarget.id)?.categoria_pai_id ?? null;
        await arquivarCategoria(deleteTarget.id);
        setDeleteTarget(null);
        setCurrentFolderId(parentId);
        setNavigationHistory([]);
        await loadAll(parentId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível arquivar o item.');
    } finally {
      setDeleting(false);
    }
  }

  function prepareDroppedFile(file: File) {
    const maxSize = 25 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('O arquivo excede o limite de 25 MB.');
      return;
    }
    if (!currentFolderId) {
      setError('Entre em uma pasta antes de enviar um documento.');
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
    return <div className="page"><Loading text="Carregando documentação..." /></div>;
  }

  if (error && !empresa) {
    return <div className="page"><div className="panel empty"><strong>{error}</strong></div></div>;
  }

  return (
    <div className="page documentacao-detail-page">
      <div className="doc-detail-back">
        <Link to="/documentacao"><ArrowLeft size={15} /> Voltar para empresas</Link>
      </div>

      <div className="page-heading doc-company-heading">
        <div>
          <span className="eyebrow">DOSSIÊ EMPRESARIAL</span>
          <h2><Folder size={24} /> Documentação</h2>
          <p>{empresa?.razao_social} · {empresa?.cnpj}</p>
        </div>
        <div className="doc-company-status">
          <span className={`status-pill ${empresa?.ativo ? 'ok' : 'off'}`}><i />{empresa?.ativo ? 'Ativa' : 'Inativa'}</span>
          <span className="regime">{empresa?.regime_tributario || 'Regime não informado'}</span>
        </div>
      </div>

      {error && <div className="panel doc-inline-error"><strong>{error}</strong><button className="icon-button" type="button" title="Fechar aviso" onClick={() => setError('')}><X size={14} /></button></div>}

      <section className="doc-explorer panel">
        <aside className="doc-explorer-sidebar" aria-label="Árvore de pastas">
          <div className="doc-side-title">
            <div><span className="eyebrow">PASTAS</span><strong>Estrutura</strong></div>
            <button className="icon-button" type="button" title="Atualizar pastas" onClick={() => void refresh()} disabled={refreshing}><RefreshCw size={14} className={refreshing ? 'spin' : ''} /></button>
          </div>
          <button className={`doc-tree-home ${currentFolderId === null ? 'active' : ''}`} type="button" onClick={() => void navigateToFolder(null, true)}>
            <Home size={15} /><span>Raiz da documentação</span>
          </button>
          <div className="doc-tree">
            {rootFolders.map((folder) => (
              <TreeNode key={folder.id} folder={folder} all={cats} expanded={expanded} setExpanded={setExpanded} activeId={currentFolderId} onOpen={(folderId) => void navigateToFolder(folderId, true)} />
            ))}
            {rootFolders.length === 0 && <div className="doc-tree-empty">Nenhuma pasta criada.</div>}
          </div>
        </aside>

        <main className="doc-explorer-main">
          <div className="doc-explorer-toolbar">
            <div className="doc-nav-actions">
              <button className="icon-button" type="button" title="Voltar" onClick={() => void goBack()} disabled={!navigationHistory.length}><ChevronBack size={15} /></button>
              <button className="icon-button" type="button" title="Subir uma pasta" onClick={() => void goUp()} disabled={!currentFolder}><ArrowUp size={15} /></button>
              <button className="icon-button" type="button" title="Ir para a raiz" onClick={() => void navigateToFolder(null, true)} disabled={currentFolderId === null}><Home size={15} /></button>
              <button className="icon-button" type="button" title="Atualizar" onClick={() => void refresh()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? 'spin' : ''} /></button>
            </div>
            <div className="doc-breadcrumb" aria-label="Localização atual">
              <button type="button" onClick={() => void navigateToFolder(null, true)}>Documentação</button>
              {breadcrumb.map((item) => <span key={item.id}><ChevronRight size={13} /><button type="button" onClick={() => void navigateToFolder(item.id, true)}>{item.nome}</button></span>)}
            </div>
            <div className="doc-explorer-actions">
              <button className="button secondary small" type="button" onClick={() => { setCategoryMode('root'); setModal('category'); }}><Plus size={13} /> Nova pasta</button>
              <button
                className="button secondary small"
                type="button"
                title={currentFolder ? `Criar subpasta em ${currentFolder.nome}` : 'No diretório principal, cria uma pasta na raiz'}
                onClick={() => { setCategoryMode('subfolder'); setModal('category'); }}
              >
                <FolderPlus size={13} /> Subpasta
              </button>
              <button className="button primary small" type="button" disabled={!currentFolderId} onClick={() => setModal('upload')}><Upload size={13} /> Upload</button>
            </div>
          </div>

          <div className="doc-explorer-subtoolbar">
            <div className="doc-current-location">
              <span className="doc-location-icon">{currentFolder ? <FolderOpen size={19} /> : <Home size={19} />}</span>
              <div><strong>{currentFolder?.nome ?? 'Raiz da documentação'}</strong><span>{currentFolder?.descricao || 'Pastas e documentos desta empresa'}</span></div>
            </div>
            <label className="doc-local-search"><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Pesquisar nesta pasta..." /></label>
          </div>

          {currentFolder && (
            <div className="doc-folder-context">
              <div><span>{currentFolder.documentos_count} documento(s)</span><span>{currentFolder.subpastas_count} subpasta(s)</span></div>
              <div className="doc-folder-context-actions">
                <button className="icon-button" type="button" title="Editar pasta" onClick={openEditCategory}><Pencil size={14} /></button>
                <button className="icon-button danger-icon" type="button" title="Arquivar pasta" onClick={openDeleteCategory}><Trash2 size={14} /></button>
              </div>
            </div>
          )}

          {!currentFolderId && rootFolders.length === 0 && !search.trim() ? (
            <EmptyState title="A documentação está vazia" text="Crie sua primeira pasta para começar a organizar os documentos da empresa." button="Nova pasta" onClick={() => { setCategoryMode('root'); setModal('category'); }} />
          ) : (
            <>
              <div className="doc-content-summary"><strong>{visibleFolders.length + visibleDocuments.length} item(ns)</strong><span>{visibleFolders.length} pasta(s) · {visibleDocuments.length} documento(s)</span></div>

              <div className="doc-explorer-list" onDragEnter={(event) => { event.preventDefault(); if (currentFolderId) setDragActive(true); }} onDragOver={(event) => { event.preventDefault(); if (currentFolderId) event.dataTransfer.dropEffect = 'copy'; }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragActive(false); }} onDrop={handleDrop}>
                <div className="doc-list-header"><span>Nome</span><span>Tipo</span><span>Itens / versões</span><span>Atualizado</span><span></span></div>
                {visibleFolders.map((folder) => (
                  <button className="doc-list-row doc-list-folder" key={`folder-${folder.id}`} type="button" onDoubleClick={() => void navigateToFolder(folder.id, true)} onClick={() => void navigateToFolder(folder.id, true)}>
                    <span className="doc-name-cell"><span className="doc-row-icon folder"><Folder size={17} /></span><span><strong>{folder.nome}</strong><small>{folder.descricao || 'Pasta de documentos'}</small></span></span>
                    <span>Pasta</span>
                    <span>{folder.subpastas_count} subpasta(s) · {folder.documentos_count} doc(s)</span>
                    <span>—</span>
                    <ArrowRight size={15} />
                  </button>
                ))}

                {visibleDocuments.map((doc) => (
                  <div className="doc-list-row" key={`document-${doc.id}`}>
                    <span className="doc-name-cell"><span className="doc-row-icon file"><FileText size={17} /></span><span><strong>{doc.nome}</strong><small>{doc.nome_arquivo || 'Arquivo sem nome'}</small></span></span>
                    <span>{documentType(doc.nome_arquivo)}</span>
                    <span>{doc.versoes_count} versão(ões)</span>
                    <span>{doc.atualizado_em || doc.criado_em}</span>
                    <span className="doc-row-actions">
                      <button className="icon-button" type="button" title="Histórico de versões" onClick={() => void openVersions(doc)}><History size={14} /></button>
                      {doc.ultima_versao_id && <>
                        <button className="icon-button" type="button" title="Visualizar" onClick={() => void visualizarVersao(doc.ultima_versao_id as number)}><Eye size={14} /></button>
                        <button className="icon-button" type="button" title="Baixar" onClick={() => void baixarVersao(doc.ultima_versao_id as number, doc.nome_arquivo || doc.nome)}><Download size={14} /></button>
                      </>}
                      <button className="icon-button danger-icon" type="button" title="Arquivar documento" onClick={() => setDeleteTarget({ kind: 'document', id: doc.id, name: doc.nome })}><Trash2 size={14} /></button>
                    </span>
                  </div>
                ))}

                {!loadingDocs && visibleFolders.length === 0 && visibleDocuments.length === 0 && <div className="doc-list-empty"><File size={25} /><strong>Nenhum item encontrado</strong><span>Limpe a pesquisa ou envie um novo documento.</span></div>}
              </div>

              {currentFolderId && <div className={`doc-drop-hint ${dragActive ? 'active' : ''}`} role="button" tabIndex={0} onClick={() => setModal('upload')} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setModal('upload'); }}>
                <Upload size={17} /><span><strong>Arraste arquivos para esta pasta</strong> ou clique para selecionar</span><small>Máximo de {25} MB por arquivo</small>
              </div>}
            </>
          )}
        </main>
      </section>

      {modal === 'category' && (
        <Modal
          title={categoryMode === 'subfolder' && currentFolder ? `Nova subpasta em ${currentFolder.nome}` : 'Nova pasta'}
          onClose={() => setModal(null)}
        >
          <CategoryForm
            mode={categoryMode}
            parent={categoryMode === 'subfolder' ? currentFolder : null}
            existingNames={(foldersByParent.get(categoryMode === 'subfolder' ? currentFolderId : null) ?? []).map((folder) => folder.nome)}
            onCancel={() => setModal(null)}
            onSave={async (data) => {
              const created = await criarCategoria(empresaId, data);
              const createdParentId = data.categoria_pai_id ?? null;
              setModal(null);
              await loadAll(created.id);
              setExpanded((state) => ({
                ...state,
                ...(createdParentId ? { [createdParentId]: true } : {}),
              }));
            }}
          />
        </Modal>
      )}

      {modal === 'editCategory' && categoryTarget && (
        <Modal title={`Editar pasta · ${categoryTarget.nome}`} onClose={() => setModal(null)}>
          <CategoryEditForm
            category={categoryTarget}
            existingNames={(foldersByParent.get(categoryTarget.categoria_pai_id ?? null) ?? []).filter((folder) => folder.id !== categoryTarget.id).map((folder) => folder.nome)}
            onCancel={() => setModal(null)}
            onSave={async (data) => { await atualizarCategoria(categoryTarget.id, data); setModal(null); await loadAll(categoryTarget.id, { keepHistory: true }); }}
          />
        </Modal>
      )}

      {modal === 'upload' && currentFolder && (
        <Modal title={`Adicionar documento · ${currentFolder.nome}`} onClose={() => { setDropFile(null); setModal(null); }}>
          <UploadForm
            initialFile={dropFile}
            onCancel={() => { setDropFile(null); setModal(null); }}
            onSave={async (data) => { await uploadDocumento(empresaId, currentFolder.id, data.nome, data.file, data.observacao); setDropFile(null); setModal(null); await loadDocuments(currentFolder.id); await loadAll(currentFolder.id, { keepHistory: true }); }}
          />
        </Modal>
      )}

      {modal === 'version' && docTarget && (
        <Modal title={`Histórico · ${docTarget.nome}`} onClose={() => setModal(null)}>
          <div className="version-list">
            {versions.length === 0 ? <span>Nenhuma versão registrada.</span> : versions.map((version) => (
              <div className="version-row" key={version.id}>
                <div><strong>Versão {version.versao}</strong><small>{version.nome_arquivo || 'Arquivo'} · {version.usuario_nome || 'Usuário'} · {version.criado_em}</small></div>
                <div className="download-actions"><button className="icon-button" type="button" onClick={() => void visualizarVersao(version.id)} title="Visualizar"><Eye size={14} /></button><button className="icon-button" type="button" onClick={() => void baixarVersao(version.id, version.nome_arquivo || `documento_v${version.versao}`)} title="Baixar"><Download size={14} /></button></div>
              </div>
            ))}
          </div>
          <div className="modal-actions"><button className="button secondary" type="button" onClick={() => setModal(null)}>Fechar</button></div>
          <InlineVersionForm documentId={docTarget.id} onDone={async () => { const result = await listarVersoes(docTarget.id); setVersions(result.versoes); await loadDocuments(currentFolderId); }} />
        </Modal>
      )}

      {deleteTarget && (
        <Modal title={deleteTarget.kind === 'document' ? 'Arquivar documento' : 'Arquivar pasta'} onClose={() => { if (!deleting) setDeleteTarget(null); }}>
          <div className="delete-confirm">
            <div className="delete-confirm-icon"><Trash2 size={22} /></div>
            <h4>Confirmar arquivamento</h4>
            <p>“{deleteTarget.name}” deixará de aparecer na navegação ativa. O histórico permanece preservado.</p>
            {deleteTarget.kind === 'category' && <p className="delete-warning">Subpastas e documentos ativos desta pasta também serão arquivados.</p>}
            <div className="modal-actions"><button className="button secondary" type="button" disabled={deleting} onClick={() => setDeleteTarget(null)}>Cancelar</button><button className="button danger" type="button" disabled={deleting} onClick={() => void confirmDelete()}><Trash2 size={13} /> {deleting ? 'Arquivando...' : 'Arquivar'}</button></div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function TreeNode({ folder, all, expanded, setExpanded, activeId, onOpen }: { folder: CategoriaDocumento; all: CategoriaDocumento[]; expanded: Record<number, boolean>; setExpanded: Dispatch<SetStateAction<Record<number, boolean>>>; activeId: number | null; onOpen: (id: number) => void }) {
  const children = all.filter((item) => item.ativo && item.categoria_pai_id === folder.id).sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR'));
  const isExpanded = expanded[folder.id] ?? false;
  return (
    <div className="doc-tree-node">
      <div className={`doc-tree-row ${activeId === folder.id ? 'active' : ''}`}>
        {children.length > 0 ? <button className="doc-tree-toggle" type="button" title={isExpanded ? 'Recolher' : 'Expandir'} onClick={() => setExpanded((state) => ({ ...state, [folder.id]: !isExpanded }))}>{isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}</button> : <span className="doc-tree-spacer" />}
        <button className="doc-tree-item" type="button" onClick={() => onOpen(folder.id)}><Folder size={14} /><span>{folder.nome}</span><small>{folder.documentos_count}</small></button>
      </div>
      {isExpanded && children.length > 0 && <div className="doc-tree-children">{children.map((child) => <TreeNode key={child.id} folder={child} all={all} expanded={expanded} setExpanded={setExpanded} activeId={activeId} onOpen={onOpen} />)}</div>}
    </div>
  );
}

function EmptyState({ title, text, button, onClick }: { title: string; text: string; button: string; onClick: () => void }) {
  return <div className="doc-list-empty prominent"><Folder size={30} /><strong>{title}</strong><span>{text}</span><button className="button primary small" type="button" onClick={onClick}><Plus size={13} /> {button}</button></div>;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return <div className="modal-backdrop"><div className="modal-card doc-modal-card"><div className="modal-head"><h3>{title}</h3><button className="icon-button" type="button" onClick={onClose} title="Fechar"><X size={15} /></button></div>{children}</div></div>;
}

function CategoryForm({ onCancel, onSave, existingNames, parent, mode }: {
  onCancel: () => void;
  onSave: (data: { nome: string; descricao?: string; categoria_pai_id?: number | null }) => Promise<void>;
  existingNames: string[];
  parent: CategoriaDocumento | null;
  mode: 'root' | 'subfolder';
}) {
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [saving, setSaving] = useState(false);
  const duplicated = existingNames.some((value) => value.trim().toLocaleLowerCase() === nome.trim().toLocaleLowerCase());
  const targetParent = mode === 'subfolder' ? parent : null;
  const locationLabel = targetParent?.nome ?? 'Raiz da documentação';
  const actionLabel = saving ? 'Criando...' : targetParent ? 'Criar subpasta' : 'Criar pasta';

  async function handleSave() {
    if (!nome.trim() || duplicated || saving) return;
    setSaving(true);
    try {
      await onSave({
        nome: nome.trim(),
        descricao: descricao.trim() || undefined,
        categoria_pai_id: targetParent?.id ?? null,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-form">
      <div className="doc-modal-context">
        <Folder size={17} />
        <div><span>Local</span><strong>{locationLabel}</strong></div>
      </div>
      <label>Nome da pasta
        <input value={nome} onChange={(event) => setNome(event.target.value)} placeholder="Ex.: Contratos" autoFocus />
        {duplicated && <small className="form-error">Já existe uma pasta com esse nome neste local.</small>}
      </label>
      <label>Descrição (opcional)
        <textarea value={descricao} onChange={(event) => setDescricao(event.target.value)} placeholder="Descreva o conteúdo desta pasta" />
      </label>
      <div className="modal-actions">
        <button className="button secondary" type="button" onClick={onCancel}>Cancelar</button>
        <button className="button primary" type="button" disabled={!nome.trim() || duplicated || saving} onClick={() => void handleSave()}>
          {actionLabel}
        </button>
      </div>
    </div>
  );
}

function CategoryEditForm({ category, onCancel, onSave, existingNames }: { category: CategoriaDocumento; onCancel: () => void; onSave: (data: { nome: string; descricao?: string }) => Promise<void>; existingNames: string[] }) {
  const [nome, setNome] = useState(category.nome);
  const [descricao, setDescricao] = useState(category.descricao || '');
  const [saving, setSaving] = useState(false);
  const duplicated = existingNames.some((value) => value.trim().toLocaleLowerCase() === nome.trim().toLocaleLowerCase());
  async function handleSave() { if (!nome.trim() || duplicated || saving) return; setSaving(true); try { await onSave({ nome: nome.trim(), descricao: descricao.trim() || undefined }); } finally { setSaving(false); } }
  return <div className="modal-form"><div className="doc-modal-context"><Pencil size={17} /><div><span>Editando</span><strong>{category.nome}</strong></div></div><label>Nome da pasta<input value={nome} onChange={(event) => setNome(event.target.value)} autoFocus />{duplicated && <small className="form-error">Já existe outra pasta com esse nome neste local.</small>}</label><label>Descrição (opcional)<textarea value={descricao} onChange={(event) => setDescricao(event.target.value)} /></label><div className="modal-actions"><button className="button secondary" type="button" onClick={onCancel}>Cancelar</button><button className="button primary" type="button" disabled={!nome.trim() || duplicated || saving} onClick={() => void handleSave()}>{saving ? 'Salvando...' : 'Salvar alterações'}</button></div></div>;
}

function UploadForm({ initialFile, onCancel, onSave }: { initialFile?: File | null; onCancel: () => void; onSave: (data: { nome: string; file: File; observacao?: string }) => Promise<void> }) {
  const [nome, setNome] = useState(initialFile ? initialFile.name.replace(/\.[^.]+$/, '') : '');
  const [observacao, setObservacao] = useState('');
  const [file, setFile] = useState<File | null>(initialFile ?? null);
  const [dragging, setDragging] = useState(false);
  const [sending, setSending] = useState(false);
  useEffect(() => { if (!initialFile) return; setFile(initialFile); setNome(initialFile.name.replace(/\.[^.]+$/, '')); }, [initialFile]);
  function acceptFile(nextFile: File) { if (nextFile.size > 25 * 1024 * 1024) return; setFile(nextFile); setNome(nextFile.name.replace(/\.[^.]+$/, '')); }
  async function submit() { if (!file || !nome.trim() || sending) return; setSending(true); try { await onSave({ nome: nome.trim(), file, observacao: observacao.trim() || undefined }); } finally { setSending(false); } }
  return <div className="modal-form"><label>Nome do documento<input value={nome} onChange={(event) => setNome(event.target.value)} placeholder="Ex.: Contrato Social 2026" autoFocus /></label><div className={`doc-modal-drop ${dragging ? 'drag-active' : ''}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); const next = event.dataTransfer.files?.[0]; if (next) acceptFile(next); }}><Upload size={20} /><strong>{dragging ? 'Solte o arquivo aqui' : file ? file.name : 'Arraste o arquivo para cá'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · pronto para envio` : 'ou clique para selecionar'}</span><input type="file" onChange={(event) => { const next = event.target.files?.[0]; if (next) acceptFile(next); }} /></div><label>Observação (opcional)<textarea value={observacao} onChange={(event) => setObservacao(event.target.value)} placeholder="Observação interna sobre este arquivo" /></label><div className="modal-actions"><button className="button secondary" type="button" disabled={sending} onClick={onCancel}>Cancelar</button><button className="button primary" type="button" disabled={!nome.trim() || !file || sending} onClick={() => void submit()}>{sending ? 'Enviando...' : 'Enviar documento'}</button></div></div>;
}

function InlineVersionForm({ documentId, onDone }: { documentId: number; onDone: () => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  async function handleUpload() { if (!file || sending) return; setSending(true); try { await uploadNovaVersao(documentId, file); setFile(null); await onDone(); } finally { setSending(false); } }
  return <div className="version-upload"><h4>Adicionar nova versão</h4><input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><button className="button primary" type="button" disabled={!file || sending} onClick={() => void handleUpload()}>{sending ? 'Enviando...' : 'Enviar nova versão'}</button></div>;
}

function documentType(name?: string | null) { const ext = name?.split('.').pop()?.toUpperCase(); return ext ? ext : 'Arquivo'; }
