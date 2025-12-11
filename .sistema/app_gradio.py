import json
from pathlib import Path
import gradio as gr
import pandas as pd
from datetime import datetime
from textract import (
    extract_tables_from_image,
    limpiar_datos,
    validar_y_multiplicar,
    actualizar_inventario_layout
)


def load_config():
    """Carga la configuración desde config.json"""
    config_path = Path(__file__).parent / 'config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def process_file(files, tipo_operacion, inventario_inicial, fecha_inventario):
    """Procesa los archivos subidos y retorna los resultados"""
    if files is None or len(files) == 0:
        return (
            "⚠️ Por favor, carga al menos un archivo (imagen/PDF del pedido)",
            None,
            "0",
            "0",
            "0",
            None
        )

    if inventario_inicial is None:
        return (
            "⚠️ Por favor, carga el archivo de inventario inicial",
            None,
            "0",
            "0",
            "0",
            None
        )

    if not fecha_inventario:
        return (
            "⚠️ Por favor, selecciona una fecha en el calendario",
            None,
            "0",
            "0",
            "0",
            None
        )

    try:
        config = load_config()
        use_aws = config.get('USAR_AWS', False)

        # Obtener ruta base del proyecto (directorio padre de .sistema)
        base_path = Path(__file__).parent.parent

        # Crear carpeta de uploads
        (base_path / 'uploads').mkdir(exist_ok=True)

        status_msg = "⏳ Iniciando procesamiento...\n\n"

        all_results = []

        for file_path in files:
            file_name = Path(file_path).name
            status_msg += f"📄 Procesando: {file_name}\n"

            # Copiar archivo a uploads
            upload_path = base_path / 'uploads' / file_name
            if str(file_path) != str(upload_path):
                import shutil
                shutil.copy2(file_path, upload_path)

            if use_aws:
                status_msg += "  → Extrayendo con AWS Textract...\n"
                dataframes = extract_tables_from_image(str(upload_path))

                if not dataframes:
                    status_msg += "  ⚠️ No se encontraron tablas\n\n"
                    continue

                # Seleccionar la tabla más grande
                if len(dataframes) > 1:
                    tablas_grandes = [df for df in dataframes if len(df) >= 5]
                    df_raw = max(tablas_grandes if tablas_grandes else dataframes, key=lambda df: len(df))
                else:
                    df_raw = dataframes[0]

                csv_path = Path(__file__).parent / 'datos_raw.csv'
                df_raw.to_csv(csv_path, index=False, encoding='utf-8-sig')
                status_msg += f"  ✓ Extraídas {len(dataframes)} tabla(s)\n"
            else:
                status_msg += "  → Cargando desde CSV...\n"
                csv_path = Path(__file__).parent / 'datos_raw.csv'
                df_raw = pd.read_csv(csv_path, encoding='utf-8-sig')
                status_msg += "  ✓ Datos cargados\n"

            # Limpiar datos (diferente según tipo de operación)
            status_msg += "  → Limpiando datos...\n"
            df_clean = limpiar_datos(df_raw, tipo_operacion=tipo_operacion.lower())
            status_msg += f"  ✓ {len(df_clean)} productos encontrados\n"

            # Validar y multiplicar
            status_msg += "  → Validando productos...\n"
            config_path = Path(__file__).parent / 'config.json'
            df_final = validar_y_multiplicar(df_clean, str(config_path), tipo_operacion=tipo_operacion.lower())
            status_msg += f"  ✓ {len(df_final)} productos validados\n\n"

            all_results.append(df_final)

        # Combinar todos los resultados
        if not all_results:
            return (
                status_msg + "\n❌ No se procesaron archivos exitosamente",
                None,
                "0",
                "0",
                "0"
            )

        df_combined = pd.concat(all_results, ignore_index=True)

        # Exportar a Excel temporal
        output_file = Path(__file__).parent / 'productos_final.xlsx'
        df_combined.to_excel(output_file, index=False, engine='openpyxl')
        status_msg += f"💾 Productos procesados temporalmente\n"

        # Generar nombre de archivo de inventario con fecha en formato DD_MM_YYYY
        # Parsear la fecha del calendario (viene en formato ISO: YYYY-MM-DD o YYYY-MM-DD HH:MM:SS)
        try:
            if ' ' in fecha_inventario:
                fecha_obj = datetime.strptime(fecha_inventario.split()[0], '%Y-%m-%d')
            else:
                fecha_obj = datetime.strptime(fecha_inventario, '%Y-%m-%d')
            fecha_formateada = fecha_obj.strftime('%d_%m_%Y')
        except:
            # Si falla, usar la fecha actual
            fecha_formateada = datetime.now().strftime('%d_%m_%Y')

        # Obtener ruta de Descargas del usuario
        import os
        descargas_path = Path.home() / 'Downloads'
        inventario_output = descargas_path / f'inventario_{fecha_formateada}.xlsx'

        # Actualizar inventario
        if not df_combined.empty:
            result_path = actualizar_inventario_layout(
                df_combined,
                inventario_inicial,
                tipo_operacion=tipo_operacion.lower(),
                output_path=str(inventario_output)
            )
            if result_path:
                # Mostrar ruta de Descargas
                status_msg += f"💾 Inventario guardado en Descargas: inventario_{fecha_formateada}.xlsx\n"
            else:
                status_msg += f"⚠️ Error al guardar inventario\n"

        status_msg += "\n✅ PROCESAMIENTO COMPLETADO"

        # Preparar resultados
        num_productos = str(len(df_combined))
        cantidad_original = f"{df_combined['Cantidad_Original'].sum():.0f}"
        cantidad_final = f"{df_combined['Cantidad_Final'].sum():.0f}"

        # Formatear tabla para visualización
        df_display = df_combined[['Producto', 'Cantidad_Original', 'Multiplicador', 'Cantidad_Final', 'Categoria']].copy()
        df_display.columns = ['Producto', 'Cantidad', 'Multiplicador', 'Total', 'Categoría']

        # Retornar ruta de Descargas
        ruta_amigable = f"Descargas/inventario_{fecha_formateada}.xlsx"

        return (
            status_msg,
            df_display,
            num_productos,
            cantidad_original,
            cantidad_final,
            ruta_amigable
        )

    except FileNotFoundError as e:
        return (
            f"❌ Error: Archivo no encontrado\n{str(e)}",
            None,
            "",
            "",
            "",
            None
        )
    except Exception as e:
        import traceback
        error_msg = f"❌ Error al procesar:\n{str(e)}\n\n{traceback.format_exc()}"
        return (
            error_msg,
            None,
            "",
            "",
            "",
            None
        )


# CSS mejorado - Diseño oscuro moderno con principios UX/UI
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-primary: #0f1419;
    --bg-secondary: #1a1f2e;
    --bg-tertiary: #252d3d;
    --border-primary: #2d3748;
    --border-accent: #4a9eff;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-primary: #4a9eff;
    --accent-hover: #3b82f6;
    --success: #10b981;
    --warning: #f59e0b;
    --spacing-unit: 8px;
}

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.gradio-container {
    background: var(--bg-primary) !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
    padding: calc(var(--spacing-unit) * 3) !important;
}

#component-0 {
    background: var(--bg-primary) !important;
}

.main {
    background: var(--bg-primary) !important;
}

/* Header con jerarquía visual clara */
#header-box {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 16px;
    padding: calc(var(--spacing-unit) * 4) calc(var(--spacing-unit) * 3);
    margin-bottom: calc(var(--spacing-unit) * 4);
    border: 1px solid var(--border-primary);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

#main-title {
    font-size: 2.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    text-align: center;
    margin: 0;
    line-height: 1.2;
}

#subtitle {
    font-size: 0.95rem;
    color: var(--text-secondary);
    text-align: center;
    margin-top: calc(var(--spacing-unit) * 1.5);
    letter-spacing: 0.02em;
    font-weight: 400;
}

/* Selector de operación - GRANDE Y MUY VISIBLE */
#operation-selector {
    background: var(--bg-secondary) !important;
    border: 3px solid var(--accent-primary) !important;
    border-radius: 20px !important;
    padding: calc(var(--spacing-unit) * 6) !important;
    margin-bottom: calc(var(--spacing-unit) * 5) !important;
    box-shadow: 0 8px 32px rgba(74, 158, 255, 0.25), 0 0 0 1px rgba(74, 158, 255, 0.2) !important;
    animation: pulse-border 2s ease-in-out infinite !important;
}

@keyframes pulse-border {
    0%, 100% {
        box-shadow: 0 8px 32px rgba(74, 158, 255, 0.25), 0 0 0 1px rgba(74, 158, 255, 0.2);
    }
    50% {
        box-shadow: 0 12px 40px rgba(74, 158, 255, 0.35), 0 0 0 1px rgba(74, 158, 255, 0.3);
    }
}

.operation-title {
    color: var(--text-primary) !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    margin-bottom: calc(var(--spacing-unit) * 4) !important;
    text-align: center !important;
    letter-spacing: 0.02em !important;
    text-transform: uppercase !important;
}

/* Secciones con espaciado consistente (8px grid) */
.upload-section {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 12px !important;
    padding: calc(var(--spacing-unit) * 3) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    transition: all 0.2s ease !important;
}

.upload-section:hover {
    border-color: var(--border-accent) !important;
}

/* Cards con micro-interacciones */
.stat-card {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 12px !important;
    padding: calc(var(--spacing-unit) * 3) calc(var(--spacing-unit) * 2) !important;
    text-align: center !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
}

.stat-card:hover {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 4px 16px rgba(74, 158, 255, 0.2) !important;
    transform: translateY(-2px) !important;
}

.stat-label {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-weight: 600 !important;
    margin-bottom: calc(var(--spacing-unit) * 1.5) !important;
}

.stat-value {
    color: var(--accent-primary) !important;
    font-size: 2.25rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    letter-spacing: -0.02em !important;
}

/* Títulos de sección con mejor jerarquía */
.section-title {
    color: var(--text-primary) !important;
    font-size: 0.875rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-weight: 600 !important;
    margin-bottom: calc(var(--spacing-unit) * 2) !important;
    padding-bottom: calc(var(--spacing-unit) * 1.5) !important;
    border-bottom: 1px solid var(--border-primary) !important;
}

/* Status output con legibilidad mejorada */
#status-output {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 12px !important;
    padding: calc(var(--spacing-unit) * 2.5) !important;
    font-family: 'JetBrains Mono', 'SF Mono', 'Courier New', monospace !important;
    font-size: 0.875rem !important;
    color: var(--text-secondary) !important;
    line-height: 1.7 !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2) !important;
}

/* Botón principal con estados claros */
#process-btn {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-hover) 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: calc(var(--spacing-unit) * 2) calc(var(--spacing-unit) * 4) !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    text-transform: uppercase !important;
    color: #ffffff !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 12px rgba(74, 158, 255, 0.3), 0 2px 4px rgba(0, 0, 0, 0.2) !important;
    width: 100% !important;
}

#process-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(74, 158, 255, 0.4), 0 2px 4px rgba(0, 0, 0, 0.2) !important;
}

#process-btn:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3) !important;
}

/* File upload con estado visual claro */
.file-upload {
    border: 2px dashed var(--border-primary) !important;
    border-radius: 12px !important;
    background: var(--bg-tertiary) !important;
    transition: all 0.2s ease !important;
    padding: calc(var(--spacing-unit) * 3) !important;
    min-height: 120px !important;
}

.file-upload:hover {
    border-color: var(--accent-primary) !important;
    background: rgba(74, 158, 255, 0.05) !important;
}

/* Tabla con contraste adecuado */
.dataframe {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
}

.dataframe thead {
    background: var(--bg-tertiary) !important;
}

.dataframe th {
    background: var(--bg-tertiary) !important;
    color: var(--text-primary) !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em !important;
    font-weight: 600 !important;
    padding: calc(var(--spacing-unit) * 2) calc(var(--spacing-unit) * 1.5) !important;
    border-color: var(--border-primary) !important;
}

.dataframe td {
    border-color: var(--border-primary) !important;
    color: var(--text-secondary) !important;
    padding: calc(var(--spacing-unit) * 1.5) !important;
    background: var(--bg-secondary) !important;
}

.dataframe tr:hover td {
    background: var(--bg-tertiary) !important;
}

/* Radio buttons - BOTONES GRANDES Y MUY VISIBLES */
.svelte-1gfkn6j {
    gap: calc(var(--spacing-unit) * 4) !important;
    display: flex !important;
    justify-content: center !important;
    flex-wrap: wrap !important;
}

label.svelte-1gfkn6j {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    padding: calc(var(--spacing-unit) * 5) calc(var(--spacing-unit) * 8) !important;
    background: var(--bg-tertiary) !important;
    border: 3px solid var(--border-primary) !important;
    border-radius: 16px !important;
    cursor: pointer !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    min-width: 280px !important;
    text-align: center !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
}

label.svelte-1gfkn6j:hover {
    background: rgba(74, 158, 255, 0.15) !important;
    border-color: var(--accent-primary) !important;
    color: #ffffff !important;
    transform: translateY(-4px) scale(1.05) !important;
    box-shadow: 0 8px 24px rgba(74, 158, 255, 0.4) !important;
}

input[type="radio"]:checked + label.svelte-1gfkn6j {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-hover) 100%) !important;
    color: #ffffff !important;
    border-color: var(--accent-primary) !important;
    box-shadow: 0 8px 32px rgba(74, 158, 255, 0.5), 0 0 0 3px rgba(74, 158, 255, 0.2) !important;
    transform: scale(1.08) !important;
}

/* Ajustes de accesibilidad */
*:focus-visible {
    outline: 2px solid var(--accent-primary) !important;
    outline-offset: 2px !important;
}

/* Scrollbar personalizado */
::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-primary);
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--accent-primary);
}
"""

# Crear interfaz
with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as demo:

    # Header
    with gr.Group(elem_id="header-box"):
        gr.HTML('<h1 id="main-title">MAXIPASTEL</h1>')
        gr.HTML('<p id="subtitle">SISTEMA DE PROCESAMIENTO DE PEDIDOS</p>')

    # Selector de tipo de operación - PROMINENTE Y GRANDE
    with gr.Group(elem_id="operation-selector"):
        gr.HTML('<div class="operation-title">📋 SELECCIONA EL TIPO DE OPERACIÓN</div>')
        tipo_operacion = gr.Radio(
            choices=["Entrada", "Salida"],
            value=None,
            label="",
            info="Elige el tipo de movimiento de inventario",
            elem_classes="operation-radio"
        )

    # Contenedor principal - oculto hasta seleccionar operación
    main_content = gr.Column(visible=False)

    with main_content:
        with gr.Row():
            # Columna izquierda
            with gr.Column(scale=1):
                # Upload inventario inicial
                gr.HTML('<div class="section-title">📊 ARCHIVO DE INVENTARIO INICIAL</div>')
                with gr.Group(elem_classes="upload-section"):
                    inventario_input = gr.File(
                        label="Sube tu archivo de inventario actual (.xlsx)",
                        file_count="single",
                        file_types=[".xlsx"],
                        elem_classes="file-upload"
                    )

                # Campo de fecha - Calendario
                gr.HTML('<div class="section-title" style="margin-top: 1.5rem;">📅 FECHA DEL INVENTARIO</div>')
                with gr.Group(elem_classes="upload-section"):
                    fecha_input = gr.DateTime(
                        label="Selecciona la fecha del inventario",
                        include_time=False,
                        type="string"
                    )

                # Upload pedidos
                gr.HTML('<div class="section-title" style="margin-top: 1.5rem;">📤 ARCHIVOS DE PEDIDOS</div>')
                with gr.Group(elem_classes="upload-section"):
                    file_input = gr.File(
                        label="Arrastra imágenes/PDFs de pedidos aquí",
                        file_count="multiple",
                        file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                        elem_classes="file-upload"
                    )

                    process_btn = gr.Button(
                        "PROCESAR",
                        elem_id="process-btn",
                        size="lg"
                    )

                # Estadísticas
                gr.HTML('<div class="section-title" style="margin-top: 2rem;">📊 ESTADÍSTICAS</div>')
                with gr.Row():
                    with gr.Column():
                        with gr.Group(elem_classes="stat-card"):
                            gr.HTML('<div class="stat-label">Total de Productos</div>')
                            num_productos = gr.HTML('<div class="stat-value">0</div>')

                # Variables ocultas para mantener compatibilidad
                cantidad_original = gr.HTML(visible=False)
                cantidad_final = gr.HTML(visible=False)

            # Columna derecha
            with gr.Column(scale=2):
                # Estado
                gr.HTML('<div class="section-title">⚡ ESTADO DEL PROCESO</div>')
                status_output = gr.Textbox(
                    value="Esperando archivos...",
                    show_label=False,
                    lines=12,
                    max_lines=20,
                    interactive=False,
                    elem_id="status-output"
                )

                # Resultados
                gr.HTML('<div class="section-title" style="margin-top: 2rem;">📋 TABLA DE RESULTADOS</div>')
                results_table = gr.Dataframe(
                    headers=["Producto", "Cantidad", "Multiplicador", "Total", "Categoría"],
                    interactive=False,
                    wrap=True,
                    elem_classes="dataframe"
                )

                # Archivo generado
                gr.HTML('<div class="section-title" style="margin-top: 2rem;">📥 ARCHIVO GENERADO</div>')
                archivo_generado = gr.Textbox(
                    label="Inventario actualizado guardado en:",
                    interactive=False,
                    lines=2
                )

    # Event handler para mostrar contenido al seleccionar operación
    def mostrar_contenido(operacion):
        """Muestra el contenido principal cuando se selecciona una operación"""
        if operacion is None:
            return gr.update(visible=False)
        return gr.update(visible=True)

    tipo_operacion.change(
        fn=mostrar_contenido,
        inputs=[tipo_operacion],
        outputs=[main_content]
    )

    # Event handler
    def update_stats(status, table, n_prod, cant_orig, cant_final, archivo):
        """Actualiza las estadísticas con HTML"""
        n_prod_html = f'<div class="stat-value">{n_prod}</div>'
        cant_orig_html = f'<div class="stat-value">{cant_orig}</div>'
        cant_final_html = f'<div class="stat-value">{cant_final}</div>'
        return status, table, n_prod_html, cant_orig_html, cant_final_html, archivo

    process_btn.click(
        fn=process_file,
        inputs=[file_input, tipo_operacion, inventario_input, fecha_input],
        outputs=[status_output, results_table, num_productos, cantidad_original, cantidad_final, archivo_generado]
    ).then(
        fn=update_stats,
        inputs=[status_output, results_table, num_productos, cantidad_original, cantidad_final, archivo_generado],
        outputs=[status_output, results_table, num_productos, cantidad_original, cantidad_final, archivo_generado]
    )


if __name__ == "__main__":
    # Obtener ruta base del proyecto
    base_path = Path(__file__).parent.parent

    # Crear carpeta uploads
    (base_path / 'uploads').mkdir(exist_ok=True)

    # Lanzar aplicación
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True
    )
