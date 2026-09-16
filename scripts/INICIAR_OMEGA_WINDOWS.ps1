$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root'; .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$root\frontend'; npm run dev -- --host 0.0.0.0"
