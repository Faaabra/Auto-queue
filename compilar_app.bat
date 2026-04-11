@echo off
color 0A
echo =======================================================
echo         GENERANDO RUST AUTO-QUEUE LAUNCHER V2
echo =======================================================
echo Por favor, espera. PyInstaller esta convirtiendo el codigo a .exe...
echo Esto puede tomar entre 1 y 2 minutos. No cierres esta ventana.
echo Cerrando versiones anteriores para evitar bloqueos...
taskkill /F /IM "RustAutoQueue.exe" /T >nul 2>&1
taskkill /F /IM "main.exe" /T >nul 2>&1
echo.

python -m PyInstaller --noconsole --uac-admin --onefile --name="RustAutoQueue" --icon="rust.ico" --add-data="rust.ico;." main.py

echo.
echo =======================================================
echo               ¡COMPILACION TERMINADA!
echo.
echo Revisa la carpeta "dist" (que esta aqui al lado)
echo Ahi dentro encontraras tu nuevo "RustAutoQueue.exe" puro.
echo =======================================================
pause
