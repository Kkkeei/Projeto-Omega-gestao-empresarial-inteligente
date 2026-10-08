import os
import sqlite3
from datetime import datetime
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "omega.db"
DEFAULT_STORAGE_BASE = BASE_DIR.parent / "storage"

def _configured_db_path() -> Path:
    return Path(os.getenv("OMEGA_DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()

def _configured_storage_base() -> Path:
    return Path(os.getenv("OMEGA_STORAGE_PATH", str(DEFAULT_STORAGE_BASE))).expanduser().resolve()

# Mantemos constantes para módulos existentes, mas sempre derivadas do ambiente
# no momento do import. Testes configuram as variáveis antes de importar este módulo.
DB_PATH = _configured_db_path()
STORAGE_BASE = _configured_storage_base()
BACKUP_DIR = STORAGE_BASE / "backups" / "database"


def _sqlite_add_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add a column safely to SQLite legacy tables.

    SQLite does not allow non-constant defaults such as CURRENT_TIMESTAMP in
    ALTER TABLE ... ADD COLUMN. Add the column without that default and let
    the migration backfill existing rows explicitly.
    """
    safe_definition = definition
    if "DEFAULT CURRENT_TIMESTAMP" in safe_definition.upper():
        safe_definition = safe_definition.replace(" DEFAULT CURRENT_TIMESTAMP", "").replace(" default CURRENT_TIMESTAMP", "")
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {safe_definition}")


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

        CREATE TABLE IF NOT EXISTS faturamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            competencia_ano INTEGER NOT NULL,
            competencia_mes INTEGER NOT NULL,
            valor REAL NOT NULL DEFAULT 0,
            observacao TEXT,
            data_faturamento TEXT,
            periodicidade TEXT NOT NULL DEFAULT 'Mensal',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, competencia_ano, competencia_mes),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tributos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            sigla TEXT,
            esfera TEXT,
            categoria TEXT,
            periodicidade TEXT,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS empresa_impostos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tributo_id INTEGER NOT NULL,
            regime_tributario TEXT,
            obrigatorio INTEGER NOT NULL DEFAULT 1,
            vigencia_inicio TEXT,
            vigencia_fim TEXT,
            status TEXT NOT NULL DEFAULT 'ATIVO',
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, tributo_id, vigencia_inicio),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (tributo_id) REFERENCES tributos(id)
        );

        CREATE TABLE IF NOT EXISTS impostos_mensais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tributo_id INTEGER NOT NULL,
            competencia_ano INTEGER NOT NULL,
            competencia_mes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            valor REAL,
            data_vencimento TEXT,
            data_pagamento TEXT,
            numero_documento TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id, tributo_id, competencia_ano, competencia_mes),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (tributo_id) REFERENCES tributos(id)
        );

        CREATE TABLE IF NOT EXISTS documentos_impostos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imposto_mensal_id INTEGER NOT NULL,
            nome_arquivo TEXT NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            extensao TEXT,
            mime_type TEXT,
            tamanho INTEGER,
            hash_arquivo TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (imposto_mensal_id) REFERENCES impostos_mensais(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notificacoes_impostos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            imposto_mensal_id INTEGER,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT,
            prioridade TEXT NOT NULL DEFAULT 'NORMAL',
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            prazo TEXT,
            lida_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (imposto_mensal_id) REFERENCES impostos_mensais(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS declaracoes_faturamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            periodo_inicio TEXT NOT NULL,
            periodo_fim TEXT NOT NULL,
            valor_total REAL NOT NULL DEFAULT 0,
            nome_arquivo TEXT NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            usuario_id INTEGER,
            data_geracao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS banco_brasil_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL UNIQUE,
            percentual_a_vista REAL NOT NULL DEFAULT 20,
            percentual_a_prazo REAL NOT NULL DEFAULT 80,
            percentual_cartao REAL,
            percentual_cheque REAL,
            percentual_boleto REAL,
            prazo_medio_dias INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
        );

        """)


        # ================================================================
        # Certificados Digitais (A1/A3)
        # ================================================================
        # O armazenamento físico do A1 fica fora do banco e sempre
        # criptografado. O banco guarda apenas metadados e referências.
        # A3 nunca recebe chave privada/PFX/PIN.
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('A1','A3')),
            meio_armazenamento TEXT NOT NULL CHECK(meio_armazenamento IN ('PFX','CARTAO','TOKEN')),
            titular_tipo TEXT NOT NULL DEFAULT 'PJ' CHECK(titular_tipo IN ('PJ','PF','NAO_IDENTIFICADO')),
            nome_titular TEXT,
            documento_titular TEXT,
            emissor TEXT,
            numero_serie TEXT,
            thumbprint_sha256 TEXT,
            algoritmo TEXT,
            data_emissao TEXT,
            data_validade TEXT,
            status TEXT NOT NULL DEFAULT 'ATIVO' CHECK(status IN ('ATIVO','INATIVO','EXPIRADO','NAO_VINCULADO')),
            apto_para_uso INTEGER NOT NULL DEFAULT 1,
            storage_ref TEXT,
            arquivo_nome TEXT,
            dispositivo_modelo TEXT,
            dispositivo_identificador TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS certificado_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificado_id INTEGER NOT NULL,
            tipo_evento TEXT NOT NULL,
            usuario_id INTEGER,
            descricao TEXT,
            dados TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificado_id) REFERENCES certificados(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS certificado_uso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificado_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            ultima_utilizacao TEXT,
            quantidade_usos INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'ATIVO',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(certificado_id, modulo),
            FOREIGN KEY (certificado_id) REFERENCES certificados(id) ON DELETE CASCADE
        );

        """)

        # Migrations do módulo Certificados. CREATE TABLE IF NOT EXISTS não
        # altera tabelas já existentes; portanto, bancos legados precisam
        # receber explicitamente as novas colunas antes de qualquer consulta.
        colunas_certificados = {r[1] for r in conexao.execute("PRAGMA table_info(certificados)").fetchall()}
        for coluna, tipo in (
            ("apto_para_uso", "INTEGER NOT NULL DEFAULT 1"),
            ("storage_ref", "TEXT"),
            ("arquivo_nome", "TEXT"),
            ("dispositivo_modelo", "TEXT"),
            ("dispositivo_identificador", "TEXT"),
            ("thumbprint_sha256", "TEXT"),
            ("algoritmo", "TEXT"),
            ("data_emissao", "TEXT"),
            ("data_validade", "TEXT"),
            ("status", "TEXT NOT NULL DEFAULT 'ATIVO'"),
            ("titular_tipo", "TEXT NOT NULL DEFAULT 'PJ'"),
            ("nome_titular", "TEXT"),
            ("documento_titular", "TEXT"),
            ("emissor", "TEXT"),
            ("numero_serie", "TEXT"),
            ("meio_armazenamento", "TEXT NOT NULL DEFAULT 'PFX'"),
            ("tipo", "TEXT NOT NULL DEFAULT 'A1'"),
            ("criado_por", "INTEGER"),
            ("criado_em", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
            ("atualizado_em", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ):
            if coluna not in colunas_certificados:
                _sqlite_add_column(cursor, "certificados", coluna, tipo)
                if coluna in {"criado_em", "atualizado_em"}:
                    cursor.execute(f"UPDATE certificados SET {coluna}=CURRENT_TIMESTAMP WHERE {coluna} IS NULL OR TRIM({coluna})='' ")

        # Bancos antigos também podem ter as tabelas de histórico/uso com
        # estrutura parcial. Adicione somente colunas ausentes, sem apagar dados.
        for tabela, colunas in {
            "certificado_eventos": (
                ("tipo_evento", "TEXT NOT NULL DEFAULT 'REGISTRO'"),
                ("usuario_id", "INTEGER"),
                ("descricao", "TEXT"),
                ("dados", "TEXT"),
                ("criado_em", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
            ),
            "certificado_uso": (
                ("modulo", "TEXT NOT NULL DEFAULT 'GERAL'"),
                ("ultima_utilizacao", "TEXT"),
                ("quantidade_usos", "INTEGER NOT NULL DEFAULT 0"),
                ("status", "TEXT NOT NULL DEFAULT 'ATIVO'"),
                ("criado_em", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
                ("atualizado_em", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
            ),
        }.items():
            colunas_existentes = {r[1] for r in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()}
            for coluna, tipo in colunas:
                if coluna not in colunas_existentes:
                    _sqlite_add_column(cursor, tabela, coluna, tipo)
                    if coluna in {"criado_em", "atualizado_em"}:
                        cursor.execute(f"UPDATE {tabela} SET {coluna}=CURRENT_TIMESTAMP WHERE {coluna} IS NULL OR TRIM({coluna})='' ")

        cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_certificados_empresa ON certificados(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_certificados_status ON certificados(status);
        CREATE INDEX IF NOT EXISTS idx_certificados_validade ON certificados(data_validade);
        CREATE INDEX IF NOT EXISTS idx_certificado_eventos_certificado ON certificado_eventos(certificado_id);
        CREATE INDEX IF NOT EXISTS idx_certificado_uso_certificado ON certificado_uso(certificado_id);
        """)

        # Pessoas físicas são entidades próprias. Não criamos empresa fictícia
        # para representar CPF: certificados PF ficam em tabelas próprias,
        # preservando integralmente o modelo PJ existente.
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS pessoas_fisicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS certificados_pf (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('A1','A3')),
            meio_armazenamento TEXT NOT NULL CHECK(meio_armazenamento IN ('PFX','CARTAO','TOKEN')),
            nome_titular TEXT NOT NULL,
            documento_titular TEXT NOT NULL,
            emissor TEXT,
            numero_serie TEXT,
            thumbprint_sha256 TEXT,
            algoritmo TEXT,
            data_emissao TEXT,
            data_validade TEXT,
            status TEXT NOT NULL DEFAULT 'ATIVO' CHECK(status IN ('ATIVO','INATIVO','EXPIRADO','NAO_VINCULADO')),
            apto_para_uso INTEGER NOT NULL DEFAULT 1,
            storage_ref TEXT,
            arquivo_nome TEXT,
            dispositivo_modelo TEXT,
            dispositivo_identificador TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pessoa_id) REFERENCES pessoas_fisicas(id) ON DELETE CASCADE,
            FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS certificado_pf_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificado_id INTEGER NOT NULL,
            tipo_evento TEXT NOT NULL,
            usuario_id INTEGER,
            descricao TEXT,
            dados TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificado_id) REFERENCES certificados_pf(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS certificado_pf_uso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificado_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            ultima_utilizacao TEXT,
            quantidade_usos INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'ATIVO',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(certificado_id, modulo),
            FOREIGN KEY (certificado_id) REFERENCES certificados_pf(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_pessoas_fisicas_cpf ON pessoas_fisicas(cpf);
        CREATE INDEX IF NOT EXISTS idx_certificados_pf_pessoa ON certificados_pf(pessoa_id);
        CREATE INDEX IF NOT EXISTS idx_certificados_pf_status ON certificados_pf(status);
        CREATE INDEX IF NOT EXISTS idx_certificados_pf_validade ON certificados_pf(data_validade);
        CREATE INDEX IF NOT EXISTS idx_certificado_pf_eventos_certificado ON certificado_pf_eventos(certificado_id);
        CREATE INDEX IF NOT EXISTS idx_certificado_pf_uso_certificado ON certificado_pf_uso(certificado_id);
        """)

        # Migrations for Faturamento. Nunca remover dados existentes.
        colunas_faturamentos = {r[1] for r in conexao.execute("PRAGMA table_info(faturamentos)").fetchall()}
        if "data_faturamento" not in colunas_faturamentos:
            cursor.execute("ALTER TABLE faturamentos ADD COLUMN data_faturamento TEXT")
        if "periodicidade" not in colunas_faturamentos:
            cursor.execute("ALTER TABLE faturamentos ADD COLUMN periodicidade TEXT NOT NULL DEFAULT 'Mensal'")
        # Registros legados recebem como data o primeiro dia da própria competência.
        cursor.execute(
            """
            UPDATE faturamentos
               SET data_faturamento = printf('%04d-%02d-01', competencia_ano, competencia_mes)
             WHERE data_faturamento IS NULL OR TRIM(data_faturamento) = ''
            """
        )

        # Migrations for Documentação. Never remove legacy data.
        # These changes must happen before creating indexes on the new columns.
        # Migrations do módulo Impostos. Nunca remover dados existentes.
        colunas_doc_imp = {r[1] for r in conexao.execute("PRAGMA table_info(documentos_impostos)").fetchall()}
        for coluna, tipo in (
            ("competencia_extraida", "TEXT"),
            ("valor_extraido", "REAL"),
            ("vencimento_extraido", "TEXT"),
            ("codigo_receita", "TEXT"),
            ("cnpj_extraido", "TEXT"),
            ("data_pagamento_extraida", "TEXT"),
            ("periodo_apuracao_inicio", "TEXT"),
            ("periodo_apuracao_fim", "TEXT"),
            ("mensagem_cliente", "TEXT"),
            ("enviado_em", "TEXT"),
            ("usuario_upload_id", "INTEGER"),
            ("status_documento", "TEXT NOT NULL DEFAULT 'CONFIRMADO'"),
        ):
            if coluna not in colunas_doc_imp:
                cursor.execute(f"ALTER TABLE documentos_impostos ADD COLUMN {coluna} {tipo}")

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS impostos_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imposto_mensal_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            tributo_id INTEGER NOT NULL,
            competencia_ano INTEGER NOT NULL,
            competencia_mes INTEGER NOT NULL,
            acao TEXT NOT NULL,
            status_anterior TEXT,
            status_novo TEXT,
            valor_anterior REAL,
            valor_novo REAL,
            dados_anteriores TEXT,
            dados_novos TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (imposto_mensal_id) REFERENCES impostos_mensais(id) ON DELETE CASCADE,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (tributo_id) REFERENCES tributos(id)
        );

        CREATE TABLE IF NOT EXISTS impostos_notificacoes_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publico TEXT NOT NULL UNIQUE,
            guia_enviada INTEGER NOT NULL DEFAULT 1,
            antes_vencimento INTEGER NOT NULL DEFAULT 1,
            dias_antes INTEGER NOT NULL DEFAULT 5,
            dia_vencimento INTEGER NOT NULL DEFAULT 1,
            nao_pagamento INTEGER NOT NULL DEFAULT 1,
            imposto_vencido INTEGER NOT NULL DEFAULT 1,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS impostos_notificacoes_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            imposto_mensal_id INTEGER,
            publico TEXT NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT,
            agendado_para TEXT,
            status TEXT NOT NULL DEFAULT 'PROGRAMADA',
            enviado_em TEXT,
            erro TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
            FOREIGN KEY (imposto_mensal_id) REFERENCES impostos_mensais(id) ON DELETE SET NULL
        );
        """)

        cursor.execute("INSERT OR IGNORE INTO impostos_notificacoes_config (publico, imposto_vencido) VALUES ('CLIENTE', 0)")
        cursor.execute("INSERT OR IGNORE INTO impostos_notificacoes_config (publico, imposto_vencido) VALUES ('CONTABILIDADE', 1)")
        cursor.execute("UPDATE impostos_notificacoes_config SET imposto_vencido=0 WHERE publico='CLIENTE'")

        colunas_documentos = {r[1] for r in conexao.execute("PRAGMA table_info(documentos)").fetchall()}
        if "categoria_id" not in colunas_documentos:
            cursor.execute("ALTER TABLE documentos ADD COLUMN categoria_id INTEGER")

        colunas_versoes = {r[1] for r in conexao.execute("PRAGMA table_info(documento_versoes)").fetchall()}
        for coluna, tipo in (("mime_type", "TEXT"), ("usuario_upload_id", "INTEGER"), ("tamanho", "INTEGER"), ("hash_arquivo", "TEXT")):
            if coluna not in colunas_versoes:
                cursor.execute(f"ALTER TABLE documento_versoes ADD COLUMN {coluna} {tipo}")

        # All indexes are created only after compatibility migrations.
        cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_tributos_ativo ON tributos(ativo);
        CREATE INDEX IF NOT EXISTS idx_empresa_impostos_empresa ON empresa_impostos(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_empresa_impostos_tributo ON empresa_impostos(tributo_id);
        CREATE INDEX IF NOT EXISTS idx_impostos_mensais_competencia ON impostos_mensais(empresa_id, competencia_ano, competencia_mes);
        CREATE INDEX IF NOT EXISTS idx_impostos_mensais_status ON impostos_mensais(status);
        CREATE INDEX IF NOT EXISTS idx_documentos_impostos_mensal ON documentos_impostos(imposto_mensal_id);
        CREATE INDEX IF NOT EXISTS idx_notificacoes_impostos_empresa ON notificacoes_impostos(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_impostos_historico_mensal ON impostos_historico(imposto_mensal_id);
        CREATE INDEX IF NOT EXISTS idx_impostos_historico_empresa ON impostos_historico(empresa_id, criado_em);
        CREATE INDEX IF NOT EXISTS idx_impostos_notif_eventos_empresa ON impostos_notificacoes_eventos(empresa_id, agendado_para);
        CREATE INDEX IF NOT EXISTS idx_impostos_notif_eventos_mensal ON impostos_notificacoes_eventos(imposto_mensal_id);
        CREATE INDEX IF NOT EXISTS idx_impostos_notif_config_publico ON impostos_notificacoes_config(publico);


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
        CREATE INDEX IF NOT EXISTS idx_faturamentos_empresa_competencia ON faturamentos(empresa_id, competencia_ano, competencia_mes);
        CREATE INDEX IF NOT EXISTS idx_declaracoes_faturamento_empresa_data ON declaracoes_faturamento(empresa_id, data_geracao);
        CREATE INDEX IF NOT EXISTS idx_banco_brasil_config_empresa ON banco_brasil_config(empresa_id);
        CREATE INDEX IF NOT EXISTS idx_auditorias_entidade ON auditorias(entidade, entidade_id);
        CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_usuario ON tokens_redefinicao_senha(usuario_id);
        CREATE INDEX IF NOT EXISTS idx_reset_tokens_expira ON tokens_redefinicao_senha(expira_em);
        CREATE INDEX IF NOT EXISTS idx_automacao_locks_expira ON automacao_locks(expira_em);
        CREATE INDEX IF NOT EXISTS idx_faturamentos_empresa_competencia ON faturamentos(empresa_id, competencia_ano, competencia_mes);
        CREATE INDEX IF NOT EXISTS idx_faturamentos_competencia ON faturamentos(competencia_ano, competencia_mes);
        CREATE INDEX IF NOT EXISTS idx_declaracoes_faturamento_empresa ON declaracoes_faturamento(empresa_id, data_geracao);
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

    try:
        retention = max(0, int(os.getenv("OMEGA_BACKUP_RETENTION", "100")))
    except ValueError:
        retention = 100
    if retention:
        arquivos = sorted(BACKUP_DIR.rglob("*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
        for antigo in arquivos[retention:]:
            try:
                antigo.unlink()
            except OSError:
                pass
    return destino
