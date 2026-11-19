"""Modelo inicial para adaptar uma automação ao contrato do ÔMEGA.

Este arquivo é apenas um template: não inicia browser, não acessa portais e
não deve ser tratado como uma automação operacional até ser implementado e testado.
"""
from pathlib import Path
from typing import Any


def executar(contexto: dict[str, Any]) -> dict[str, Any]:
    """Execute uma rotina e devolva resultado padronizado para o worker.

    Chaves recomendadas em contexto:
      - empresa_id
      - cnpj
      - diretorio_trabalho
      - configuracoes não secretas

    Nunca inclua senhas, tokens, cookies ou PINs no retorno/log.
    """
    workdir = Path(contexto.get("diretorio_trabalho", ".")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    # TODO: integrar a lógica real da automação aqui.
    return {
        "status": "PENDENCIA",
        "mensagem": "Template ainda não conectado a uma automação real.",
        "arquivos": [],
        "dados": {
            "empresa_id": contexto.get("empresa_id"),
            "cnpj": contexto.get("cnpj"),
        },
    }
