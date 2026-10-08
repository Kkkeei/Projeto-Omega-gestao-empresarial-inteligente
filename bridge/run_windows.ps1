$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python não encontrado. Instale Python 3.11+ e habilite o comando 'py'."
}

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not $env:OMEGA_BRIDGE_TOKEN) {
    $env:OMEGA_BRIDGE_TOKEN = Read-Host "Informe o OMEGA_BRIDGE_TOKEN usado no frontend"
}
if (-not $env:OMEGA_PKCS11_MODULE) {
    $safeSign = Join-Path $env:WINDIR "System32\aetpkss1.dll"
    $safeNet = Join-Path $env:WINDIR "System32\eTPKCS11.dll"
    if (Test-Path $safeSign) {
        $env:OMEGA_PKCS11_MODULE = $safeSign
        Write-Host "PKCS#11 detectado automaticamente (SafeSign): $safeSign" -ForegroundColor Cyan
    } elseif (Test-Path $safeNet) {
        $env:OMEGA_PKCS11_MODULE = $safeNet
        Write-Host "PKCS#11 detectado automaticamente (SafeNet): $safeNet" -ForegroundColor Cyan
    } else {
        Write-Host "Nenhuma DLL PKCS#11 padrão foi encontrada." -ForegroundColor Yellow
        $env:OMEGA_PKCS11_MODULE = Read-Host "Informe o caminho completo da DLL PKCS#11 do middleware A3 (ou deixe vazio para detectar depois)"
    }
}
if (-not $env:OMEGA_BRIDGE_ALLOWED_ORIGINS) {
    $env:OMEGA_BRIDGE_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
}

Write-Host ""
Write-Host "OMEGA Bridge iniciado em http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "PKCS#11: $env:OMEGA_PKCS11_MODULE"
Write-Host "Origens: $env:OMEGA_BRIDGE_ALLOWED_ORIGINS"
Write-Host ""

& .\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8765
