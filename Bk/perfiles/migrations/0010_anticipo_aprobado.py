# Generated by Django 5.0.6 on 2024-08-14 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perfiles', '0009_orden_estado_alter_orden_tiempo_entrega'),
    ]

    operations = [
        migrations.AddField(
            model_name='anticipo',
            name='aprobado',
            field=models.BooleanField(default=False),
        ),
    ]
