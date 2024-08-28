# Generated by Django 4.2.9 on 2024-08-16 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_alter_solicitud_fecha'),
    ]

    operations = [
        migrations.CreateModel(
            name='Orden',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField()),
                ('codigo_cotizacion', models.CharField(max_length=100)),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cantidad', models.IntegerField()),
                ('empresa', models.CharField(max_length=255)),
                ('destino', models.CharField(max_length=255)),
                ('tiempo_entrega', models.CharField(max_length=255)),
                ('observaciones', models.TextField(blank=True, null=True)),
            ],
        ),
    ]
