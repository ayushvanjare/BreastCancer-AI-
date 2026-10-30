param([switch]$InstallDependencies)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "BreastCare AI - Phase 2.2 local launcher" -ForegroundColor Cyan
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js was not found. Install Node.js 20 LTS or newer, then retry." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "npm was not found. Reinstall Node.js with npm enabled, then retry." }

$backendEnvironment = Join-Path $PSScriptRoot "backend\.venv"
$recoveredEnvironment = Join-Path $PSScriptRoot "backend\.venv_recovered"
if (Test-Path (Join-Path $recoveredEnvironment "Scripts\python.exe")) { $backendEnvironment = $recoveredEnvironment }
$backendPython = Join-Path $backendEnvironment "Scripts\python.exe"
$createdBackendEnvironment = $false
if (-not (Test-Path $backendPython)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python was not found. Install Python 3.11 or 3.12, then retry." }
    Write-Host "Creating the backend environment..." -ForegroundColor Yellow
    python -m venv $backendEnvironment
    if ($LASTEXITCODE -ne 0) { throw "Could not create the backend Python environment." }
    $createdBackendEnvironment = $true
}
if ($createdBackendEnvironment -or $InstallDependencies) {
    Write-Host "Installing backend requirements (PyTorch is not included)..." -ForegroundColor Yellow
    & $backendPython -m pip install -r (Join-Path $PSScriptRoot "backend\requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
} else {
    Write-Host "Using the existing backend environment. Pass -InstallDependencies to update requirements." -ForegroundColor DarkGray
}

$frontendModules = Join-Path $PSScriptRoot "frontend\node_modules"
if (-not (Test-Path $frontendModules) -or $InstallDependencies) {
    Write-Host "Installing frontend dependencies from the lock file..." -ForegroundColor Yellow
    Push-Location (Join-Path $PSScriptRoot "frontend")
    try { npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." } }
    finally { Pop-Location }
} else {
    Write-Host "Using the existing frontend dependencies." -ForegroundColor DarkGray
}

foreach ($port in @(8000, 5173)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { throw "Port $port is already in use. Close the existing BreastCare AI server window before starting another copy." }
}

$backendCommand = "Set-Location '$PSScriptRoot\backend'; & '$backendPython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "Set-Location '$PSScriptRoot\frontend'; npm run dev -- --host 127.0.0.1"
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendCommand) -WindowStyle Normal
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCommand) -WindowStyle Normal
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "API docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "To stop BreastCare AI, press Ctrl+C in both opened server windows or close them." -ForegroundColor Cyan
