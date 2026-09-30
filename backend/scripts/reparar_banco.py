#!/usr/bin/env python3
"""Diagnóstico e recuperação segura de omega.db usando SQLite .recover.

USO (com o backend PARADO):
    python scripts/reparar_banco.py

O script nunca apaga o banco original. Ele cria cópias de segurança e, se a
recuperação for bem-sucedida, instala o banco recuperado como omega.db.
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "omega.db"
BACKUP_DIR = ROOT / "backups" / "database_recovery"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def integrity(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "arquivo inexistente"
    con = sqlite3.connect(path)
    try:
        row = con.execute("PRAGMA quick_check").fetchone()
        msg = str(row[0]) if row else "unknown"
        return msg.lower() == "ok", msg
    except sqlite3.DatabaseError as exc:
        return False, str(exc)
    finally:
        con.close()


def main() -> int:
    if not DB.exists():
        print(f"Banco não encontrado: {DB}")
        return 1

    ok, detail = integrity(DB)
    print(f"Banco: {DB}")
    print(f"Integridade: {detail}")
    if ok:
        print("O banco está íntegro. Nenhuma recuperação é necessária.")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    original_copy = BACKUP_DIR / f"omega_corrompido_{STAMP}.db"
    shutil.copy2(DB, original_copy)
    for suffix in ("-wal", "-shm"):
        sidecar = DB.with_name(DB.name + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, BACKUP_DIR / f"omega_corrompido_{STAMP}.db{suffix}")

    sqlite3_bin = shutil.which("sqlite3")
    if not sqlite3_bin:
        print("ERRO: o comando sqlite3 não está instalado.")
        print("Instale o pacote SQLite da sua distribuição e execute este script novamente.")
        print(f"Backup preservado em: {original_copy}")
        return 2

    recovered = BACKUP_DIR / f"omega_recuperado_{STAMP}.db"
    cmd = [sqlite3_bin, str(DB)]
    recover = subprocess.run(
        cmd,
        input='.recover\n',
        text=True,
        capture_output=True,
        check=False,
    )
    if recover.returncode != 0 and not recover.stdout:
        print("ERRO ao executar .recover:")
        print(recover.stderr.strip())
        return 3

    apply = subprocess.run(
        [sqlite3_bin, str(recovered)],
        input=recover.stdout,
        text=True,
        capture_output=True,
        check=False,
    )
    if apply.returncode != 0:
        print("ERRO ao construir o banco recuperado:")
        print(apply.stderr.strip())
        print(f"Backup original preservado em: {original_copy}")
        return 4

    ok2, detail2 = integrity(recovered)
    print(f"Banco recuperado: {recovered}")
    print(f"Integridade recuperada: {detail2}")
    if not ok2:
        print("A recuperação não produziu um banco íntegro. NÃO substituindo o original.")
        return 5

    archived = BACKUP_DIR / f"omega_original_{STAMP}.db"
    DB.rename(archived)
    recovered.rename(DB)
    for suffix in ("-wal", "-shm"):
        sidecar = DB.with_name(DB.name + suffix)
        if sidecar.exists():
            sidecar.unlink()
    print(f"Banco recuperado instalado em: {DB}")
    print(f"Banco original arquivado em: {archived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
