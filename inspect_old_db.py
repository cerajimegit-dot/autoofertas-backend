#!/usr/bin/env python
"""
Inspeccionar estructura de la base de datos antigua (stock.db)
"""
import sqlite3
import json

db_path = r'C:\Users\prueb\CascadeProjects\playa\stock.db'

try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Obtener todas las tablas
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    
    print("TABLAS EN stock.db:")
    print("=" * 60)
    
    schema = {}
    
    for table_name in tables:
        table = table_name[0]
        
        # Obtener estructura de la tabla
        c.execute(f"PRAGMA table_info({table})")
        columns = c.fetchall()
        
        # Obtener cantidad de registros
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        
        print(f"\nTabla: {table} ({count} registros)")
        print("-" * 60)
        
        col_info = []
        for col in columns:
            col_id, col_name, col_type, not_null, default, pk = col
            print(f"  - {col_name} ({col_type})")
            col_info.append({
                'name': col_name,
                'type': col_type,
                'pk': bool(pk),
                'not_null': bool(not_null)
            })
        
        schema[table] = {
            'columns': col_info,
            'row_count': count
        }
        
        # Mostrar primeros registros
        if count > 0:
            c.execute(f"SELECT * FROM {table} LIMIT 3")
            sample = c.fetchall()
            print(f"\n  Muestra de datos (primeros 3):")
            for row in sample:
                print(f"    {row}")
    
    conn.close()
    
    # Guardar esquema a archivo
    with open('stock_db_schema.json', 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("Esquema guardado en stock_db_schema.json")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
