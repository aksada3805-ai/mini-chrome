@echo off
REM Launcher for Mini Chrome (Windows cmd)
REM Uses project .venv Python if present, otherwise falls back to system python.
setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe
if exist "%VENV_PY%" (
  "%VENV_PY%" "%SCRIPT_DIR%mini_chrome_full.py" %*
) else (
  python "%SCRIPT_DIR%mini_chrome_full.py" %*
)
endlocal
