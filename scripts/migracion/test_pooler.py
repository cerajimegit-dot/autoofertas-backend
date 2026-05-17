"""Test rapido de los dos pooler modes de Supabase."""
import os, time
from pathlib import Path
import psycopg2

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

base_url = env_vals["DATABASE_URL"]
# Probar ambos puertos
for port in [5432, 6543]:
    url = base_url.replace(':5432/', f':{port}/').replace(':6543/', f':{port}/')
    print(f"\n>>> Puerto {port} ({'session' if port == 5432 else 'transaction'} mode)")
    t0 = time.time()
    try:
        conn = psycopg2.connect(url, connect_timeout=10, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT 1, current_database(), inet_server_addr()")
        row = cur.fetchone()
        print(f"  OK en {time.time()-t0:.2f}s")
        print(f"  Row: {row}")
        cur.execute("SELECT count(*) FROM core_sale")
        print(f"  core_sale count: {cur.fetchone()[0]}")
        conn.close()
    except Exception as e:
        print(f"  FAIL en {time.time()-t0:.2f}s: {type(e).__name__}: {str(e)[:200]}")
