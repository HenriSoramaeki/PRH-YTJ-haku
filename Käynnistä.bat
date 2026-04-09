@echo off
chcp 65001 >nul

cd /d "%~dp0"

if not exist "backend\app\main.py" (
  echo Virhe: Käynnistä.bat pitää olla projektin juurikansiossa ^(PRH haku^).
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo Python ei löydy. Asenna Python 3.12+ osoitteesta https://www.python.org/downloads/
  echo Asennuksessa valitse: "Add python.exe to PATH".
  pause
  exit /b 1
)

REM Ensimmäinen ajo: virtuaaliympäristö ja pip-paketit
if not exist "backend\.venv\Scripts\python.exe" (
  echo Luodaan virtuaaliympäristö ^(ensimmäinen kerta voi kestää hetken^)...
  python -m venv "backend\.venv"
  if errorlevel 1 (
    echo Virtuaaliympäristön luonti epäonnistui.
    pause
    exit /b 1
  )
  call "backend\.venv\Scripts\pip.exe" install -r "backend\requirements.txt"
  if errorlevel 1 (
    echo Riippuvuuksien asennus epäonnistui.
    pause
    exit /b 1
  )
)

REM Käyttöliittymän build jos puuttuu
if not exist "frontend\dist\index.html" (
  where node >nul 2>&1
  if errorlevel 1 (
    echo.
    echo Node.js ei löydy. Asenna Node 20 LTS osoitteesta https://nodejs.org/
    echo TAI rakenna käyttöliittymä kerran toisella koneella ja kopioi kansio frontend\dist tähän.
    pause
    exit /b 1
  )
  echo Rakennetaan käyttöliittymä ^(ensimmäinen kerta voi kestää^)...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    echo npm install epäonnistui.
    pause
    exit /b 1
  )
  call npm run build
  if errorlevel 1 (
    popd
    echo npm run build epäonnistui.
    pause
    exit /b 1
  )
  popd
)

echo.
echo Käynnistetään palvelin ja avataan selain.
echo Osoite on AINA: http://127.0.0.1:8000  ^(portti 8000 mukana^)
echo Älä sulje uutta "Etelä-Karjala ICT" -ikkunaa käytön aikana.
echo.

REM Erillinen .bat toimii luotettavasti myös kun polussa on välilyönti ^(esim. PRH haku^)
start "Etelä-Karjala ICT" "%~dp0backend\run_server.bat"

timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:8000/"

echo Selain pitäisi avautua. Jos sivu ei lataudu, odota 5-10 s ja paina F5.
echo.
echo Lopetus: sulje ikkuna nimeltä "Etelä-Karjala ICT" ^(musta komentorivi^).
pause
