import json
from datetime import datetime
from app.db.database import conectar_banco


TIPOS = {
    "SINCRONIZACAO_EMPRESA": "Sincronização cadastral da empresa",
    "CONSULTA_CERTIDAO": "Consulta de certidão",
}


def executar(dados):
    conexao = conectar_banco()
    try:
        if dados.get("empresa_id") and not conexao.execute("SELECT id FROM empresas WHERE id=?", (dados["empresa_id"],)).fetchone():
            raise LookupError("Empresa não encontrada.")
        tipo = dados["tipo"]
        if tipo not in TIPOS:
            raise ValueError(f"Tipo de automação não suportado no MVP: {tipo}")
        cur = conexao.execute("""
            INSERT INTO execucoes_automacao (automacao_id,empresa_id,tipo,status,mensagem,resultado,origem)
            VALUES (?,?,?,?,?,?,?)
        """, (dados.get("automacao_id"), dados.get("empresa_id"), tipo, "CONCLUÍDA", "Execução registrada pelo núcleo do MVP.", json.dumps(dados.get("configuracao") or {}, ensure_ascii=False), "API"))
        exec_id = cur.lastrowid
        conexao.execute("UPDATE execucoes_automacao SET fim=CURRENT_TIMESTAMP WHERE id=?", (exec_id,))
        conexao.commit()
        return dict(conexao.execute("SELECT * FROM execucoes_automacao WHERE id=?", (exec_id,)).fetchone())
    finally:
        conexao.close()


def historico(empresa_id=None):
    conexao = conectar_banco()
    try:
        sql = "SELECT * FROM execucoes_automacao WHERE 1=1"; params=[]
        if empresa_id is not None:
            sql += " AND empresa_id=?"; params.append(empresa_id)
        sql += " ORDER BY id DESC"
        return [dict(r) for r in conexao.execute(sql, params).fetchall()]
    finally:
        conexao.close()
