from app.db.database import conectar_banco


def resumo():
    conexao = conectar_banco()
    try:
        total = conexao.execute("SELECT COUNT(*) AS n FROM empresas").fetchone()["n"]
        ativas = conexao.execute("SELECT COUNT(*) AS n FROM empresas WHERE ativo=1").fetchone()["n"]
        pendencias_abertas = conexao.execute("""
            SELECT COUNT(*) AS n FROM pendencias
            WHERE UPPER(TRIM(COALESCE(status, ''))) NOT IN
                  ('RESOLVIDA', 'RESOLVIDO', 'FECHADA', 'FECHADO')
        """).fetchone()["n"]
        regulares = conexao.execute("""
            SELECT COUNT(DISTINCT c.empresa_id) AS n
            FROM certidoes c JOIN empresas e ON e.id=c.empresa_id
            WHERE e.ativo=1 AND UPPER(TRIM(COALESCE(c.situacao, '')))='REGULAR'
        """).fetchone()["n"]
        vencidas = conexao.execute("""
            SELECT COUNT(*) AS n FROM certidoes c
            JOIN empresas e ON e.id=c.empresa_id
            WHERE e.ativo=1 AND c.data_validade IS NOT NULL
              AND date(c.data_validade)<date('now')
        """).fetchone()["n"]
        proximas = conexao.execute("""
            SELECT COUNT(*) AS n FROM certidoes c
            JOIN empresas e ON e.id=c.empresa_id
            WHERE e.ativo=1 AND c.data_validade IS NOT NULL
              AND date(c.data_validade)>=date('now')
              AND date(c.data_validade)<=date('now','+30 day')
        """).fetchone()["n"]
        automacoes = conexao.execute("""
            SELECT COUNT(*) AS n FROM execucoes_automacao
            WHERE UPPER(REPLACE(TRIM(COALESCE(status, '')), ' ', '_'))
                  IN ('EXECUTANDO','EM_EXECUCAO','PENDENTE','PROCESSANDO')
        """).fetchone()["n"]
        return {
            "empresas_total": total,
            "empresas": total,
            "empresas_ativas": ativas,
            "empresas_inativas": total - ativas,
            "empresas_regulares": regulares,
            "pendencias_abertas": pendencias_abertas,
            "certidoes_vencidas": vencidas,
            "certidoes_proximas_vencimento": proximas,
            "automacoes_em_andamento": automacoes,
        }
    finally:
        conexao.close()
