@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1 || (
  echo Install Python 3.10+ from https://python.org and try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating venv...
  python -m venv .venv
  call .venv\Scripts\pip install -r requirements.txt
)

call .venv\Scripts\python.exe main.py --check
if errorlevel 1 (
  echo.
  echo Fix the issue above ^(usually OBS Virtual Camera^), then run this again.
  pause
  exit /b 1
)

call .venv\Scripts\python.exe main.py
