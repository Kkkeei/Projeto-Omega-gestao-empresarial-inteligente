from datetime import datetime
from app.db.database import conectar_banco


def listar(empresa_id=None, status=None):
    conexao = conectar_banco()
    try:
        sql = "SELECT * FROM pendencias WHERE 1=1"
        params = []
        if empresa_id is not None:
            sql += " AND empresa_id = ?"; params.append(empresa_id)
        if status:
            sql += " AND status = ?"; params.append(status)
        sql += " ORDER BY CASE prioridade WHEN 'ALTA' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END, id DESC"
        return [dict(r) for r in conexao.execute(sql, params).fetchall()]
    finally:
        conexao.close()


def criar(dados):
    conexao = conectar_banco()
    try:
        if not conexao.execute("SELECT id FROM empresas WHERE id=?", (dados["empresa_id"],)).fetchone():
            raise LookupError("Empresa não encontrada.")
        cur = conexao.execute("""
            INSERT INTO pendencias (empresa_id,tipo,origem,titulo,descricao,status,prioridade,data_identificacao,prazo,observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, tuple(dados.get(k) for k in ["empresa_id","tipo","origem","titulo","descricao","status","prioridade","data_identificacao","prazo","observacao"]))
        conexao.commit()
        return dict(conexao.execute("SELECT * FROM pendencias WHERE id=?", (cur.lastrowid,)).fetchone())
    finally:
        conexao.close()


def atualizar(pendencia_id, dados):
    conexao = conectar_banco()
    try:
        atual = conexao.execute("SELECT * FROM pendencias WHERE id=?", (pendencia_id,)).fetchone()
        if not atual: raise LookupError("Pendência não encontrada.")
        dados = {k:v for k,v in dados.items() if v is not None}
        if dados.get("status") == "RESOLVIDA" and not dados.get("data_resolucao"):
            dados["data_resolucao"] = datetime.now().strftime("%Y-%m-%d")
        if dados:
            sets = ", ".join(f"{k}=?" for k in dados)
            conexao.execute(f"UPDATE pendencias SET {sets}, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (*dados.values(), pendencia_id))
            conexao.commit()
        return dict(conexao.execute("SELECT * FROM pendencias WHERE id=?", (pendencia_id,)).fetchone())
    finally:
        conexao.close()
