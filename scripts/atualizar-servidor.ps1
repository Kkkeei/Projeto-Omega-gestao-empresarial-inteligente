[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Base = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Base "backend"
$Db = Join-Path $Backend "omega.db"
$Storage = Join-Path $Base "storage"
$CertStorage = Join-Path $Storage "certificados"
$EnvFile = Join-Path $Backend ".env"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Branch = "feat/omega-ux-operacional"

Write-Host "Projeto: $Base"
if (!(Test-Path (Join-Path $Base ".git"))) {
    throw "Esta pasta não é um clone Git. Conecte o repositório primeiro; não faça atualização por ZIP sobre os dados."
}
if (!(Test-Path $Db)) { throw "Banco não encontrado: $Db. Abortando para não criar outro banco." }
if (!(Test-Path $Storage)) { throw "Storage não encontrado: $Storage. Abortando para não criar outra pasta." }
if (!(Test-Path $EnvFile)) { throw ".env não encontrado: $EnvFile. Abortando." }
if (!(Test-Path $Python)) { throw "Python do ambiente virtual não encontrado: $Python." }

$tracked = @(& git -C $Base ls-files -- "backend/omega.db" "backend/omega.db-shm" "backend/omega.db-wal" "backend/.env" "storage")
if ($LASTEXITCODE -ne 0) { throw "Não foi possível verificar arquivos rastreados pelo Git." }
if ($tracked.Count -gt 0) {
    $tracked | ForEach-Object { Write-Host "ARQUIVO DE DADOS RASTREADO: $_" }
    throw "O Git está rastreando arquivos de dados/configuração. Corrija isso antes de atualizar."
}

$status = @(& git -C $Base status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "Não foi possível consultar o estado do Git." }
if ($status.Count -gt 0) {
    $status | ForEach-Object { Write-Host $_ }
    throw "Há alterações locais de código. Faça commit/backup delas antes da atualização."
}

$confirm = Read-Host "Digite ATUALIZAR para criar backup e atualizar apenas o código"
if ($confirm -cne "ATUALIZAR") { throw "Cancelado. Nenhuma alteração realizada." }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path (Split-Path $Base -Parent) "OMEGA_BACKUP_PRE_DEPLOY_$stamp"
New-Item -ItemType Directory -Path $Backup | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Backup "storage") | Out-Null

# Use SQLite's backup API so the snapshot is consistent even if WAL was used.
$env:OMEGA_DEPLOY_DB = $Db
$env:OMEGA_DEPLOY_BACKUP = Join-Path $Backup "omega.db"
@'
import os, sqlite3
from pathlib import Path
src = sqlite3.connect(os.environ["OMEGA_DEPLOY_DB"], timeout=30)
try:
    dst = sqlite3.connect(os.environ["OMEGA_DEPLOY_BACKUP"])
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
finally:
    src.close()
with sqlite3.connect(os.environ["OMEGA_DEPLOY_BACKUP"]) as con:
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "empresas" not in tables or "certificados" not in tables:
        raise SystemExit("Backup inválido: tabelas esperadas não encontradas.")
print("Backup SQLite validado.")
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { throw "Backup do banco falhou. Atualização cancelada." }

if (Test-Path $CertStorage) {
    Compress-Archive -LiteralPath $CertStorage -DestinationPath (Join-Path $Backup "certificados.zip")
}
Copy-Item $EnvFile (Join-Path $Backup "backend.env")
Write-Host "Backup criado: $Backup"

# Pare apenas processos Uvicorn iniciados a partir desta instalação.
$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains($Base) -and
    $_.CommandLine -match 'uvicorn|main:app'
}
foreach ($proc in $procs) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

& git -C $Base fetch origin $Branch
if ($LASTEXITCODE -ne 0) { throw "git fetch falhou. Backup preservado em $Backup." }
& git -C $Base pull --ff-only origin $Branch
if ($LASTEXITCODE -ne 0) { throw "git pull falhou. Backup preservado em $Backup. Resolva o Git antes de iniciar." }

# Verify paths using the deployed Python configuration; do not print secrets.
$env:PYTHONPATH = $Backend
@'
import os
from pathlib import Path
from app.db import database

expected_db = (Path(os.environ["OMEGA_DEPLOY_DB"])).resolve()
expected_storage = (Path(os.environ["OMEGA_DEPLOY_STORAGE"])).resolve()
print("DB configurado:", database.DB_PATH)
print("Storage configurado:", database.STORAGE_BASE)
if database.DB_PATH.resolve() != expected_db:
    raise SystemExit("O caminho do banco mudou após a atualização; não inicie o servidor.")
if database.STORAGE_BASE.resolve() != expected_storage:
    raise SystemExit("O caminho do storage mudou após a atualização; não inicie o servidor.")
if not database.DB_PATH.is_file():
    raise SystemExit("Banco ausente após atualização.")
if not database.STORAGE_BASE.is_dir():
    raise SystemExit("Storage ausente após atualização.")
print("Caminhos persistentes validados.")
'@ | ForEach-Object { $_ } # kept separate from Python invocation below
$env:OMEGA_DEPLOY_STORAGE = $Storage
@'
import os
from pathlib import Path
from app.db import database
expected_db = Path(os.environ["OMEGA_DEPLOY_DB"]).resolve()
expected_storage = Path(os.environ["OMEGA_DEPLOY_STORAGE"]).resolve()
print("DB configurado:", database.DB_PATH)
print("Storage configurado:", database.STORAGE_BASE)
if database.DB_PATH.resolve() != expected_db:
    raise SystemExit("O caminho do banco mudou após a atualização; não inicie o servidor.")
if database.STORAGE_BASE.resolve() != expected_storage:
    raise SystemExit("O caminho do storage mudou após a atualização; não inicie o servidor.")
if not database.DB_PATH.is_file() or not database.STORAGE_BASE.is_dir():
    raise SystemExit("Banco ou storage ausente após atualização.")
print("Caminhos persistentes validados.")
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { throw "Validação falhou. NÃO inicie o servidor. Backup: $Backup" }

Write-Host ""
Write-Host "Atualização concluída. Banco, .env e storage foram preservados."
Write-Host "Backup: $Backup"
Write-Host "O servidor foi deixado parado; inicie pelo seu procedimento habitual após validar o resultado."
