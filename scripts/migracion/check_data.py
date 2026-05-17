"""Verifica conteos reales en Postgres y diagnostica filtros."""
import os
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

conn = psycopg2.connect(env_vals["DATABASE_URL"])
cur = conn.cursor()

print("=== Conteos en Postgres ===")
for t in ["core_sale", "core_quotum", "core_vehicle", "core_customer", "core_branch", "core_customuser"]:
    cur.execute(f'SELECT count(*) FROM "{t}"')
    print(f"  {t}: {cur.fetchone()[0]}")

print()
print("=== Admin user setup ===")
cur.execute("""
    SELECT u.id, u.username, u.is_superuser, u.is_staff, u.role, u.enterprise_id,
           (SELECT count(*) FROM core_customuser_branches_visible WHERE customuser_id = u.id) AS branches_visible
    FROM core_customuser u WHERE u.username = 'admin'
""")
row = cur.fetchone()
if row:
    print(f"  admin: id={row[0]}, superuser={row[2]}, staff={row[3]}, role={row[4]}, enterprise={row[5]}")
    print(f"  branches_visible: {row[6]}")

print()
print("=== Sales por branch + enterprise ===")
cur.execute("""
    SELECT s.enterprise_id, s.branch_id, b.name, count(*)
    FROM core_sale s
    LEFT JOIN core_branch b ON b.id = s.branch_id
    GROUP BY s.enterprise_id, s.branch_id, b.name
    ORDER BY s.enterprise_id, s.branch_id
""")
for r in cur.fetchall():
    print(f"  enterprise={r[0]} branch={r[1]} ({r[2]}): {r[3]} sales")

conn.close()
