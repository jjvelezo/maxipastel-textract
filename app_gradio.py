import json
from pathlib import Path
import gradio as gr
import pandas as pd
from textract import (
    extract_tables_from_image,
    limpiar_datos,
    validar_y_multiplicar,
    actualizar_inventario_layout
)


def load_config():
    """Carga la configuración desde config.json"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def process_file(files, tipo_operacion):
    """Procesa los archivos subidos y retorna los resultados"""
    if files is None or len(files) == 0:
        return (
            "⚠️ Por favor, carga al menos un archivo",
            None,
            "0",
            "0",
            "0"
        )

    try:
        config = load_config()
        use_aws = config.get('USAR_AWS', False)

        # Crear carpeta de uploads
        Path('uploads').mkdir(exist_ok=True)

        status_msg = "⏳ Iniciando procesamiento...\n\n"

        all_results = []

        for file_path in files:
            file_name = Path(file_path).name
            status_msg += f"📄 Procesando: {file_name}\n"

            # Copiar archivo a uploads
            upload_path = Path('uploads') / file_name
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

                df_raw.to_csv('datos_raw.csv', index=False, encoding='utf-8-sig')
                status_msg += f"  ✓ Extraídas {len(dataframes)} tabla(s)\n"
            else:
                status_msg += "  → Cargando desde CSV...\n"
                df_raw = pd.read_csv('datos_raw.csv', encoding='utf-8-sig')
                status_msg += "  ✓ Datos cargados\n"

            # Limpiar datos
            status_msg += "  → Limpiando datos...\n"
            df_clean = limpiar_datos(df_raw)
            status_msg += f"  ✓ {len(df_clean)} productos encontrados\n"

            # Validar y multiplicar
            status_msg += "  → Validando productos...\n"
            df_final = validar_y_multiplicar(df_clean, 'config.json')
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

        # Exportar a Excel
        output_file = 'productos_final.xlsx'
        df_combined.to_excel(output_file, index=False, engine='openpyxl')
        status_msg += f"💾 Exportado a: {output_file}\n"

        # Actualizar inventario
        if not df_combined.empty:
            actualizar_inventario_layout(df_combined, 'Inventario_layout.xlsx', tipo_operacion=tipo_operacion.lower())
            status_msg += f"💾 Inventario actualizado ({tipo_operacion}): Inventario_layout.xlsx\n"

        status_msg += "\n✅ PROCESAMIENTO COMPLETADO"

        # Preparar resultados
        num_productos = str(len(df_combined))
        cantidad_original = f"{df_combined['Cantidad_Original'].sum():.0f}"
        cantidad_final = f"{df_combined['Cantidad_Final'].sum():.0f}"

        # Formatear tabla para visualización
        df_display = df_combined[['Producto', 'Cantidad_Original', 'Multiplicador', 'Cantidad_Final', 'Categoria']].copy()
        df_display.columns = ['Producto', 'Cantidad', 'Multiplicador', 'Total', 'Categoría']

        return (
            status_msg,
            df_display,
            num_productos,
            cantidad_original,
            cantidad_final
        )

    except FileNotFoundError as e:
        return (
            f"❌ Error: Archivo no encontrado\n{str(e)}",
            None,
            "",
            "",
            ""
        )
    except Exception as e:
        import traceback
        error_msg = f"❌ Error al procesar:\n{str(e)}\n\n{traceback.format_exc()}"
        return (
            error_msg,
            None,
            "",
            "",
            ""
        )


# CSS mejorado
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.gradio-container {
    background: #000000 !important;
    max-width: 1600px !important;
    margin: 0 auto !important;
}

#component-0 {
    background: #000000 !important;
}

.main {
    background: #000000 !important;
}

#header-box {
    background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
    border-radius: 0 0 24px 24px;
    padding: 3rem 2rem;
    margin-bottom: 3rem;
    border: 1px solid #ff3333;
    border-top: none;
    box-shadow: 0 10px 40px rgba(255,51,51,0.3);
}

#main-title {
    font-size: 3.5rem;
    font-weight: 800;
    letter-spacing: 0.4rem;
    color: #ffffff;
    text-align: center;
    margin: 0;
    text-shadow: 0 0 30px rgba(255,51,51,0.5);
}

#subtitle {
    font-size: 1.1rem;
    color: #aaaaaa;
    text-align: center;
    margin-top: 1rem;
    letter-spacing: 0.15rem;
    font-weight: 400;
}

.upload-section {
    background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%) !important;
    border: 2px solid #ff3333 !important;
    border-radius: 16px !important;
    padding: 2rem !important;
}

.stat-card {
    background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%) !important;
    border: 2px solid #ff3333 !important;
    border-radius: 16px !important;
    padding: 2rem 1.5rem !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
}

.stat-card:hover {
    border-color: #ff5555 !important;
    box-shadow: 0 0 20px rgba(255,51,51,0.3) !important;
    transform: translateY(-2px) !important;
}

.stat-label {
    color: #cccccc !important;
    font-size: 0.9rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.15rem !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
}

.stat-value {
    color: #ff3333 !important;
    font-size: 3rem !important;
    font-weight: 800 !important;
    line-height: 1 !important;
    text-shadow: 0 0 20px rgba(255,51,51,0.5) !important;
}

.section-title {
    color: #aaaaaa !important;
    font-size: 0.85rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.2rem !important;
    font-weight: 700 !important;
    margin-bottom: 1.5rem !important;
    padding-bottom: 0.75rem !important;
    border-bottom: 2px solid #ff3333 !important;
}

#status-output {
    background: #1a1a1a !important;
    border: 2px solid #ff3333 !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    font-size: 0.95rem !important;
    color: #ffffff !important;
    line-height: 1.6 !important;
}

#process-btn {
    background: linear-gradient(135deg, #ff3333 0%, #cc0000 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 1rem 3rem !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1rem !important;
    text-transform: uppercase !important;
    color: #ffffff !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(255,51,51,0.4) !important;
}

#process-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(255,51,51,0.6) !important;
}

.file-upload {
    border: 2px dashed #ff3333 !important;
    border-radius: 12px !important;
    background: #1a1a1a !important;
    transition: all 0.3s ease !important;
}

.file-upload:hover {
    border-color: #ff5555 !important;
    background: #2a2a2a !important;
}

.dataframe {
    background: #1a1a1a !important;
    border: 2px solid #ff3333 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

.dataframe thead {
    background: #2a2a2a !important;
}

.dataframe th {
    background: #2a2a2a !important;
    color: #ffffff !important;
    text-transform: uppercase !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.1rem !important;
    font-weight: 700 !important;
    padding: 1rem !important;
    border-color: #ff3333 !important;
}

.dataframe td {
    border-color: #333333 !important;
    color: #ffffff !important;
    padding: 0.75rem 1rem !important;
    background: #1a1a1a !important;
}

.dataframe tr:hover td {
    background: #2a2a2a !important;
}
"""

# Crear interfaz
with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as demo:

    # Header
    with gr.Group(elem_id="header-box"):
        gr.HTML('<h1 id="main-title">MAXIPASTEL</h1>')
        gr.HTML('<p id="subtitle">SISTEMA DE PROCESAMIENTO DE PEDIDOS</p>')

    with gr.Row():
        # Columna izquierda
        with gr.Column(scale=1):
            # Upload
            gr.HTML('<div class="section-title">📤 CARGAR ARCHIVOS</div>')
            with gr.Group(elem_classes="upload-section"):
                file_input = gr.File(
                    label="Arrastra archivos aquí o haz clic",
                    file_count="multiple",
                    file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                    elem_classes="file-upload"
                )

                # Selector de tipo de operación
                tipo_operacion = gr.Radio(
                    choices=["Entrada", "Salida"],
                    value="Entrada",
                    label="Tipo de operación",
                    info="Selecciona si es entrada o salida de inventario"
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

    # Event handler
    def update_stats(status, table, n_prod, cant_orig, cant_final):
        """Actualiza las estadísticas con HTML"""
        n_prod_html = f'<div class="stat-value">{n_prod}</div>'
        cant_orig_html = f'<div class="stat-value">{cant_orig}</div>'
        cant_final_html = f'<div class="stat-value">{cant_final}</div>'
        return status, table, n_prod_html, cant_orig_html, cant_final_html

    process_btn.click(
        fn=process_file,
        inputs=[file_input, tipo_operacion],
        outputs=[status_output, results_table, num_productos, cantidad_original, cantidad_final]
    ).then(
        fn=update_stats,
        inputs=[status_output, results_table, num_productos, cantidad_original, cantidad_final],
        outputs=[status_output, results_table, num_productos, cantidad_original, cantidad_final]
    )


if __name__ == "__main__":
    # Crear carpeta de uploads
    Path('uploads').mkdir(exist_ok=True)

    # Lanzar aplicación
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True
    )
