"""Habilita búsqueda fuzzy de vehículos con pg_trgm sobre VIN.

Mismo patrón que la migración 0010 que cubría Customer.first_name+last_name.
Acá creamos un índice GIN sobre `vin` para que `similarity()` no haga
seq scan en tablas con miles de vehículos.

NOTA: requiere que la extensión pg_trgm ya esté creada (la creó la
migración 0010). Es dependencia transitiva — 0013 → 0012 → 0011 → 0010.
"""

from django.db import migrations


def create_vin_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        # Idempotente. CREATE INDEX IF NOT EXISTS.
        c.execute('''
            CREATE INDEX IF NOT EXISTS core_vehicle_vin_trgm_idx
            ON core_vehicle
            USING gin (vin gin_trgm_ops);
        ''')


def drop_vin_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute('DROP INDEX IF EXISTS core_vehicle_vin_trgm_idx;')


class Migration(migrations.Migration):

    dependencies = [
        # Cadena: 0011 → 0012_alter_sale_status → 0012_vehicle_search_pg_trgm
        # (no-op) → ESTE. Hacemos linear el grafo de 0012 a 0013 para que
        # Django no se queje de leaves duplicadas.
        ('core', '0012_vehicle_search_pg_trgm'),
    ]

    operations = [
        migrations.RunPython(create_vin_index, drop_vin_index),
    ]
