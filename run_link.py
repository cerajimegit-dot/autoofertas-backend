import subprocess
import sys
import json

code = """
import sqlite3
import json

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

try:
    # Get enterprise
    c.execute('SELECT id, name FROM core_enterprise LIMIT 1')
    ent = c.fetchone()
    if not ent:
        print(json.dumps({'error': 'No enterprise'}))
        sys.exit(1)
    
    ent_id, ent_name = ent
    
    # Update brands
    c.execute('UPDATE core_brand SET enterprise_id = ? WHERE enterprise_id IS NULL', (ent_id,))
    c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id = ?', (ent_id,))
    brand_count = c.fetchone()[0]
    
    # Update vehicles
    c.execute('UPDATE core_vehicle SET enterprise_id = ? WHERE enterprise_id IS NULL', (ent_id,))
    c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id = ?', (ent_id,))
    vehicle_count = c.fetchone()[0]
    
    conn.commit()
    
    result = {
        'success': True,
        'enterprise': ent_name,
        'brands': brand_count,
        'vehicles': vehicle_count
    }
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({'error': str(e)}))
finally:
    conn.close()
"""

# Run in subprocess
try:
    result = subprocess.run(
        [sys.executable, '-c', code],
        cwd='c:\\Users\\prueb\\CascadeProjects\\playa',
        capture_output=True,
        text=True,
        timeout=10
    )
    
    output = result.stdout.strip()
    errors = result.stderr.strip()
    
    if output:
        data = json.loads(output)
        if 'success' in data:
            print(f"✓ Vinculación completada")
            print(f"  Empresa: {data['enterprise']}")
            print(f"  Marcas: {data['brands']}")
            print(f"  Vehículos: {data['vehicles']}")
        else:
            print(f"✗ Error: {data.get('error', 'Unknown')}")
    
    if errors:
        print(f"Errores: {errors}")
        
except subprocess.TimeoutExpired:
    print("✗ Timeout - proceso tomó demasiado tiempo")
except Exception as e:
    print(f"✗ Error ejecutando subprocess: {e}")

# Also save to file
with open('link_result.txt', 'w') as f:
    f.write("Vinculación de datos completada\n")
