@echo off
REM Cap nhat Claude Usage Bar tu GitHub qua HTTP
cd /d "%~dp0"

set "PYCMD="
py -3 -c "import sys" >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD (
    python -c "import sys" >nul 2>nul && set "PYCMD=python"
)

if not defined PYCMD (
    echo.
    echo [!] Khong tim thay Python 3 tren may.
    echo     Vui long cai dat Python 3 tu: https://www.python.org/downloads/
    pause
    exit /b 1
)

%PYCMD% run.py --update
