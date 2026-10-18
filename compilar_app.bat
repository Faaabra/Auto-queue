@echo off
setlocal
cd /d "%~dp0"
echo Preparando el entorno de compilacion de Rust Auto-Queue...
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto :failed
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath releases RustAutoQueue.spec
if errorlevel 1 goto :failed
echo Compilacion correcta: releases\RustAutoQueue.exe
pause
exit /b 0
:failed
echo ERROR: la compilacion no se ha completado. Revisa el mensaje anterior.
echo Necesitas Python 3.12 o posterior instalado. Cierra la app si el ejecutable esta bloqueado.
pause
exit /b 1
