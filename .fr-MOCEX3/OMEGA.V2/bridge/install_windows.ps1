$ErrorActionPreference = "Stop"

# Instalador de uso único do OMEGA A3 Bridge.
# Depois da instalação, o Bridge inicia automaticamente no logon do Windows.
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Join-Path $env:LOCALAPPDATA "OMEGA\A3Bridge"
$VenvDir = Join-Path $InstallDir ".venv"
$Launcher = Join-Path $InstallDir "start_bridge.cmd"
$LogFile = Join-Path $InstallDir "bridge.log"
$TaskName = "OMEGA A3 Bridge"
$DefaultToken = "omega-local-a3-bridge-v1"

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) { return "py" }
    if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
    throw "Python 3 não foi encontrado. Instale Python 3.11+ e execute este instalador novamente."
}

Write-Host ""; Write-Host "OMEGA A3 Bridge - instalação" -ForegroundColor Cyan
Write-Host "O componente será instalado em: $InstallDir"

$python = Find-Python
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# Copia apenas os arquivos necessários, mantendo a instalação independente do ZIP original.
Copy-Item (Join-Path $SourceDir "app.py") $InstallDir -Force
Copy-Item (Join-Path $SourceDir "requirements.txt") $InstallDir -Force
Copy-Item (Join-Path $SourceDir "__init__.py") $InstallDir -Force -ErrorAction SilentlyContinue

if (-not (Test-Path $VenvDir)) {
    & $python -3 -m venv $VenvDir
}
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$venvPythonW = Join-Path $VenvDir "Scripts\pythonw.exe"
& $venvPython -m pip install --disable-pip-version-check -q --upgrade pip
& $venvPython -m pip install --disable-pip-version-check -q -r (Join-Path $InstallDir "requirements.txt")

# Detecta automaticamente o middleware mais comum do cartão VALID/SafeSign e SafeNet.
$pkcs11 = ""
$Candidates = @(
    (Join-Path $env:WINDIR "System32\aetpkss1.dll"),
    (Join-Path $env:WINDIR "SysWOW64\aetpkss1.dll"),
    (Join-Path $env:WINDIR "System32\eTPKCS11.dll"),
    (Join-Path $env:WINDIR "SysWOW64\eTPKCS11.dll")
)
foreach ($candidate in $Candidates) {
    if (Test-Path $candidate) { $pkcs11 = $candidate; break }
}

# O token local é deliberadamente fixo e limitado ao serviço localhost + Origin autorizado.
# O frontend usa o mesmo fallback; não há configuração manual para o usuário final.
$envFile = Join-Path $InstallDir ".env"
@"
OMEGA_BRIDGE_TOKEN=$DefaultToken
OMEGA_BRIDGE_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
OMEGA_PKCS11_MODULE=$pkcs11
"@ | Set-Content -Path $envFile -Encoding UTF8

# Launcher sem janela de console. Variáveis são carregadas a cada inicialização.
$launcherContent = @"
@echo off
set "OMEGA_BRIDGE_TOKEN=$DefaultToken"
set "OMEGA_BRIDGE_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173"
set "OMEGA_PKCS11_MODULE=$pkcs11"
cd /d "$InstallDir"
"$venvPythonW" -m uvicorn app:app --host 127.0.0.1 --port 8765 >> "$LogFile" 2>&1
"@
Set-Content -Path $Launcher -Value $launcherContent -Encoding ASCII

# Recria a tarefa agendada no usuário atual. Não exige terminal após a instalação.
& schtasks.exe /Delete /TN $TaskName /F 2>$null | Out-Null
& schtasks.exe /Create /TN $TaskName /TR "`"$Launcher`"" /SC ONLOGON /RL LIMITED /F | Out-Null
& schtasks.exe /Run /TN $TaskName | Out-Null

Start-Sleep -Seconds 2
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/health" -TimeoutSec 5
    Write-Host ""; Write-Host "Instalação concluída." -ForegroundColor Green
    Write-Host "Bridge iniciado automaticamente no Windows."
    if ($pkcs11) { Write-Host "PKCS#11 detectado: $pkcs11" -ForegroundColor Green }
    else { Write-Host "PKCS#11 ainda não foi localizado; instale o middleware do cartão A3." -ForegroundColor Yellow }
    Write-Host "Health: $($health.status)"
} catch {
    Write-Host "O Bridge foi instalado, mas ainda não respondeu ao health check." -ForegroundColor Yellow
    Write-Host "Isso normalmente significa que o Python/middleware ainda está sendo inicializado."
}
Write-Host ""; Write-Host "Você não precisa executar comandos novamente. O Bridge iniciará automaticamente." -ForegroundColor Cyan
Read-Host "Pressione ENTER para fechar"
