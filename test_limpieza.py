"""
Script para probar la limpieza de datos
"""
import sys
sys.path.insert(0, '.sistema')

import pandas as pd
from textract import limpiar_datos, validar_y_multiplicar

# Cargar datos raw
csv_path = ".sistema/datos_raw.csv"
print(f"Cargando: {csv_path}\n")
df_raw = pd.read_csv(csv_path, encoding='utf-8-sig')

print("="*60)
print("DATOS RAW:")
print("="*60)
print(df_raw.to_string(index=False))
print(f"\nColumnas: {list(df_raw.columns)}")

# Limpiar datos
print("\n" + "="*60)
print("LIMPIANDO DATOS (ENTRADA):")
print("="*60)
df_clean = limpiar_datos(df_raw, tipo_operacion='entrada')

print("\n" + "="*60)
print("DATOS LIMPIOS:")
print("="*60)
print(df_clean.to_string(index=False))

# Validar y multiplicar
print("\n" + "="*60)
print("VALIDANDO Y MULTIPLICANDO:")
print("="*60)
df_final = validar_y_multiplicar(df_clean, '.sistema/config.json', tipo_operacion='entrada')

print("\n" + "="*60)
print("RESULTADO FINAL:")
print("="*60)
print(df_final.to_string(index=False))
