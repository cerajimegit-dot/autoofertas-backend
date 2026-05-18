"""Agrega `exchange_rate` a VehicleCost.

Antes los costos extras en USD no tenían dónde guardar el TC del
momento — el análisis de margen los contabilizaba como 0 y avisaba.
Con este campo, el costo en USD queda congelado al TC que el operador
cargó al crear el VehicleCost.

NULLABLE para no romper data existente. Los VehicleCost que ya existen
en producción con currency='USD' van a quedar con exchange_rate=NULL;
el `clean()` del modelo sólo aplica a creates y updates nuevos. Si
querés forzar que se completen, después podés mostrar en el panel
"calidad de datos" los VehicleCost USD sin TC.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_customer_search_pg_trgm'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclecost',
            name='exchange_rate',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                verbose_name='Tipo de cambio',
                help_text='Obligatorio si moneda=USD. Se usa para calcular '
                          'el equivalente en PYG en el análisis de margen.',
            ),
        ),
    ]
