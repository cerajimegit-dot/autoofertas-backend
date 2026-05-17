"""
Migracion directa SQLite -> Postgres (sin dumpdata).
Copia tabla por tabla con SQL plano, evitando problemas de serializacion del ORM.
Asume que migrate --noinput ya corrio en Postgres (schema vacio creado).

Uso:
    python scripts\\migracion\\direct_copy_to_postgres.py
"""
import os, sys, sqlite3, json
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date

BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(BASE_DIR)

import psycopg2
from psycopg2.extras import execute_values

# Cargar DATABASE_URL del .env
env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

DATABASE_URL = env_vals["DATABASE_URL"]
SQLITE = str(BASE_DIR / "db.sqlite3")

# Orden de tablas (parents -> children)
TABLES_ORDER = [
    # Sistema Django
    "django_content_type",
    "auth_group",
    "auth_permission",
    "auth_group_permissions",
    # Core (parents)
    "core_enterprise",
    "core_paymentform",
    "core_branch",
    "core_brand",
    "core_vehiclemodel",
    "core_exchangerate",
    "core_customuser",
    "core_customuser_groups",
    "core_customuser_user_permissions",
    "core_customuser_branches_visible",
    "core_viewpermission",
    "core_customer",
    "core_vehicle",
    "core_vehiclecost",
    "core_sale",
    "core_quotum",
    "core_auditlog",
    "django_admin_log",
    "django_session",
]


def get_sqlite_columns(slc, table):
    slc.execute(f'PRAGMA table_info("{table}")')
    return [r[1] for r in slc.fetchall()]


def truncate_postgres(pg):
    """Vacia todas las tablas en orden inverso, respetando FKs con CASCADE."""
    cur = pg.cursor()
    cur.execute("SET session_replication_role = 'replica';")  # disable triggers/FKs
    for t in reversed(TABLES_ORDER):
        try:
            cur.execute(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE;')
            print(f"  truncate {t}")
        except Exception as e:
            print(f"  skip {t}: {e}")
            pg.rollback()
            cur = pg.cursor()
            cur.execute("SET session_replication_role = 'replica';")
    pg.commit()
    cur.execute("SET session_replication_role = 'origin';")
    pg.commit()


NUMERIC_TYPES = {
    "smallint", "integer", "bigint", "decimal", "numeric",
    "real", "double precision", "smallserial", "serial", "bigserial",
}
BOOL_TYPES = {"boolean"}


def coerce_value(v, col_name, pg_type=None, nullable=True):
    """Normaliza valores SQLite -> Postgres usando los tipos reales y nullability destino."""
    if v is None:
        if not nullable:
            if pg_type in NUMERIC_TYPES:
                return 0
            if pg_type in BOOL_TYPES:
                return False
            return ""
        return None
    # Strings vacios
    if isinstance(v, str) and v.strip() == "":
        if pg_type in NUMERIC_TYPES:
            return None if nullable else 0
        if pg_type in BOOL_TYPES:
            return None if nullable else False
        return v  # text vacio se queda como ''
    # Boolean coercion
    if pg_type in BOOL_TYPES and isinstance(v, int) and not isinstance(v, bool):
        return bool(v)
    if isinstance(v, int) and col_name.startswith(("is_", "has_")):
        return bool(v)
    return v


def copy_table(slc, pg, table):
    """Copia una tabla SQLite -> Postgres."""
    cols = get_sqlite_columns(slc, table)
    if not cols:
        return 0, "no columns"
    # Verificar que la tabla exista en Postgres
    pgc = pg.cursor()
    pgc.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name=%s", (table,))
    if pgc.fetchone()[0] == 0:
        return 0, "tabla no existe en Postgres"

    # Verificar que las columnas coincidan (Postgres puede tener menos) + leer tipos y nullability
    pgc.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name=%s", (table,))
    pg_info_map = {r[0]: {"type": r[1], "nullable": r[2] == "YES"} for r in pgc.fetchall()}
    pg_types_map = {c: info["type"] for c, info in pg_info_map.items()}
    pg_nullable_map = {c: info["nullable"] for c, info in pg_info_map.items()}
    pg_cols = set(pg_info_map.keys())
    final_cols = [c for c in cols if c in pg_cols]
    skipped = [c for c in cols if c not in pg_cols]
    if skipped:
        print(f"    cols saltadas (no en pg): {skipped}")
    if not final_cols:
        return 0, "ninguna columna compartida"

    col_list = ", ".join(f'"{c}"' for c in final_cols)
    slc.execute(f'SELECT {", ".join([chr(34)+c+chr(34) for c in final_cols])} FROM "{table}"')
    rows = []
    for r in slc.fetchall():
        rows.append(tuple(coerce_value(v, c, pg_types_map.get(c), pg_nullable_map.get(c, True)) for v, c in zip(r, final_cols)))
    if not rows:
        return 0, "vacia"

    placeholders = "(" + ",".join(["%s"] * len(final_cols)) + ")"
    sql = f'INSERT INTO "{table}" ({col_list}) VALUES %s'
    try:
        execute_values(pgc, sql, rows, template=placeholders, page_size=500)
        pg.commit()
        return len(rows), "ok"
    except Exception as e:
        pg.rollback()
        return 0, f"ERROR: {e}"


def reset_sequences(pg):
    """Resetea sequences de Postgres a MAX(id)+1."""
    cur = pg.cursor()
    cur.execute("""
        SELECT tablename FROM pg_tables
        WHERE schemaname='public'
        AND EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name=pg_tables.tablename AND column_name='id'
        )
    """)
    tables = [r[0] for r in cur.fetchall()]
    fixed = 0
    for t in tables:
        try:
            cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('"public"."{t}"', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{t}"), 1),
                    (SELECT MAX(id) IS NOT NULL FROM "{t}")
                )
            """)
            fixed += 1
        except Exception as e:
            print(f"  skip seq {t}: {e}")
            pg.rollback()
            cur = pg.cursor()
    pg.commit()
    return fixed


def verify(slc, pgc):
    print("\n" + "=" * 60)
    print(f"{'Tabla':<38}{'SQLite':>10}{'Postgres':>10}")
    print("-" * 60)
    all_ok = True
    for t in TABLES_ORDER:
        try:
            slc.execute(f'SELECT count(*) FROM "{t}"')
            a = slc.fetchone()[0]
        except Exception:
            a = -1
        try:
            pgc.execute(f'SELECT count(*) FROM "{t}"')
            b = pgc.fetchone()[0]
        except Exception:
            b = -1
        flag = "" if a == b else "  <-- DIFF"
        if a != b and not (a == -1 or b == -1):
            all_ok = False
        print(f"{t:<38}{a:>10}{b:>10}{flag}")
    return all_ok


def main():
    print("=" * 70)
    print("MIGRACION DIRECTA SQLite -> Postgres")
    print("=" * 70)
    sl = sqlite3.connect(SQLITE)
    slc = sl.cursor()
    pg = psycopg2.connect(DATABASE_URL)
    pgc = pg.cursor()

    print("\n>>> Truncando tablas Postgres...")
    truncate_postgres(pg)

    print("\n>>> Copiando datos tabla por tabla...")
    # Disable FK checks for the duration of the copy
    pgc.execute("SET session_replication_role = 'replica';")
    pg.commit()
    for t in TABLES_ORDER:
        n, msg = copy_table(slc, pg, t)
        print(f"  {t:<38} {n:>6} filas  ({msg})")
    pgc.execute("SET session_replication_role = 'origin';")
    pg.commit()

    print("\n>>> Reseteando sequences...")
    n = reset_sequences(pg)
    print(f"  sequences ajustadas: {n}")

    print("\n>>> Verificacion final:")
    ok = verify(slc, pgc)
    print()
    print("RESULTADO:", "OK - todos los conteos coinciden" if ok else "DIFERENCIAS - revisar arriba")

    sl.close()
    pg.close()


if __name__ == "__main__":
    main()
