@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virhe: virtuaaliympäristö puuttuu. Käynnistä ensin projektin juuresta Käynnistä.bat.
  pause
  exit /b 1
)

echo Palvelin: http://127.0.0.1:8000
echo Sulje tämä ikkuna kun lopetat.
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
