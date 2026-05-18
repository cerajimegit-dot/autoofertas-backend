"""Habilita búsqueda fuzzy de clientes con la extensión pg_trgm.

Crea la extensión `pg_trgm` (idempotente, IF NOT EXISTS) y dos índices GIN
sobre los campos donde el usuario tipea con errores:
  - `first_name || ' ' || last_name` (nombre completo lowercased)
  - `document_number`

Sin estos índices, una búsqueda por `similarity()` en una tabla con miles
de clientes hace seq scan y se nota (>200 ms). Con el índice GIN
trigram, queda en <20 ms.

NOTA: en SQLite (tests, dev local) la migración no hace nada — esos
backends no soportan extensiones. El código de búsqueda detecta esto
en tiempo de ejecución y cae al fallback ILIKE.

NOTA Supabase: `CREATE EXTENSION pg_trgm` requiere que el usuario sea
SUPERUSER. En el plan free de Supabase, el usuario `postgres` provisto
ya lo es; en otros entornos puede fallar — por eso el operador está
envuelto en `state_operations=[]` y un IF NOT EXISTS, y la búsqueda
funciona igual sin la extensión.
"""

from django.db import migrations


def create_extension_and_indexes(apps, schema_editor):
    """Crea pg_trgm + índices SÓLO en Postgres. En SQLite, no-op."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        # Idempotente. Si la extensión no se puede crear (permisos),
        # dejamos que estalle — la migración falla explícitamente y el
        # operador sabe que tiene que pedirle a Supabase que la habilite.
        c.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
        # Índice GIN sobre el nombre completo lowercased. Usamos COALESCE
        # para no dejar nulls que rompan la concatenación.
        c.execute('''
            CREATE INDEX IF NOT EXISTS core_customer_fullname_trgm_idx
            ON core_customer
            USING gin (
                LOWER(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
                gin_trgm_ops
            );
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS core_customer_document_trgm_idx
            ON core_customer
            USING gin (document_number gin_trgm_ops);
        ''')


def drop_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute('DROP INDEX IF EXISTS core_customer_fullname_trgm_idx;')
        c.execute('DROP INDEX IF EXISTS core_customer_document_trgm_idx;')
        # No dropeamos la extensión: puede estar siendo usada por otras
        # tablas o índices fuera de este modelo.


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_cash_movement'),
    ]

    operations = [
        migrations.RunPython(create_extension_and_indexes, drop_indexes),
    ]
