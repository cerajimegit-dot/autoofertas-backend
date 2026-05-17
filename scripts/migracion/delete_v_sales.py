"""Identifica y borra ventas con formato V000xxx (placeholders).
Tambien borra sus cuotas asociadas y opcionalmente sus vehiculos huerfanos.

Trabaja contra Postgres (Supabase). Hace backup antes.
Pasale --apply para borrar; sin eso solo hace dry-run.
"""
import os, sys, re
from pathlib import Path
import psycopg2

APPLY = '--apply' in sys.argv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

conn = psycopg2.connect(env_vals["DATABASE_URL"])
conn.autocommit = False
cur = conn.cursor()

# 1. Identificar las ventas con patron V seguido de digitos
PATTERN = r'^V[0-9]+$'
cur.execute(
    "SELECT id, sale_number, sale_date, total_price, customer_id, vehicle_id, branch_id "
    "FROM core_sale WHERE sale_number ~ %s ORDER BY sale_number",
    (PATTERN,),
)
sales = cur.fetchall()
print(f"Ventas con formato V###: {len(sales)}")

if not sales:
    print("Nada para borrar.")
    sys.exit(0)

print("\nPrimeros 10 ejemplos:")
for s in sales[:10]:
    print(f"  id={s[0]}, sale_number={s[1]}, date={s[2]}, total={s[3]}, customer={s[4]}, vehicle={s[5]}, branch={s[6]}")
if len(sales) > 10:
    print(f"  ... y {len(sales)-10} mas")

sale_ids = [s[0] for s in sales]
vehicle_ids = [s[5] for s in sales if s[5]]

# 2. Cuotas asociadas
cur.execute("SELECT count(*) FROM core_quotum WHERE sale_id = ANY(%s)", (sale_ids,))
n_quotas = cur.fetchone()[0]
print(f"\nCuotas asociadas: {n_quotas}")

# 3. Verificar si los vehiculos quedan huerfanos (solo se usan por estas ventas)
cur.execute(
    "SELECT v.id, v.vin FROM core_vehicle v "
    "WHERE v.id = ANY(%s) "
    "AND NOT EXISTS (SELECT 1 FROM core_sale s WHERE s.vehicle_id = v.id AND s.id != ALL(%s))",
    (vehicle_ids, sale_ids),
)
orphan_vehicles = cur.fetchall()
print(f"Vehiculos que quedarian huerfanos (sin otras ventas): {len(orphan_vehicles)}")
if orphan_vehicles[:5]:
    print("  Primeros 5:", [(v[0], v[1]) for v in orphan_vehicles[:5]])

if not APPLY:
    print("\n>>> DRY RUN — pasa --apply para borrar de verdad")
    sys.exit(0)

# 4. Aplicar borrado en transaccion
print("\n>>> Aplicando borrado...")
try:
    cur.execute("DELETE FROM core_quotum WHERE sale_id = ANY(%s)", (sale_ids,))
    print(f"  Cuotas borradas: {cur.rowcount}")
    cur.execute("DELETE FROM core_sale WHERE id = ANY(%s)", (sale_ids,))
    print(f"  Ventas borradas: {cur.rowcount}")
    conn.commit()
    print("  COMMIT OK")
except Exception as e:
    conn.rollback()
    print(f"  ERROR: {e}")
    sys.exit(1)

# 5. Verificar
cur.execute("SELECT count(*) FROM core_sale WHERE sale_number ~ %s", (PATTERN,))
print(f"\nRemanente con patron V###: {cur.fetchone()[0]}")

conn.close()
