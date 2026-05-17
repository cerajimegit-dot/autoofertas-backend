"""
Migracion de SQLite local a Postgres (Supabase).

Pasos:
1. Probar conexion a Postgres
2. Backup de SQLite
3. Dump de datos desde SQLite (excluyendo contenttypes/permissions)
4. Cambiar a Postgres y correr migrate (crea schema vacio)
5. Limpiar tablas con datos por defecto que Django crea durante migrate
6. Cargar datos en Postgres
7. Resetear sequences
8. Verificar conteos

Uso: python scripts/migracion/migrate_to_postgres.py

Requisitos: psycopg2-binary y dj-database-url instalados (estan en requirements.txt)
"""
import os
import sys
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))


def run(cmd, check=True, env=None):
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, env=env or os.environ)
    if check and result.returncode != 0:
        raise RuntimeError(f"Comando fallo (exit {result.returncode}): {cmd}")
    return result


def step(msg):
    print("\n" + "=" * 70)
    print(f">>> {msg}")
    print("=" * 70)


# Cargar .env manualmente para extraer DATABASE_URL
def load_env():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        raise RuntimeError(".env no existe — crearlo primero")
    vals = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
    return vals


env_vals = load_env()
DATABASE_URL = env_vals.get("DATABASE_URL", "")
if not DATABASE_URL or "supabase" not in DATABASE_URL:
    raise RuntimeError("DATABASE_URL no esta seteado o no apunta a Supabase")


# === PASO 1: Probar conexion ===
step("PASO 1: Probando conexion a Postgres")
try:
    import psycopg2
except ImportError:
    print("Instalando psycopg2-binary...")
    run("pip install psycopg2-binary dj-database-url")
    import psycopg2

try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SELECT version(), current_database(), current_user")
    row = cur.fetchone()
    print(f"OK - DB: {row[1]} | User: {row[2]}")
    print(f"Version: {row[0][:80]}")
    cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
    n_tables = cur.fetchone()[0]
    print(f"Tablas en public: {n_tables}")
    conn.close()
except Exception as e:
    raise RuntimeError(f"No se pudo conectar a Postgres: {e}")


# === PASO 2: Backup de SQLite ===
step("PASO 2: Backup de SQLite")
backup_dir = BASE_DIR / "backups"
backup_dir.mkdir(exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"db_pre_postgres_{stamp}.sqlite3"
shutil.copy(BASE_DIR / "db.sqlite3", backup_file)
print(f"Backup OK: {backup_file}")


# === PASO 3: Dump desde SQLite ===
step("PASO 3: Dump de datos desde SQLite")
dump_file = BASE_DIR / "scripts" / "migracion" / f"dump_{stamp}.json"
# Forzar SQLite para el dump
env_sqlite = os.environ.copy()
env_sqlite["DB_ENGINE"] = "sqlite"
run(
    f'python manage.py dumpdata '
    f'--exclude=contenttypes --exclude=auth.permission --exclude=admin.logentry '
    f'--exclude=sessions --natural-foreign --indent=2 -o "{dump_file}"',
    env=env_sqlite,
)
print(f"Dump OK: {dump_file}")
print(f"Tamano: {dump_file.stat().st_size / 1024:.1f} KB")


# === PASO 4: Crear schema en Postgres ===
step("PASO 4: Crear schema en Postgres (migrate)")
env_pg = os.environ.copy()
env_pg["DB_ENGINE"] = "postgres"
run("python manage.py migrate --noinput", env=env_pg)


# === PASO 5: Vaciar tablas auto-pobladas por migrate ===
step("PASO 5: Vaciar tablas auto-pobladas para evitar conflictos")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()
# Estas tablas se pueblan durante migrate; las vaciamos para que el load no choque
for tbl in ["django_content_type", "auth_permission"]:
    try:
        cur.execute(f'DELETE FROM "{tbl}"')
        print(f"  Vaciado: {tbl}")
    except Exception as e:
        print(f"  Skip {tbl}: {e}")
conn.close()


# === PASO 6: Cargar datos ===
step("PASO 6: Cargar datos en Postgres")
run(f'python manage.py loaddata "{dump_file}"', env=env_pg)


# === PASO 7: Resetear sequences ===
step("PASO 7: Resetear sequences de Postgres")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()
cur.execute("""
    SELECT 'SELECT setval(pg_get_serial_sequence(''' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ''', ''id''), '
        || 'COALESCE((SELECT MAX(id) FROM ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || '), 1));'
    FROM pg_tables
    WHERE schemaname = 'public'
    AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = pg_tables.tablename AND column_name = 'id'
    )
""")
seq_cmds = [r[0] for r in cur.fetchall()]
for sql in seq_cmds:
    try:
        cur.execute(sql)
    except Exception as e:
        print(f"  Skip: {e}")
print(f"  Sequences reseteados: {len(seq_cmds)}")
conn.close()


# === PASO 8: Verificar ===
step("PASO 8: Verificar conteos SQLite vs Postgres")
import sqlite3

tables_to_check = [
    "core_enterprise", "core_branch", "core_customuser", "core_customer",
    "core_brand", "core_vehiclemodel", "core_vehicle",
    "core_sale", "core_quotum", "core_paymentform",
]

sl = sqlite3.connect(str(BASE_DIR / "db.sqlite3"))
slc = sl.cursor()
pg = psycopg2.connect(DATABASE_URL)
pgc = pg.cursor()

print(f"\n{'Tabla':<28}{'SQLite':>10}{'Postgres':>12}{'Match':>10}")
print("-" * 60)
all_match = True
for t in tables_to_check:
    slc.execute(f'SELECT count(*) FROM {t}')
    a = slc.fetchone()[0]
    pgc.execute(f'SELECT count(*) FROM {t}')
    b = pgc.fetchone()[0]
    match = "OK" if a == b else "DIFF"
    if a != b:
        all_match = False
    print(f"{t:<28}{a:>10}{b:>12}{match:>10}")

sl.close()
pg.close()


step("MIGRACION COMPLETADA" if all_match else "MIGRACION CON DIFERENCIAS - revisar")
print(f"Backup SQLite:  {backup_file}")
print(f"Dump JSON:      {dump_file}")
print()
print("Para usar Postgres ahora cambia .env:")
print("  DB_ENGINE=postgres")
print()
print("Para volver a SQLite:")
print("  DB_ENGINE=sqlite")
