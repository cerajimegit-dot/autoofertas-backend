"""Crea indices en Postgres (Supabase) para acelerar las queries mas frecuentes.
CREATE INDEX CONCURRENTLY no bloquea las tablas - se puede correr en produccion.
"""
import os, time
from pathlib import Path
import psycopg2

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

# Para CREATE INDEX CONCURRENTLY se necesita autocommit
conn = psycopg2.connect(env_vals["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

INDEXES = [
    # ===== SALES =====
    ("idx_sale_enterprise", "core_sale", "(enterprise_id)"),
    ("idx_sale_branch_status", "core_sale", "(branch_id, status)"),
    ("idx_sale_sale_date", "core_sale", "(sale_date DESC)"),
    ("idx_sale_customer", "core_sale", "(customer_id)"),
    ("idx_sale_vehicle", "core_sale", "(vehicle_id)"),

    # ===== QUOTAS =====
    ("idx_quotum_enterprise", "core_quotum", "(enterprise_id)"),
    ("idx_quotum_sale", "core_quotum", "(sale_id)"),
    ("idx_quotum_due_date", "core_quotum", "(due_date)"),
    ("idx_quotum_payment_date", "core_quotum", "(payment_date)"),
    ("idx_quotum_status", "core_quotum", "(status)"),
    ("idx_quotum_status_due_date", "core_quotum", "(status, due_date)"),

    # ===== VEHICLES =====
    ("idx_vehicle_enterprise", "core_vehicle", "(enterprise_id)"),
    ("idx_vehicle_branch_state", "core_vehicle", "(branch_id, state)"),
    ("idx_vehicle_vin", "core_vehicle", "(vin)"),
    ("idx_vehicle_brand_model", "core_vehicle", "(brand_id, model_id)"),

    # ===== CUSTOMERS =====
    ("idx_customer_enterprise", "core_customer", "(enterprise_id)"),
    # GIN trigram index para LIKE '%nombre%' — necesita extension pg_trgm
    # Lo intentamos; si la extension no esta, lo saltamos
]

print(f"Creando {len(INDEXES)} indices en Postgres (CONCURRENTLY - sin bloqueo)")
print()
for name, table, cols in INDEXES:
    sql = f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON "{table}" {cols}'
    t0 = time.time()
    try:
        cur.execute(sql)
        print(f"  OK ({(time.time()-t0)*1000:.0f}ms) {name}")
    except Exception as e:
        print(f"  FAIL {name}: {str(e)[:120]}")

# Trigram para busqueda fuzzy de clientes (opcional, requiere extension)
print("\nIntentando crear indice GIN trigram para busqueda fuzzy de clientes...")
try:
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    cur.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_name_trgm
        ON core_customer USING gin ((first_name || ' ' || last_name) gin_trgm_ops)
    """)
    print("  OK: indice trigram creado")
except Exception as e:
    print(f"  SKIP: {str(e)[:120]}")

# Verificar tamaño de indices
print("\n=== Indices existentes en las tablas grandes ===")
cur.execute("""
    SELECT
        c.relname AS tabla,
        i.relname AS indexname,
        pg_size_pretty(pg_relation_size(i.oid)) AS size
    FROM pg_class c
    JOIN pg_index ix ON ix.indrelid = c.oid
    JOIN pg_class i ON i.oid = ix.indexrelid
    WHERE c.relname IN ('core_sale', 'core_quotum', 'core_vehicle', 'core_customer')
    ORDER BY c.relname, i.relname
""")
for r in cur.fetchall():
    print(f"  {r[0]:<20} {r[1]:<40} {r[2]}")

conn.close()
print("\nListo.")
