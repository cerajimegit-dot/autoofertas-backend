#!/usr/bin/env python
import sqlite3
import sys

db_path = 'db.sqlite3'
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    # Get first enterprise
    c.execute('SELECT id, name FROM core_enterprise ORDER BY id LIMIT 1')
    result = c.fetchone()
    
    if not result:
        print('ERROR: No enterprise found')
        sys.exit(1)
    
    ent_id, ent_name = result
    
    # Check and update brands
    c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL')
    orphan_brands = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM core_brand')
    total_brands = c.fetchone()[0]
    
    if orphan_brands > 0:
        c.execute('UPDATE core_brand SET enterprise_id = ? WHERE enterprise_id IS NULL', (ent_id,))
        print(f'Updated {orphan_brands} orphaned brands')
    
    # Check and update vehicles
    c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL')
    orphan_vehicles = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM core_vehicle')
    total_vehicles = c.fetchone()[0]
    
    if orphan_vehicles > 0:
        c.execute('UPDATE core_vehicle SET enterprise_id = ? WHERE enterprise_id IS NULL', (ent_id,))
        print(f'Updated {orphan_vehicles} orphaned vehicles')
    
    conn.commit()
    print(f'SUCCESS: All data linked to enterprise "{ent_name}" (ID: {ent_id})')
    print(f'Brands: {total_brands} total')
    print(f'Vehicles: {total_vehicles} total')
    
except Exception as e:
    conn.rollback()
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    conn.close()
