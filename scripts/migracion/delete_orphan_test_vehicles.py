"""Borra vehiculos huerfanos con VIN tipo VIN0xxxxx (testing).
Dry-run por default; pasale --apply para borrar.
"""
import os, sys
from pathlib import Path
import psycopg2

APPLY = '--apply' in sys.argv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

conn = psycopg2.connect(env_vals["DATABASE_URL"])
cur = conn.cursor()

# Vehiculos test (VIN ~ '^VIN[0-9]+$') que no tienen ventas que los referencien
cur.execute("""
    SELECT v.id, v.vin, v.year, v.color
    FROM core_vehicle v
    WHERE v.vin ~ '^VIN[0-9]+$'
    AND NOT EXISTS (SELECT 1 FROM core_sale s WHERE s.vehicle_id = v.id)
    ORDER BY v.id
""")
rows = cur.fetchall()
print(f"Vehiculos test huerfanos: {len(rows)}")
for r in rows[:15]:
    print(f"  id={r[0]}, vin={r[1]}, year={r[2]}, color={r[3]!r}")
if len(rows) > 15:
    print(f"  ... y {len(rows)-15} mas")

if not APPLY:
    print("\n>>> DRY RUN — pasa --apply para borrar")
    sys.exit(0)

ids = [r[0] for r in rows]
try:
    # Tambien borramos VehicleCost si refiere
    cur.execute("DELETE FROM core_vehiclecost WHERE vehicle_id = ANY(%s)", (ids,))
    print(f"VehicleCosts borrados: {cur.rowcount}")
    cur.execute("DELETE FROM core_vehicle WHERE id = ANY(%s)", (ids,))
    print(f"Vehiculos borrados: {cur.rowcount}")
    conn.commit()
    print("COMMIT OK")
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
conn.close()
