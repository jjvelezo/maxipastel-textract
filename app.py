import json
from pathlib import Path
from nicegui import ui, app
import pandas as pd
from textract import (
    extract_tables_from_image,
    limpiar_datos,
    validar_y_multiplicar,
    actualizar_inventario_layout
)

# Variables globales
uploaded_file_path = None
processing_results = None


def load_config():
    """Carga la configuración desde config.json"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)


async def process_file(file_path: str, use_aws: bool, status_label, results_container):
    """Procesa el archivo subido y muestra los resultados"""
    global processing_results

    try:
        status_label.text = 'Procesando...'
        status_label.classes('text-red-400 font-bold')
        results_container.clear()

        if use_aws:
            dataframes = extract_tables_from_image(file_path)

            if not dataframes:
                status_label.text = 'Error: No se encontraron tablas'
                status_label.classes('text-red-500 font-bold')
                return

            # Seleccionar la tabla más grande
            if len(dataframes) > 1:
                tablas_grandes = [df for df in dataframes if len(df) >= 5]
                df_raw = max(tablas_grandes if tablas_grandes else dataframes, key=lambda df: len(df))
            else:
                df_raw = dataframes[0]

            df_raw.to_csv('datos_raw.csv', index=False, encoding='utf-8-sig')
        else:
            df_raw = pd.read_csv('datos_raw.csv', encoding='utf-8-sig')

        # Limpiar y validar
        df_clean = limpiar_datos(df_raw)
        df_final = validar_y_multiplicar(df_clean, 'config.json')

        # Exportar
        output_file = 'productos_final.xlsx'
        df_final.to_excel(output_file, index=False, engine='openpyxl')

        # Actualizar inventario
        if not df_final.empty:
            actualizar_inventario_layout(df_final, 'Inventario_layout.xlsx')

        processing_results = df_final

        # Mostrar resultados
        status_label.text = 'Completado'
        status_label.classes('text-red-500 font-bold')

        with results_container:
            if df_final.empty:
                ui.label('No se encontraron productos').classes('text-orange-400 text-lg')
            else:
                # Estadísticas
                with ui.row().classes('w-full gap-8 mb-6'):
                    with ui.card().classes('flex-1 bg-gray-900 border-2 border-red-500'):
                        ui.label('Total de Productos').classes('text-white text-base font-semibold')
                        ui.label(str(len(df_final))).classes('text-4xl font-bold text-red-500')

                # Tabla de resultados
                columns = [
                    {'name': 'producto', 'label': 'Producto', 'field': 'Producto', 'align': 'left'},
                    {'name': 'cantidad_original', 'label': 'Cantidad', 'field': 'Cantidad_Original', 'align': 'center'},
                    {'name': 'multiplicador', 'label': 'Multiplicador', 'field': 'Multiplicador', 'align': 'center'},
                    {'name': 'cantidad_final', 'label': 'Total', 'field': 'Cantidad_Final', 'align': 'center'},
                    {'name': 'categoria', 'label': 'Categoría', 'field': 'Categoria', 'align': 'left'},
                ]

                rows = df_final.to_dict('records')

                ui.table(
                    columns=columns,
                    rows=rows,
                    row_key='Producto'
                ).classes('w-full').props('dark flat dense')

    except FileNotFoundError as e:
        status_label.text = 'Error: Archivo no encontrado'
        status_label.classes('text-red-500 font-bold')
    except Exception as e:
        status_label.text = 'Error al procesar'
        status_label.classes('text-red-500 font-bold')
        with results_container:
            ui.label(f'Error: {str(e)}').classes('text-red-500 font-semibold')


@ui.page('/')
def main_page():
    """Página principal de la aplicación"""
    global uploaded_file_path

    # Cargar configuración
    config = load_config()
    use_aws = config.get('USAR_AWS', False)

    # Estilos personalizados
    ui.add_head_html('''
        <style>
            body {
                background-color: #000000 !important;
            }
            .nicegui-content {
                background-color: #000000 !important;
            }
        </style>
    ''')

    # Header minimalista
    with ui.header().classes('bg-black border-b-2 border-red-500'):
        with ui.row().classes('w-full max-w-6xl mx-auto items-center justify-between px-6'):
            ui.label('MAXIPASTEL').classes('text-3xl font-bold tracking-wider text-white')
            ui.label('Procesador de Pedidos').classes('text-base text-gray-300')

    # Contenedor principal
    with ui.column().classes('w-full max-w-6xl mx-auto p-8 gap-6'):

        # Card de carga
        with ui.card().classes('w-full p-8 bg-gray-900 border-2 border-red-500'):
            upload_label = ui.label('Arrastra el archivo o haz clic para seleccionar').classes('text-white text-center w-full mb-4 text-lg font-semibold')

            async def handle_upload(e):
                global uploaded_file_path

                file_content = e.content.read()
                file_name = e.name
                file_path = Path('uploads') / file_name
                file_path.parent.mkdir(exist_ok=True)

                with open(file_path, 'wb') as f:
                    f.write(file_content)

                uploaded_file_path = str(file_path)
                upload_label.text = f'{file_name}'
                upload_label.classes('text-red-500 font-mono text-center w-full mb-4 text-lg font-bold')

                config = load_config()
                await process_file(uploaded_file_path, config.get('USAR_AWS', False), status_label, results_container)

            ui.upload(
                on_upload=handle_upload,
                auto_upload=True,
                multiple=False,
                max_file_size=50_000_000
            ).classes('w-full').props('accept=".pdf,.jpg,.jpeg,.png" dark color="grey-8"')

        # Estado
        with ui.card().classes('w-full p-4 bg-gray-900 border-2 border-red-500'):
            status_label = ui.label('Esperando archivo').classes('text-white font-mono text-center w-full font-semibold')

        # Resultados
        with ui.card().classes('w-full p-8 bg-gray-900 border-2 border-red-500'):
            ui.label('RESULTADOS').classes('text-base font-bold mb-6 text-white tracking-wider')
            results_container = ui.column().classes('w-full')


if __name__ in {"__main__", "__mp_main__"}:
    Path('uploads').mkdir(exist_ok=True)

    ui.run(
        title='Maxipastel - Procesador',
        favicon='📊',
        dark=True,
        reload=False,
        port=8080
    )
