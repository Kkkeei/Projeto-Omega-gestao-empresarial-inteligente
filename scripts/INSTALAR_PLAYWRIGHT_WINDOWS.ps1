$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."
& .\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
& .\.venv\Scripts\python.exe -m playwright install chromium
Write-Host "Dependencias e Chromium do Playwright instalados."
