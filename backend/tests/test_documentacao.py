from pathlib import Path
from uuid import uuid4
from io import BytesIO
from zipfile import ZipFile

from app.modules.documentacao import service


def _empresa_id() -> int:
    conexao = service.conectar_banco()
    try:
        row = conexao.execute("SELECT id FROM empresas ORDER BY id LIMIT 1").fetchone()
        assert row is not None
        return int(row["id"])
    finally:
        conexao.close()


def test_documentacao_subpastas_criacao_navegacao_e_arquivo_fisico():
    empresa_id = _empresa_id()
    suffix = uuid4().hex[:8]
    root = service.criar_categoria(empresa_id, f"__TESTE_RAIZ_{suffix}", "Pasta de teste")
    child = service.criar_categoria(empresa_id, f"__TESTE_SUBPASTA_{suffix}", "Subpasta de teste", root["id"])
    try:
        assert child["categoria_pai_id"] == root["id"]

        categorias = service.listar_categorias(empresa_id)
        by_id = {item["id"]: item for item in categorias}
        assert root["id"] in by_id
        assert child["id"] in by_id
        assert by_id[root["id"]]["subpastas_count"] >= 1
        assert by_id[child["id"]]["categoria_pai_id"] == root["id"]

        root_dir = service.STORAGE_ROOT / str(empresa_id) / str(root["id"])
        child_dir = service.STORAGE_ROOT / str(empresa_id) / str(child["id"])
        assert root_dir.is_dir()
        assert child_dir.is_dir()

        renamed = service.atualizar_categoria(child["id"], f"__TESTE_SUBPASTA_RENOMEADA_{suffix}", "Atualizada")
        assert renamed["nome"].endswith(suffix)

        archived = service.arquivar_categoria(root["id"])
        assert archived["categorias_arquivadas"] >= 2
        remaining = service.listar_categorias(empresa_id)
        assert root["id"] not in {item["id"] for item in remaining}
        assert child["id"] not in {item["id"] for item in remaining}
    finally:
        # Diretórios vazios são seguros para remover; documentos reais não são tocados.
        for path in [service.STORAGE_ROOT / str(empresa_id) / str(child["id"]), service.STORAGE_ROOT / str(empresa_id) / str(root["id"])]:
            try:
                path.rmdir()
            except OSError:
                pass

def _office_package(kind: str) -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        if kind == "word":
            zf.writestr("word/document.xml", "<document/>")
        elif kind == "excel":
            zf.writestr("xl/workbook.xml", "<workbook/>")
        elif kind == "powerpoint":
            zf.writestr("ppt/presentation.xml", "<presentation/>")
        elif kind == "odf":
            zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
    return buf.getvalue()


def test_documentacao_reconhece_formatos_comuns_de_documentos():
    office_word = _office_package("word")
    office_excel = _office_package("excel")
    office_ppt = _office_package("powerpoint")
    office_odf = _office_package("odf")
    cases = {
        "contrato.doc": (b"\xd0\xcf\x11\xe0", "application/msword"),
        "contrato.docx": (office_word, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "contrato.docm": (office_word, "application/vnd.ms-word.document.macroEnabled.12"),
        "planilha.xls": (b"\xd0\xcf\x11\xe0", "application/vnd.ms-excel"),
        "planilha.xlsx": (office_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "planilha.xlsm": (office_excel, "application/vnd.ms-excel.sheet.macroEnabled.12"),
        "apresentacao.ppt": (b"\xd0\xcf\x11\xe0", "application/vnd.ms-powerpoint"),
        "apresentacao.pptx": (office_ppt, "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        "texto.odt": (office_odf, "application/vnd.oasis.opendocument.text"),
        "planilha.ods": (office_odf, "application/vnd.oasis.opendocument.spreadsheet"),
        "texto.rtf": (b"{\\rtf1", "application/rtf"),
        "foto.webp": (b"RIFF0000WEBP", "image/webp"),
        "foto.gif": (b"GIF89a", "image/gif"),
        "foto.bmp": (b"BM0000", "image/bmp"),
    }
    for filename, (payload, expected_mime) in cases.items():
        assert service._detect_server_mime(filename, payload) == expected_mime


def test_documentacao_rejeita_extensao_desconhecida_e_office_invalido():
    import pytest

    with pytest.raises(ValueError, match="Tipo de arquivo não permitido"):
        service._detect_server_mime("arquivo.exe", b"MZ")

    with pytest.raises(ValueError, match="pacote ZIP válido"):
        service._detect_server_mime("contrato.docx", b"not-a-zip")

    with pytest.raises(ValueError, match="assinatura válida"):
        service._detect_server_mime("contrato.doc", b"arquivo comum")

def test_documentacao_aceita_formatos_textuais_adicionais_e_rejeita_executaveis():
    assert service._detect_server_mime("arquivo.xml", b"<xml/>") == "application/xml"
    assert service._detect_server_mime("arquivo.json", b"{}") == "application/json"
    assert service._detect_server_mime("arquivo.txt", b"texto") == "text/plain"
    assert service._detect_server_mime("arquivo.xyz", b"conteudo") == "application/octet-stream"

    import pytest
    with pytest.raises(ValueError, match="executáveis ou scripts"):
        service._detect_server_mime("arquivo.exe", b"MZ")


def test_documentacao_uploada_word_e_registra_mime_correto():
    from fastapi import UploadFile

    empresa_id = _empresa_id()
    suffix = uuid4().hex[:8]
    categoria = service.criar_categoria(empresa_id, f"__TESTE_WORD_{suffix}", "Teste Word")
    arquivo = UploadFile(filename="Contrato Social.docx", file=BytesIO(_office_package("word")))
    try:
        documento = service.upload_documento(empresa_id, categoria["id"], "Contrato Social", arquivo, 1, "Teste Word")
        versoes = service.listar_versoes(documento["id"])
        assert versoes[0]["nome_arquivo"] == "Contrato Social.docx"
        assert versoes[0]["extensao"] == ".docx"
        assert versoes[0]["mime_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    finally:
        try:
            service.arquivar_documento(documento["id"], 1)
        except (UnboundLocalError, LookupError):
            pass
        try:
            service.arquivar_categoria(categoria["id"], 1)
        except Exception:
            pass
        for path in [service.STORAGE_ROOT / str(empresa_id) / str(categoria["id"])]:
            try:
                for child in path.iterdir():
                    child.unlink(missing_ok=True)
                path.rmdir()
            except OSError:
                pass



def test_documentacao_upload_http_docx_real():
    from fastapi.testclient import TestClient
    from main import app
    from app.services.auth_service import buscar_usuario_por_id, create_access_token, ensure_admin_user

    client = TestClient(app)
    ensure_admin_user()
    admin = buscar_usuario_por_id(1)
    assert admin is not None
    headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
    empresa_id = _empresa_id()
    suffix = uuid4().hex[:8]
    categoria = service.criar_categoria(empresa_id, f"__TESTE_HTTP_WORD_{suffix}", "Teste HTTP Word")
    try:
        response = client.post(
            f"/api/v1/documentacao/empresas/{empresa_id}/documentos/upload",
            headers=headers,
            data={"categoria_id": str(categoria["id"]), "nome_documento": "Contrato HTTP"},
            files={
                "arquivo": (
                    "Contrato HTTP.docx",
                    _office_package("word"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        versoes = service.listar_versoes(body["id"])
        assert versoes[0]["extensao"] == ".docx"
        assert versoes[0]["mime_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    finally:
        try:
            if 'body' in locals() and body.get("id"):
                service.arquivar_documento(body["id"], 1)
        except Exception:
            pass
        try:
            service.arquivar_categoria(categoria["id"], 1)
        except Exception:
            pass
