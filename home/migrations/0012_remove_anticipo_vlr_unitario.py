# Generated by Django 4.2.9 on 2024-09-24 20:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0011_remove_anticipo_aprobado_alter_anticipo_fecha_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='anticipo',
            name='vlr_unitario',
        ),
    ]
