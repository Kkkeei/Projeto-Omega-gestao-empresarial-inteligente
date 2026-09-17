"""Cria e faz pequenas migrações das tabelas do módulo de Faturamento."""

import sqlite3

from app.db.database import conectar_banco


def _colunas(cursor, tabela: str) -> set[str]:
    return {
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({tabela})").fetchall()
    }


def criar_tabelas_faturamento() -> None:
    conn = conectar_banco()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS faturamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                competencia_ano INTEGER NOT NULL,
                competencia_mes INTEGER NOT NULL,
                valor REAL NOT NULL DEFAULT 0,
                observacao TEXT,
                usuario_id INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
            """
        )

        cursor.execute(
            """
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
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
            """
        )

        if "usuario_id" not in _colunas(cursor, "faturamentos"):
            cursor.execute(
                "ALTER TABLE faturamentos ADD COLUMN usuario_id INTEGER"
            )

        if "criado_em" not in _colunas(cursor, "faturamentos"):
            cursor.execute(
                "ALTER TABLE faturamentos ADD COLUMN criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )

        if "atualizado_em" not in _colunas(cursor, "faturamentos"):
            cursor.execute(
                "ALTER TABLE faturamentos ADD COLUMN atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_faturamentos_empresa_competencia
            ON faturamentos (empresa_id, competencia_ano, competencia_mes)
            """
        )

        try:
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_faturamentos_empresa_competencia
                ON faturamentos (empresa_id, competencia_ano, competencia_mes)
                """
            )
        except sqlite3.IntegrityError:
            # Se a base antiga já tiver duplicidades, não derruba o servidor.
            # O repository continua fazendo a validação antes do INSERT.
            print(
                "Aviso: não foi possível criar o índice único de faturamentos "
                "porque existem competências duplicadas na base atual."
            )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_declaracoes_faturamento_empresa
            ON declaracoes_faturamento (empresa_id, data_geracao)
            """
        )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    criar_tabelas_faturamento()
    print("Tabelas do Faturamento verificadas/criadas com sucesso.")


if __name__ == "__main__":
    main()
