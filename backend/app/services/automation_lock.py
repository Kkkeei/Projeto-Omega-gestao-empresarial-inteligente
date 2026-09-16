"""Lock distribuído para automações que usam a sessão gráfica do Windows.

Como PyAutoGUI controla teclado/mouse da máquina inteira, apenas uma automação
visual de certidões deve executar por vez. O lock é persistido no SQLite para
proteger inclusive contra dois processos/workers diferentes do FastAPI.
"""
from __future__ import annotations

import asyncio
import os
import socket
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncIterator

from app.db.database import DB_PATH, conectar_banco

LOCK_NAME = "CENTRAL_CERTIDOES_GUI"
DEFAULT_TTL_MINUTES = int(os.getenv("OMEGA_AUTOMACAO_LOCK_TTL_MINUTES", "240"))


class AutomationBusyError(RuntimeError):
    def __init__(self, message: str = "Já existe uma automação de certidões em execução. Aguarde a conclusão antes de iniciar outra."):
        super().__init__(message)
        self.message = message


def _agora() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat(timespec="seconds")


def _garantir_tabela(conexao: sqlite3.Connection) -> None:
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS automacao_locks (
            lock_name TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            tipo TEXT NOT NULL,
            empresa_id INTEGER,
            empresa TEXT,
            iniciado_em TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            host TEXT,
            pid INTEGER,
            mensagem TEXT
        )
        """
    )
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS idx_automacao_locks_expira ON automacao_locks(expira_em)"
    )


def _limpar_expirados(conexao: sqlite3.Connection) -> None:
    conexao.execute(
        "DELETE FROM automacao_locks WHERE lock_name=? AND expira_em <= ?",
        (LOCK_NAME, _iso(_agora())),
    )


def _acquire_lock_sync(
    tipo: str,
    empresa_id: int | None = None,
    empresa: str | None = None,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> dict[str, Any] | None:
    # Conexão curta e timeout baixo: uma segunda requisição deve receber 409,
    # não ficar esperando dezenas de segundos pelo SQLite.
    conexao = sqlite3.connect(DB_PATH, timeout=1.0)
    conexao.row_factory = sqlite3.Row
    try:
        _garantir_tabela(conexao)
        conexao.execute("BEGIN IMMEDIATE")
        _limpar_expirados(conexao)
        existente = conexao.execute(
            "SELECT lock_name, token, tipo, empresa_id, empresa, iniciado_em, expira_em, host, pid, mensagem FROM automacao_locks WHERE lock_name=?",
            (LOCK_NAME,),
        ).fetchone()
        if existente:
            conexao.commit()
            return None

        token = uuid.uuid4().hex
        inicio = _agora()
        expira = inicio + timedelta(minutes=max(5, ttl_minutes))
        mensagem = "Uma automação visual está em execução. As demais consultas ficam temporariamente bloqueadas para proteger a sessão do Windows."
        conexao.execute(
            """
            INSERT INTO automacao_locks
            (lock_name, token, tipo, empresa_id, empresa, iniciado_em, expira_em, host, pid, mensagem)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                LOCK_NAME,
                token,
                tipo,
                empresa_id,
                empresa,
                _iso(inicio),
                _iso(expira),
                socket.gethostname(),
                os.getpid(),
                mensagem,
            ),
        )
        conexao.commit()
        return {
            "token": token,
            "tipo": tipo,
            "empresa_id": empresa_id,
            "empresa": empresa,
            "iniciado_em": _iso(inicio),
            "expira_em": _iso(expira),
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "mensagem": mensagem,
        }
    except sqlite3.IntegrityError:
        conexao.rollback()
        return None
    except sqlite3.OperationalError as exc:
        conexao.rollback()
        if "locked" in str(exc).lower():
            return None
        raise
    finally:
        conexao.close()


def _release_lock_sync(token: str) -> None:
    conexao = conectar_banco()
    try:
        conexao.execute("DELETE FROM automacao_locks WHERE lock_name=? AND token=?", (LOCK_NAME, token))
        conexao.commit()
    finally:
        conexao.close()


def _status_sync() -> dict[str, Any]:
    conexao = conectar_banco()
    try:
        _garantir_tabela(conexao)
        _limpar_expirados(conexao)
        conexao.commit()
        row = conexao.execute(
            "SELECT lock_name, tipo, empresa_id, empresa, iniciado_em, expira_em, host, pid, mensagem FROM automacao_locks WHERE lock_name=?",
            (LOCK_NAME,),
        ).fetchone()
        if not row:
            return {"ocupada": False, "mensagem": "Nenhuma automação de certidões em execução."}
        return {"ocupada": True, **dict(row)}
    finally:
        conexao.close()


async def status_automacao() -> dict[str, Any]:
    return await asyncio.to_thread(_status_sync)


@asynccontextmanager
async def lock_automacao(
    tipo: str,
    empresa_id: int | None = None,
    empresa: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    lock = await asyncio.to_thread(_acquire_lock_sync, tipo, empresa_id, empresa)
    if not lock:
        status = await status_automacao()
        if status.get("ocupada"):
            nome = status.get("empresa") or "outra empresa"
            tipo_atual = status.get("tipo") or "outra automação"
            raise AutomationBusyError(
                f"A central de certidões já está executando {tipo_atual} para {nome}. "
                "Aguarde a conclusão antes de iniciar outra consulta."
            )
        raise AutomationBusyError()
    try:
        yield lock
    finally:
        await asyncio.to_thread(_release_lock_sync, lock["token"])
