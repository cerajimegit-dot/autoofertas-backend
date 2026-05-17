#!/usr/bin/env python
"""
Script para inspeccionar archivos ODS en archivos_playa
genera reporte detallado de estructura y contenido
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Agregar path al proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Instalar y importar dependencias
try:
    import ezodf
except ImportError:
    print("📦 Instalando ezodf...")
    os.system(f"{sys.executable} -m pip install ezodf lxml -q")
    import ezodf

try:
    from openpyxl import load_workbook
except ImportError:
    print("📦 Instalando openpyxl...")
    os.system(f"{sys.executable} -m pip install openpyxl -q")
    from openpyxl import load_workbook

ARCHIVOS_DIR = PROJECT_ROOT / "archivos_playa"

def inspect_ods(filepath):
    """Inspecciona archivo ODS en detalle"""
    print(f"\n📋 Inspeccionando: {filepath.name}")
    print("─" * 80)
    
    try:
        doc = ezodf.opendoc(str(filepath))
        file_info = {
            'filename': filepath.name,
            'size_mb': filepath.stat().st_size / (1024 * 1024),
            'sheets': []
        }
        
        for sheet_idx, sheet in enumerate(doc.sheets, 1):
            sheet_info = {
                'name': sheet.name,
                'rows': 0,
                'cols': 0,
                'columns': [],
                'data_preview': [],
                'stats': {}
            }
            
            rows_list = []
            
            for row_idx, row in enumerate(sheet.rows()):
                row_data = []
                for cell in row:
                    try:
                        value = cell.plaintext() if hasattr(cell, 'plaintext') else str(cell)
                    except:
                        value = ""
                    row_data.append(value)
                
                # Guardar todas las filas
                if any(str(v).strip() for v in row_data):
                    rows_list.append(row_data)
            
            if not rows_list:
                print(f"   ⚠️  Hoja {sheet_idx} '{sheet.name}' está vacía")
                continue
            
            # Procesar datos
            headers = rows_list[0] if rows_list else []
            sheet_info['columns'] = [str(h).strip() for h in headers]
            sheet_info['rows'] = len(rows_list) - 1  # Descontar encabezado
            sheet_info['cols'] = len(headers)
            
            # Preview de datos
            sheet_info['data_preview'] = rows_list[1:6]  # Primeros 5 registros
            
            # Estadísticas por columna
            for col_idx, col_name in enumerate(headers):
                col_values = []
                for row_data in rows_list[1:]:
                    if col_idx < len(row_data):
                        val = str(row_data[col_idx]).strip()
                        if val:
                            col_values.append(val)
                
                sheet_info['stats'][str(col_name)] = {
                    'filled': len(col_values),
                    'empty': len(rows_list) - 1 - len(col_values),
                    'sample_values': list(set(col_values[:3]))  # Valores únicos
                }
            
            file_info['sheets'].append(sheet_info)
            
            # Imprimir resumen
            print(f"   ✅ Hoja {sheet_idx}: '{sheet.name}'")
            print(f"      Filas: {sheet_info['rows']}")
            print(f"      Columnas: {sheet_info['cols']}")
            print(f"      Campos: {', '.join(sheet_info['columns'][:5])}")
            
        return file_info
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def print_detailed_report(file_info):
    """Imprime reporte detallado de un archivo"""
    if not file_info:
        return
    
    print(f"\n{'='*80}")
    print(f"DETALLE: {file_info['filename']}")
    print(f"{'='*80}")
    print(f"Tamaño: {file_info['size_mb']:.2f} MB\n")
    
    for sheet in file_info['sheets']:
        print(f"\n📊 HOJA: {sheet['name']}")
        print(f"   Registros: {sheet['rows']}")
        print(f"   Campos: {sheet['cols']}\n")
        
        print("   📌 COLUMNAS:")
        for idx, col in enumerate(sheet['columns'], 1):
            stat = sheet['stats'].get(col, {})
            filled = stat.get('filled', 0)
            empty = stat.get('empty', 0)
            print(f"      {idx:2}. {col:<30} [Llenos: {filled:>4} | Vacíos: {empty:>4}]")
        
        print(f"\n   📋 PREVIEW (primeros 5 registros):")
        print("   " + "─" * 76)
        
        # Imprimir como tabla
        col_widths = [max(len(str(c)), 15) for c in sheet['columns']]
        header = " | ".join(str(c[:w-2]).ljust(w) for c, w in zip(sheet['columns'], col_widths))
        print(f"   {header}")
        print("   " + "─" * 76)
        
        for row in sheet['data_preview']:
            row_parts = []
            for i, w in enumerate(col_widths):
                val = str(row[i] if i < len(row) else "")[:w-2]
                row_parts.append(val.ljust(w))
            row_str = " | ".join(row_parts)
            print(f"   {row_str}")

def main():
    print("\n" + "="*80)
    print("🔍 INSPECCIÓN DE ARCHIVOS - PLAYAS DE AUTOS")
    print("="*80)
    print(f"Directorio: {ARCHIVOS_DIR}")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not ARCHIVOS_DIR.exists():
        print(f"❌ Directorio no encontrado: {ARCHIVOS_DIR}")
        return
    
    # Buscar archivos
    files = sorted([f for f in ARCHIVOS_DIR.glob("*") if f.is_file() and f.suffix.lower() in ['.ods', '.xlsx']])
    
    if not files:
        print(f"❌ No se encontraron archivos .ods o .xlsx")
        return
    
    print(f"📁 Archivos encontrados: {len(files)}\n")
    
    # Inspeccionar cada archivo
    all_info = []
    for filepath in files:
        info = inspect_ods(filepath)
        if info:
            all_info.append(info)
    
    # Imprimir reportes detallados
    for info in all_info:
        print_detailed_report(info)
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DE INSPECCIÓN")
    print("="*80)
    
    total_records = 0
    total_files = len(all_info)
    
    for info in all_info:
        print(f"\n📄 {info['filename']}")
        for sheet in info['sheets']:
            total_records += sheet['rows']
            print(f"   - {sheet['name']}: {sheet['rows']} registros × {sheet['cols']} campos")
    
    print(f"\n{'─'*80}")
    print(f"Total de archivos: {total_files}")
    print(f"Total de registros a cargar: {total_records}")
    print(f"{'─'*80}")
    
    # Implicaciones
    print(f"\n⚠️  IMPLICACIONES DE CARGA:")
    print(f"   1. Stock (Vehículos): Se cargarán en tabla core_vehicle")
    print(f"   2. Ventas: Se cargarán en tabla core_sale")
    print(f"   3. Cuotas: Se cargarán en tabla core_quotum")
    print(f"\n   ✅ Todos los datos son REALES (producción)")
    print(f"   ⚠️  Se recomienda BACKUP antes de importar")
    
    print("\n" + "="*80)
    print("✅ INSPECCIÓN COMPLETADA")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
