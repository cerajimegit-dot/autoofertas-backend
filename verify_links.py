#!/usr/bin/env python
import sqlite3
import sys

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Verificar marcas sin empresa
c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL')
orphan_brands = c.fetchone()[0]

# Verificar vehículos sin empresa
c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL')
orphan_vehicles = c.fetchone()[0]

# Total de marcas
c.execute('SELECT COUNT(*) FROM core_brand')
total_brands = c.fetchone()[0]

# Total de vehículos
c.execute('SELECT COUNT(*) FROM core_vehicle')
total_vehicles = c.fetchone()[0]

print(f'Orphaned brands: {orphan_brands}/{total_brands}')
print(f'Orphaned vehicles: {orphan_vehicles}/{total_vehicles}')

conn.close()

sys.exit(0)
