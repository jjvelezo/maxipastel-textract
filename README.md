# MaxiPastel - Sistema de Procesamiento de Inventario

Sistema automatizado para procesar pedidos y actualizar inventarios usando reconocimiento de texto en imágenes y PDFs.

---

## Requisitos del Sistema

### Windows
- Windows 10 o superior
- Python 3.11 o superior
- Conexión a Internet (para la primera instalación)

### macOS
- macOS 10.14 o superior
- Python 3.11 o superior
- Conexión a Internet (para la primera instalación)

---

## Instalación

### Paso 1: Instalar Python

#### Windows
1. Descarga Python 3.11 desde [python.org](https://www.python.org/downloads/)
2. Durante la instalación, **marca la casilla "Add Python to PATH"**
3. Completa la instalación

#### macOS
1. Descarga Python 3.11 desde [python.org](https://www.python.org/downloads/)
2. Abre el instalador descargado (.pkg) y sigue las instrucciones
3. Completa la instalación

### Paso 2: Configurar Credenciales de AWS

El sistema utiliza Amazon Textract para extraer texto de imágenes. Necesitas configurar tus credenciales de AWS:

1. Abre una ventana de terminal o símbolo del sistema
2. Ejecuta los siguientes comandos (reemplaza con tus credenciales):

**Windows (CMD):**
```cmd
setx AWS_ACCESS_KEY_ID "tu_access_key_aqui"
setx AWS_SECRET_ACCESS_KEY "tu_secret_key_aqui"
setx AWS_DEFAULT_REGION "us-east-1"
```

**Windows (PowerShell):**
```powershell
[System.Environment]::SetEnvironmentVariable('AWS_ACCESS_KEY_ID', 'tu_access_key_aqui', 'User')
[System.Environment]::SetEnvironmentVariable('AWS_SECRET_ACCESS_KEY', 'tu_secret_key_aqui', 'User')
[System.Environment]::SetEnvironmentVariable('AWS_DEFAULT_REGION', 'us-east-1', 'User')
```

**macOS/Linux:**
```bash
echo 'export AWS_ACCESS_KEY_ID="tu_access_key_aqui"' >> ~/.bash_profile
echo 'export AWS_SECRET_ACCESS_KEY="tu_secret_key_aqui"' >> ~/.bash_profile
echo 'export AWS_DEFAULT_REGION="us-east-1"' >> ~/.bash_profile
source ~/.bash_profile
```

3. **Reinicia tu computadora** para que las variables de entorno tomen efecto

---

## Cómo Usar el Sistema

### Inicio Rápido

#### Windows
1. Haz doble clic en `EJECUTAR_Windows.bat`
2. El sistema se instalará automáticamente la primera vez (puede tardar 2-3 minutos)
3. Se abrirá automáticamente en tu navegador

#### macOS
1. Haz doble clic en `EJECUTAR_Mac.command`
   - Si aparece un mensaje de seguridad, ve a "Preferencias del Sistema" > "Seguridad y Privacidad" y permite ejecutar el archivo
2. El sistema se instalará automáticamente la primera vez (puede tardar 2-3 minutos)
3. Se abrirá automáticamente en tu navegador

### Uso de la Interfaz

1. **Cargar Inventario Inicial:**
   - Haz clic en "Cargar Inventario Layout (Excel)"
   - Selecciona tu archivo de inventario inicial (.xlsx)

2. **Seleccionar Fecha:**
   - Usa el calendario para seleccionar la fecha del inventario

3. **Cargar Imágenes del Pedido:**
   - Haz clic en "Cargar Imágenes/PDFs del Pedido"
   - Selecciona una o varias imágenes/PDFs del pedido
   - Formatos soportados: JPG, PNG, PDF

4. **Seleccionar Tipo de Operación:**
   - **Entrada:** Para cuando recibes productos (se suman al inventario)
   - **Salida:** Para cuando envías productos (se restan del inventario)

5. **Procesar:**
   - Haz clic en "Procesar Pedido"
   - Espera mientras el sistema procesa las imágenes (puede tardar 10-30 segundos)

6. **Descargar Resultado:**
   - Una vez procesado, aparecerá un botón "Descargar Excel"
   - Haz clic para descargar el inventario actualizado

### Resultados

El sistema mostrará:
- **Productos detectados:** Cantidad de productos encontrados en las imágenes
- **Productos procesados:** Cantidad de productos que coinciden con la configuración
- **Productos actualizados:** Cantidad de productos actualizados en el inventario
- **Vista previa:** Tabla con los cambios realizados

---

## Configuración Avanzada

### Archivo de Configuración

El archivo `.sistema/config.json` contiene las reglas de procesamiento:

- **variantes.entrada:** Nombres que el sistema reconocerá en las imágenes
- **variantes.salida:** Nombres que se usarán en el inventario final
- **multiplicador:** Factor de conversión (ejemplo: si viene "PALO DE QUESO X 10 UND", el multiplicador es 10)

### Ejemplo de configuración:

```json
{
  "Palos": {
    "variantes": [
      {
        "entrada": [
          "palo de queso",
          "PALO DE QUESO X 10 UND"
        ],
        "salida": [
          "PALITOS"
        ],
        "multiplicador": 10
      }
    ]
  }
}
```

---

## Solución de Problemas

### "Python no está instalado o no está en el PATH"
- Reinstala Python y asegúrate de marcar "Add Python to PATH"
- En Windows, cierra todas las ventanas y vuelve a intentar

### "ERROR: No se pudo conectar a AWS Textract"
- Verifica que configuraste correctamente las credenciales de AWS
- Asegúrate de haber reiniciado la computadora después de configurar las variables de entorno
- Verifica que las credenciales tengan permisos para usar Textract

### "No se pudieron instalar las dependencias"
- Verifica tu conexión a Internet
- Ejecuta como administrador (Windows) o con sudo (Mac)

### La aplicación no se abre en el navegador
- Abre manualmente tu navegador y ve a: `http://localhost:7860`

### "Permission denied" en macOS
- Abre Terminal y ejecuta:
  ```bash
  chmod +x EJECUTAR_Mac.command
  ```

---

## Archivos Importantes

- `EJECUTAR_Windows.bat` - Ejecutable para Windows
- `EJECUTAR_Mac.command` - Ejecutable para macOS
- `.sistema/config.json` - Configuración de productos
- `.sistema/textract.py` - Motor de procesamiento
- `.sistema/app_gradio.py` - Interfaz web

---

## Notas Importantes

1. **Primera Ejecución:** La primera vez que ejecutes el programa tardará más tiempo (2-5 minutos) porque descarga e instala las dependencias necesarias.

2. **Costos de AWS:** El uso de Amazon Textract tiene un costo asociado. Consulta la página de precios de AWS Textract para más información.

3. **Conexión a Internet:** Necesitas conexión a Internet para:
   - La primera instalación de dependencias
   - Cada vez que proceses imágenes (se conecta a AWS Textract)

4. **Archivos Generados:** Los archivos procesados se guardan automáticamente en la carpeta `uploads/`

---

## Soporte

Si tienes problemas o preguntas sobre el sistema, contacta con el desarrollador.

---

## Versión

**Versión 1.0** - Diciembre 2025
