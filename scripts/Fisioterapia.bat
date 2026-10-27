@echo off
chcp 65001 >nul
cd /d "%~dp0"
set URL=http://127.0.0.1:8765/

if not exist fisioterapia.exe (
  echo No se encuentra fisioterapia.exe en esta carpeta.
  pause
  exit /b 1
)

rem Quita el bloqueo de "archivo descargado" para que Windows no lo detenga
powershell -NoProfile -Command "Unblock-File -Path .\fisioterapia.exe" >nul 2>&1

rem Si ya está en marcha ESTA misma versión, solo abre el navegador. Si es otra versión,
rem el programa se encarga de cerrarla y abrir la nueva.
for /f "delims=" %%v in ('fisioterapia.exe -version') do set NUEVA=%%v
powershell -NoProfile -Command "try { $v = (Invoke-RestMethod -TimeoutSec 1 '%URL%api/changelog').version; if ($v -eq '%NUEVA%') { exit 0 } else { exit 2 } } catch { exit 1 }"
if %errorlevel%==0 (start "" %URL% & exit /b)

echo ============================================
echo   Fisioterapia - NO CIERRES esta ventana
echo   mientras uses la aplicacion.
echo ============================================
fisioterapia.exe
echo.
echo La aplicacion se ha detenido.
pause
