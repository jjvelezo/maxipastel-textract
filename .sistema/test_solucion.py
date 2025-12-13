import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import json
import re
from textract import limpiar_datos_entrada, validar_y_multiplicar_entrada

# Cargar datos raw
df_raw = pd.read_csv('datos_raw.csv')
print('=== PASO 1: DATOS RAW ===')
print(f'Total filas: {len(df_raw)}')
pasteles_raw = df_raw[df_raw.iloc[:, 0].str.contains('PASTEL', na=False, case=False)]
print(f'Pasteles en datos_raw: {len(pasteles_raw)}')

# Limpiar datos
print('\n=== PASO 2: LIMPIAR DATOS ===')
df_clean = limpiar_datos_entrada(df_raw)
print(f'Total productos limpios: {len(df_clean)}')
pasteles_clean = df_clean[df_clean['Producto'].str.contains('PASTEL', na=False, case=False)]
print(f'Pasteles en df_clean: {len(pasteles_clean)}')

# Validar y multiplicar
print('\n=== PASO 3: VALIDAR Y MULTIPLICAR ===')
df_validated = validar_y_multiplicar_entrada(df_clean, 'config.json')
print(f'Total productos validados: {len(df_validated)}')
pasteles_validated = df_validated[df_validated['Producto'].str.contains('PASTEL', na=False, case=False)]
print(f'Pasteles en df_validated: {len(pasteles_validated)}')
print('\nPasteles individuales:')
print(pasteles_validated[['Producto', 'Cantidad_Original', 'Multiplicador', 'Cantidad_Final']].to_string())

# Simular agrupación (NUEVA LÓGICA DE ENTRADA)
print('\n=== PASO 4: AGRUPAR POR CATEGORÍA (NUEVA LÓGICA) ===')
df_agrupado = df_validated.groupby('Categoria', as_index=False).agg({
    'Producto': 'first',
    'Cantidad_Original': 'sum',
    'Multiplicador': 'first',
    'Cantidad_Final': 'sum'
})

print(f'Total categorías únicas: {len(df_agrupado)}')
pasteles_agrupado = df_agrupado[df_agrupado['Categoria'] == 'Pasteles']
print(f'\nCategoría Pasteles agrupada:')
print(pasteles_agrupado[['Producto', 'Cantidad_Original', 'Multiplicador', 'Cantidad_Final']].to_string())

print('\n=== RESUMEN ===')
print(f'Pasteles originales (datos_raw): {len(pasteles_raw)}')
print(f'Pasteles después de limpieza: {len(pasteles_clean)}')
print(f'Pasteles después de validar: {len(pasteles_validated)}')
print(f'Cantidad Original Total: {pasteles_validated["Cantidad_Original"].sum()}')
print(f'Cantidad Final Total: {pasteles_validated["Cantidad_Final"].sum()}')
print(f'\nDespués de agrupar por categoría: 1 fila (Pasteles) con {pasteles_agrupado["Cantidad_Final"].iloc[0]} unidades')
