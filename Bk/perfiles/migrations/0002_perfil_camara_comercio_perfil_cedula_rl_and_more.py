# Generated by Django 5.0.7 on 2024-08-06 16:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perfiles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='camara_comercio',
            field=models.FileField(blank=True, upload_to='documents/'),
        ),
        migrations.AddField(
            model_name='perfil',
            name='cedula_rl',
            field=models.FileField(blank=True, upload_to='documents/'),
        ),
        migrations.AddField(
            model_name='perfil',
            name='certificado_bancario',
            field=models.FileField(blank=True, upload_to='documents/'),
        ),
        migrations.AddField(
            model_name='perfil',
            name='rut',
            field=models.FileField(blank=True, upload_to='documents/'),
        ),
    ]
