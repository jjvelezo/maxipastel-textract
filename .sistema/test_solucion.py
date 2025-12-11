import sys
import os
sys.path.insert(0, '.')

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from textract import limpiar_datos_salida, validar_y_multiplicar_salida
import pandas as pd

# Cargar datos raw de ambas imagenes
print('=== SIMULACION: Procesando ambas imagenes ===')
print()

# Imagen 1
df1_raw = pd.read_csv('datos_raw.csv', encoding='utf-8-sig')
print('IMAGEN 1 - Limpiando datos...')
df1_clean = limpiar_datos_salida(df1_raw, 'config.json')
print(f'  Encontrados: {len(df1_clean)} productos')

# Imagen 2
df2_raw = pd.read_csv('temp_imagen2.csv', encoding='utf-8-sig')
print('IMAGEN 2 - Limpiando datos...')
df2_clean = limpiar_datos_salida(df2_raw, 'config.json')
print(f'  Encontrados: {len(df2_clean)} productos')

print()
print('=== Validando y asignando nombres de salida ===')
df1_final = validar_y_multiplicar_salida(df1_clean, 'config.json')
df2_final = validar_y_multiplicar_salida(df2_clean, 'config.json')

print()
print('IMAGEN 1 - Productos validados:')
print(df1_final[['Producto', 'Cantidad_Original', 'Categoria']].head(10).to_string(index=False))

print()
print('IMAGEN 2 - Productos validados:')
print(df2_final[['Producto', 'Cantidad_Original', 'Categoria']].to_string(index=False))

# Combinar
df_combined = pd.concat([df1_final, df2_final], ignore_index=True)
print()
print('=== COMBINADOS (antes de eliminar duplicados) ===')
print(f'Total: {len(df_combined)} productos')
palos = df_combined[df_combined['Categoria'] == 'Palos']
print(f'Palos: {len(palos)} filas')
if len(palos) > 0:
    print(palos[['Producto', 'Cantidad_Original']].to_string(index=False))

# Eliminar duplicados
df_final = df_combined.drop_duplicates(subset=['Categoria'], keep='first')
print()
print('=== RESULTADO FINAL (despues de eliminar duplicados) ===')
print(f'Total: {len(df_final)} productos unicos')
palos_final = df_final[df_final['Categoria'] == 'Palos']
if len(palos_final) > 0:
    print('Palos:')
    print(palos_final[['Producto', 'Cantidad_Original']].to_string(index=False))
