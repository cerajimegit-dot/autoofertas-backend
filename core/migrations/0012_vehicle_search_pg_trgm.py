"""No-op intencional.

Originalmente generamos esta migración para crear el índice GIN trgm
sobre Vehicle.vin, pero el flujo de SaaS hizo que Django también
detectara 0012_alter_sale_status (un drift legítimo del modelo Sale).
Como Django no permite dos migraciones con el mismo número como leaves
hermanos, renumeré la mía a 0013_vehicle_search_pg_trgm.

Mantengo este archivo con dependencia explícita a 0012_alter_sale_status
para que el grafo de Django lo trate como una continuación (no como un
leaf alternativo). El `operations = []` lo hace un no-op runtime.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0012_alter_sale_status'),
    ]
    operations = []
