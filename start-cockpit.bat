@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

start "Grok-Comfy Cockpit Server" "%PYTHON%" -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8787
timeout /t 1 >nul
start "" "http://127.0.0.1:8787"

endlocal
