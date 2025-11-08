# Interfaz de Usuario - Extractor de Tablas Maxipastel

## Descripción

Interfaz web moderna y minimalista creada con NiceGUI para procesar pedidos de Maxipastel a partir de imágenes o PDFs.

## Características

- **Interfaz amigable**: Diseño limpio y profesional
- **Drag & Drop**: Arrastra archivos directamente a la interfaz
- **Procesamiento automático**: Al cargar un archivo, se procesa inmediatamente
- **Configuración dinámica**: Cambia entre AWS Textract y CSV guardado sin reiniciar
- **Resultados en tiempo real**: Visualiza los resultados en una tabla interactiva
- **Multi-formato**: Soporta PDF, JPG, JPEG, PNG

## Uso

### 1. Ejecutar la aplicación

```bash
python app.py
```

La aplicación se iniciará en `http://localhost:8080`

### 2. Configurar AWS Textract (opcional)

- **Activado**: Procesa el archivo con AWS Textract (requiere credenciales configuradas)
- **Desactivado**: Usa el último CSV guardado (más rápido, sin costos)

Puedes cambiar esta configuración en cualquier momento usando el switch en la interfaz.

### 3. Cargar archivo

Tienes dos opciones:

- **Arrastra y suelta**: Arrastra el archivo PDF/imagen directamente al área de carga
- **Seleccionar archivo**: Haz clic en el área de carga para abrir el selector de archivos

### 4. Ver resultados

Los resultados se mostrarán automáticamente:

- Cantidad de productos procesados
- Cantidad total original y final
- Tabla detallada con:
  - Producto
  - Cantidad original
  - Multiplicador aplicado
  - Cantidad final
  - Categoría

## Archivos generados

- **productos_final.xlsx**: Resultados del procesamiento
- **Inventario_layout.xlsx**: Inventario actualizado con las nuevas entradas
- **datos_raw.csv**: Datos crudos extraídos (si usas AWS Textract)

## Configuración

La configuración se guarda en `config.json`:

```json
{
  "USAR_AWS": false,
  "Pasteles": { ... },
  ...
}
```

- `USAR_AWS`: Define si usar AWS Textract o CSV guardado

## Requisitos

- Python 3.8+
- NiceGUI
- Pandas
- Boto3 (solo si usas AWS Textract)
- PyMuPDF (para procesar PDFs)
- openpyxl (para Excel)

## Ventajas sobre el script de consola

1. **Más fácil de usar**: No requiere editar código
2. **Visual**: Ves los resultados inmediatamente
3. **Configurable en vivo**: Cambia la configuración sin reiniciar
4. **Drag & Drop**: Arrastra archivos directamente
5. **Multiplataforma**: Funciona en cualquier navegador
