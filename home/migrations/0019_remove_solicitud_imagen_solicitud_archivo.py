# Generated by Django 4.2.9 on 2024-10-07 20:11

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0018_remove_solicitud_solicitado_diario_observaciones_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='solicitud',
            name='imagen',
        ),
        migrations.AddField(
            model_name='solicitud',
            name='archivo',
            field=models.FileField(blank=True, null=True, upload_to='archivos/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'xlsx', 'xls'])]),
        ),
    ]
