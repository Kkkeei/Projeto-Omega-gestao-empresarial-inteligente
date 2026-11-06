from datetime import date
import hashlib
import mimetypes
import os
import secrets
from pathlib import Path
from fastapi import UploadFile

from . import repository
from .models import competencia_anterior
from .storage import garantir_diretorio_obrigacao, nome_seguro, STORAGE_ROOT


def validar_competencia(competencia: int) -> None:
    ano, mes = divmod(competencia, 100)
    if ano < 1900 or ano > 2999 or mes not in range(1, 13):
        raise ValueError("A competência deve estar no formato YYYYMM.")


def obter_status_modulo() -> dict[str, str | int]:
    """Retorna informações de disponibilidade sem criar tabelas implicitamente."""
    return {
        "modulo": "contabil",
        "status": "disponivel",
        "competencia_atual": competencia_anterior(),
    }


def exigir_empresa(empresa_id: int) -> dict:
    empresa = repository.obter_empresa(empresa_id)
    if empresa is None:
        raise LookupError("Empresa não encontrada.")
    return empresa


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx"}
MAX_UPLOAD_BYTES = int(os.getenv("OMEGA_CONTABIL_MAX_MB", "25")) * 1024 * 1024


def _require_competencia(value: int) -> None:
    validar_competencia(value)


def criar_categoria(empresa_id: int, nome: str, descricao: str | None, user_id: int):
    conn = repository.conectar_banco()
    try:
        if not repository.empresa_existe(empresa_id): raise LookupError("Empresa não encontrada.")
        nome = nome.strip()
        if not nome: raise ValueError("O nome da categoria é obrigatório.")
        ordem = conn.execute("SELECT COALESCE(MAX(ordem),0)+1 n FROM contabil_categorias WHERE empresa_id=?", (empresa_id,)).fetchone()["n"]
        cur = conn.execute("INSERT INTO contabil_categorias (empresa_id,nome,descricao,ordem,criado_por) VALUES (?,?,?,?,?)", (empresa_id,nome,descricao,ordem,user_id))
        repository.registrar_historico(conn, empresa_id, user_id, "CATEGORIA", cur.lastrowid, "CRIAR", {"nome": nome})
        conn.commit()
        return dict(conn.execute("SELECT *, CAST(ativo AS BOOLEAN) ativo FROM contabil_categorias WHERE id=?", (cur.lastrowid,)).fetchone())
    except Exception: conn.rollback(); raise
    finally: conn.close()


def atualizar_categoria(categoria_id: int, nome: str, descricao: str | None, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT * FROM contabil_categorias WHERE id=? AND ativo=1", (categoria_id,)).fetchone()
        if not row: raise LookupError("Categoria não encontrada.")
        anterior = dict(row)
        conn.execute("UPDATE contabil_categorias SET nome=?, descricao=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (nome.strip(), descricao, categoria_id))
        repository.registrar_historico(conn, row["empresa_id"], user_id, "CATEGORIA", categoria_id, "EDITAR", {"nome": nome, "descricao": descricao}, anterior)
        conn.commit()
        return dict(conn.execute("SELECT * FROM contabil_categorias WHERE id=?", (categoria_id,)).fetchone())
    finally: conn.close()


def arquivar_categoria(categoria_id: int, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT * FROM contabil_categorias WHERE id=? AND ativo=1", (categoria_id,)).fetchone()
        if not row: raise LookupError("Categoria não encontrada.")
        if conn.execute("SELECT 1 FROM contabil_documentos WHERE categoria_id=? LIMIT 1", (categoria_id,)).fetchone():
            raise ValueError("Não é possível arquivar uma categoria com documentos vinculados.")
        conn.execute("UPDATE contabil_categorias SET ativo=0, arquivado_em=CURRENT_TIMESTAMP WHERE id=?", (categoria_id,))
        repository.registrar_historico(conn, row["empresa_id"], user_id, "CATEGORIA", categoria_id, "ARQUIVAR")
        conn.commit()
        return {"ok": True}
    finally: conn.close()


def criar_documento(empresa_id: int, data, user_id: int):
    _require_competencia(data.competencia_inicio)
    exigir_empresa(empresa_id)
    conn = repository.conectar_banco()
    try:
        cat = conn.execute("SELECT 1 FROM contabil_categorias WHERE id=? AND empresa_id=? AND ativo=1", (data.categoria_id, empresa_id)).fetchone()
        if not cat: raise LookupError("Categoria não encontrada.")
        cur = conn.execute("INSERT INTO contabil_documentos (empresa_id,categoria_id,nome,observacao,competencia_inicio,criado_por,atualizado_por) VALUES (?,?,?,?,?,?,?)",
                           (empresa_id,data.categoria_id,data.nome.strip(),data.observacao,data.competencia_inicio,user_id,user_id))
        conn.execute("INSERT INTO contabil_obrigacoes (documento_id,empresa_id,competencia,criada_por) VALUES (?,?,?,?)", (cur.lastrowid,empresa_id,data.competencia_inicio,user_id))
        repository.registrar_historico(conn, empresa_id, user_id, "DOCUMENTO", cur.lastrowid, "CRIAR", {"nome": data.nome})
        conn.commit()
        return repository.documentacao(empresa_id, data.competencia_inicio, data.competencia_inicio // 100, user_id)["documentos"][-1]
    except Exception: conn.rollback(); raise
    finally: conn.close()


def atualizar_documento(documento_id: int, data, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT * FROM contabil_documentos WHERE id=? AND ativo=1", (documento_id,)).fetchone()
        if not row: raise LookupError("Documento não encontrado.")
        if not conn.execute("SELECT 1 FROM contabil_categorias WHERE id=? AND empresa_id=? AND ativo=1", (data.categoria_id,row["empresa_id"])).fetchone():
            raise LookupError("Categoria não encontrada.")
        conn.execute("UPDATE contabil_documentos SET nome=?, categoria_id=?, observacao=?, atualizado_por=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                     (data.nome.strip(),data.categoria_id,data.observacao,user_id,documento_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"DOCUMENTO",documento_id,"EDITAR",{"nome":data.nome,"categoria_id":data.categoria_id},dict(row))
        conn.commit()
        return repository.documentacao(row["empresa_id"], row["competencia_inicio"], row["competencia_inicio"] // 100, user_id)["documentos"][-1]
    finally: conn.close()


def inativar_documento(documento_id: int, data, user_id: int):
    _require_competencia(data.competencia_fim)
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT * FROM contabil_documentos WHERE id=? AND ativo=1", (documento_id,)).fetchone()
        if not row: raise LookupError("Documento não encontrado.")
        if data.competencia_fim < row["competencia_inicio"]: raise ValueError("A competência final é inválida.")
        conn.execute("UPDATE contabil_documentos SET competencia_fim=?, ativo=0, inativado_em=CURRENT_TIMESTAMP, motivo_inativacao=?, observacao_inativacao=?, atualizado_por=? WHERE id=?",
                     (data.competencia_fim,data.motivo,data.observacao,user_id,documento_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"DOCUMENTO",documento_id,"INATIVAR",{"competencia_fim":data.competencia_fim,"motivo":data.motivo})
        conn.commit()
        return {"id": documento_id, "ativo": False, "competencia_fim": data.competencia_fim}
    finally: conn.close()


def listar_arquivos(obrigacao_id: int):
    conn = repository.conectar_banco()
    try: return {"arquivos": [dict(r) for r in conn.execute("""SELECT a.*, u.nome enviado_por_nome FROM contabil_arquivos a LEFT JOIN usuarios u ON u.id=a.enviado_por WHERE a.obrigacao_id=? AND a.excluido_em IS NULL ORDER BY a.enviado_em DESC""",(obrigacao_id,)).fetchall()]}
    finally: conn.close()


def upload_arquivos(obrigacao_id: int, uploads: list[UploadFile], user_id: int):
    conn = repository.conectar_banco()
    written: list[Path] = []
    try:
        obligation = conn.execute("SELECT * FROM contabil_obrigacoes WHERE id=? AND cancelada_em IS NULL", (obrigacao_id,)).fetchone()
        if not obligation: raise LookupError("Obrigação não encontrada.")
        for upload in uploads:
            ext = Path(upload.filename or "").suffix.lower()
            if ext not in ALLOWED_EXTENSIONS: raise ValueError("Tipo de arquivo não permitido.")
            data = upload.file.read()
            if len(data) > MAX_UPLOAD_BYTES: raise ValueError("O arquivo excede o limite permitido.")
            if not data: raise ValueError("O arquivo está vazio.")
            if not _conteudo_compativel(ext, data):
                raise ValueError("O conteúdo do arquivo não corresponde ao tipo informado.")
            directory = garantir_diretorio_obrigacao(obligation["empresa_id"], obligation["competencia"], obrigacao_id)
            physical = directory / f"{secrets.token_hex(16)}{ext}"
            physical.write_bytes(data); written.append(physical)
            cur = conn.execute("""INSERT INTO contabil_arquivos
              (obrigacao_id,nome_original,nome_armazenado,caminho_storage,extensao,mime_type,tamanho,hash_sha256,enviado_por)
              VALUES (?,?,?,?,?,?,?,?,?)""",
              (obrigacao_id,nome_seguro(upload.filename or "arquivo"),physical.name,str(physical.relative_to(STORAGE_ROOT)),ext,upload.content_type or mimetypes.guess_type(upload.filename or "")[0],len(data),hashlib.sha256(data).hexdigest(),user_id))
            repository.registrar_historico(conn,obligation["empresa_id"],user_id,"ARQUIVO",cur.lastrowid,"UPLOAD",{"nome": upload.filename})
        conn.commit()
        return listar_arquivos(obrigacao_id)
    except Exception:
        conn.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise
    finally: conn.close()


def renomear_arquivo(arquivo_id: int, nome: str, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT a.*,o.empresa_id FROM contabil_arquivos a JOIN contabil_obrigacoes o ON o.id=a.obrigacao_id WHERE a.id=? AND a.excluido_em IS NULL",(arquivo_id,)).fetchone()
        if not row: raise LookupError("Arquivo não encontrado.")
        safe = nome_seguro(nome)
        conn.execute("UPDATE contabil_arquivos SET nome_original=? WHERE id=?",(safe,arquivo_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"ARQUIVO",arquivo_id,"RENOMEAR",{"nome":safe},{"nome":row["nome_original"]})
        conn.commit()
        return dict(conn.execute("SELECT * FROM contabil_arquivos WHERE id=?",(arquivo_id,)).fetchone())
    finally: conn.close()


def excluir_arquivo(arquivo_id: int, motivo: str | None, user_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT a.*,o.empresa_id FROM contabil_arquivos a JOIN contabil_obrigacoes o ON o.id=a.obrigacao_id WHERE a.id=? AND a.excluido_em IS NULL",(arquivo_id,)).fetchone()
        if not row: raise LookupError("Arquivo não encontrado.")
        conn.execute("UPDATE contabil_arquivos SET excluido_em=CURRENT_TIMESTAMP, excluido_por=?, motivo_exclusao=? WHERE id=?",(user_id,motivo,arquivo_id))
        repository.registrar_historico(conn,row["empresa_id"],user_id,"ARQUIVO",arquivo_id,"EXCLUIR",{"motivo":motivo})
        conn.commit(); return {"ok": True}
    finally: conn.close()


def obter_arquivo(arquivo_id: int):
    conn = repository.conectar_banco()
    try:
        row = conn.execute("SELECT a.*,o.empresa_id,o.competencia FROM contabil_arquivos a JOIN contabil_obrigacoes o ON o.id=a.obrigacao_id WHERE a.id=? AND a.excluido_em IS NULL",(arquivo_id,)).fetchone()
        return dict(row) if row else None
    finally: conn.close()


def _conteudo_compativel(ext: str, data: bytes) -> bool:
    if ext == ".pdf":
        return data.startswith(b"%PDF-")
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".xlsx":
        return data.startswith(b"PK\x03\x04")
    return False
