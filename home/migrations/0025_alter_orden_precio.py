# Generated by Django 4.2.9 on 2024-11-01 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0024_alter_cotizacion_precio'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orden',
            name='precio',
            field=models.DecimalField(decimal_places=2, max_digits=15),
        ),
    ]
