from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_sale_sale_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='down_payment',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name='Entrega Inicial',
            ),
        ),
    ]
