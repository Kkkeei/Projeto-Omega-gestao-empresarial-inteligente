from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.db.database import BASE_DIR, STORAGE_BASE, conectar_banco

STORAGE_ROOT = STORAGE_BASE / "documentos" / "empresas"
DEFAULT_CATEGORIES = [
    ("Societário", "Contratos, alterações, QSA, atos e certidões societárias."),
    ("Pessoal (Sócio)", "Documentos pessoais e cadastrais dos sócios."),
    ("IRPF", "Declarações, recibos e documentos de Imposto de Renda da pessoa física."),
]
MAX_UPLOAD_MB = int(os.getenv("OMEGA_DOCUMENTO_MAX_MB", "25"))


def _safe_name(value: str) -> str:
    value = re.sub(r"[^\w\-.() ]+", "_", value, flags=re.UNICODE).strip()
    return value[:160] or "documento"


def _category_storage_path(empresa_id: int, categoria_id: int) -> Path:
    """Diretório físico estável da categoria.

    O caminho usa IDs estáveis, nunca o nome exibido da pasta. Assim, renomear uma
    pasta não quebra documentos existentes e a hierarquia lógica continua no banco.
    """
    return STORAGE_ROOT / str(empresa_id) / str(categoria_id)


def _ensure_category_directory(empresa_id: int, categoria_id: int) -> Path:
    path = _category_storage_path(empresa_id, categoria_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_default_categories(conexao, empresa_id: int) -> None:
    """Garante as categorias iniciais e seus diretórios físicos."""
    rows = conexao.execute(
        "SELECT id FROM categorias_documentos WHERE empresa_id=? LIMIT 1",
        (empresa_id,),
    ).fetchall()
    if not rows:
        for ordem, (nome, descricao) in enumerate(DEFAULT_CATEGORIES, start=1):
            cur = conexao.execute(
                "INSERT INTO categorias_documentos (empresa_id, categoria_pai_id, nome, descricao, ordem, ativo) VALUES (?, NULL, ?, ?, ?, 1)",
                (empresa_id, nome, descricao, ordem),
            )
            _ensure_category_directory(empresa_id, int(cur.lastrowid))
        return

    # Corrige instalações antigas em que a categoria existia no banco, mas o
    # diretório físico ainda não havia sido criado.
    for row in conexao.execute(
        "SELECT id FROM categorias_documentos WHERE empresa_id=? AND ativo=1",
        (empresa_id,),
    ).fetchall():
        _ensure_category_directory(empresa_id, int(row["id"]))


def _empresa_exists(conexao, empresa_id: int) -> bool:
    return conexao.execute("SELECT 1 FROM empresas WHERE id=?", (empresa_id,)).fetchone() is not None


def listar_empresas_documentacao(q: str | None, regime: str | None, ativo: bool | None, page: int, page_size: int):
    page = max(1, page)
    page_size = min(500, max(1, page_size))
    offset = (page - 1) * page_size
    filtros = []
    params: list[Any] = []
    if q:
        termo = f"%{q.strip()}%"
        filtros.append("(e.razao_social LIKE ? OR COALESCE(e.nome_fantasia,'') LIKE ? OR e.cnpj LIKE ? OR COALESCE(e.inscricao_estadual,'') LIKE ? OR COALESCE(e.nire,'') LIKE ?)")
        params.extend([termo, termo, termo, termo, termo])
    if regime and regime.upper() != "TODOS":
        filtros.append("UPPER(COALESCE(e.regime_tributario,'')) = UPPER(?)")
        params.append(regime)
    if ativo is not None:
        filtros.append("e.ativo = ?")
        params.append(1 if ativo else 0)
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    conexao = conectar_banco()
    try:
        total = conexao.execute(f"SELECT COUNT(*) c FROM empresas e{where}", params).fetchone()["c"]
        rows = conexao.execute(
            f"""
            SELECT e.id,e.razao_social,e.nome_fantasia,e.cnpj,e.regime_tributario,e.ativo,
                   e.municipio,e.uf,
                   (SELECT COUNT(*) FROM documentos d WHERE d.empresa_id=e.id AND d.ativo=1 AND d.categoria_id IS NOT NULL) AS documentos_count
              FROM empresas e
              {where}
             ORDER BY UPPER(e.razao_social) ASC
             LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()
        return {"total": total, "page": page, "page_size": page_size, "empresas": [dict(r) for r in rows]}
    finally:
        conexao.close()


def listar_categorias(empresa_id: int):
    """Retorna a árvore inteira da empresa para permitir navegação por níveis."""
    conexao = conectar_banco()
    try:
        if not _empresa_exists(conexao, empresa_id):
            raise LookupError("Empresa não encontrada.")

        ensure_default_categories(conexao, empresa_id)
        conexao.commit()
        rows = conexao.execute(
            """
            SELECT c.id,c.empresa_id,c.categoria_pai_id,c.nome,c.descricao,c.ordem,c.ativo,
                   (SELECT COUNT(*) FROM documentos d WHERE d.categoria_id=c.id AND d.ativo=1) AS documentos_count,
                   (SELECT COUNT(*) FROM categorias_documentos child WHERE child.categoria_pai_id=c.id AND child.ativo=1) AS subpastas_count
              FROM categorias_documentos c
             WHERE c.empresa_id=?
               AND c.ativo=1
             ORDER BY COALESCE(c.categoria_pai_id,0), c.ordem, UPPER(c.nome)
            """,
            (empresa_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conexao.close()


def criar_categoria(empresa_id: int, nome: str, descricao: str | None, categoria_pai_id: int | None = None):
    nome = nome.strip()
    descricao = descricao.strip() if descricao else None
    if not nome:
        raise ValueError("O nome da pasta é obrigatório.")

    conexao = conectar_banco()
    created_dir: Path | None = None
    try:
        if not _empresa_exists(conexao, empresa_id):
            raise LookupError("Empresa não encontrada.")

        if categoria_pai_id is not None:
            parent = conexao.execute(
                "SELECT id FROM categorias_documentos WHERE id=? AND empresa_id=? AND ativo=1",
                (categoria_pai_id, empresa_id),
            ).fetchone()
            if not parent:
                raise ValueError("Pasta pai inválida.")

        exists = conexao.execute(
            """
            SELECT id
              FROM categorias_documentos
             WHERE empresa_id=?
               AND ativo=1
               AND ((categoria_pai_id=? ) OR (categoria_pai_id IS NULL AND ? IS NULL))
               AND UPPER(nome)=UPPER(?)
             LIMIT 1
            """,
            (empresa_id, categoria_pai_id, categoria_pai_id, nome),
        ).fetchone()
        if exists:
            raise ValueError("Já existe uma pasta com esse nome neste local.")

        ordem = conexao.execute(
            """
            SELECT COALESCE(MAX(ordem),0)+1 o
              FROM categorias_documentos
             WHERE empresa_id=?
               AND ((categoria_pai_id=? ) OR (categoria_pai_id IS NULL AND ? IS NULL))
            """,
            (empresa_id, categoria_pai_id, categoria_pai_id),
        ).fetchone()["o"]

        cur = conexao.execute(
            "INSERT INTO categorias_documentos (empresa_id,categoria_pai_id,nome,descricao,ordem,ativo) VALUES (?,?,?,?,?,1)",
            (empresa_id,categoria_pai_id,nome,descricao,ordem),
        )
        categoria_id = int(cur.lastrowid)
        # A criação da categoria só é confirmada se o diretório físico também puder
        # ser criado. Isso elimina a divergência "pasta no banco / sem pasta no disco".
        created_dir = _ensure_category_directory(empresa_id, categoria_id)

        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_novos,origem) VALUES (?,?,?,?,?)",
            (
                "CATEGORIA_DOCUMENTO",
                categoria_id,
                "CRIAR",
                json.dumps(
                    {"empresa_id": empresa_id, "categoria_pai_id": categoria_pai_id, "nome": nome},
                    ensure_ascii=False,
                ),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
        return dict(conexao.execute("SELECT * FROM categorias_documentos WHERE id=?", (categoria_id,)).fetchone())
    except Exception:
        conexao.rollback()
        if created_dir is not None:
            try:
                created_dir.rmdir()
            except OSError:
                pass
        raise
    finally:
        conexao.close()


def atualizar_categoria(categoria_id: int, nome: str, descricao: str | None, user_id: int | None = None):
    nome = nome.strip()
    descricao = descricao.strip() if descricao else None
    if not nome:
        raise ValueError("O nome da pasta é obrigatório.")

    conexao = conectar_banco()
    try:
        categoria = conexao.execute(
            "SELECT * FROM categorias_documentos WHERE id=?",
            (categoria_id,),
        ).fetchone()
        if not categoria:
            raise LookupError("Pasta não encontrada.")
        if not categoria["ativo"]:
            raise LookupError("A pasta está arquivada.")

        existente = conexao.execute(
            """
            SELECT id
              FROM categorias_documentos
             WHERE empresa_id=?
               AND ativo=1
               AND ((categoria_pai_id=? ) OR (categoria_pai_id IS NULL AND ? IS NULL))
               AND UPPER(nome)=UPPER(?)
               AND id<>?
             LIMIT 1
            """,
            (categoria["empresa_id"], categoria["categoria_pai_id"], categoria["categoria_pai_id"], nome, categoria_id),
        ).fetchone()
        if existente:
            raise ValueError("Já existe outra pasta com esse nome neste local.")

        conexao.execute(
            """
            UPDATE categorias_documentos
               SET nome=?, descricao=?, atualizado_em=CURRENT_TIMESTAMP
             WHERE id=?
            """,
            (nome, descricao, categoria_id),
        )
        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)",
            (
                "CATEGORIA_DOCUMENTO",
                categoria_id,
                "EDITAR",
                json.dumps(dict(categoria), ensure_ascii=False),
                json.dumps({"nome": nome, "descricao": descricao, "usuario_id": user_id}, ensure_ascii=False),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
        row = conexao.execute(
            """
            SELECT c.id,c.empresa_id,c.categoria_pai_id,c.nome,c.descricao,c.ordem,c.ativo,
                   (SELECT COUNT(*) FROM documentos d WHERE d.categoria_id=c.id AND d.ativo=1) AS documentos_count,
                   (SELECT COUNT(*) FROM categorias_documentos child WHERE child.categoria_pai_id=c.id AND child.ativo=1) AS subpastas_count
              FROM categorias_documentos c
             WHERE c.id=?
            """,
            (categoria_id,),
        ).fetchone()
        return dict(row)
    finally:
        conexao.close()


def _descendant_category_ids(conexao, categoria_id: int) -> list[int]:
    rows = conexao.execute(
        "SELECT id FROM categorias_documentos WHERE categoria_pai_id=? AND ativo=1 ORDER BY ordem, id",
        (categoria_id,),
    ).fetchall()
    ids = [int(row["id"]) for row in rows]
    for child_id in list(ids):
        ids.extend(_descendant_category_ids(conexao, child_id))
    return ids


def arquivar_categoria(categoria_id: int, user_id: int | None = None):
    conexao = conectar_banco()
    try:
        categoria = conexao.execute("SELECT * FROM categorias_documentos WHERE id=?", (categoria_id,)).fetchone()
        if not categoria:
            raise LookupError("Pasta não encontrada.")
        if not categoria["ativo"]:
            return dict(categoria)

        category_ids = [categoria_id] + _descendant_category_ids(conexao, categoria_id)
        placeholders = ",".join("?" for _ in category_ids)
        documentos = conexao.execute(
            f"SELECT id,nome FROM documentos WHERE categoria_id IN ({placeholders}) AND ativo=1",
            category_ids,
        ).fetchall()

        conexao.execute(
            f"UPDATE categorias_documentos SET ativo=0,arquivado_em=CURRENT_TIMESTAMP,atualizado_em=CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
            category_ids,
        )
        if documentos:
            doc_ids = [int(doc["id"]) for doc in documentos]
            doc_placeholders = ",".join("?" for _ in doc_ids)
            conexao.execute(
                f"UPDATE documentos SET ativo=0,atualizado_em=CURRENT_TIMESTAMP WHERE id IN ({doc_placeholders})",
                doc_ids,
            )
            for doc_id in doc_ids:
                conexao.execute(
                    "INSERT INTO auditorias (entidade,entidade_id,acao,dados_novos,origem) VALUES (?,?,?,?,?)",
                    (
                        "DOCUMENTO",
                        doc_id,
                        "ARQUIVADO_PELA_PASTA",
                        json.dumps({"categoria_id": categoria_id, "usuario_id": user_id}, ensure_ascii=False),
                        "DOCUMENTACAO",
                    ),
                )

        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)",
            (
                "CATEGORIA_DOCUMENTO",
                categoria_id,
                "ARQUIVAR",
                json.dumps(dict(categoria), ensure_ascii=False),
                json.dumps(
                    {"usuario_id": user_id, "categorias_arquivadas": category_ids, "documentos_arquivados": len(documentos)},
                    ensure_ascii=False,
                ),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
        result = dict(conexao.execute("SELECT * FROM categorias_documentos WHERE id=?", (categoria_id,)).fetchone())
        result["categorias_arquivadas"] = len(category_ids)
        result["documentos_arquivados"] = len(documentos)
        return result
    finally:
        conexao.close()


def arquivar_documento(documento_id: int, user_id: int | None = None):
    conexao = conectar_banco()
    try:
        documento = conexao.execute("SELECT * FROM documentos WHERE id=?", (documento_id,)).fetchone()
        if not documento:
            raise LookupError("Documento não encontrado.")
        if not documento["ativo"]:
            return dict(documento)
        conexao.execute("UPDATE documentos SET ativo=0,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (documento_id,))
        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)",
            (
                "DOCUMENTO",
                documento_id,
                "ARQUIVAR",
                json.dumps(dict(documento), ensure_ascii=False),
                json.dumps({"usuario_id": user_id}, ensure_ascii=False),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
        return dict(conexao.execute("SELECT * FROM documentos WHERE id=?", (documento_id,)).fetchone())
    finally:
        conexao.close()


def listar_documentos(empresa_id: int, categoria_id: int | None = None):
    conexao = conectar_banco()
    try:
        if not _empresa_exists(conexao, empresa_id):
            raise LookupError("Empresa não encontrada.")
        if categoria_id is not None:
            category = conexao.execute(
                "SELECT id,ativo FROM categorias_documentos WHERE id=? AND empresa_id=?",
                (categoria_id, empresa_id),
            ).fetchone()
            if not category or not category["ativo"]:
                raise LookupError("Pasta não encontrada ou arquivada.")

        query = """
            SELECT d.id,d.empresa_id,d.categoria_id,d.tipo,d.nome,d.descricao,d.origem,d.ativo,d.criado_em,d.atualizado_em,
                   c.nome AS categoria_nome,
                   (SELECT COUNT(*) FROM documento_versoes v WHERE v.documento_id=d.id) AS versoes_count,
                   (SELECT v.id FROM documento_versoes v WHERE v.documento_id=d.id ORDER BY v.versao DESC LIMIT 1) AS ultima_versao_id,
                   (SELECT v.versao FROM documento_versoes v WHERE v.documento_id=d.id ORDER BY v.versao DESC LIMIT 1) AS ultima_versao,
                   (SELECT v.nome_arquivo FROM documento_versoes v WHERE v.documento_id=d.id ORDER BY v.versao DESC LIMIT 1) AS nome_arquivo
              FROM documentos d
              LEFT JOIN categorias_documentos c ON c.id=d.categoria_id
             WHERE d.empresa_id=? AND d.ativo=1 AND d.categoria_id IS NOT NULL
        """
        params: list[Any] = [empresa_id]
        if categoria_id is not None:
            query += " AND d.categoria_id=?"
            params.append(categoria_id)
        query += " ORDER BY UPPER(d.nome), d.id DESC"
        rows = conexao.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conexao.close()


def _detect_server_mime(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    magic = data[:16]
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("O arquivo informado como PDF não possui assinatura PDF válida.")
        return "application/pdf"
    if ext in {".jpg", ".jpeg"}:
        if not data.startswith(b"\xff\xd8\xff"):
            raise ValueError("O arquivo de imagem JPG não possui assinatura válida.")
        return "image/jpeg"
    if ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("O arquivo PNG não possui assinatura válida.")
        return "image/png"
    if ext in {".docx", ".xlsx", ".pptx"}:
        if not data.startswith(b"PK"):
            raise ValueError("O arquivo Office não possui um pacote ZIP válido.")
        return mimetypes.guess_type(filename)[0] or "application/zip"
    if ext in {".doc", ".xls", ".ppt"}:
        if not data.startswith(b"\xd0\xcf\x11\xe0"):
            raise ValueError("O arquivo Office legado não possui assinatura válida.")
        return mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if ext in {".txt", ".csv"}:
        # Texto não é servido inline pelo endpoint; portanto não representa conteúdo ativo.
        return "text/plain" if ext == ".txt" else "text/csv"
    raise ValueError("Tipo de arquivo não permitido. Use PDF, JPG, PNG, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT ou CSV.")


def _write_file(upload: UploadFile, destino: Path) -> tuple[int, str, str]:
    filename = upload.filename or "documento"
    data = upload.file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Arquivo excede o limite de {MAX_UPLOAD_MB} MB.")
    mime = _detect_server_mime(filename, data)
    # Nunca confie no Content-Type enviado pelo navegador; o MIME vem do conteúdo/extensão validados.
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(data)
    return len(data), hashlib.sha256(data).hexdigest(), mime


def upload_documento(empresa_id: int, categoria_id: int, nome_documento: str, upload: UploadFile, user_id: int, observacao: str | None = None):
    nome_documento = nome_documento.strip() or Path(upload.filename or "documento").stem
    conexao = conectar_banco()
    created_path: Path | None = None
    try:
        if not _empresa_exists(conexao, empresa_id):
            raise LookupError("Empresa não encontrada.")
        cat = conexao.execute(
            "SELECT * FROM categorias_documentos WHERE id=? AND empresa_id=? AND ativo=1",
            (categoria_id, empresa_id),
        ).fetchone()
        if not cat:
            raise ValueError("Pasta inválida ou arquivada.")
        _ensure_category_directory(empresa_id, categoria_id)
        cur = conexao.execute(
            "INSERT INTO documentos (empresa_id,tipo,nome,descricao,categoria,categoria_id,origem,ativo) VALUES (?,?,?,?,?,?,?,1)",
            (empresa_id, "DOCUMENTO_EMPRESARIAL", nome_documento, observacao, cat["nome"], categoria_id, "UPLOAD_MANUAL"),
        )
        documento_id = cur.lastrowid
        versao = 1
        original = _safe_name(upload.filename or f"{nome_documento}.bin")
        ext = Path(original).suffix.lower()
        filename = f"{documento_id}_v{versao}_{original}"
        destino = _category_storage_path(empresa_id, categoria_id) / filename
        tamanho, digest, mime = _write_file(upload, destino)
        created_path = destino
        rel = str(destino.resolve().relative_to(BASE_DIR.parent.resolve()))
        conexao.execute(
            "INSERT INTO documento_versoes (documento_id,versao,nome_arquivo,caminho_arquivo,extensao,tamanho,hash_arquivo,mime_type,origem,observacao,usuario_upload_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (documento_id, versao, upload.filename or original, rel, ext, tamanho, digest, mime, "UPLOAD_MANUAL", observacao, user_id),
        )
        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_novos,origem) VALUES (?,?,?,?,?)",
            (
                "DOCUMENTO",
                documento_id,
                "UPLOAD",
                json.dumps(
                    {"empresa_id":empresa_id,"categoria_id":categoria_id,"usuario_id":user_id,"nome":nome_documento,"arquivo":upload.filename},
                    ensure_ascii=False,
                ),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
        return documento_por_id(documento_id)
    except Exception:
        conexao.rollback()
        if created_path:
            created_path.unlink(missing_ok=True)
        raise
    finally:
        conexao.close()


def documento_por_id(documento_id: int):
    conexao = conectar_banco()
    try:
        row = conexao.execute(
            """
            SELECT d.*,c.nome categoria_nome
              FROM documentos d
              LEFT JOIN categorias_documentos c ON c.id=d.categoria_id
             WHERE d.id=?
            """,
            (documento_id,),
        ).fetchone()
        if not row:
            raise LookupError("Documento não encontrado.")
        return dict(row)
    finally:
        conexao.close()


def listar_versoes(documento_id: int):
    conexao = conectar_banco()
    try:
        rows = conexao.execute(
            """
            SELECT v.*,u.nome AS usuario_nome,u.email AS usuario_email
              FROM documento_versoes v
              LEFT JOIN usuarios u ON u.id=v.usuario_upload_id
             WHERE v.documento_id=?
             ORDER BY v.versao DESC
            """,
            (documento_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conexao.close()


def nova_versao(documento_id: int, upload: UploadFile, user_id: int, observacao: str | None = None):
    conexao = conectar_banco()
    created_path: Path | None = None
    try:
        doc = conexao.execute(
            "SELECT * FROM documentos WHERE id=? AND ativo=1 AND categoria_id IS NOT NULL",
            (documento_id,),
        ).fetchone()
        if not doc:
            raise LookupError("Documento não encontrado ou indisponível para atualização.")
        _ensure_category_directory(int(doc["empresa_id"]), int(doc["categoria_id"]))
        # Serializa o cálculo da próxima versão para evitar duas requisições
        # concorrentes escolherem o mesmo número.
        conexao.execute("BEGIN IMMEDIATE")
        row = conexao.execute("SELECT COALESCE(MAX(versao),0)+1 v FROM documento_versoes WHERE documento_id=?", (documento_id,)).fetchone()
        versao = row["v"]
        original = _safe_name(upload.filename or f"documento_v{versao}.bin")
        ext = Path(original).suffix.lower()
        filename = f"{documento_id}_v{versao}_{original}"
        destino = _category_storage_path(int(doc["empresa_id"]), int(doc["categoria_id"])) / filename
        tamanho, digest, mime = _write_file(upload, destino)
        created_path = destino
        rel = str(destino.resolve().relative_to(BASE_DIR.parent.resolve()))
        conexao.execute(
            "INSERT INTO documento_versoes (documento_id,versao,nome_arquivo,caminho_arquivo,extensao,tamanho,hash_arquivo,mime_type,origem,observacao,usuario_upload_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (documento_id,versao,upload.filename or original,rel,ext,tamanho,digest,mime,"NOVA_VERSAO",observacao,user_id),
        )
        conexao.execute("UPDATE documentos SET atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (documento_id,))
        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_novos,origem) VALUES (?,?,?,?,?)",
            (
                "DOCUMENTO",
                documento_id,
                "NOVA_VERSAO",
                json.dumps({"versao":versao,"usuario_id":user_id,"arquivo":upload.filename}, ensure_ascii=False),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
        return documento_por_id(documento_id)
    except Exception:
        conexao.rollback()
        if created_path:
            created_path.unlink(missing_ok=True)
        raise
    finally:
        conexao.close()


def arquivo_versao(versao_id: int):
    conexao = conectar_banco()
    try:
        row = conexao.execute(
            """
            SELECT v.*,d.empresa_id,d.nome AS documento_nome,d.ativo AS documento_ativo,
                   c.nome AS categoria_nome
              FROM documento_versoes v
              JOIN documentos d ON d.id=v.documento_id
              LEFT JOIN categorias_documentos c ON c.id=d.categoria_id
             WHERE v.id=?
            """,
            (versao_id,),
        ).fetchone()
        if not row:
            raise LookupError("Arquivo não encontrado.")
        return dict(row)
    finally:
        conexao.close()


def registrar_acesso_arquivo(versao_id: int, user_id: int | None, acao: str) -> None:
    conexao = conectar_banco()
    try:
        row = conexao.execute(
            "SELECT documento_id FROM documento_versoes WHERE id=?",
            (versao_id,),
        ).fetchone()
        if not row:
            return
        conexao.execute(
            "INSERT INTO auditorias (entidade,entidade_id,acao,dados_novos,origem) VALUES (?,?,?,?,?)",
            (
                "DOCUMENTO_VERSAO",
                versao_id,
                acao,
                json.dumps({"documento_id": row["documento_id"], "usuario_id": user_id}, ensure_ascii=False),
                "DOCUMENTACAO",
            ),
        )
        conexao.commit()
    finally:
        conexao.close()
