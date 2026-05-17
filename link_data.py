import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / 'db.sqlite3'

def link_data():
    """Vincula vehículos y marcas con la empresa de pruebas"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    result = {
        'status': 'success',
        'messages': []
    }
    
    try:
        # 1. Obtener empresa
        c.execute('SELECT id, name FROM core_enterprise LIMIT 1')
        enterprise = c.fetchone()
        if not enterprise:
            return {'status': 'error', 'message': 'No enterprises found'}
        
        ent_id, ent_name = enterprise
        result['messages'].append(f'Enterprise: {ent_name} (ID: {ent_id})')
        
        # 2. Actualizar marcas
        c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL')
        orphan_brands = c.fetchone()[0]
        
        if orphan_brands > 0:
            c.execute(
                'UPDATE core_brand SET enterprise_id = ? WHERE enterprise_id IS NULL',
                (ent_id,)
            )
            result['messages'].append(f'Brands updated: {orphan_brands}')
        
        c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id = ?', (ent_id,))
        total_brands = c.fetchone()[0]
        result['messages'].append(f'Total brands: {total_brands}')
        
        # 3. Actualizar vehículos
        c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL')
        orphan_vehicles = c.fetchone()[0]
        
        if orphan_vehicles > 0:
            c.execute(
                'UPDATE core_vehicle SET enterprise_id = ? WHERE enterprise_id IS NULL',
                (ent_id,)
            )
            result['messages'].append(f'Vehicles updated: {orphan_vehicles}')
        
        c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id = ?', (ent_id,))
        total_vehicles = c.fetchone()[0]
        result['messages'].append(f'Total vehicles: {total_vehicles}')
        
        result['enterprise'] = ent_name
        result['brands'] = total_brands
        result['vehicles'] = total_vehicles
        
        conn.commit()
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    finally:
        conn.close()
    
    return result

if __name__ == '__main__':
    result = link_data()
    print(json.dumps(result, indent=2, ensure_ascii=False))
