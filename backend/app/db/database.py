import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "omega.db"
STORAGE_BASE = BASE_DIR.parent / "storage"
BACKUP_DIR = STORAGE_BASE / "backups" / "database"


def conectar_banco() -> sqlite3.Connection:
    conexao = sqlite3.connect(DB_PATH, timeout=30)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA journal_mode = WAL")
    conexao.execute("PRAGMA synchronous = FULL")
    conexao.execute("PRAGMA busy_timeout = 30000")
    return conexao


def criar_tabelas() -> None:
    conexao = conectar_banco()
    try:
        cursor = conexao.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT NOT NULL UNIQUE,
            razao_social TEXT NOT NULL,
            nome_fantasia TEXT,
            inscricao_estadual TEXT,
            inscricao_municipal TEXT,
            email TEXT,
            nire TEXT,
            regime_tributario TEXT,
            data_entrada TEXT,
            data_saida TEXT,
            data_abertura TEXT,
            natureza_juridica TEXT,
            porte TEXT,
            capital_social REAL,
            cnae_principal TEXT,
            cnaes_secundarios TEXT,
            logradouro TEXT,
            numero TEXT,
            complemento TEXT,
            bairro TEXT,
            municipio TEXT,
            codigo_ibge TEXT,
            uf TEXT,
            cep TEXT,
            telefone TEXT,
            responsavel TEXT,
            segmento TEXT,
            grupo_empresarial TEXT,
            observacoes TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ultima_sincronizacao TEXT
        );

        CREATE TABLE IF NOT EXISTS empresa_historicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo_evento TEXT NOT NULL,
            descricao TEXT,
            dados_anteriores TEXT,
            dados_novos TEXT,
            origem TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS regimes_tributarios_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            regime_anterior TEXT,
            regime_novo TEXT NOT NULL,
            mes_inicio INTEGER,
            ano_inicio INTEGER,
            data_alteracao TEXT NOT NULL,
            origem TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS socios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            cpf_cnpj TEXT,
            qualificacao TEXT,
            data_entrada TEXT,
            data_saida TEXT,
            percentual_participacao REAL,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tipos_certidao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            esfera TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            origem TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            categoria_id INTEGER,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS categorias_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            categoria_pai_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            ordem INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1,
            arquivado_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, categoria_pai_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (categoria_pai_id) REFERENCES categorias_documentos(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS documento_versoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            versao INTEGER NOT NULL,
            nome_arquivo TEXT,
            caminho_arquivo TEXT,
            extensao TEXT,
            tamanho INTEGER,
            hash_arquivo TEXT,
            mime_type TEXT,
            usuario_upload_id INTEGER,
            origem TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(documento_id, versao),
            FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS certidoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo_certidao_id INTEGER NOT NULL,
            situacao TEXT NOT NULL,
            numero_certidao TEXT,
            data_emissao TEXT,
            data_validade TEXT,
            documento_id INTEGER,
            origem TEXT,
            observacao TEXT,
            atualizada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, tipo_certidao_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (tipo_certidao_id) REFERENCES tipos_certidao(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id)
        );

        CREATE TABLE IF NOT EXISTS consultas_certidoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo_certidao_id INTEGER NOT NULL,
            certidao_id INTEGER,
            situacao TEXT NOT NULL,
            numero_certidao TEXT,
            data_emissao TEXT,
            data_validade TEXT,
            pdf_path TEXT,
            origem TEXT,
            mensagem TEXT,
            texto_extraido TEXT,
            consultado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (tipo_certidao_id) REFERENCES tipos_certidao(id),
            FOREIGN KEY (certidao_id) REFERENCES certidoes(id) ON DELETE SET NULL
        );

        -- Histórico permanente: cada consulta gera um snapshot imutável.
        CREATE TABLE IF NOT EXISTS certidoes_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consulta_id INTEGER NOT NULL UNIQUE,
            empresa_id INTEGER NOT NULL,
            tipo_certidao_id INTEGER NOT NULL,
            certidao_id INTEGER,
            situacao TEXT NOT NULL,
            numero_certidao TEXT,
            data_emissao TEXT,
            data_validade TEXT,
            pdf_path TEXT,
            documento_id INTEGER,
            hash_arquivo TEXT,
            nome_arquivo_original TEXT,
            status_processamento TEXT,
            erro_tecnico TEXT,
            mensagem TEXT,
            texto_extraido TEXT,
            consultado_em TEXT NOT NULL,
            registrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (consulta_id) REFERENCES consultas_certidoes(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (tipo_certidao_id) REFERENCES tipos_certidao(id)
        );

        CREATE TABLE IF NOT EXISTS pendencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            origem TEXT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'ABERTA',
            prioridade TEXT NOT NULL DEFAULT 'NORMAL',
            data_identificacao TEXT,
            prazo TEXT,
            data_resolucao TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS automacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            configuracao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS execucoes_automacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            automacao_id INTEGER,
            empresa_id INTEGER,
            tipo TEXT NOT NULL,
            status TEXT NOT NULL,
            inicio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fim TEXT,
            mensagem TEXT,
            erro_tecnico TEXT,
            resultado TEXT,
            origem TEXT,
            FOREIGN KEY (automacao_id) REFERENCES automacoes(id) ON DELETE SET NULL,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL DEFAULT 'USUARIO',
            ativo INTEGER NOT NULL DEFAULT 1,
            token_version INTEGER NOT NULL DEFAULT 0,
            deve_trocar_senha INTEGER NOT NULL DEFAULT 0,
            ultimo_login TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS auditorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidade TEXT NOT NULL,
            entidade_id INTEGER,
            acao TEXT NOT NULL,
            dados_anteriores TEXT,
            dados_novos TEXT,
            origem TEXT,
            ip TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tokens_redefinicao_senha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expira_em TEXT NOT NULL,
            usado_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS automacao_locks (
            lock_name TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            tipo TEXT NOT NULL,
            empresa_id INTEGER,
            empresa TEXT,
            iniciado_em TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            host TEXT,
            pid INTEGER,
            mensagem TEXT
        );

        CREATE TABLE IF NOT EXISTS integracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT,
            descricao TEXT,
            url TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            configuracao TEXT,
            ultima_execucao TEXT,
            status TEXT,
            mensagem TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        """)

        # Migrations for Documentação. Never remove legacy data.
        # These changes must happen before creating indexes on the new columns.
        colunas_documentos = {r[1] for r in conexao.execute("PRAGMA table_info(documentos)").fetchall()}
        if "categoria_id" not in colunas_documentos:
            cursor.execute("ALTER TABLE documentos ADD COLUMN categoria_id INTEGER")

        colunas_versoes = {r[1] for r in conexao.execute("PRAGMA table_info(documento_versoes)").fetchall()}
        for coluna, tipo in (("mime_type", "TEXT"), ("usuario_upload_id", "INTEGER"), ("tamanho", "INTEGER"), ("hash_arquivo", "TEXT")):
            if coluna not in colunas_versoes:
                cursor.execute(f"ALTER TABLE documento_versoes ADD COLUMN {coluna} {tipo}")

        # All indexes are created only after compatibility migrations.
        cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_empresas_cnpj ON empresas(cnpj);
        CREATE INDEX IF NOT EXISTS idx_empresas_razao ON empresas(razao_social);
        CREATE INDEX IF NOT EXISTS idx_empresas_fantasia ON empresas(nome_fantasia);
        CREATE INDEX IF NOT EXISTS idx_empresas_ativo ON empresas(ativo);
        CREATE INDEX IF NOT EXISTS idx_historicos_empresa ON empresa_historicos(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_regime_empresa ON regimes_tributarios_historico(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_socios_empresa ON socios(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_certidoes_empresa ON certidoes(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_consultas_empresa ON consultas_certidoes(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_consultas_tipo ON consultas_certidoes(tipo_certidao_id);
        CREATE INDEX IF NOT EXISTS idx_consultas_data ON consultas_certidoes(consultado_em);
        CREATE INDEX IF NOT EXISTS idx_certidoes_historico_empresa ON certidoes_historico(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_certidoes_historico_data ON certidoes_historico(consultado_em);
        CREATE INDEX IF NOT EXISTS idx_pendencias_empresa ON pendencias(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_pendencias_status ON pendencias(status);
        CREATE INDEX IF NOT EXISTS idx_execucoes_empresa ON execucoes_automacao(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_documentos_empresa ON documentos(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_documentos_categoria ON documentos(categoria_id);
        CREATE INDEX IF NOT EXISTS idx_categorias_empresa ON categorias_documentos(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_categorias_pai ON categorias_documentos(categoria_pai_id);
        CREATE INDEX IF NOT EXISTS idx_documento_versoes_usuario ON documento_versoes(usuario_upload_id);
        CREATE INDEX IF NOT EXISTS idx_auditorias_entidade ON auditorias(entidade, entidade_id);
        CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_usuario ON tokens_redefinicao_senha(usuario_id);
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_expira ON tokens_redefinicao_senha(expira_em);
        CREATE INDEX IF NOT EXISTS idx_automacao_locks_expira ON automacao_locks(expira_em);
        """)

        empresas_existentes = cursor.execute("SELECT id FROM empresas").fetchall()
        categorias_padrao = [
            ("Societário", "Contratos, alterações, QSA, atos e certidões societárias.", 1),
            ("Pessoal (Sócio)", "Documentos pessoais e cadastrais dos sócios.", 2),
            ("IRPF", "Declarações, recibos e documentos de Imposto de Renda da pessoa física.", 3),
        ]
        for emp in empresas_existentes:
            for nome, descricao, ordem in categorias_padrao:
                cursor.execute("INSERT OR IGNORE INTO categorias_documentos (empresa_id,categoria_pai_id,nome,descricao,ordem,ativo) VALUES (?,NULL,?,?,?,1)", (emp["id"], nome, descricao, ordem))

        tipos = [
            ("Federal - RFB/PGFN", "Certidão Federal", "FEDERAL"),
            ("FGTS - CRF", "Certificado de Regularidade do FGTS", "FEDERAL"),
            ("CNDT - TST", "Certidão Negativa de Débitos Trabalhistas", "TRABALHISTA"),
            ("Estadual - SEFAZ", "Certidão Estadual", "ESTADUAL"),
            ("Narrativa de Débito Fiscal - SEFAZ", "Certidão Negativa/Narrativa de Débito Fiscal da SEFAZ-PE", "ESTADUAL"),
            ("Municipal", "Certidão Municipal", "MUNICIPAL"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO tipos_certidao (nome, descricao, esfera) VALUES (?, ?, ?)",
            tipos,
        )
        # Migração incremental para o módulo de Certidão Estadual.
        # ALTER TABLE só é executado quando a coluna ainda não existe.
        colunas_consultas = {r[1] for r in conexao.execute("PRAGMA table_info(consultas_certidoes)").fetchall()}
        migracoes = {
            "pendencia": "ALTER TABLE consultas_certidoes ADD COLUMN pendencia INTEGER NOT NULL DEFAULT 0",
            "pendencia_detalhes": "ALTER TABLE consultas_certidoes ADD COLUMN pendencia_detalhes TEXT",
            "nome_arquivo_original": "ALTER TABLE consultas_certidoes ADD COLUMN nome_arquivo_original TEXT",
            "status_processamento": "ALTER TABLE consultas_certidoes ADD COLUMN status_processamento TEXT",
            "erro_tecnico": "ALTER TABLE consultas_certidoes ADD COLUMN erro_tecnico TEXT",
            "texto_extraido": "ALTER TABLE consultas_certidoes ADD COLUMN texto_extraido TEXT",
        }
        for coluna, sql in migracoes.items():
            if coluna not in colunas_consultas:
                cursor.execute(sql)

        colunas_historico = {r[1] for r in conexao.execute("PRAGMA table_info(certidoes_historico)").fetchall()}
        if "texto_extraido" not in colunas_historico:
            cursor.execute("ALTER TABLE certidoes_historico ADD COLUMN texto_extraido TEXT")

        cursor.execute(
            "INSERT OR IGNORE INTO automacoes (tipo,nome,descricao,configuracao) VALUES (?,?,?,?)",
            ("CONSULTA_CERTIDAO_ESTADUAL", "Certidão Estadual - SEFAZ-PE", "Consulta automática da Certidão de Regularidade Fiscal no e-Fisco da SEFAZ Pernambuco.", "{\"origem\":\"SEFAZ-PE\"}"),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO automacoes (tipo,nome,descricao,configuracao) VALUES (?,?,?,?)",
            ("CONSULTA_CERTIDAO_FEDERAL", "Certidão Federal - RFB/PGFN", "Consulta da Certidão Federal de Regularidade Fiscal no portal da Receita Federal/PGFN.", "{\"origem\":\"RFB/PGFN\",\"metodo\":\"PYAUTOGUI\"}"),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO integracoes (nome,tipo,descricao,url) VALUES (?,?,?,?)",
            ("Receita Federal / PGFN", "CERTIDAO_FEDERAL", "Consulta da Certidão de Débitos Relativos a Créditos Tributários Federais e à Dívida Ativa da União.", "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj"),
        )
        cursor.execute(
            "UPDATE automacoes SET configuracao=? WHERE tipo=?",
            ("{\"origem\":\"RFB/PGFN\",\"metodo\":\"PYAUTOGUI\"}", "CONSULTA_CERTIDAO_FEDERAL"),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO automacoes (tipo,nome,descricao,configuracao) VALUES (?,?,?,?)",
            ("CONSULTA_CERTIDAO_NARRATIVA", "Certidão Narrativa de Débito Fiscal - SEFAZ-PE", "Consulta por navegador da Certidão Negativa/Narrativa de Débito Fiscal da SEFAZ Pernambuco, com leitura do documento.", "{\"origem\":\"SEFAZ-PE\",\"metodo\":\"PYAutoGUI\"}"),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO integracoes (nome,tipo,descricao,url) VALUES (?,?,?,?)",
            ("SEFAZ-PE / e-Fisco", "CERTIDAO_ESTADUAL", "Emissão de Certidão de Regularidade Fiscal da SEFAZ Pernambuco.", "https://efisco.sefaz.pe.gov.br/sfi_trb_gcc/PREmitirCertidaoRegularidadeFiscalMovel"),
        )

        # Migra o histórico que já existia antes da proteção permanente.
        cursor.execute("""
            INSERT OR IGNORE INTO certidoes_historico
            (consulta_id,empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,
             data_emissao,data_validade,pdf_path,mensagem,consultado_em)
            SELECT id,empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,
                   data_emissao,data_validade,pdf_path,mensagem,consultado_em
              FROM consultas_certidoes
        """)

        # Reconstrói a fotografia ATUAL para bancos que já possuíam consultas
        # antes desta versão. O histórico existente continua intocado.
        # Isso impede que uma certidão antiga fique invisível na tela apenas
        # porque ainda não havia uma linha correspondente em `certidoes`.
        cursor.execute("""
            INSERT OR IGNORE INTO certidoes
            (empresa_id,tipo_certidao_id,situacao,numero_certidao,data_emissao,data_validade,
             documento_id,origem,observacao,atualizada_em)
            SELECT cc.empresa_id, cc.tipo_certidao_id, cc.situacao, cc.numero_certidao,
                   cc.data_emissao, cc.data_validade,
                   (SELECT h.documento_id FROM certidoes_historico h
                      WHERE h.consulta_id=cc.id LIMIT 1),
                   COALESCE(cc.origem, 'SEFAZ-PE'),
                   cc.mensagem, cc.consultado_em
              FROM consultas_certidoes cc
             WHERE cc.tipo_certidao_id = (SELECT id FROM tipos_certidao WHERE nome='Estadual - SEFAZ' LIMIT 1)
               AND NOT EXISTS (SELECT 1 FROM certidoes c
                                WHERE c.empresa_id=cc.empresa_id
                                  AND c.tipo_certidao_id=cc.tipo_certidao_id)
               AND cc.id = (SELECT MAX(cc2.id) FROM consultas_certidoes cc2
                              WHERE cc2.empresa_id=cc.empresa_id
                                AND cc2.tipo_certidao_id=cc.tipo_certidao_id)
        """)

        # As tabelas de evidência são append-only. Nenhum endpoint da aplicação
        # pode apagar ou alterar uma consulta já registrada.
        cursor.executescript("""
        CREATE TRIGGER IF NOT EXISTS trg_consultas_certidoes_no_delete
        BEFORE DELETE ON consultas_certidoes
        BEGIN
            SELECT RAISE(ABORT, 'Historico de certidoes e imutavel: exclusao bloqueada.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_consultas_certidoes_no_update
        BEFORE UPDATE ON consultas_certidoes
        BEGIN
            SELECT RAISE(ABORT, 'Historico de certidoes e imutavel: alteracao bloqueada.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_certidoes_historico_no_delete
        BEFORE DELETE ON certidoes_historico
        BEGIN
            SELECT RAISE(ABORT, 'Historico permanente de certidoes e imutavel.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_certidoes_historico_no_update
        BEFORE UPDATE ON certidoes_historico
        BEGIN
            SELECT RAISE(ABORT, 'Historico permanente de certidoes e imutavel.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_certidoes_no_delete
        BEFORE DELETE ON certidoes
        BEGIN
            SELECT RAISE(ABORT, 'Certidoes nao podem ser excluidas; o historico e permanente.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_documento_versoes_certidao_no_delete
        BEFORE DELETE ON documento_versoes
        WHEN EXISTS (SELECT 1 FROM documentos d WHERE d.id=OLD.documento_id AND d.tipo='CERTIDAO_ESTADUAL_SEFAZ_PE')
        BEGIN
            SELECT RAISE(ABORT, 'Documentos de certidao nao podem ser excluidos.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_documentos_certidao_no_delete
        BEFORE DELETE ON documentos
        WHEN OLD.tipo='CERTIDAO_ESTADUAL_SEFAZ_PE'
        BEGIN
            SELECT RAISE(ABORT, 'Documentos de certidao nao podem ser excluidos.');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_empresas_no_delete_com_certidoes
        BEFORE DELETE ON empresas
        WHEN EXISTS (SELECT 1 FROM consultas_certidoes c WHERE c.empresa_id=OLD.id)
        BEGIN
            SELECT RAISE(ABORT, 'Empresa possui historico fiscal permanente e nao pode ser excluida.');
        END;
        """)
        conexao.commit()
        from app.services.auth_service import ensure_admin_user
        ensure_admin_user()
    finally:
        conexao.close()


def backup_banco_permanente() -> Path:
    """Cria uma cópia SQLite consistente, sem sobrescrever backups anteriores."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    agora = datetime.now()
    pasta = BACKUP_DIR / str(agora.year) / f"{agora.month:02d}"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"omega_{agora.strftime('%Y-%m-%d_%H%M%S_%f')}.sqlite3"
    origem = sqlite3.connect(DB_PATH, timeout=30)
    try:
        backup = sqlite3.connect(destino)
        try:
            origem.backup(backup)
            backup.execute("PRAGMA journal_mode=DELETE")
            backup.commit()
        finally:
            backup.close()
    finally:
        origem.close()
    return destino
