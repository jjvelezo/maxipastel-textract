# Maxipastel - Procesador de Inventarios

Sistema automatizado para extraer y procesar inventarios de imágenes usando Amazon Textract.

## Descripción

Esta aplicación utiliza Amazon Textract para extraer tablas de imágenes de inventarios, procesa los datos y aplica reglas de negocio configurables para calcular cantidades finales de productos.

## Características

- Extracción automática de tablas desde imágenes usando AWS Textract
- Limpieza y normalización de datos
- Validación de productos contra configuración predefinida
- Aplicación de multiplicadores por categoría
- Exportación a Excel
- Modo offline: posibilidad de trabajar con datos previamente extraídos (ahorro de costos AWS)

## Requisitos

- Python 3.7+
- Cuenta de AWS con acceso a Amazon Textract
- Credenciales de AWS configuradas

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd maxipastel-3
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install boto3 pandas openpyxl
```

4. Configurar credenciales de AWS (archivo ~/.aws/credentials o variables de entorno)

## Configuración

El archivo [config.json](config.json) define las categorías de productos y sus multiplicadores:

```json
{
  "Pasteles": {
    "entrada": ["PASTEL RANCHERO X 6 UND", ...],
    "operacion": "suma",
    "multiplicador": 6,
    "salida": ["pasteles"]
  }
}
```

## Uso

### Modo AWS (con extracción de imagen)

1. Colocar la imagen en el directorio del proyecto
2. Editar [textract.py](textract.py) línea 212:
```python
USAR_AWS = True
image_path = "tu_imagen.jpeg"
```
3. Ejecutar:
```bash
python textract.py
```

### Modo Offline (sin costos AWS)

1. Asegurarse de tener el archivo `datos_raw.csv` generado previamente
2. Editar [textract.py](textract.py) línea 217:
```python
USAR_AWS = False
```
3. Ejecutar:
```bash
python textract.py
```

## Estructura del Proyecto

```
maxipastel-3/
├── textract.py              # Script principal
├── config.json              # Configuración de productos
├── datos_raw.csv           # Datos extraídos (generado)
├── productos_final.xlsx    # Resultado final (generado)
└── README.md
```

## Salida

El script genera:
- `datos_raw.csv`: Datos extraídos de Textract
- `productos_final.xlsx`: Excel con productos validados y cantidades calculadas

## Notas

- La primera ejecución requiere AWS Textract (genera costo)
- Los datos raw se guardan en CSV para reutilización
- Solo se procesan productos que coincidan con `config.json`

## Licencia

Uso privado - Maxipastel
