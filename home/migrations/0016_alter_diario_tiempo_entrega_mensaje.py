# Generated by Django 4.2.9 on 2024-10-02 20:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('home', '0015_anticipo_oculto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='diario',
            name='tiempo_entrega',
            field=models.DateField(verbose_name='Hora de Entrega'),
        ),
        migrations.CreateModel(
            name='Mensaje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenido', models.TextField()),
                ('fecha_envio', models.DateTimeField(default=django.utils.timezone.now)),
                ('cotizacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='home.cotizacion')),
                ('remitente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('solicitud', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes', to='home.solicitud')),
            ],
        ),
    ]
