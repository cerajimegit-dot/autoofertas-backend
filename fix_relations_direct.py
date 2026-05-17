#!/usr/bin/env python
"""
Script directo con sqlite3 para vincular datos con empresa
"""
import sqlite3
import sys

DB_PATH = 'db.sqlite3'

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("=" * 80)
    print("RELACIONANDO DATOS CON EMPRESA DE PRUEBAS (MÉTODO DIRECTO)")
    print("=" * 80)
    
    # 1. Obtener ID de la primera empresa
    print("\n1. BUSCANDO EMPRESA DE PRUEBAS...")
    print("-" * 80)
    
    c.execute("""
        SELECT id, name, ruc FROM core_enterprise 
        ORDER BY id ASC LIMIT 1
    """)
    
    result = c.fetchone()
    if not result:
        print("ERROR: No hay empresas en la base de datos")
        sys.exit(1)
    
    enterprise_id, enterprise_name, enterprise_ruc = result
    print(f"✓ Empresa encontrada: {enterprise_name} (ID: {enterprise_id}, RUC: {enterprise_ruc})")
    
    # 2. Contar marcas actuales
    print("\n2. MARCAS ANTES DE ACTUALIZAR...")
    print("-" * 80)
    
    c.execute("""
        SELECT COUNT(*) FROM core_brand WHERE enterprise_id = ?
    """, (enterprise_id,))
    
    current_brands = c.fetchone()[0]
    print(f"  Marcas en empresa {enterprise_name}: {current_brands}")
    
    c.execute("""
        SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL
    """)
    
    orphan_brands = c.fetchone()[0]
    print(f"  Marcas sin empresa: {orphan_brands}")
    
    # 3. Actualizar marcas sin empresa
    if orphan_brands > 0:
        print(f"\n  Actualizando {orphan_brands} marcas...")
        c.execute("""
            UPDATE core_brand 
            SET enterprise_id = ?
            WHERE enterprise_id IS NULL
        """, (enterprise_id,))
        conn.commit()
        print(f"  ✓ {c.rowcount} marcas actualizadas")
    
    # 4. Verificar marcas después
    c.execute("""
        SELECT COUNT(*) FROM core_brand WHERE enterprise_id = ?
    """, (enterprise_id,))
    
    new_brands = c.fetchone()[0]
    print(f"  Marcas en empresa {enterprise_name} (después): {new_brands}")
    
    # 5. Contar vehículos actuales
    print("\n3. VEHÍCULOS ANTES DE ACTUALIZAR...")
    print("-" * 80)
    
    c.execute("""
        SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id = ?
    """, (enterprise_id,))
    
    current_vehicles = c.fetchone()[0]
    print(f"  Vehículos en empresa {enterprise_name}: {current_vehicles}")
    
    c.execute("""
        SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL
    """)
    
    orphan_vehicles = c.fetchone()[0]
    print(f"  Vehículos sin empresa: {orphan_vehicles}")
    
    # 6. Actualizar vehículos sin empresa
    if orphan_vehicles > 0:
        print(f"\n  Actualizando {orphan_vehicles} vehículos...")
        c.execute("""
            UPDATE core_vehicle 
            SET enterprise_id = ?
            WHERE enterprise_id IS NULL
        """, (enterprise_id,))
        conn.commit()
        print(f"  ✓ {c.rowcount} vehículos actualizados")
    
    # 7. Verificar vehículos después
    c.execute("""
        SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id = ?
    """, (enterprise_id,))
    
    new_vehicles = c.fetchone()[0]
    print(f"  Vehículos en empresa {enterprise_name} (después): {new_vehicles}")
    
    # 8. Resumen final
    print("\n4. RESUMEN FINAL...")
    print("-" * 80)
    
    c.execute("""
        SELECT e.id, e.name, 
               COUNT(DISTINCT b.id) as marcas,
               COUNT(DISTINCT v.id) as vehículos
        FROM core_enterprise e
        LEFT JOIN core_brand b ON e.id = b.enterprise_id
        LEFT JOIN core_vehicle v ON e.id = v.enterprise_id
        GROUP BY e.id, e.name
        ORDER BY e.id ASC
    """)
    
    print("\n  Empresas y sus datos:")
    for ent_id, ent_name, brand_count, vehicle_count in c.fetchall():
        print(f"    {ent_name} (ID: {ent_id})")
        print(f"      - Marcas: {brand_count}")
        print(f"      - Vehículos: {vehicle_count}")
    
    print("\n✓ ACTUALIZACIÓN COMPLETADA")
    print("=" * 80)
    
    conn.close()
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
