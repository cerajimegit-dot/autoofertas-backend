from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_sale_down_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='quotum',
            name='cancelled_date',
            field=models.DateField(
                null=True,
                blank=True,
                verbose_name='Fecha de Cancelación',
            ),
        ),
    ]
