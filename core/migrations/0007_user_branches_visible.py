from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_vehiclecost'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='branches_visible',
            field=models.ManyToManyField(
                blank=True,
                related_name='visible_to_users',
                to='core.branch',
                verbose_name='Sucursales visibles',
            ),
        ),
    ]
