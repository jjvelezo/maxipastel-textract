#!/bin/bash

# Cambiar al directorio donde está el script
cd "$(dirname "$0")"

echo "========================================"
echo "   INICIANDO MAXIPASTEL"
echo "========================================"
echo ""

# Verificar si existe Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no está instalado."
    echo "Por favor instala Python 3.11 desde python.org"
    echo ""
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Verificar si existe el entorno virtual
if [ ! -f "venv/bin/activate" ]; then
    echo "No se encuentra el entorno virtual. Creándolo..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: No se pudo crear el entorno virtual."
        echo ""
        read -p "Presiona Enter para salir..."
        exit 1
    fi
    echo "Entorno virtual creado exitosamente."
    echo ""
fi

# Activar entorno virtual
source venv/bin/activate

# Verificar si están instaladas las dependencias
echo "Verificando dependencias..."
python3 -c "import gradio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Instalando dependencias..."
    python3 -m pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: No se pudieron instalar las dependencias."
        echo ""
        read -p "Presiona Enter para salir..."
        exit 1
    fi
    echo "Dependencias instaladas exitosamente."
    echo ""
fi

# Ejecutar la aplicación
echo "Iniciando aplicación..."
echo ""
echo "La aplicación se abrirá en tu navegador automáticamente."
echo "Para cerrar la aplicación, cierra esta ventana o presiona Ctrl+C"
echo ""

python3 .sistema/app_gradio.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: La aplicación terminó con errores."
    echo ""
fi

read -p "Presiona Enter para salir..."
