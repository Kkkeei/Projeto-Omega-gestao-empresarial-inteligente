from pathlib import Path
from uuid import uuid4

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
