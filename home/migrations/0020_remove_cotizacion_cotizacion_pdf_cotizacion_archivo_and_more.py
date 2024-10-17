# Generated by Django 4.2.9 on 2024-10-15 15:38

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0019_remove_solicitud_imagen_solicitud_archivo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cotizacion',
            name='cotizacion_pdf',
        ),
        migrations.AddField(
            model_name='cotizacion',
            name='archivo',
            field=models.FileField(blank=True, null=True, upload_to='cotizaciones_archivos/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'doc', 'docx'])]),
        ),
        migrations.AlterField(
            model_name='diario',
            name='centro_costo',
            field=models.CharField(choices=[('ADMINISTRACIÓN', 'ADMINISTRACIÓN'), ('PRODUCCION', 'PRODUCCION'), ('ALEVINERA', 'ALEVINERA'), ('ECOPEZ', 'ECOPEZ'), ('FERRY', 'FERRY'), ('CARRO PESCA NVS 228', 'CARRO PESCA NVS 228'), ('CARRO PESCA WGY 964', 'CARRO PESCA WGY 964'), ('CARRO PESCA THS 473', 'CARRO PESCA THS 473'), ('CARRO PESCA SRP 254', 'CARRO PESCA SRP 254'), ('CARRO EXPORTACION GQZ 727', 'CARRO EXPORTACION GQZ 727'), ('CARRO EXPORTACION GRK 030', 'CARRO EXPORTACION GRK 030'), ('CARRO EXPORTACION THS 592', 'CARRO EXPORTACION THS 592'), ('UNIDAD COMERCIALIZACION', 'UNIDAD COMERCIALIZACION')], max_length=200),
        ),
        migrations.AlterField(
            model_name='solicitud',
            name='archivo',
            field=models.FileField(blank=True, null=True, upload_to='archivos/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'xls', 'xlsx'])]),
        ),
    ]