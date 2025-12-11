import boto3
import pandas as pd
import json
import re
from typing import List, Dict
from pathlib import Path
import sys

def extract_tables_from_image(image_path: str) -> List[pd.DataFrame]:
    """
    Extrae tablas de una imagen o PDF usando Amazon Textract de forma eficiente.

    Args:
        image_path: Ruta a la imagen o PDF local

    Returns:
        Lista de DataFrames, uno por cada tabla encontrada
    """
    # Inicializar cliente de Textract
    textract = boto3.client('textract')

    # Detectar si es PDF
    file_extension = Path(image_path).suffix.lower()

    all_dataframes = []

    if file_extension == '.pdf':
        # Usar PyMuPDF para convertir PDF a imágenes (sin dependencias externas)
        try:
            import fitz  # PyMuPDF
        except ImportError:
            print("\nERROR: La libreria 'PyMuPDF' no esta instalada.")
            print("Por favor instala: pip install PyMuPDF")
            sys.exit(1)

        # Convertir PDF a imágenes (una por página)
        print("Convirtiendo PDF a imagenes...")
        try:
            pdf_document = fitz.open(image_path)
            print(f"Se encontraron {len(pdf_document)} pagina(s)")

            # Procesar cada página
            for page_num in range(len(pdf_document)):
                print(f"Procesando pagina {page_num + 1}/{len(pdf_document)}...")

                # Obtener la página
                page = pdf_document[page_num]

                # Convertir página a imagen (matriz de píxeles)
                pix = page.get_pixmap(dpi=300)

                # Convertir a bytes PNG
                image_bytes = pix.tobytes("png")

                # Llamar a Textract
                response = textract.analyze_document(
                    Document={'Bytes': image_bytes},
                    FeatureTypes=['TABLES']
                )

                # Extraer tablas de esta página
                page_dataframes = parse_tables(response)
                all_dataframes.extend(page_dataframes)

            pdf_document.close()

        except Exception as e:
            print(f"\nERROR: No se pudo convertir el PDF: {str(e)}")
            sys.exit(1)

    else:
        # Es una imagen normal (JPEG, PNG, etc.)
        with open(image_path, 'rb') as document:
            image_bytes = document.read()

        # Llamar a Textract - solo feature TABLES para minimizar costos
        response = textract.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['TABLES']  # Solo tablas, no FORMS ni QUERIES
        )

        # Extraer tablas del response
        all_dataframes = parse_tables(response)

    return all_dataframes


def parse_tables(response: Dict) -> List[pd.DataFrame]:
    """
    Parsea la respuesta de Textract y convierte las tablas a DataFrames.

    Args:
        response: Respuesta de analyze_document

    Returns:
        Lista de DataFrames
    """
    blocks = response['Blocks']

    # Crear diccionario de bloques por ID para acceso rápido
    block_map = {block['Id']: block for block in blocks}

    # Encontrar todos los bloques de tipo TABLE
    table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']

    dataframes = []

    for table in table_blocks:
        # Construir matriz de la tabla
        rows_dict = {}

        if 'Relationships' in table:
            for relationship in table['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for cell_id in relationship['Ids']:
                        cell = block_map[cell_id]
                        if cell['BlockType'] == 'CELL':
                            row_index = cell['RowIndex']
                            col_index = cell['ColumnIndex']

                            # Obtener texto de la celda
                            cell_text = get_cell_text(cell, block_map)

                            # Almacenar en diccionario
                            if row_index not in rows_dict:
                                rows_dict[row_index] = {}
                            rows_dict[row_index][col_index] = cell_text

        # Convertir a DataFrame
        if rows_dict:
            # Ordenar filas y columnas
            sorted_rows = sorted(rows_dict.items())

            # Construir lista de listas
            table_data = []
            for _, row in sorted_rows:
                sorted_cols = sorted(row.items())
                table_data.append([text for _, text in sorted_cols])

            # Crear DataFrame (primera fila como header si existe)
            if len(table_data) > 1:
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
            else:
                df = pd.DataFrame(table_data)

            dataframes.append(df)

    return dataframes


def get_cell_text(cell: Dict, block_map: Dict) -> str:
    """
    Extrae el texto de una celda.

    Args:
        cell: Bloque de celda
        block_map: Diccionario de bloques por ID

    Returns:
        Texto de la celda
    """
    text = ""
    if 'Relationships' in cell:
        for relationship in cell['Relationships']:
            if relationship['Type'] == 'CHILD':
                for word_id in relationship['Ids']:
                    word = block_map.get(word_id)
                    if word and word['BlockType'] == 'WORD':
                        text += word.get('Text', '') + " "
    return text.strip()


def limpiar_datos(df: pd.DataFrame, tipo_operacion: str = 'entrada') -> pd.DataFrame:
    """
    Redirige a la función correcta según el tipo de operación.

    Args:
        df: DataFrame raw extraído de la imagen
        tipo_operacion: 'entrada' o 'salida'

    Returns:
        DataFrame limpio con columnas 'Producto' y 'Cantidad'
    """
    if tipo_operacion.lower() == 'salida':
        config_path = Path(__file__).parent / 'config.json'
        return limpiar_datos_salida(df, str(config_path))
    else:
        return limpiar_datos_entrada(df)


def limpiar_datos_entrada(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el DataFrame para ENTRADA (pedidos).

    COMPORTAMIENTO:
    1. Busca columna de cantidad (palabras clave: 'cantidad', 'cant', 'qty')
    2. Detecta si primera columna es ID numérico (>70% valores numéricos)
       - Si es numérico: usa segunda columna como producto
       - Si no: usa primera columna como producto
    3. Elimina filas vacías y convierte cantidades a números
    4. Limpia prefijos del producto

    Returns:
        DataFrame con columnas: ['Producto', 'Cantidad']
    """
    df_clean = df.copy()

    # Normalizar nombres de columnas
    df_clean.columns = df_clean.columns.str.strip().str.lower()

    # Buscar columna de cantidad
    cantidad_col = None

    # ENTRADA: Busca columna "Cantidad" explícitamente (pedidos con encabezado)
    print("  * Modo ENTRADA: Buscando columna 'Cantidad'...")
    for col in df_clean.columns:
        col_lower = str(col).lower()
        if 'cantidad' in col_lower or 'cant' in col_lower or 'qty' in col_lower or 'unid' in col_lower:
            cantidad_col = col
            print(f"  ✓ Columna de cantidad encontrada: '{col}'")
            break

    if cantidad_col is None:
        # Intentar usar la última columna como cantidad
        if len(df_clean.columns) >= 2:
            cantidad_col = df_clean.columns[-1]
            print(f"  ! No se encontró 'Cantidad', usando última columna: '{cantidad_col}'")
        else:
            raise ValueError(f"No se encontró columna de Cantidad. Columnas: {list(df_clean.columns)}")

    # Detectar si la primera columna es numérica (ID/Referencia)
    # En ese caso, usar la segunda columna como producto
    if len(df_clean.columns) == 0:
        raise ValueError(f"El DataFrame no tiene columnas después de normalizar. DataFrame original tenía: {list(df.columns)}")

    if len(df_clean) == 0:
        raise ValueError(f"El DataFrame no tiene filas después de cargar. Verifica que la imagen tenga contenido.")

    primera_col = df_clean.columns[0]

    # Intentar convertir la primera columna a numérico y ver cuántos valores son válidos
    try:
        primera_col_data = df_clean[primera_col]
        if primera_col_data is None or len(primera_col_data) == 0:
            print(f"  ! ADVERTENCIA: Primera columna '{primera_col}' está vacía")
            porcentaje_numerico = 0
        else:
            valores_numericos = pd.to_numeric(primera_col_data, errors='coerce')
            porcentaje_numerico = valores_numericos.notna().sum() / len(df_clean) if len(df_clean) > 0 else 0
    except Exception as e:
        print(f"  ! Error al analizar primera columna: {e}")
        print(f"  ! Columnas: {list(df_clean.columns)}")
        print(f"  ! Primeras filas del DataFrame:")
        print(df_clean.head())
        porcentaje_numerico = 0

    # Si más del 70% de los valores en la primera columna son numéricos, usar la segunda columna
    if porcentaje_numerico > 0.7 and len(df_clean.columns) > 1:
        print(f"  * Primera columna '{primera_col}' es numerica ({porcentaje_numerico:.0%}), usando segunda columna como Producto")
        producto_col = df_clean.columns[1]
    else:
        print(f"  * Usando primera columna '{primera_col}' como Producto")
        producto_col = primera_col

    # Seleccionar solo esas columnas y renombrar
    df_clean = df_clean[[producto_col, cantidad_col]].copy()
    df_clean.columns = ['Producto', 'Cantidad']

    # Limpiar valores nulos y vacíos
    df_clean = df_clean.dropna(subset=['Producto', 'Cantidad'])
    # Convertir Producto a string antes de usar .str accessor
    df_clean['Producto'] = df_clean['Producto'].astype(str)
    df_clean = df_clean[df_clean['Producto'].str.strip() != '']

    # Convertir cantidad a numérico (reemplazar comas por puntos primero)
    df_clean['Cantidad'] = df_clean['Cantidad'].astype(str).str.replace(',', '.')
    df_clean['Cantidad'] = pd.to_numeric(df_clean['Cantidad'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Cantidad'])

    # Limpiar espacios en producto
    df_clean['Producto'] = df_clean['Producto'].str.strip()

    # Eliminar prefijos numéricos (1., 1-, 14.-, etc.) del inicio del nombre del producto
    # Patrón: número(s) + punto/guión/espacio al inicio
    df_clean['Producto'] = df_clean['Producto'].apply(
        lambda x: re.sub(r'^\d+[\.\-\s]+[\|\s]*', '', x).strip()
    )

    # Eliminar prefijos de error de OCR (I, |, i) al inicio del producto
    df_clean['Producto'] = df_clean['Producto'].apply(
        lambda x: re.sub(r'^[I\|i]\s*', '', x).strip()
    )

    return df_clean.reset_index(drop=True)


def limpiar_datos_salida(df: pd.DataFrame, config_path: str = 'config.json') -> pd.DataFrame:
    """
    Limpia el DataFrame de salida (ventas) filtrando solo productos válidos.

    COMPORTAMIENTO CRÍTICO:
    1. Carga productos válidos desde config.json campo "salida"
    2. Solo extrae líneas que coincidan con productos válidos
    3. Filtra datos irrelevantes (Beneficio, cajero, totales, etc.)
    4. DETECCIÓN INTELIGENTE DE CANTIDAD:
       - Busca en todas las columnas (segunda, tercera, etc.)
       - CASO 1: Si la celda contiene múltiples números separados por espacios
         Ejemplo: "294.800 30" o "57 182.100"
         → Divide por espacios y busca el número ENTERO
       - CASO 2: Si la celda contiene un solo número
         → Verifica si es entero (cantidad) o decimal (precio)
       - Identifica números ENTEROS como cantidad (67, 27, 30)
       - Ignora números con decimales (precios: 294.800, 59.400)
    5. Usa normalización de texto para comparar productos

    Returns:
        DataFrame con columnas: ['Producto', 'Cantidad']
    """
    # Cargar productos válidos
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    productos_validos_salida = set()
    for categoria, info in config.items():
        if not isinstance(info, dict) or 'variantes' not in info:
            continue
        for variante in info['variantes']:
            salidas = variante.get('salida', [])
            for salida in salidas:
                productos_validos_salida.add(normalizar_texto(salida))

    if not productos_validos_salida:
        raise ValueError("No se encontraron productos de salida válidos en config.json")

    print(f"  * Cargados {len(productos_validos_salida)} productos válidos de salida")

    df_clean = df.copy()
    if len(df_clean.columns) > 0:
        df_clean.columns = df_clean.columns.astype(str).str.strip().str.lower()

    resultados = []
    productos_filtrados = []

    for idx, row in df_clean.iterrows():
        # Convertir toda la fila a lista de strings
        valores = [str(v).strip() if pd.notna(v) else '' for v in row.values]

        if not any(valores):
            continue

        # Saltar encabezados con "plu"
        if valores and 'plu' in valores[0].lower():
            continue

        # Buscar producto en primera columna
        if len(valores) >= 2 and valores[0]:
            producto = valores[0]
            producto_normalizado = normalizar_texto(producto)

            # FILTRO: verificar si es producto válido
            es_producto_valido = False
            for producto_config in productos_validos_salida:
                if producto_normalizado in producto_config or producto_config in producto_normalizado:
                    es_producto_valido = True
                    break

            if not es_producto_valido:
                productos_filtrados.append(producto)
                continue

            # DETECCIÓN INTELIGENTE: Buscar la columna con números enteros
            # La cantidad es un número entero (67, 27)
            # El precio tiene decimales (294.800, 59.400)
            cantidad = None

            # Revisar columnas desde la segunda en adelante
            for i in range(1, len(valores)):
                if not valores[i]:
                    continue

                valor_celda = valores[i]

                # CASO 1: La celda contiene múltiples números separados por espacios
                # Ejemplo: "294.800 30" o "57 182.100"
                if ' ' in valor_celda:
                    # Dividir por espacios y buscar números
                    partes = valor_celda.split()
                    for parte in partes:
                        parte_limpia = parte.replace(',', '.')
                        try:
                            num = float(parte_limpia)
                            # Si es entero, es la cantidad
                            if num > 0 and num == int(num):
                                cantidad = int(num)
                                break
                        except (ValueError, TypeError):
                            continue

                    if cantidad is not None:
                        break

                # CASO 2: La celda contiene un solo número
                else:
                    valor_str = valor_celda.replace(',', '.')
                    try:
                        valor_num = float(valor_str)

                        # Si es un número entero (sin decimales significativos)
                        # Ejemplo: 67.0 == 67, pero 59.4 != 59
                        if valor_num > 0 and valor_num == int(valor_num):
                            cantidad = int(valor_num)
                            break
                    except (ValueError, TypeError):
                        continue

            # Si encontramos una cantidad válida, agregar el resultado
            if cantidad is not None and cantidad > 0:
                resultados.append({
                    'Producto': producto,
                    'Cantidad': cantidad
                })
            else:
                # Debug: mostrar qué valores se encontraron
                print(f"  ! No se encontró cantidad entera para '{producto}': valores = {valores[1:]}")

    if productos_filtrados:
        productos_unicos = list(set(productos_filtrados))[:5]
        print(f"  * Filtrados {len(productos_filtrados)} datos no-inventario: {', '.join(productos_unicos)}...")

    if not resultados:
        raise ValueError("No se encontraron productos válidos en los datos de salida")

    df_final = pd.DataFrame(resultados)
    df_final['Producto'] = df_final['Producto'].str.strip()
    df_final['Producto'] = df_final['Producto'].apply(
        lambda x: re.sub(r'^\d+[\.\-\s]+[\|\s]*', '', x).strip()
    )
    df_final['Producto'] = df_final['Producto'].apply(
        lambda x: re.sub(r'^[I\|i]\s*', '', x).strip()
    )

    print(f"  ✓ Procesados {len(df_final)} productos de salida (ventas)")
    return df_final.reset_index(drop=True)


def normalizar_texto(texto: str) -> str:
    """
    Normaliza un texto eliminando espacios, puntos, guiones y caracteres especiales.
    Mantiene números y letras. Convierte todo a minúsculas para facilitar comparaciones.

    Args:
        texto: Texto a normalizar

    Returns:
        Texto normalizado (solo letras y números en minúsculas, sin espacios ni puntuación)
    """
    # Convertir a minúsculas
    texto = texto.lower().strip()

    # Eliminar puntos, guiones, espacios, y caracteres especiales comunes
    # Mantener solo letras y números
    texto_limpio = re.sub(r'[^a-záéíóúñ0-9]', '', texto)

    return texto_limpio


def validar_y_multiplicar(df_clean: pd.DataFrame, config_path: str = 'config.json', tipo_operacion: str = 'entrada') -> pd.DataFrame:
    """
    Redirige a la función correcta según el tipo de operación.
    """
    if tipo_operacion.lower() == 'salida':
        return validar_y_multiplicar_salida(df_clean, config_path)
    else:
        return validar_y_multiplicar_entrada(df_clean, config_path)


def validar_y_multiplicar_entrada(df_clean: pd.DataFrame, config_path: str = 'config.json') -> pd.DataFrame:
    """
    Valida productos contra config.json y MULTIPLICA las cantidades.

    COMPORTAMIENTO:
    1. Busca cada producto en el campo "entrada" de config.json
    2. Usa normalización de texto para comparar
    3. MULTIPLICA la cantidad por el multiplicador definido
       Ejemplo: 2 cajas × multiplicador 12 = 24 unidades
    4. Productos no encontrados: marca como "(no registrado)" con multiplicador 1

    Returns:
        DataFrame con columnas:
        ['Producto', 'Cantidad_Original', 'Multiplicador', 'Cantidad_Final', 'Categoria']
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    resultados = []
    productos_no_encontrados = []

    for _, row in df_clean.iterrows():
        producto = row['Producto']
        cantidad = row['Cantidad']
        producto_normalizado = normalizar_texto(producto)
        encontrado = False

        for categoria, info in config.items():
            if not isinstance(info, dict) or 'variantes' not in info:
                continue

            variantes = info['variantes']
            for variante in variantes:
                entradas = variante.get('entrada', [])
                multiplicador = variante['multiplicador']

                for entrada in entradas:
                    entrada_normalizada = normalizar_texto(entrada)
                    if entrada_normalizada in producto_normalizado or producto_normalizado in entrada_normalizada:
                        cantidad_final = cantidad * multiplicador
                        resultados.append({
                            'Producto': producto,
                            'Cantidad_Original': cantidad,
                            'Multiplicador': multiplicador,
                            'Cantidad_Final': cantidad_final,
                            'Categoria': categoria
                        })
                        encontrado = True
                        break
                if encontrado:
                    break
            if encontrado:
                break

        if not encontrado:
            productos_no_encontrados.append(producto)
            categoria_no_registrada = f"{producto} (no registrado)"
            print(f"  ! Producto no registrado: '{producto}'")
            resultados.append({
                'Producto': producto,
                'Cantidad_Original': cantidad,
                'Multiplicador': 1,
                'Cantidad_Final': cantidad,
                'Categoria': categoria_no_registrada
            })

    if productos_no_encontrados:
        print(f"\n! Se encontraron {len(productos_no_encontrados)} producto(s) no registrado(s) en config.json")

    return pd.DataFrame(resultados)


def validar_y_multiplicar_salida(df_clean: pd.DataFrame, config_path: str = 'config.json') -> pd.DataFrame:
    """
    Valida productos de salida contra config.json SIN multiplicar cantidades.

    COMPORTAMIENTO:
    1. Busca cada producto en el campo "salida" de config.json
    2. Usa normalización de texto para comparar
    3. NO MULTIPLICA la cantidad (siempre multiplicador = 1)
       Las ventas ya vienen en unidades individuales
    4. Productos no encontrados: marca como "(no registrado)"

    Returns:
        DataFrame con columnas:
        ['Producto', 'Cantidad_Original', 'Multiplicador', 'Cantidad_Final', 'Categoria']
        Nota: Multiplicador siempre es 1, Cantidad_Final = Cantidad_Original
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    resultados = []
    productos_no_encontrados = []

    for _, row in df_clean.iterrows():
        producto = row['Producto']
        cantidad = row['Cantidad']
        producto_normalizado = normalizar_texto(producto)
        encontrado = False

        for categoria, info in config.items():
            if not isinstance(info, dict) or 'variantes' not in info:
                continue

            variantes = info['variantes']
            for variante in variantes:
                salidas = variante.get('salida', [])
                if not salidas:
                    continue

                for salida in salidas:
                    salida_normalizada = normalizar_texto(salida)
                    if salida_normalizada in producto_normalizado or producto_normalizado in salida_normalizada:
                        resultados.append({
                            'Producto': producto,  # Mantener el nombre original de la factura
                            'Cantidad_Original': cantidad,
                            'Multiplicador': 1,
                            'Cantidad_Final': cantidad,
                            'Categoria': categoria
                        })
                        encontrado = True
                        break
                if encontrado:
                    break
            if encontrado:
                break

        if not encontrado:
            productos_no_encontrados.append(producto)
            categoria_no_registrada = f"{producto} (no registrado)"
            print(f"  ! Producto de salida no registrado: '{producto}'")
            resultados.append({
                'Producto': producto,
                'Cantidad_Original': cantidad,
                'Multiplicador': 1,
                'Cantidad_Final': cantidad,
                'Categoria': categoria_no_registrada
            })

    if productos_no_encontrados:
        print(f"\n! Se encontraron {len(productos_no_encontrados)} producto(s) de salida no registrado(s)")

    return pd.DataFrame(resultados)


def actualizar_inventario_layout(df_final: pd.DataFrame, layout_path: str = 'Inventario_layout.xlsx', tipo_operacion: str = 'entrada', output_path: str = None) -> str:
    """
    Actualiza el archivo de inventario con las cantidades finales por categoría.

    Preserva TODO el estilo del Excel: bordes, colores, fuentes, espaciado, etc.
    Busca la columna especificada (entrada o salida) en los encabezados y la fila con el nombre de la categoría,
    luego coloca el valor en la intersección.

    Args:
        df_final: DataFrame con las cantidades finales por categoría
        layout_path: Ruta al archivo de inventario inicial (subido por el usuario)
        tipo_operacion: 'entrada' o 'salida' - determina qué columna usar en el Excel
        output_path: Ruta donde guardar el archivo actualizado. Si es None, sobrescribe layout_path

    Returns:
        Ruta del archivo guardado
    """
    from openpyxl import load_workbook
    from copy import copy

    try:
        # Cargar el workbook existente
        wb_original = load_workbook(layout_path, data_only=False, keep_vba=False)
        ws_original = wb_original.active

        # Cargar también con data_only para intentar obtener valores
        wb_valores = load_workbook(layout_path, data_only=True, keep_vba=False)
        ws_valores = wb_valores.active

        # Crear workbook nuevo para resultado final
        wb = load_workbook(layout_path, data_only=False, keep_vba=False)
        ws = wb.active

        # Buscar columnas que contienen "Inv Final" o columna G
        print("  → Identificando columnas con fórmulas a preservar...")
        columnas_con_formulas = set()

        # Buscar en la primera fila (encabezados)
        for col_idx in range(1, ws.max_column + 1):
            header_cell = ws.cell(row=1, column=col_idx)
            if header_cell.value:
                header_text = str(header_cell.value).lower().strip()
                # Si contiene "inv final" o "inventario final"
                if 'inv' in header_text and 'final' in header_text:
                    columnas_con_formulas.add(col_idx)
                    print(f"  ✓ Columna {col_idx} ('{header_cell.value}') mantendrá fórmulas")
            # Columna G (índice 7)
            if col_idx == 7:
                columnas_con_formulas.add(col_idx)
                print(f"  ✓ Columna G (índice {col_idx}) mantendrá fórmulas")

        # Convertir fórmulas a valores EXCEPTO en las columnas identificadas
        print("  → Convirtiendo fórmulas a valores (excepto columnas especiales)...")
        formulas_convertidas = 0
        formulas_preservadas = 0

        for row_idx in range(1, ws.max_row + 1):
            for col_idx in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell_valor = ws_valores.cell(row=row_idx, column=col_idx)

                # Si la celda tiene una fórmula
                if isinstance(cell.value, str) and cell.value.startswith('='):
                    # Si está en una columna que debe preservar fórmulas, NO convertir
                    if col_idx in columnas_con_formulas:
                        formulas_preservadas += 1
                        continue

                    # Convertir a valor
                    if cell_valor.value is not None:
                        cell.value = cell_valor.value
                        formulas_convertidas += 1
                    else:
                        # Si no hay valor, poner 0
                        cell.value = 0
                        formulas_convertidas += 1
                elif cell_valor.value is not None and cell.value != cell_valor.value:
                    # Asegurar que usamos valores, no fórmulas (excepto columnas especiales)
                    if col_idx not in columnas_con_formulas:
                        cell.value = cell_valor.value

        print(f"  ✓ {formulas_convertidas} fórmulas convertidas a valores")
        print(f"  ✓ {formulas_preservadas} fórmulas preservadas (Inv Final, Columna G)")

        # Cerrar workbooks auxiliares
        wb_original.close()
        wb_valores.close()

        # Agrupar por categoría y sumar cantidades finales
        cantidades_por_categoria = df_final.groupby('Categoria')['Cantidad_Final'].sum()

        # Buscar la columna que contiene el tipo de operación en la primera fila (encabezados)
        col_entrada_idx = None
        for col_idx, col in enumerate(ws.iter_cols(min_row=1, max_row=1), start=1):
            cell_value = col[0].value
            if cell_value and str(cell_value).lower().strip() == tipo_operacion.lower():
                col_entrada_idx = col_idx
                break

        if col_entrada_idx is None:
            print(f"  ! No se encontro la columna '{tipo_operacion}' en {layout_path}")
            return

        # Actualizar o crear filas para cada categoría
        for categoria, cantidad in cantidades_por_categoria.items():
            if categoria == 'Sin Categoria':
                continue  # Ignorar productos sin categoría

            # Buscar la fila que contiene el nombre de la categoría en la primera columna
            fila_encontrada = False
            for fila_idx, row in enumerate(ws.iter_rows(min_col=1, max_col=1), start=1):
                cell_value = row[0].value
                if cell_value and str(cell_value).strip() == categoria:
                    # Actualizar la celda en la intersección
                    target_cell = ws.cell(row=fila_idx, column=col_entrada_idx)
                    target_cell.value = cantidad
                    fila_encontrada = True
                    print(f"  + Actualizado '{categoria}': {cantidad}")
                    break

            if not fila_encontrada:
                # Encontrar la última fila con datos reales en la primera columna
                ultima_fila_real = 1
                for fila_idx in range(1, ws.max_row + 1):
                    cell_value = ws.cell(row=fila_idx, column=1).value
                    if cell_value and str(cell_value).strip():
                        ultima_fila_real = fila_idx

                # Crear nueva fila inmediatamente después del último producto
                nueva_fila = ultima_fila_real + 1

                # Copiar estilos de la fila anterior si existe
                if ultima_fila_real > 1:
                    for col_idx in range(1, ws.max_column + 1):
                        celda_anterior = ws.cell(row=ultima_fila_real, column=col_idx)
                        celda_nueva = ws.cell(row=nueva_fila, column=col_idx)

                        # Copiar estilos (bordes, fuente, relleno, alineación)
                        if celda_anterior.has_style:
                            celda_nueva.font = copy(celda_anterior.font)
                            celda_nueva.border = copy(celda_anterior.border)
                            celda_nueva.fill = copy(celda_anterior.fill)
                            celda_nueva.number_format = copy(celda_anterior.number_format)
                            celda_nueva.protection = copy(celda_anterior.protection)
                            celda_nueva.alignment = copy(celda_anterior.alignment)

                # Asignar valores
                ws.cell(row=nueva_fila, column=1).value = categoria
                ws.cell(row=nueva_fila, column=col_entrada_idx).value = cantidad
                print(f"  + Creada nueva categoria '{categoria}': {cantidad}")

        # Guardar el workbook preservando todos los estilos
        save_path = output_path if output_path else layout_path
        wb.save(save_path)
        print(f"\n+ Inventario actualizado exitosamente: '{save_path}'")
        print("  (Se preservaron todos los bordes, colores y estilos del Excel)")
        print("  (Todas las fórmulas fueron convertidas a valores)")

        return save_path

    except FileNotFoundError:
        print(f"\n! ADVERTENCIA: No se encontro el archivo '{layout_path}'")
        return None

    except Exception as e:
        print(f"\nX Error al actualizar inventario: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # ==================== CONFIGURACIÓN ====================
    # Cargar configuración desde config.json
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    USAR_AWS = config.get('USAR_AWS', False)
    #image_path = "WhatsApp Image 2025-11-04 at 10.35.29 PM (1).jpeg"
    image_path = "1 DE NOVIEMBRE 2025 (1).pdf"
    csv_path = "datos_raw.csv"
    # =======================================================

    try:
        if USAR_AWS:
            # PASO 1A: Extraer tablas de la imagen con AWS
            print(f"Analizando imagen: {image_path}")
            print("Extrayendo tablas con Amazon Textract...")

            dataframes = extract_tables_from_image(image_path)

            if not dataframes:
                print("No se encontraron tablas en la imagen")
                exit(1)

            print(f"\nSe encontraron {len(dataframes)} tabla(s)")

            # Si hay múltiples tablas, filtrar y seleccionar la más grande
            # (ignorar tablas pequeñas que son encabezados)
            if len(dataframes) > 1:
                print("Filtrando tablas (ignorando encabezados)...")
                # Filtrar tablas con al menos 5 filas (probablemente son tablas de productos)
                tablas_grandes = [df for df in dataframes if len(df) >= 5]

                if tablas_grandes:
                    # Tomar la tabla más grande
                    df_raw = max(tablas_grandes, key=lambda df: len(df))
                    print(f"Tabla seleccionada: {df_raw.shape[0]} filas x {df_raw.shape[1]} columnas")
                else:
                    # Si no hay tablas grandes, tomar la más grande disponible
                    df_raw = max(dataframes, key=lambda df: len(df))
                    print(f"Tabla seleccionada (sin filtro): {df_raw.shape[0]} filas x {df_raw.shape[1]} columnas")
            else:
                df_raw = dataframes[0]

            # Guardar CSV para reutilización
            df_raw.to_csv('datos_raw.csv', index=False, encoding='utf-8-sig')
            print("DataFrame guardado en 'datos_raw.csv'")
        else:
            # PASO 1B: Cargar desde CSV
            print(f"Cargando datos desde: {csv_path}")
            df_raw = pd.read_csv(csv_path, encoding='utf-8-sig', thousands=None, decimal='.')
            print("Datos cargados exitosamente")

        # Mostrar datos raw
        print(f"\nDimensiones: {df_raw.shape[0]} filas x {df_raw.shape[1]} columnas")
        print("\nVista previa del DataFrame raw:")
        print(df_raw.head(10).to_string(index=False))

        # PASO 2: Limpiar datos (solo producto y cantidad)
        print("\n" + "="*60)
        print("PASO 2: Limpiando datos...")
        df_clean = limpiar_datos(df_raw)
        print(f"Datos limpios: {len(df_clean)} productos encontrados")
        print("\nDataFrame limpio (Producto y Cantidad):")
        print(df_clean.to_string(index=False))

        # PASO 3: Validar contra config.json y multiplicar
        print("\n" + "="*60)
        print("PASO 3: Validando productos y aplicando multiplicador...")
        df_final = validar_y_multiplicar(df_clean, 'config.json')

        if df_final.empty:
            print("\nADVERTENCIA: No se encontraron productos que coincidan con config.json")
            print("\nProductos en el pedido:")
            for producto in df_clean['Producto'].unique():
                print(f"  - {producto}")
        else:
            print(f"\nProductos validados: {len(df_final)}")
            print("\nDataFrame final:")
            print(df_final.to_string(index=False))

        # PASO 4: Exportar a Excel (siempre exportar, incluso si está vacío)
        print("\n" + "="*60)
        print("PASO 4: Exportando a Excel...")
        output_file = 'productos_final.xlsx'
        df_final.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\nArchivo exportado exitosamente: '{output_file}'")

        # PASO 5: Actualizar Inventario_layout.xlsx
        if not df_final.empty:
            print("\n" + "="*60)
            print("PASO 5: Actualizando Inventario_layout.xlsx...")
            # Por defecto usa 'entrada' en el script standalone
            actualizar_inventario_layout(df_final, 'Inventario_layout.xlsx', tipo_operacion='entrada')

            # Resumen
            print("\n" + "="*60)
            print("RESUMEN:")
            print(f"  - Total productos validados: {len(df_final)}")
            print(f"  - Cantidad total original: {df_final['Cantidad_Original'].sum():.0f}")
            print(f"  - Cantidad total final: {df_final['Cantidad_Final'].sum():.0f}")

    except FileNotFoundError as e:
        print(f"Error: No se encontro el archivo - {str(e)}")
    except ValueError as e:
        print(f"Error de validacion: {str(e)}")
    except Exception as e:
        print(f"Error al procesar la imagen: {str(e)}")
        import traceback
        traceback.print_exc()
