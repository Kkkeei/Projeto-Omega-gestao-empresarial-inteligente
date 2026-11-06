import re
from pathlib import Path

from app.db.database import STORAGE_BASE


STORAGE_ROOT = STORAGE_BASE / "contabil" / "documentos"


def nome_seguro(nome: str) -> str:
    """Normaliza nomes recebidos antes de usá-los no armazenamento."""
    normalizado = re.sub(r"[^\w\-.() ]+", "_", nome, flags=re.UNICODE).strip()
    return normalizado[:160] or "arquivo"


def caminho_obrigacao(empresa_id: int, competencia: int, obrigacao_id: int) -> Path:
    if empresa_id <= 0 or obrigacao_id <= 0:
        raise ValueError("Os identificadores devem ser positivos.")
    ano, mes = divmod(competencia, 100)
    if ano < 1900 or ano > 2999 or mes not in range(1, 13):
        raise ValueError("A competência deve estar no formato YYYYMM.")
    return STORAGE_ROOT / str(empresa_id) / f"{ano:04d}{mes:02d}" / str(obrigacao_id)


def garantir_diretorio_obrigacao(empresa_id: int, competencia: int, obrigacao_id: int) -> Path:
    caminho = caminho_obrigacao(empresa_id, competencia, obrigacao_id)
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def resolver_caminho_armazenado(caminho: str) -> Path:
    """Resolve um caminho relativo ao diretório exclusivo do módulo contábil."""
    informado = Path(caminho.replace("\\", "/"))
    caminho_resolvido = informado.resolve() if informado.is_absolute() else (STORAGE_ROOT / informado).resolve()
    try:
        caminho_resolvido.relative_to(STORAGE_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Arquivo fora do armazenamento contábil permitido.") from exc
    return caminho_resolvido
