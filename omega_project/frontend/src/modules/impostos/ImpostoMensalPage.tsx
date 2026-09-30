import {useEffect, useRef, useState} from 'react';
import {ArrowLeft, CalendarDays, CheckCircle2, Download, Edit3, FileText, History, Mail, UploadCloud, X} from 'lucide-react';
import {Link, useParams, useSearchParams} from 'react-router-dom';
import {
  baixarDocumento,
  confirmarGuia,
  marcarComoPago,
  obterDetalheImposto,
  prepararGuia,
  registrarImposto,
  registrarSituacao,
  reenviarNotificacao,
  visualizarDocumento,
  obterPreviewDocumento,
  type DocumentoImposto,
  type ImpostoDetalhe,
  type NotificacaoEvento,
} from '../../services/api/impostos';
import {Loading} from '../../components/ui/Loading';
import {ErrorState} from '../../components/ui/ErrorState';
import './Impostos.css';

function dinheiro(v: number | undefined | null) {
  return new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(v || 0));
}

function dataBr(v?: string | null) {
  if (!v) return '—';
  const p = v.slice(0, 10).split('-');
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : '—';
}

function Modal({
  children,
  onClose,
  wide = false,
}: {
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div
      className="imp-modal-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={`imp-dialog ${wide ? 'wide' : ''}`}>{children}</div>
    </div>
  );
}

function Field({
  label,
  value,
  edit,
  onChange,
}: {
  label: string;
  value: string;
  edit: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="imp-extracted-field">
      <span>{label}</span>
      {edit ? (
        <input value={value === '—' ? '' : value} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <strong>{value}</strong>
      )}
    </label>
  );
}

function Communication({
  eventos,
  onReenviar,
}: {
  eventos: NotificacaoEvento[];
  onReenviar: (id: number) => Promise<void>;
}) {
  return (
    <div className="panel imp-communication">
      <h3>
        <Mail size={14} /> Comunicação com o cliente
      </h3>
      {eventos.length ? (
        <div className="imp-timeline">
          {eventos.map((event) => (
            <div key={event.id} className="imp-timeline-item">
              <i />
              <div>
                <strong>{event.titulo}</strong>
                <span>{event.mensagem || '—'}</span>
                <small>
                  {event.agendado_para ? new Date(event.agendado_para).toLocaleString('pt-BR') : 'Sem agendamento'} · {event.status}
                </small>
                {event.status !== 'ENVIADA' && (
                  <button className="button ghost" onClick={() => void onReenviar(event.id)}>
                    Enviar novamente
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="imp-muted">Nenhuma comunicação registrada.</p>
      )}
    </div>
  );
}

function ConfirmModal({
  draft,
  setDraft,
  onBack,
  onConfirm,
  busy,
  onReplace,
}: {
  draft: any;
  setDraft: (value: any) => void;
  onBack: () => void;
  onConfirm: () => void;
  onReplace: () => void;
  busy: boolean;
}) {
  const ex = draft.extracao || {};
  const [edit, setEdit] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  useEffect(() => {
    let active = true;
    let objectUrl = '';
    const carregarPreview = async () => {
      if (!draft?.documento?.id) return;
      try {
        objectUrl = await obterPreviewDocumento(draft.documento.id);
        if (active) setPreviewUrl(objectUrl);
      } catch {}
    };
    void carregarPreview();
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [draft?.documento?.id]);
  const valor = ex.valor_extraido == null ? '' : String(ex.valor_extraido);
  const valorDisplay = valor === '' ? '—' : dinheiro(Number(valor));

  const updateExtracao = (field: string, value: string) => {
    setDraft((current: any) => ({
      ...current,
      extracao: {
        ...(current?.extracao || {}),
        [field]: value,
      },
    }));
  };

  return (
    <Modal onClose={onBack} wide>
      <div className="imp-dialog-head">
        <div>
          <span className="eyebrow">ETAPA 2 DE 3</span>
          <h3>Conferir informações</h3>
          <p>
            ✓ Enviar arquivo → <strong>② Conferir informações</strong> → ③ Confirmar
          </p>
        </div>
        <button className="icon-button" onClick={onBack} aria-label="Fechar">
          <X size={14} />
        </button>
      </div>

      <div className="imp-confirm-grid">
        <div className="imp-file-preview">
          {previewUrl && draft.documento?.mime_type?.startsWith('image/') ? (
            <img src={previewUrl} alt="Pré-visualização da guia" className="imp-document-preview-image" />
          ) : previewUrl && draft.documento?.mime_type === 'application/pdf' ? (
            <iframe src={previewUrl} title="Pré-visualização da guia" className="imp-document-preview-frame" />
          ) : (
            <FileText size={38} />
          )}
          <strong>{draft.documento?.nome_arquivo || 'Documento'}</strong>
          <small>{draft.documento?.tamanho ? `${Math.round(draft.documento.tamanho / 1024)} KB` : ''}{draft.documento?.enviado_em ? ` · Enviado em ${new Date(draft.documento.enviado_em).toLocaleString('pt-BR')}` : ''}</small>
          {draft.documento?.id ? (
            <div className="imp-preview-actions">
              <button className="imp-link-button" onClick={() => void visualizarDocumento(draft.documento.id)}>Visualizar</button>
              <button className="imp-link-button" onClick={onReplace}>Substituir arquivo</button>
            </div>
          ) : null}
        </div>

        <div>
          <div className="imp-extracted-head">
            <strong>Informações extraídas</strong>
            <button className="button ghost" onClick={() => setEdit((value) => !value)}>
              <Edit3 size={12} /> {edit ? 'Fechar edição' : 'Editar'}
            </button>
          </div>

          <div className="imp-extracted-grid">
            <Field
              label="Competência"
              value={ex.competencia_extraida || '—'}
              edit={edit}
              onChange={(value) => updateExtracao('competencia_extraida', value)}
            />
            <Field
              label="Vencimento"
              value={ex.vencimento_extraido || '—'}
              edit={edit}
              onChange={(value) => updateExtracao('vencimento_extraido', value)}
            />
            <Field
              label="Valor"
              value={valorDisplay}
              edit={edit}
              onChange={(value) => updateExtracao('valor_extraido', value.replace(',', '.').replace(/[^0-9.-]/g, ''))}
            />
            <Field
              label="Código da receita"
              value={ex.codigo_receita || '—'}
              edit={edit}
              onChange={(value) => updateExtracao('codigo_receita', value)}
            />
            <Field
              label="CNPJ"
              value={ex.cnpj_extraido || '—'}
              edit={edit}
              onChange={(value) => updateExtracao('cnpj_extraido', value)}
            />
            <Field
              label="Data do pagamento"
              value={ex.data_pagamento_extraida || '—'}
              edit={edit}
              onChange={(value) => updateExtracao('data_pagamento_extraida', value)}
            />
          </div>
        </div>

        <label className="imp-modal-label">
          <span>Mensagem ao cliente (padrão)</span>
          <textarea
            rows={6}
            value={
              draft.mensagem_cliente ||
              `Prezado cliente,\n\nSegue em anexo a guia referente à competência ${ex.competencia_extraida || ''}, com vencimento em ${
                ex.vencimento_extraido ? dataBr(ex.vencimento_extraido) : ''
              }, no valor de ${ex.valor_extraido != null ? dinheiro(Number(ex.valor_extraido)) : 'R$ 0,00'}.\n\nQualquer dúvida estamos à disposição.\n\nAtenciosamente,\nEquipe Contábil`
            }
            onChange={(event) => setDraft((current: any) => ({...current, mensagem_cliente: event.target.value}))}
          />
        </label>
      </div>

      <div className="modal-actions">
        <button className="button secondary" onClick={onBack}>Voltar</button>
        <button className="button primary" disabled={busy} onClick={onConfirm}>
          {busy ? 'Salvando...' : 'Confirmar e salvar'}
        </button>
      </div>
    </Modal>
  );
}

export function ImpostoMensalPage() {
  const {empresaId, tributoId} = useParams();
  const empresa = Number(empresaId);
  const tributo = Number(tributoId);
  const [params] = useSearchParams();

  const agora = new Date();
  const competenciaAnterior = new Date(agora.getFullYear(), agora.getMonth() - 1, 1);
  const [ano, setAno] = useState(Number(params.get('ano')) || competenciaAnterior.getFullYear());
  const [mes, setMes] = useState(Number(params.get('mes')) || competenciaAnterior.getMonth() + 1);

  const [data, setData] = useState<ImpostoDetalhe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(false);
  const [modo, setModo] = useState<'GUIA' | 'CREDOR' | 'SEM_MOVIMENTACAO'>('GUIA');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [draft, setDraft] = useState<any>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [editVenc, setEditVenc] = useState('');
  const [editPag, setEditPag] = useState('');
  const [editDoc, setEditDoc] = useState('');
  const [editObs, setEditObs] = useState('');
  const [baseObs, setBaseObs] = useState('');
  const [reload, setReload] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      setData(await obterDetalheImposto(empresa, tributo, ano, mes));
    } catch (errorValue) {
      setError(errorValue instanceof Error ? errorValue.message : 'Erro ao carregar o imposto.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [empresa, tributo, ano, mes, reload]);

  const mensal = data?.mensal;
  const doc = data?.documentos?.[0] as DocumentoImposto | undefined;
  const titulo = data?.tributo.nome || 'Imposto';
  useEffect(() => { if (mensal) setBaseObs(mensal.observacao || ''); }, [mensal?.id, mensal?.observacao]);

  async function saveBaseObservation() {
    setBusy(true);
    try {
      await registrarImposto(empresa, {
        tributo_id: tributo,
        competencia_ano: ano,
        competencia_mes: mes,
        status: mensal?.status || 'PENDENTE',
        valor: mensal?.valor ?? null,
        data_vencimento: mensal?.data_vencimento || null,
        data_pagamento: mensal?.data_pagamento || null,
        numero_documento: mensal?.numero_documento || null,
        observacao: baseObs || null,
      });
      setReload((value) => value + 1);
      setNotice('Observação salva.');
    } catch (errorValue) {
      setNotice(errorValue instanceof Error ? errorValue.message : 'Não foi possível salvar a observação.');
    } finally {
      setBusy(false);
    }
  }

  async function saveSituation(tipo: 'CREDOR' | 'SEM_MOVIMENTACAO') {
    setBusy(true);
    try {
      await registrarSituacao(
        empresa,
        {
          tributo_id: tributo,
          competencia_ano: ano,
          competencia_mes: mes,
          observacao: draft?.observacao || '',
        },
        tipo,
      );
      setModal(false);
      setDraft(null);
      setReload((value) => value + 1);
      setNotice('Registro mensal salvo.');
    } catch (errorValue) {
      setNotice(errorValue instanceof Error ? errorValue.message : 'Não foi possível salvar.');
    } finally {
      setBusy(false);
    }
  }

  async function upload() {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setNotice('O arquivo excede o limite de 10 MB.');
      return;
    }

    setBusy(true);
    try {
      const result = await prepararGuia(empresa, tributo, ano, mes, file);
      setDraft({documento: result.documento, extracao: result.extracao, observacao: '', mensagem_cliente: ''});
      setModal(false);
      setConfirmOpen(true);
    } catch (errorValue) {
      setNotice(errorValue instanceof Error ? errorValue.message : 'Não foi possível processar a guia.');
    } finally {
      setBusy(false);
    }
  }

  const replaceFile = () => {
    setConfirmOpen(false);
    setFile(null);
    if (fileRef.current) fileRef.current.value = '';
    setModo('GUIA');
    setModal(true);
  };

  async function confirm() {
    if (!draft?.documento?.id) return;
    setBusy(true);
    try {
      const ex = draft.extracao || {};
      await confirmarGuia(empresa, tributo, {
        documento_id: draft.documento.id,
        competencia_ano: ano,
        competencia_mes: mes,
        competencia_extraida: ex.competencia_extraida || null,
        valor: ex.valor_extraido === '' || ex.valor_extraido == null ? null : Number(ex.valor_extraido),
        vencimento: ex.vencimento_extraido || null,
        codigo_receita: ex.codigo_receita || null,
        cnpj: ex.cnpj_extraido || null,
        data_pagamento: ex.data_pagamento_extraida || null,
        periodo_apuracao_inicio: ex.periodo_apuracao_inicio || null,
        periodo_apuracao_fim: ex.periodo_apuracao_fim || null,
        mensagem_cliente: draft.mensagem_cliente || null,
        observacao: draft.observacao || null,
      });
      setConfirmOpen(false);
      setDraft(null);
      setFile(null);
      setReload((value) => value + 1);
      setNotice('Guia confirmada e salva com sucesso.');
    } catch (errorValue) {
      setNotice(errorValue instanceof Error ? errorValue.message : 'Não foi possível confirmar a guia.');
    } finally {
      setBusy(false);
    }
  }

  async function pay() {
    if (!mensal) return;
    try {
      await marcarComoPago(empresa, tributo, ano, mes);
      setReload((value) => value + 1);
      setNotice('Pagamento registrado.');
    } catch (errorValue) {
      setNotice(errorValue instanceof Error ? errorValue.message : 'Não foi possível registrar o pagamento.');
    }
  }

  if (loading && !data) return <div className="page"><Loading /></div>;
  if (error && !data) return <div className="page"><ErrorState message={error} onRetry={() => void load()} /></div>;
  if (!data || !mensal) return null;

  const abrirEdicao = () => {
    setEditValue(mensal.valor != null ? String(mensal.valor) : '');
    setEditVenc(mensal.data_vencimento || '');
    setEditPag(mensal.data_pagamento || '');
    setEditDoc(mensal.numero_documento || '');
    setEditObs(mensal.observacao || '');
    setEditOpen(true);
  };

  const salvarEdicao = async () => {
    setBusy(true);
    try {
      await registrarImposto(empresa, {
        tributo_id: tributo,
        competencia_ano: ano,
        competencia_mes: mes,
        status: mensal.status,
        valor: editValue === '' ? null : Number(editValue),
        data_vencimento: editVenc || null,
        data_pagamento: editPag || null,
        numero_documento: editDoc || null,
        observacao: editObs || null,
      });
      setEditOpen(false);
      setReload((value) => value + 1);
      setNotice('Registro atualizado.');
    } catch (errorValue) {
      setNotice(errorValue instanceof Error ? errorValue.message : 'Não foi possível atualizar o registro.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page impostos-page">
      <Link to={`/impostos/empresa/${empresa}`} className="back-link">
        <ArrowLeft size={15} /> Voltar para {data.empresa.razao_social}
      </Link>

      <div className="imp-tax-detail-head">
        <div>
          <span className="eyebrow">IMPOSTO · {data.competencia.label}</span>
          <h2>{titulo}</h2>
          <div className="imp-tax-detail-status">
            <span className={`imp-tax-status ${mensal.status_exibicao.toLowerCase()}`}>{mensal.status_exibicao}</span>
            <span><CalendarDays size={13} /> {data.competencia.label}</span>
          </div>
        </div>
        <div className="imp-section-actions">
          <button className="button secondary" onClick={() => setReload((value) => value + 1)}>
            <History size={13} /> Atualizar
          </button>
          {mensal.status_exibicao !== 'PENDENTE' && (
            <button className="button secondary" onClick={abrirEdicao}>
              <Edit3 size={13} /> Editar registro
            </button>
          )}
          {['A_VENCER', 'EM_ATRASO'].includes(mensal.status_exibicao) && (
            <button className="button primary" onClick={() => void pay()}>
              <CheckCircle2 size={13} /> Marcar como pago
            </button>
          )}
        </div>
      </div>

      {notice && (
        <div className="imp-inline-alert">
          {notice}
          <button className="icon-button" onClick={() => setNotice('')} aria-label="Fechar aviso">
            <X size={13} />
          </button>
        </div>
      )}

      {mensal.status === 'PENDENTE' && !doc ? (
        <>
        <div className="imp-tax-empty-grid">
          <div
            className="panel imp-upload-empty"
            onClick={() => setModal(true)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const droppedFile = event.dataTransfer.files[0];
              if (droppedFile) {
                setFile(droppedFile);
                setModo('GUIA');
                setModal(true);
              }
            }}
          >
            <UploadCloud size={38} />
            <strong>Arraste a guia do imposto</strong>
            <span>ou clique para registrar</span>
            <small>PDF, JPG ou PNG (máx. 10MB)</small>
          </div>

          <div className="panel imp-tax-info">
            <h3>Informações do imposto</h3>
            <dl>
              <dt>Esfera</dt><dd>{data.tributo.esfera}</dd>
              <dt>Código do tributo</dt><dd>{data.tributo.sigla}</dd>
              <dt>Competência inicial</dt><dd>{data.tributo.vigencia_inicio ? data.tributo.vigencia_inicio.slice(5, 7) + '/' + data.tributo.vigencia_inicio.slice(0, 4) : '—'}</dd>
              <dt>Situação</dt><dd>{data.tributo.status}</dd>
            </dl>
          </div>
        </div>
        <div className="panel imp-base-observation">
          <label className="imp-modal-label">Observações (opcional)
            <textarea rows={4} value={baseObs} onChange={(event) => setBaseObs(event.target.value)} placeholder="Informe aqui o motivo da ausência de pagamento, se foi credor ou qualquer outra observação..." />
          </label>
          <div className="modal-actions imp-base-observation-actions">
            <button className="button secondary" disabled={busy || baseObs === (mensal.observacao || '')} onClick={() => void saveBaseObservation()}>Salvar observação</button>
          </div>
        </div>
        </>
      ) : (
        <div className="imp-tax-registered-grid">
          <div className="panel">
            <div className="imp-registered-card">
              <div>
                <span className="eyebrow">REGISTRO MENSAL</span>
                <h3>{titulo} — {data.competencia.label}</h3>
                <span className={`imp-tax-status ${mensal.status_exibicao.toLowerCase()}`}>{mensal.status_exibicao}</span>
              </div>
              <div className="imp-big-money">{dinheiro(mensal.valor)}</div>
            </div>
            <div className="imp-info-grid">
              <div><span>Competência</span><strong>{data.competencia.label}</strong></div>
              <div><span>Vencimento</span><strong>{dataBr(mensal.data_vencimento)}</strong></div>
              <div><span>Data do pagamento</span><strong>{dataBr(mensal.data_pagamento)}</strong></div>
              <div><span>Código de receita</span><strong>{mensal.numero_documento || '—'}</strong></div>
            </div>
            {mensal.observacao && <div className="imp-observation"><strong>Observação</strong><p>{mensal.observacao}</p></div>}
          </div>

          <Communication
            eventos={data.notificacoes || []}
            onReenviar={async (id) => {
              try {
                await reenviarNotificacao(id);
                setNotice('Evento de reenvio criado.');
              } catch (errorValue) {
                setNotice(errorValue instanceof Error ? errorValue.message : 'Erro ao criar reenvio.');
              }
            }}
          />
        </div>
      )}

      {doc && (
        <>
          <div className="panel imp-document-card">
            <div>
              <FileText size={24} />
              <div>
                <strong>Documento da guia</strong>
                <span>{doc.nome_arquivo} · {doc.enviado_em ? `Enviado em ${new Date(doc.enviado_em).toLocaleString('pt-BR')}` : (doc.criado_em ? new Date(doc.criado_em).toLocaleString('pt-BR') : 'Data não informada')} · {doc.usuario_upload_nome || 'Usuário do sistema'}</span>
              </div>
            </div>
            <button className="button secondary" onClick={() => void baixarDocumento(doc.id)}>
              <Download size={13} /> Baixar
            </button>
          </div>

          <div className="imp-tax-registered-grid imp-after-document">
            <div className="panel imp-document-info">
              <h3>Informações extraídas do documento</h3>
              <div className="imp-info-grid">
                <div><span>Competência</span><strong>{doc.competencia_extraida || '—'}</strong></div>
                <div><span>Valor</span><strong>{doc.valor_extraido != null ? dinheiro(doc.valor_extraido) : '—'}</strong></div>
                <div><span>Vencimento</span><strong>{dataBr(doc.vencimento_extraido)}</strong></div>
                <div><span>Código de receita</span><strong>{doc.codigo_receita || '—'}</strong></div>
                <div><span>CNPJ</span><strong>{doc.cnpj_extraido || '—'}</strong></div>
                <div><span>Data do pagamento</span><strong>{dataBr(doc.data_pagamento_extraida)}</strong></div>
                <div>
                  <span>Período de apuração</span>
                  <strong>
                    {doc.periodo_apuracao_inicio && doc.periodo_apuracao_fim
                      ? `${dataBr(doc.periodo_apuracao_inicio)} a ${dataBr(doc.periodo_apuracao_fim)}`
                      : '—'}
                  </strong>
                </div>
              </div>
              {doc.mensagem_cliente && (
                <div className="imp-observation">
                  <strong>Mensagem ao cliente</strong>
                  <p>{doc.mensagem_cliente}</p>
                </div>
              )}
            </div>

            <div className="panel imp-history">
              <h3><History size={14} /> Histórico</h3>
              {data.historico?.length ? (
                <div className="imp-timeline">
                  {data.historico.slice(0, 12).map((history: any) => (
                    <div className="imp-timeline-item" key={history.id}>
                      <i />
                      <div>
                        <strong>{history.acao}</strong>
                        <span>{history.status_anterior || '—'} → {history.status_novo || '—'}</span>
                        <small>{history.criado_em ? new Date(history.criado_em).toLocaleString('pt-BR') : ''}</small>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="imp-muted">Nenhuma alteração registrada.</p>
              )}
            </div>
          </div>
        </>
      )}

      {modal && (
        <Modal onClose={() => setModal(false)}>
          <div className="imp-dialog-head">
            <div>
              <span className="eyebrow">REGISTRO MENSAL</span>
              <h3>Adicionar guia de pagamento — {titulo}</h3>
            </div>
            <button className="icon-button" onClick={() => setModal(false)} aria-label="Fechar">
              <X size={14} />
            </button>
          </div>

          <div className="modal-body">
            <div className="imp-radio-options">
              <label className={modo === 'GUIA' ? 'active' : ''}>
                <input type="radio" checked={modo === 'GUIA'} onChange={() => setModo('GUIA')} />
                <span><strong>Adicionar guia de pagamento</strong><small>Selecione o arquivo para que o sistema leia as informações.</small></span>
              </label>
              <label className={modo === 'CREDOR' ? 'active' : ''}>
                <input type="radio" checked={modo === 'CREDOR'} onChange={() => setModo('CREDOR')} />
                <span><strong>Informar que foi credor neste mês</strong><small>Marque se o imposto gerou crédito e não houve pagamento.</small></span>
              </label>
              <label className={modo === 'SEM_MOVIMENTACAO' ? 'active' : ''}>
                <input type="radio" checked={modo === 'SEM_MOVIMENTACAO'} onChange={() => setModo('SEM_MOVIMENTACAO')} />
                <span><strong>Sem movimentação neste mês</strong><small>Marque se não houve fato gerador para este imposto.</small></span>
              </label>
            </div>

            {modo === 'GUIA' ? (
              <div
                className="imp-drop-zone"
                onClick={() => fileRef.current?.click()}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  setFile(event.dataTransfer.files[0] || null);
                }}
              >
                <UploadCloud size={28} />
                <strong>{file ? file.name : 'Selecione o arquivo da guia'}</strong>
                <span>ou arraste o arquivo aqui</span>
                <small>PDF, JPG ou PNG (máx. 10MB)</small>
                <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" hidden onChange={(event) => setFile(event.target.files?.[0] || null)} />
              </div>
            ) : (
              <label className="imp-modal-label">
                Observação
                <textarea
                  rows={5}
                  value={draft?.observacao || ''}
                  onChange={(event) => setDraft((current: any) => ({...(current || {}), observacao: event.target.value}))}
                  placeholder={modo === 'CREDOR' ? 'Ex.: PIS credor na competência 08/2026, não houve valor a recolher.' : 'Ex.: Não houve faturamento no mês.'}
                />
              </label>
            )}
          </div>

          <div className="modal-actions">
            <button className="button secondary" onClick={() => setModal(false)}>Cancelar</button>
            <button
              className="button primary"
              disabled={busy || (modo === 'GUIA' && !file)}
              onClick={() => modo === 'GUIA' ? void upload() : void saveSituation(modo)}
            >
              {busy ? 'Processando...' : 'Salvar'}
            </button>
          </div>
        </Modal>
      )}

      {editOpen && (
        <Modal onClose={() => setEditOpen(false)}>
          <div className="imp-dialog-head">
            <div><span className="eyebrow">CORREÇÃO</span><h3>Editar registro — {titulo}</h3></div>
            <button className="icon-button" onClick={() => setEditOpen(false)} aria-label="Fechar"><X size={14} /></button>
          </div>
          <div className="modal-body">
            <div className="form-grid">
              <label>Valor<input type="number" step="0.01" min="0" value={editValue} onChange={(event) => setEditValue(event.target.value)} /></label>
              <label>Vencimento<input type="date" value={editVenc} onChange={(event) => setEditVenc(event.target.value)} /></label>
              <label>Pagamento<input type="date" value={editPag} onChange={(event) => setEditPag(event.target.value)} /></label>
              <label>Número da guia<input value={editDoc} onChange={(event) => setEditDoc(event.target.value)} /></label>
            </div>
            <label className="imp-modal-label">Observação<textarea rows={4} value={editObs} onChange={(event) => setEditObs(event.target.value)} /></label>
          </div>
          <div className="modal-actions">
            <button className="button secondary" onClick={() => setEditOpen(false)}>Cancelar</button>
            <button className="button primary" disabled={busy} onClick={() => void salvarEdicao()}>
              {busy ? 'Salvando...' : 'Salvar alterações'}
            </button>
          </div>
        </Modal>
      )}

      {confirmOpen && draft && (
        <ConfirmModal draft={draft} setDraft={setDraft} onBack={() => setConfirmOpen(false)} onConfirm={() => void confirm()} onReplace={replaceFile} busy={busy} />
      )}
    </div>
  );
}
