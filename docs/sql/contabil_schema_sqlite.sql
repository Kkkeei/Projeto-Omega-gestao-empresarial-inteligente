-- Plataforma OMEGA - modulo Contabil
-- SQLite - proposta inicial de schema. NAO executar automaticamente.
-- Depende das tabelas existentes: empresas(id) e usuarios(id).
-- Aplicar somente depois de backup e revisao do schema atual.

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS contabil_atribuicoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    atribuido_por INTEGER,
    atribuido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    encerrado_em TEXT,
    motivo_encerramento TEXT,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE RESTRICT,
    FOREIGN KEY (atribuido_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_contabil_atribuicao_ativa_empresa
    ON contabil_atribuicoes(empresa_id)
    WHERE encerrado_em IS NULL;

CREATE INDEX IF NOT EXISTS idx_contabil_atribuicoes_usuario_ativa
    ON contabil_atribuicoes(usuario_id, encerrado_em);

CREATE TABLE IF NOT EXISTS contabil_atribuicoes_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    atribuicao_anterior_id INTEGER,
    atribuicao_nova_id INTEGER,
    usuario_anterior_id INTEGER,
    usuario_novo_id INTEGER,
    alterado_por INTEGER,
    acao TEXT NOT NULL,
    motivo TEXT,
    dados_anteriores TEXT,
    dados_novos TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT,
    FOREIGN KEY (atribuicao_anterior_id) REFERENCES contabil_atribuicoes(id) ON DELETE SET NULL,
    FOREIGN KEY (atribuicao_nova_id) REFERENCES contabil_atribuicoes(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_anterior_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_novo_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (alterado_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contabil_atribuicoes_hist_empresa
    ON contabil_atribuicoes_historico(empresa_id, criado_em DESC);

CREATE TABLE IF NOT EXISTS contabil_categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    ordem INTEGER NOT NULL DEFAULT 0,
    padrao INTEGER NOT NULL DEFAULT 0 CHECK (padrao IN (0,1)),
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    arquivado_em TEXT,
    criado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT,
    FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_contabil_categoria_nome_ativa
    ON contabil_categorias(empresa_id, nome COLLATE NOCASE)
    WHERE ativo = 1;

CREATE INDEX IF NOT EXISTS idx_contabil_categorias_empresa_ordem
    ON contabil_categorias(empresa_id, ativo, ordem, nome);

CREATE TABLE IF NOT EXISTS contabil_documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    observacao TEXT,
    competencia_inicio INTEGER NOT NULL,
    competencia_fim INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    inativado_em TEXT,
    motivo_inativacao TEXT,
    observacao_inativacao TEXT,
    criado_por INTEGER,
    atualizado_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((competencia_inicio / 100) BETWEEN 1900 AND 2999),
    CHECK ((competencia_inicio % 100) BETWEEN 1 AND 12),
    CHECK (competencia_fim IS NULL OR ((competencia_fim / 100) BETWEEN 1900 AND 2999)),
    CHECK (competencia_fim IS NULL OR ((competencia_fim % 100) BETWEEN 1 AND 12)),
    CHECK (competencia_fim IS NULL OR competencia_fim >= competencia_inicio),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT,
    FOREIGN KEY (categoria_id) REFERENCES contabil_categorias(id) ON DELETE RESTRICT,
    FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (atualizado_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contabil_documentos_empresa_periodo
    ON contabil_documentos(empresa_id, competencia_inicio, competencia_fim, ativo);

CREATE INDEX IF NOT EXISTS idx_contabil_documentos_categoria
    ON contabil_documentos(empresa_id, categoria_id, ativo);

CREATE TABLE IF NOT EXISTS contabil_obrigacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    competencia INTEGER NOT NULL,
    cancelada_em TEXT,
    motivo_cancelamento TEXT,
    criada_por INTEGER,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((competencia / 100) BETWEEN 1900 AND 2999),
    CHECK ((competencia % 100) BETWEEN 1 AND 12),
    UNIQUE(documento_id, competencia),
    FOREIGN KEY (documento_id) REFERENCES contabil_documentos(id) ON DELETE RESTRICT,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT,
    FOREIGN KEY (criada_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contabil_obrigacoes_empresa_competencia
    ON contabil_obrigacoes(empresa_id, competencia);

CREATE INDEX IF NOT EXISTS idx_contabil_obrigacoes_documento
    ON contabil_obrigacoes(documento_id, competencia);

CREATE TABLE IF NOT EXISTS contabil_arquivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    obrigacao_id INTEGER NOT NULL,
    nome_original TEXT NOT NULL,
    nome_armazenado TEXT NOT NULL,
    caminho_storage TEXT NOT NULL,
    extensao TEXT NOT NULL,
    mime_type TEXT,
    tamanho INTEGER NOT NULL CHECK (tamanho >= 0),
    hash_sha256 TEXT NOT NULL,
    enviado_por INTEGER,
    enviado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    excluido_em TEXT,
    excluido_por INTEGER,
    motivo_exclusao TEXT,
    FOREIGN KEY (obrigacao_id) REFERENCES contabil_obrigacoes(id) ON DELETE RESTRICT,
    FOREIGN KEY (enviado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (excluido_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contabil_arquivos_obrigacao_ativos
    ON contabil_arquivos(obrigacao_id, excluido_em, enviado_em DESC);

CREATE INDEX IF NOT EXISTS idx_contabil_arquivos_hash
    ON contabil_arquivos(hash_sha256);

CREATE TABLE IF NOT EXISTS contabil_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    usuario_id INTEGER,
    entidade TEXT NOT NULL,
    entidade_id INTEGER,
    acao TEXT NOT NULL,
    dados_anteriores TEXT,
    dados_novos TEXT,
    observacao TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contabil_historico_empresa_data
    ON contabil_historico(empresa_id, criado_em DESC);

CREATE INDEX IF NOT EXISTS idx_contabil_historico_entidade
    ON contabil_historico(entidade, entidade_id, criado_em DESC);

COMMIT;

-- Categorias padrao devem ser criadas por empresa de forma idempotente:
-- Extratos Bancarios
-- Aplicacoes Financeiras
-- Financiamentos / Emprestimos
-- Consorcios
-- Administradoras de Cartoes
-- Outros Documentos
--
-- A pasta virtual "Tudo" NAO deve ser gravada na tabela.
-- O status das obrigacoes e calculado no servico, nao persistido:
-- 1) arquivos ativos > 0: RECEBIDO
-- 2) competencia futura: FUTURO
-- 3) competencia igual a atual: PENDENTE
-- 4) competencia anterior sem arquivo: NAO_RECEBIDO
