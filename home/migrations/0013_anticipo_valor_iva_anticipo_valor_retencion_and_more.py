# Generated by Django 4.2.9 on 2024-09-25 16:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0012_remove_anticipo_vlr_unitario'),
    ]

    operations = [
        migrations.AddField(
            model_name='anticipo',
            name='valor_iva',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='anticipo',
            name='valor_retencion',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='anticipo',
            name='fecha',
            field=models.DateField(),
        ),
    ]
