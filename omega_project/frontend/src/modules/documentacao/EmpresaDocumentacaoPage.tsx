import { Fragment, useEffect, useMemo, useState, type DragEvent, type ReactNode } from 'react';
import {
  ArrowLeft,
  Building2,
  ChevronDown,
  ChevronRight,
  Download,
  Eye,
  FileText,
  Folder,
  FolderPlus,
  History,
  Pencil,
  Plus,
  Trash2,
  Upload,
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
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [expandedCategoryIds, setExpandedCategoryIds] = useState<Set<number>>(new Set());
  const [categoryParentId, setCategoryParentId] = useState<number | null>(null);
  const [docs, setDocs] = useState<Documento[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [modal, setModal] = useState<'upload' | 'version' | 'category' | 'editCategory' | null>(null);
  const [docTarget, setDocTarget] = useState<Documento | null>(null);
  const [categoryTarget, setCategoryTarget] = useState<CategoriaDocumento | null>(null);
  const [versions, setVersions] = useState<Versao[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<{ kind: 'document' | 'category'; id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [dropFile, setDropFile] = useState<File | null>(null);

  const activeCategories = useMemo(
    () => cats.filter((c) => c.ativo).sort((a, b) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR')),
    [cats],
  );
  const folders = useMemo(
    () => activeCategories.filter((c) => c.categoria_pai_id === null),
    [activeCategories],
  );
  const childrenByParent = useMemo(() => {
    const map = new Map<number | null, CategoriaDocumento[]>();
    for (const category of activeCategories) {
      const key = category.categoria_pai_id ?? null;
      const current = map.get(key) ?? [];
      current.push(category);
      map.set(key, current);
    }
    return map;
  }, [activeCategories]);
  const selectedFolder = selectedCategoryId
    ? activeCategories.find((c) => c.id === selectedCategoryId) ?? null
    : null;

  const selectedPath = useMemo(() => {
    const path: CategoriaDocumento[] = [];
    let current = selectedFolder;
    const safety = new Set<number>();
    while (current && !safety.has(current.id)) {
      path.unshift(current);
      safety.add(current.id);
      current = current.categoria_pai_id ? activeCategories.find((c) => c.id === current?.categoria_pai_id) ?? null : null;
    }
    return path;
  }, [selectedFolder, activeCategories]);

  async function load(preferredCategoryId?: number) {
    setLoading(true);
    setError('');
    try {
      const [empresaData, categoriaData] = await Promise.all([
        apiFetch<any>(`/api/v1/empresas/${empresaId}`),
        listarCategorias(empresaId),
      ]);
      const nextCategories = categoriaData.categorias
        .filter((c: CategoriaDocumento) => c.ativo)
        .sort((a: CategoriaDocumento, b: CategoriaDocumento) => a.ordem - b.ordem || a.nome.localeCompare(b.nome, 'pt-BR'));
      const nextFolders = nextCategories.filter((c: CategoriaDocumento) => c.categoria_pai_id === null);

      setEmpresa(empresaData);
      setCats(categoriaData.categorias);
      setExpandedCategoryIds((previous) => {
        const next = new Set(previous);
        nextFolders.forEach((folder: CategoriaDocumento) => next.add(folder.id));
        if (preferredCategoryId) {
          let current = nextCategories.find((c: CategoriaDocumento) => c.id === preferredCategoryId);
          while (current?.categoria_pai_id) {
            next.add(current.categoria_pai_id);
            current = nextCategories.find((c: CategoriaDocumento) => c.id === current?.categoria_pai_id);
          }
        }
        return next;
      });

      const wantedId = preferredCategoryId
        ?? (selectedCategoryId && nextCategories.some((c: CategoriaDocumento) => c.id === selectedCategoryId)
          ? selectedCategoryId
          : nextFolders[0]?.id ?? null);

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

  function toggleCategory(categoryId: number) {
    setExpandedCategoryIds((previous) => {
      const next = new Set(previous);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
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
        <Link to="/documentacao"><ArrowLeft size={14} /> Voltar para documentação</Link>
      </div>

      <section className="doc-company-header panel">
        <div className="doc-company-title-block">
          <span className="doc-company-avatar"><Building2 size={20} /></span>
          <div>
            <span className="eyebrow">DOSSIÊ EMPRESARIAL</span>
            <h2>{empresa?.razao_social}</h2>
            <p>{empresa?.nome_fantasia || 'Sem nome fantasia'} · {empresa?.cnpj}</p>
          </div>
        </div>
        <div className="doc-company-header-meta">
          <span className={`status-pill ${empresa?.ativo ? 'ok' : 'off'}`}><i />{empresa?.ativo ? 'Ativa' : 'Inativa'}</span>
          <span className="regime">{empresa?.regime_tributario || 'Regime não informado'}</span>
        </div>
        <div className="doc-company-header-actions">
          <button className="button secondary small" type="button" onClick={() => { setCategoryParentId(null); setModal('category'); }}><Plus size={13} /> Nova pasta</button>
        </div>
      </section>

      {error && <div className="panel doc-inline-error"><strong>{error}</strong></div>}

      <section className="doc-explorer-shell panel">
        <aside className="doc-folder-sidebar">
          <div className="doc-folder-sidebar-head">
            <div>
              <span className="eyebrow">ESTRUTURA</span>
              <h3>Pastas</h3>
            </div>
            <button className="icon-button" type="button" title="Nova pasta" onClick={() => { setCategoryParentId(null); setModal('category'); }}><Plus size={14} /></button>
          </div>
          <div className="doc-folder-breadcrumb">
            <Folder size={13} />
            <span>Documentação</span>
            {selectedPath.map((item) => <Fragment key={item.id}><ChevronRight size={11} /><strong>{item.nome}</strong></Fragment>)}
          </div>
          <div className="doc-folder-tree doc-folder-tree-sidebar" role="tree" aria-label="Pastas da documentação">
            {folders.length ? folders.map((folder) => (
              <CategoryTreeNode
                key={folder.id}
                category={folder}
                depth={0}
                selectedCategoryId={selectedCategoryId}
                childrenByParent={childrenByParent}
                expandedCategoryIds={expandedCategoryIds}
                onToggle={toggleCategory}
                onSelect={(id) => void selectFolder(id)}
              />
            )) : <div className="doc-folder-empty-inline">Nenhuma pasta criada.</div>}
          </div>
          <div className="doc-folder-sidebar-actions">
            <button className="button secondary small" type="button" onClick={() => { setCategoryParentId(null); setModal('category'); }}><Plus size={12} /> Nova pasta</button>
            {selectedFolder && <button className="button primary small" type="button" onClick={() => { setCategoryParentId(selectedFolder.id); setExpandedCategoryIds((prev) => new Set(prev).add(selectedFolder.id)); setModal('category'); }}><FolderPlus size={12} /> Subpasta</button>}
          </div>
        </aside>

        <main className="doc-folder-workspace">
          {!selectedFolder ? (
            <div className="doc-selected-empty workspace-empty">
              <Folder size={38} />
              <strong>Selecione uma pasta</strong>
              <span>Escolha uma pasta na coluna ao lado para abrir o dossiê documental.</span>
            </div>
          ) : (
            <>
              <div className="doc-workspace-head">
                <div className="doc-workspace-title">
                  <span className="doc-selected-folder-icon"><Folder size={20} /></span>
                  <div>
                    <div className="doc-workspace-breadcrumb">{selectedPath.map((item, index) => <span key={item.id}>{index ? <ChevronRight size={10} /> : null}{item.nome}</span>)}</div>
                    <h3>{selectedFolder.nome}</h3>
                    <p>{selectedFolder.descricao || 'Pasta de documentação da empresa'} · {docs.length} documento(s) · {selectedFolder.subpastas_count ?? 0} subpasta(s)</p>
                  </div>
                </div>
                <div className="doc-workspace-actions">
                  <button className="button secondary small" type="button" onClick={() => { setCategoryParentId(selectedFolder.id); setExpandedCategoryIds((prev) => new Set(prev).add(selectedFolder.id)); setModal('category'); }}><FolderPlus size={12} /> Nova subpasta</button>
                  <button className="button secondary small" type="button" onClick={openEditCategory}><Pencil size={12} /> Editar</button>
                  <button className="button primary small" type="button" onClick={() => setModal('upload')}><Upload size={12} /> Adicionar documento</button>
                  <button className="icon-button danger-icon" type="button" title="Arquivar pasta" onClick={openDeleteCategory}><Trash2 size={14} /></button>
                </div>
              </div>

              {loadingDocs ? <div className="doc-accordion-empty"><Loading text="Carregando documentos..." /></div> : (
                <>
                  <div
                    className={`doc-drop-zone doc-drop-zone-workspace ${dragActive ? 'drag-active' : ''}`}
                    onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
                    onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; }}
                    onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragActive(false); }}
                    onDrop={handleDrop}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setModal('upload'); }}
                    onClick={() => setModal('upload')}
                    aria-label={`Arraste um documento para a pasta ${selectedFolder.nome}`}
                  >
                    <span className="doc-drop-icon"><Upload size={22} /></span>
                    <div><strong>{dragActive ? 'Solte o documento aqui' : 'Arraste e solte documentos nesta pasta'}</strong><span>{dragActive ? `O arquivo será salvo em ${selectedFolder.nome}.` : 'ou clique para selecionar um arquivo do computador'}</span></div>
                    <small>Upload direto para a pasta atual · até 25 MB</small>
                  </div>

                  {docs.length === 0 ? (
                    <div className="doc-selected-empty compact">
                      <FileText size={28} />
                      <strong>Nenhum documento nesta pasta</strong>
                      <span>Use o drop acima para adicionar o primeiro arquivo.</span>
                    </div>
                  ) : (
                    <div className="doc-table doc-table-workspace">
                      <div className="doc-table-head"><span>Documento</span><span>Arquivo</span><span>Versões</span><span>Atualizado</span><span>Ações</span></div>
                      {docs.map((doc) => (
                        <div className="doc-table-row" key={doc.id}>
                          <div className="doc-table-name"><span className="doc-file-icon"><FileText size={16} /></span><div><strong>{doc.nome}</strong><small>{doc.criado_em}</small></div></div>
                          <span className="doc-file-name">{doc.nome_arquivo || '—'}</span>
                          <span className="doc-version-count">{doc.versoes_count}</span>
                          <span>{doc.atualizado_em}</span>
                          <div className="doc-table-actions">
                            <button className="icon-button" type="button" title="Histórico" onClick={() => void openVersions(doc)}><History size={14} /></button>
                            {doc.ultima_versao_id && <>
                              <button className="icon-button" type="button" title="Visualizar" onClick={() => void visualizarVersao(doc.ultima_versao_id as number)}><Eye size={14} /></button>
                              <button className="icon-button" type="button" title="Baixar" onClick={() => void baixarVersao(doc.ultima_versao_id as number, doc.nome_arquivo || doc.nome)}><Download size={14} /></button>
                            </>}
                            <button className="icon-button danger-icon" type="button" title="Arquivar documento" onClick={() => setDeleteTarget({ kind: 'document', id: doc.id, name: doc.nome })}><Trash2 size={14} /></button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </main>
      </section>

      <div className="doc-explorer-note panel"><History size={15} /><div><strong>Histórico preservado</strong><span>Pastas, documentos e versões são arquivados logicamente; o histórico permanece disponível para auditoria.</span></div></div>

      {modal === 'category' && (
        <Modal title="Criar nova pasta" onClose={() => setModal(null)}>
          <CategoryForm parent={categoryParentId ? activeCategories.find((c) => c.id === categoryParentId) ?? null : null} existingNames={(childrenByParent.get(categoryParentId) ?? []).map((folder) => folder.nome)} onCancel={() => setModal(null)} onSave={async (data) => { const created = await criarCategoria(empresaId, data); if (created.categoria_pai_id) setExpandedCategoryIds((prev) => new Set(prev).add(created.categoria_pai_id as number)); setModal(null); await load(created.id); }} />
        </Modal>
      )}
      {modal === 'editCategory' && categoryTarget && (
        <Modal title={`Editar pasta · ${categoryTarget.nome}`} onClose={() => setModal(null)}>
          <CategoryEditForm category={categoryTarget} existingNames={(childrenByParent.get(categoryTarget.categoria_pai_id ?? null) ?? []).filter((folder) => folder.id !== categoryTarget.id).map((folder) => folder.nome)} onCancel={() => setModal(null)} onSave={async (data) => { await atualizarCategoria(categoryTarget.id, data); setModal(null); await load(categoryTarget.id); }} />
        </Modal>
      )}
      {modal === 'upload' && selectedFolder && (
        <Modal title={`Adicionar documento · ${selectedFolder.nome}`} onClose={() => { setDropFile(null); setModal(null); }}>
          <UploadForm initialFile={dropFile} onCancel={() => { setDropFile(null); setModal(null); }} onSave={async (data) => { await uploadDocumento(empresaId, selectedFolder.id, data.nome, data.file, data.observacao); setDropFile(null); setModal(null); await refreshSelectedFolder(); }} />
        </Modal>
      )}
      {modal === 'version' && docTarget && (
        <Modal title={`Histórico · ${docTarget.nome}`} onClose={() => setModal(null)}>
          <div className="version-list">{versions.length === 0 ? <span>Nenhuma versão registrada.</span> : versions.map((version) => <div className="version-row" key={version.id}><div><strong>Versão {version.versao}</strong><small>{version.nome_arquivo || 'Arquivo'} · {version.usuario_nome || 'Usuário'} · {version.criado_em}</small></div><div className="download-actions"><button className="icon-button" type="button" onClick={() => void visualizarVersao(version.id)} title="Visualizar"><Eye size={14} /></button><button className="icon-button" type="button" onClick={() => void baixarVersao(version.id, version.nome_arquivo || `documento_v${version.versao}`)} title="Baixar"><Download size={14} /></button></div></div>)}</div>
          <div className="modal-actions"><button className="button secondary" type="button" onClick={() => setModal(null)}>Fechar</button></div>
          <InlineVersionForm documentId={docTarget.id} onDone={async () => { const versionResult = await listarVersoes(docTarget.id); setVersions(versionResult.versoes); await refreshSelectedFolder(); }} />
        </Modal>
      )}
      {deleteTarget && (
        <Modal title={deleteTarget.kind === 'document' ? 'Arquivar documento' : 'Arquivar pasta'} onClose={() => { if (!deleting) setDeleteTarget(null); }}>
          <div className="delete-confirm"><div className="delete-confirm-icon"><Trash2 size={22} /></div><h4>Confirmar arquivamento</h4><p>Você está prestes a arquivar <strong>“{deleteTarget.name}”</strong>. O item sairá da visão atual, mas seu histórico continuará preservado.</p>{deleteTarget.kind === 'category' && <p className="delete-warning">As subpastas e documentos vinculados também serão arquivados.</p>}<div className="modal-actions"><button className="button secondary" type="button" disabled={deleting} onClick={() => setDeleteTarget(null)}>Cancelar</button><button className="button danger" type="button" disabled={deleting} onClick={() => void confirmDelete()}><Trash2 size={13} /> {deleting ? 'Arquivando...' : 'Arquivar'}</button></div></div>
        </Modal>
      )}
    </div>
  );
}

function CategoryTreeNode({
  category,
  depth,
  selectedCategoryId,
  childrenByParent,
  expandedCategoryIds,
  onToggle,
  onSelect,
}: {
  category: CategoriaDocumento;
  depth: number;
  selectedCategoryId: number | null;
  childrenByParent: Map<number | null, CategoriaDocumento[]>;
  expandedCategoryIds: Set<number>;
  onToggle: (categoryId: number) => void;
  onSelect: (categoryId: number) => void;
}) {
  const children = childrenByParent.get(category.id) ?? [];
  const expanded = expandedCategoryIds.has(category.id);
  const selected = selectedCategoryId === category.id;

  return (
    <div className="doc-tree-node" role="treeitem" aria-expanded={children.length ? expanded : undefined} aria-selected={selected}>
      <div className={`doc-tree-row ${selected ? 'selected' : ''}`} style={{ paddingLeft: 8 + depth * 21 }}>
        <button
          className={`doc-tree-toggle ${children.length ? '' : 'empty'}`}
          type="button"
          aria-label={children.length ? (expanded ? 'Recolher subpastas' : 'Expandir subpastas') : 'Sem subpastas'}
          disabled={!children.length}
          onClick={(event) => { event.stopPropagation(); if (children.length) onToggle(category.id); }}
        >
          {children.length ? (expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span />}
        </button>
        <button className="doc-tree-select" type="button" onClick={() => onSelect(category.id)}>
          <Folder size={16} />
          <span className="doc-tree-name">{category.nome}</span>
          <span className="doc-tree-meta">{category.documentos_count ?? 0} docs</span>
          {children.length > 0 && <span className="doc-tree-meta">{children.length} sub</span>}
        </button>
      </div>
      {expanded && children.map((child) => (
        <CategoryTreeNode
          key={child.id}
          category={child}
          depth={depth + 1}
          selectedCategoryId={selectedCategoryId}
          childrenByParent={childrenByParent}
          expandedCategoryIds={expandedCategoryIds}
          onToggle={onToggle}
          onSelect={onSelect}
        />
      ))}
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

function CategoryForm({ parent, onCancel, onSave, existingNames }: {
  parent: CategoriaDocumento | null;
  onCancel: () => void;
  onSave: (data: { nome: string; descricao?: string; categoria_pai_id?: number | null }) => Promise<void>;
  existingNames: string[];
}) {
  const [nome, setNome] = useState('');
  const [descricao, setDescricao] = useState('');
  const [saving, setSaving] = useState(false);
  const duplicated = existingNames.some((value) => value.trim().toLocaleLowerCase() === nome.trim().toLocaleLowerCase());

  async function handleSave() {
    if (!nome.trim() || duplicated || saving) return;
    setSaving(true);
    try {
      await onSave({ nome: nome.trim(), descricao: descricao.trim() || undefined, categoria_pai_id: parent?.id ?? null });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-form">
      {parent && <div className="doc-parent-folder-preview"><Folder size={17} /><div><span>Subpasta de</span><strong>{parent.nome}</strong></div></div>}
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
