from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from app.db.database import conectar_banco
from app.services.empresas_service import sincronizar_empresa
from app.services.automation_lock import lock_automacao

TIPOS = {
    "SINCRONIZACAO_EMPRESA": "Sincronização cadastral da empresa",
    "CONSULTA_CERTIDAO_ESTADUAL": "Consulta de certidão estadual",
    "CONSULTA_CERTIDAO_FEDERAL": "Consulta de certidão federal",
    "CONSULTA_CERTIDAO_NARRATIVA": "Consulta de certidão narrativa",
}


async def _executar_real(tipo: str, dados: dict[str, Any]):
    empresa_id = dados.get("empresa_id")
    if not empresa_id:
        raise ValueError("Informe a empresa para executar esta automação.")

    if tipo == "SINCRONIZACAO_EMPRESA":
        return await sincronizar_empresa(int(empresa_id))

    with conectar_banco() as conn:
        empresa = conn.execute("SELECT id, razao_social FROM empresas WHERE id=? AND ativo=1", (empresa_id,)).fetchone()
    if not empresa:
        raise LookupError("Empresa não encontrada ou inativa.")

    if tipo == "CONSULTA_CERTIDAO_ESTADUAL":
        from app.services.certidoes_service import consultar_estadual
        async with lock_automacao(tipo, int(empresa_id), empresa["razao_social"]):
            return await consultar_estadual(int(empresa_id))

    if tipo == "CONSULTA_CERTIDAO_FEDERAL":
        from app.services.receita_federal_service import consultar_federal
        async with lock_automacao(tipo, int(empresa_id), empresa["razao_social"]):
            return await consultar_federal(int(empresa_id))

    if tipo == "CONSULTA_CERTIDAO_NARRATIVA":
        from app.services.certidoes_service import consultar_narrativa_pyautogui
        async with lock_automacao(tipo, int(empresa_id), empresa["razao_social"]):
            nome = (dados.get("configuracao") or {}).get("certificado_nome")
            return await asyncio.to_thread(consultar_narrativa_pyautogui, int(empresa_id), nome)

    raise ValueError(f"Tipo de automação não suportado: {tipo}")


async def executar(dados: dict[str, Any]):
    tipo = str(dados.get("tipo") or "").strip().upper()
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de automação não suportado: {tipo or 'vazio'}")

    empresa_id = dados.get("empresa_id")
    with conectar_banco() as conn:
        if empresa_id and not conn.execute("SELECT id FROM empresas WHERE id=?", (empresa_id,)).fetchone():
            raise LookupError("Empresa não encontrada.")
        cur = conn.execute(
            """
            INSERT INTO execucoes_automacao
            (automacao_id,empresa_id,tipo,status,mensagem,resultado,origem)
            VALUES (?,?,?,?,?,?,?)
            """,
            (dados.get("automacao_id"), empresa_id, tipo, "EM_EXECUCAO", "Automação iniciada.", json.dumps(dados.get("configuracao") or {}, ensure_ascii=False), "API"),
        )
        exec_id = cur.lastrowid
        conn.commit()

    try:
        resultado = await _executar_real(tipo, dados)
        status = "CONCLUÍDA"
        mensagem = "Automação concluída com sucesso."
        erro = None
    except Exception as exc:
        resultado = None
        status = "ERRO"
        mensagem = "A automação não foi concluída."
        erro = str(exc)

    with conectar_banco() as conn:
        conn.execute(
            """
            UPDATE execucoes_automacao
               SET status=?, fim=CURRENT_TIMESTAMP, mensagem=?, erro_tecnico=?, resultado=?
             WHERE id=?
            """,
            (status, mensagem, erro, json.dumps(resultado, ensure_ascii=False, default=str), exec_id),
        )
        conn.commit()
        item = conn.execute("SELECT * FROM execucoes_automacao WHERE id=?", (exec_id,)).fetchone()
        data = dict(item)

    if status == "ERRO":
        raise RuntimeError(erro or mensagem)
    return data


def historico(empresa_id=None):
    with conectar_banco() as conexao:
        sql = "SELECT * FROM execucoes_automacao WHERE 1=1"
        params = []
        if empresa_id is not None:
            sql += " AND empresa_id=?"
            params.append(empresa_id)
        sql += " ORDER BY id DESC"
        return [dict(r) for r in conexao.execute(sql, params).fetchall()]
