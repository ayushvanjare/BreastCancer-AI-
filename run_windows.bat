@echo off
setlocal
cd /d "%~dp0"
echo ===========================================
echo   BreastCare AI - Phase 2.2 local launcher
echo ===========================================
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Install Node.js 20 LTS or newer and try again.
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Reinstall Node.js with npm enabled and try again.
  pause
  exit /b 1
)
set "INSTALL_DEPS=0"
if /I "%~1"=="--install-dependencies" set "INSTALL_DEPS=1"
set "BACKEND_ENV=backend\.venv"
if exist backend\.venv_recovered\Scripts\python.exe set "BACKEND_ENV=backend\.venv_recovered"
set "BACKEND_PYTHON=%CD%\%BACKEND_ENV%\Scripts\python.exe"
set "CREATED_BACKEND_ENV=0"
if not exist "%BACKEND_PYTHON%" (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python was not found. Install Python 3.11 or 3.12 and try again.
    pause
    exit /b 1
  )
  echo Creating backend virtual environment...
  python -m venv "%BACKEND_ENV%"
  if errorlevel 1 goto fail
  set "CREATED_BACKEND_ENV=1"
)
if "%CREATED_BACKEND_ENV%"=="1" goto install_backend
if "%INSTALL_DEPS%"=="1" goto install_backend
goto check_frontend
:install_backend
echo Installing backend requirements. PyTorch is not included or changed...
"%BACKEND_PYTHON%" -m pip install -r backend\requirements.txt
if errorlevel 1 goto fail
:check_frontend
if exist frontend\node_modules if "%INSTALL_DEPS%"=="0" goto check_ports
echo Installing frontend dependencies from the lock file...
  pushd frontend
  call npm ci
  if errorlevel 1 (popd & goto fail)
  popd
:check_ports
powershell -NoProfile -Command "$p=Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue; if ($p) { exit 1 }" >nul 2>nul
if errorlevel 1 (
  echo One or both app ports are already in use. Close existing server windows before starting another copy.
  pause
  exit /b 1
)
echo Starting API and frontend in separate windows...
start "BreastCare AI API" cmd /k "cd /d ""%~dp0backend"" && ""%BACKEND_PYTHON%"" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "BreastCare AI Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 127.0.0.1"
echo Frontend: http://localhost:5173
echo API docs: http://127.0.0.1:8000/docs
echo To stop BreastCare AI, press Ctrl+C in both opened server windows or close them.
exit /b 0
:fail
echo Setup failed. Review the error above and see README.md troubleshooting.
pause
exit /b 1
