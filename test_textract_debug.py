"""
Script de prueba para verificar qué detecta AWS Textract del PDF
"""
import sys
sys.path.insert(0, '.sistema')

from textract import extract_tables_from_image
import pandas as pd

# Analizar el PDF
pdf_path = "uploads/ENERO 3.pdf"
print(f"Analizando: {pdf_path}\n")

dataframes = extract_tables_from_image(pdf_path)

print(f"\n{'='*60}")
print(f"RESULTADO: Se encontraron {len(dataframes)} tabla(s)")
print(f"{'='*60}\n")

for idx, df in enumerate(dataframes):
    print(f"TABLA {idx + 1}:")
    print(f"  Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
    print(f"  Columnas: {list(df.columns)}")
    print(f"\n  Contenido completo:")
    print(df.to_string(index=False))
    print(f"\n{'-'*60}\n")

print("\nAnálisis terminado.")
