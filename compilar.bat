@echo off
title Empaquetador The goose Brand
echo ==========================================
echo    Empaquetando The goose Brand (PyInstaller)
echo ==========================================
echo.


set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set OUTPUT_BASE=O:\Finanzas\Info Bancos\Pagos Internacionales\The Goose Brand
set "DEFAULT_OUTPUT=%OUTPUT_BASE%"

if "%OUTPUT_BASE%"=="" set "OUTPUT_BASE=%DEFAULT_OUTPUT%"

if not exist "%OUTPUT_BASE%" mkdir "%OUTPUT_BASE%"

echo.
echo La salida se generara en: "%OUTPUT_BASE%"
echo.


echo Asegurando que pyinstaller este instalado...
pip install pyinstaller

echo.
echo Preparando navegador Chromium para empaquetado local...
set PLAYWRIGHT_BROWSERS_PATH=0
playwright install chromium

echo.
echo Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "The goose Brand RPA.spec" del /q "The goose Brand RPA.spec"   

echo.
echo Creando ejecutable directamente en la ruta de destino con icono...
pyinstaller --noconfirm --onedir --windowed --name "The goose Brand RPA" --icon "icono.ico" --distpath "%OUTPUT_BASE%" --collect-all customtkinter main.py

echo.
echo ==========================================
echo    ¡Proceso completado con exito!
echo    La aplicacion esta lista en:
echo    "%OUTPUT_BASE%\The goose Brand RPA"
echo ==========================================
pause