import sqlite3
import os
import json

# Cambiar a directorio correcto
os.chdir(r'c:\Users\prueb\CascadeProjects\playa')

db_path = 'db.sqlite3'

# Conectar a base de datos
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    # Obtener primera empresa
    c.execute('SELECT id, name, ruc FROM core_enterprise ORDER BY id LIMIT 1')
    ent = c.fetchone()
    
    if ent:
        ent_id, ent_name, ent_ruc = ent
        
        # Contar y actualizar marcas
        c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL')
        orphan_brands = c.fetchone()[0]
        
        if orphan_brands > 0:
            c.execute('UPDATE core_brand SET enterprise_id = ? WHERE enterprise_id IS NULL', (ent_id,))
        
        c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id = ?', (ent_id,))
        total_brands = c.fetchone()[0]
        
        # Contar y actualizar vehículos
        c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL')
        orphan_vehicles = c.fetchone()[0]
        
        if orphan_vehicles > 0:
            c.execute('UPDATE core_vehicle SET enterprise_id = ? WHERE enterprise_id IS NULL', (ent_id,))
        
        c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id = ?', (ent_id,))
        total_vehicles = c.fetchone()[0]
        
        # Confirmar cambios
        conn.commit()
        
        # Resultado
        result = {
            'success': True,
            'enterprise': ent_name,
            'ruc': ent_ruc,
            'brands_fixed': orphan_brands,
            'total_brands': total_brands,
            'vehicles_fixed': orphan_vehicles,
            'total_vehicles': total_vehicles
        }
    else:
        result = {'error': 'No enterprise found'}
        
except Exception as e:
    conn.rollback()
    result = {'error': str(e)}
    import traceback
    traceback.print_exc()
finally:
    conn.close()

# Guardar resultado a archivo
with open('LINK_RESULT.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Resultado guardado en LINK_RESULT.json")
print(json.dumps(result, indent=2, ensure_ascii=False))
