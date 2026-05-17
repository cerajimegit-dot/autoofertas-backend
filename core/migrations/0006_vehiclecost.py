from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_quotum_cancelled_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='VehicleCost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('concept', models.CharField(max_length=100, verbose_name='Concepto')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Monto')),
                ('currency', models.CharField(choices=[('PYG', 'Guaraní'), ('USD', 'Dólar')], default='PYG', max_length=10, verbose_name='Moneda')),
                ('notes', models.TextField(blank=True, verbose_name='Notas')),
                ('order', models.IntegerField(default=0, verbose_name='Orden')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('enterprise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name='vehicle_costs', to='core.enterprise')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name='extra_costs', to='core.vehicle',
                                               verbose_name='Vehículo')),
            ],
            options={
                'verbose_name': 'Costo extra de vehículo',
                'verbose_name_plural': 'Costos extras de vehículos',
                'ordering': ['vehicle_id', 'order', 'id'],
                'indexes': [models.Index(fields=['vehicle'], name='core_vehicl_vehicle_idx')],
            },
        ),
    ]
