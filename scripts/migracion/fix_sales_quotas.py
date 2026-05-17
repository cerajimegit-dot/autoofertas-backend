"""Copia core_sale y core_quotum desde SQLite a Postgres, con coerce inteligente
y reporte de errores fila por fila si falla."""
import os, sqlite3
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_vals = {}
for line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env_vals[k.strip()] = v.strip()

DATABASE_URL = env_vals["DATABASE_URL"]
SQLITE = str(BASE_DIR / "db.sqlite3")

NUMERIC_TYPES = {
    "smallint", "integer", "bigint", "decimal", "numeric",
    "real", "double precision", "smallserial", "serial", "bigserial",
}
BOOL_TYPES = {"boolean"}

sl = sqlite3.connect(SQLITE)
slc = sl.cursor()
pg = psycopg2.connect(DATABASE_URL)
pgc = pg.cursor()


def copy_table(table):
    print(f"\n>>> Copiando {table}")
    pgc.execute(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
        (table,),
    )
    pg_info = {r[0]: {"type": r[1], "nullable": r[2] == "YES"} for r in pgc.fetchall()}

    slc.execute(f'PRAGMA table_info("{table}")')
    sl_cols = [r[1] for r in slc.fetchall()]
    final = [c for c in sl_cols if c in pg_info]

    def coerce(v, col):
        info = pg_info.get(col, {})
        t = info.get("type", "")
        nullable = info.get("nullable", True)
        if v is None:
            if not nullable:
                if t in NUMERIC_TYPES: return 0
                if t in BOOL_TYPES: return False
                return ""
            return None
        if isinstance(v, str) and v.strip() == "":
            if t in NUMERIC_TYPES: return None if nullable else 0
            if t in BOOL_TYPES: return None if nullable else False
        if t in BOOL_TYPES and isinstance(v, int) and not isinstance(v, bool):
            return bool(v)
        return v

    # Asegurar tabla vacia
    pgc.execute("SET session_replication_role = 'replica';")
    pgc.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
    pg.commit()

    col_list = ", ".join(f'"{c}"' for c in final)
    slc.execute(f'SELECT {col_list} FROM "{table}"')
    rows = [tuple(coerce(v, c) for v, c in zip(r, final)) for r in slc.fetchall()]
    print(f"  Filas a copiar: {len(rows)}")

    placeholders = "(" + ",".join(["%s"] * len(final)) + ")"
    sql = f'INSERT INTO "{table}" ({col_list}) VALUES %s'

    try:
        execute_values(pgc, sql, rows, template=placeholders, page_size=200)
        pg.commit()
        print(f"  OK - {len(rows)} filas insertadas en batch")
    except Exception as e:
        pg.rollback()
        print(f"  Batch fallo: {str(e)[:200]}")
        print(f"  Probando fila por fila...")
        pgc.execute("SET session_replication_role = 'replica';")
        pg.commit()
        ok = 0
        fail = 0
        for i, row in enumerate(rows):
            try:
                pgc.execute(
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({",".join(["%s"]*len(final))})',
                    row,
                )
                pg.commit()
                ok += 1
            except Exception as ex:
                pg.rollback()
                fail += 1
                if fail <= 3:
                    print(f"\n    Fila {i} (id={row[0]}): {str(ex)[:200]}")
                    for c, v in zip(final, row):
                        info = pg_info.get(c, {})
                        print(f"      {c}: {repr(v)} ({info.get('type')}, nullable={info.get('nullable')})")
        print(f"  Resultado: {ok} OK / {fail} FAIL")

    pgc.execute("SET session_replication_role = 'origin';")
    # Reset sequence
    pgc.execute(f"""
        SELECT setval(
            pg_get_serial_sequence('"public"."{table}"', 'id'),
            COALESCE((SELECT MAX(id) FROM "{table}"), 1),
            (SELECT MAX(id) IS NOT NULL FROM "{table}")
        )
    """)
    pg.commit()

    slc.execute(f'SELECT count(*) FROM "{table}"')
    a = slc.fetchone()[0]
    pgc.execute(f'SELECT count(*) FROM "{table}"')
    b = pgc.fetchone()[0]
    print(f"  Final: SQLite={a} | Postgres={b} | match={a==b}")


# Orden importa: sale antes que quotum (quotum tiene FK a sale)
copy_table("core_sale")
copy_table("core_quotum")

# Tambien copiamos branches_visible del admin (problema secundario)
print("\n>>> Asignando branches al admin (id=1)")
pgc.execute("SELECT id FROM core_branch ORDER BY id")
branches = [r[0] for r in pgc.fetchall()]
print(f"  Branches: {branches}")
for bid in branches:
    pgc.execute(
        "INSERT INTO core_customuser_branches_visible (customuser_id, branch_id) "
        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (1, bid),
    )
pg.commit()
pgc.execute("SELECT count(*) FROM core_customuser_branches_visible WHERE customuser_id = 1")
print(f"  Admin ahora tiene {pgc.fetchone()[0]} branches visibles")

sl.close()
pg.close()
