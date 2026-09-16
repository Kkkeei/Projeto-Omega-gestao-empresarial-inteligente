"""Sessão Chrome dedicada para automações PyAutoGUI no Windows.

Cada execução recebe um perfil temporário próprio. Isso permite encerrar somente
as instâncias abertas pela automação, sem matar o Chrome pessoal do usuário.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


class ChromeAutomationError(RuntimeError):
    pass


def _find_chrome() -> str:
    candidatos = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for candidato in candidatos:
        if candidato and Path(candidato).is_file():
            return candidato
    encontrado = shutil.which("chrome")
    if encontrado:
        return encontrado
    raise ChromeAutomationError("Google Chrome não foi encontrado no Windows.")


@dataclass
class ChromeAutomationSession:
    process: subprocess.Popen | None = None
    profile_dir: Path | None = None

    def start(self, initial_url: str | None = None) -> None:
        if self.process is not None:
            return
        chrome = _find_chrome()
        base = Path(tempfile.mkdtemp(prefix="omega_chrome_"))
        self.profile_dir = base
        args = [
            chrome,
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={base}",
        ]
        if initial_url:
            args.append(initial_url)
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            self.process = subprocess.Popen(args, creationflags=creationflags)
        except Exception:
            shutil.rmtree(base, ignore_errors=True)
            self.profile_dir = None
            raise
        # Dê tempo para a janela aparecer antes dos comandos de foco do PyAutoGUI.
        deadline = time.monotonic() + float(os.getenv("OMEGA_CHROME_BOOT_TIMEOUT", "15"))
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise ChromeAutomationError(f"Chrome encerrou imediatamente (código {self.process.returncode}).")
            time.sleep(0.2)

    def close(self) -> None:
        proc = self.process
        profile = self.profile_dir
        self.process = None
        self.profile_dir = None
        try:
            if proc is not None and proc.poll() is None:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            elif proc is not None:
                # O processo raiz pode ter encerrado, mas filhos Chrome podem permanecer.
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
        finally:
            if profile:
                shutil.rmtree(profile, ignore_errors=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
