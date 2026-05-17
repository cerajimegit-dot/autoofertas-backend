from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_viewpermission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='sale_date',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name='Fecha de Venta'
            ),
        ),
    ]
