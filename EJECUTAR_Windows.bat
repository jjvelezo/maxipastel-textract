@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================
echo    INICIANDO MAXIPASTEL
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Por favor instala Python 3.11 desde python.org
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo No se encuentra el entorno virtual. Creandolo...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        echo.
        pause
        exit /b 1
    )
    echo Entorno virtual creado exitosamente.
    echo.
)

call venv\Scripts\activate.bat

echo Verificando dependencias...
python -c "import gradio" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar las dependencias.
        echo.
        pause
        exit /b 1
    )
    echo Dependencias instaladas exitosamente.
    echo.
)

echo Iniciando aplicacion...
echo.
echo La aplicacion se abrira en tu navegador automaticamente.
echo Para cerrar la aplicacion, cierra esta ventana o presiona Ctrl+C
echo.

python .sistema\app_gradio.py

if errorlevel 1 (
    echo.
    echo ERROR: La aplicacion termino con errores.
    echo.
)

pause
