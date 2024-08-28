# Generated by Django 5.0.6 on 2024-08-13 19:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perfiles', '0006_diario_documento_pdf'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anticipo',
            name='iva',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='anticipo',
            name='retencion',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='anticipo',
            name='subtotal',
            field=models.DecimalField(decimal_places=3, max_digits=10),
        ),
        migrations.AlterField(
            model_name='anticipo',
            name='total_pagar',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='anticipo',
            name='vlr_unitario',
            field=models.DecimalField(decimal_places=3, max_digits=10),
        ),
    ]
