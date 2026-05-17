"""
Migra core_vehicle de SQLite a Postgres con coerce inteligente:
- '' en columnas numericas nullable -> NULL
- '' en columnas numericas NOT NULL -> 0
- '' en columnas text se mantiene como ''
- Booleans int -> bool
"""
import os, sqlite3
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(BASE_DIR)

env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

DATABASE_URL = env_vals["DATABASE_URL"]
SQLITE = str(BASE_DIR / "db.sqlite3")
TABLE = "core_vehicle"

NUMERIC_TYPES = {
    "smallint", "integer", "bigint", "decimal", "numeric",
    "real", "double precision", "smallserial", "serial", "bigserial",
}
BOOL_TYPES = {"boolean"}

sl = sqlite3.connect(SQLITE)
slc = sl.cursor()
pg = psycopg2.connect(DATABASE_URL)
pgc = pg.cursor()

# Leer types y nullability de Postgres
pgc.execute(
    "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
    "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
    (TABLE,),
)
pg_info = {r[0]: {"type": r[1], "nullable": r[2] == "YES"} for r in pgc.fetchall()}
print(f"Tipos Postgres para {TABLE}:")
for c, info in pg_info.items():
    print(f"  {c:<20}  {info['type']:<20} nullable={info['nullable']}")

slc.execute(f'PRAGMA table_info("{TABLE}")')
sl_cols = [r[1] for r in slc.fetchall()]
final = [c for c in sl_cols if c in pg_info]


def coerce(v, col):
    if v is None:
        # Si la columna es NOT NULL, intentar default razonable
        info = pg_info.get(col, {})
        if not info.get("nullable", True):
            if info.get("type") in NUMERIC_TYPES:
                return 0
            return ""
        return None
    info = pg_info.get(col, {})
    t = info.get("type", "")
    nullable = info.get("nullable", True)
    if isinstance(v, str) and v.strip() == "":
        if t in NUMERIC_TYPES:
            return None if nullable else 0
        if t in BOOL_TYPES:
            return None if nullable else False
        return v  # text vacio se queda como ''
    if t in BOOL_TYPES and isinstance(v, int) and not isinstance(v, bool):
        return bool(v)
    return v


# Vaciar la tabla
pgc.execute("SET session_replication_role = 'replica';")
pgc.execute(f'TRUNCATE TABLE "{TABLE}" RESTART IDENTITY CASCADE;')
pg.commit()

col_list = ", ".join(f'"{c}"' for c in final)
slc.execute(f'SELECT {col_list} FROM "{TABLE}"')
rows = [tuple(coerce(v, c) for v, c in zip(r, final)) for r in slc.fetchall()]
print(f"\nFilas a copiar: {len(rows)}")

placeholders = "(" + ",".join(["%s"] * len(final)) + ")"
sql = f'INSERT INTO "{TABLE}" ({col_list}) VALUES %s'

try:
    execute_values(pgc, sql, rows, template=placeholders, page_size=500)
    pg.commit()
    print(f"OK - {len(rows)} filas insertadas")
except Exception as e:
    pg.rollback()
    print(f"\nBatch fallo: {e}")
    print("\nProbando fila por fila:")
    failures = 0
    for i, row in enumerate(rows):
        try:
            pgc.execute(
                f'INSERT INTO "{TABLE}" ({col_list}) VALUES ({",".join(["%s"]*len(final))})',
                row,
            )
            pg.commit()
        except Exception as ex:
            pg.rollback()
            failures += 1
            if failures <= 3:
                print(f"\n  Fila {i} (id={row[0]}): {ex}")
                for c, v in zip(final, row):
                    info = pg_info.get(c, {})
                    print(f"    {c}: {repr(v)} ({info.get('type')}, nullable={info.get('nullable')})")
    print(f"\nFallos: {failures}/{len(rows)}")

pgc.execute("SET session_replication_role = 'origin';")
pgc.execute(f"""
    SELECT setval(
        pg_get_serial_sequence('"public"."{TABLE}"', 'id'),
        COALESCE((SELECT MAX(id) FROM "{TABLE}"), 1),
        (SELECT MAX(id) IS NOT NULL FROM "{TABLE}")
    )
""")
pg.commit()

slc.execute(f'SELECT count(*) FROM "{TABLE}"')
a = slc.fetchone()[0]
pgc.execute(f'SELECT count(*) FROM "{TABLE}"')
b = pgc.fetchone()[0]
print(f"\nSQLite: {a} | Postgres: {b} | match: {a==b}")

sl.close()
pg.close()
