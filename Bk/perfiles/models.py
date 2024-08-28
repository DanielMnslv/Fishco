from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import forms
from decimal import Decimal, ROUND_HALF_UP


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.CharField(max_length=255, blank=True)
    web = models.URLField(blank=True)
    rut = models.CharField(max_length=20, blank=True, null=True)
    camara_comercio = models.CharField(max_length=20, blank=True, null=True)
    cedula_rl = models.CharField(max_length=20, blank=True, null=True)
    certificado_bancario = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.usuario.username


@receiver(post_save, sender=User)
def crear_usuario_perfil(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(usuario=instance)


@receiver(post_save, sender=User)
def guardar_usuario_perfil(sender, instance, **kwargs):
    instance.perfil.save()


class Solicitud(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ]

    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()
    cantidad = models.IntegerField()
    destino = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50)
    observaciones = models.TextField(blank=True, null=True)
    solicitado = models.CharField(max_length=255)
    imagen = models.ImageField(upload_to="imagenes/", blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="pendiente")
    comentarios = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Orden(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    ]

    descripcion = models.TextField()
    codigo_cotizacion = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    empresa = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    tiempo_entrega = models.DateTimeField()
    observaciones = models.TextField(blank=True, null=True)
    documento_pdf = models.FileField(upload_to="documentos_pdf/", blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PENDIENTE')

    def __str__(self):
        return f"{self.codigo_cotizacion} - {self.descripcion}"




class Anticipo(models.Model):
    nit = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    centro_costo = models.CharField(max_length=50)
    producto_servicio = models.CharField(max_length=100)
    vlr_unitario = models.DecimalField(max_digits=10, decimal_places=3)
    subtotal = models.DecimalField(max_digits=10, decimal_places=3)
    iva = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    retencion = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    total_pagar = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    aprobado = models.BooleanField(default=False)  # Nuevo campo para aprobación

    def save(self, *args, **kwargs):
        self.vlr_unitario = Decimal(self.vlr_unitario).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        self.subtotal = Decimal(self.cantidad * self.vlr_unitario).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        self.iva = Decimal(self.subtotal * (self.iva or 0)).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        self.retencion = Decimal(self.subtotal * (self.retencion or 0)).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )
        self.total_pagar = Decimal(self.subtotal + self.iva - self.retencion).quantize(
            Decimal(".01"), rounding=ROUND_HALF_UP
        )

        super().save(*args, **kwargs)


class AnticipoForm(forms.ModelForm):
    class Meta:
        model = Anticipo
        fields = [
            "nit",
            "nombre",
            "cantidad",
            "centro_costo",
            "producto_servicio",
            "vlr_unitario",
            "subtotal",
            "iva",
            "retencion",
            "total_pagar",
            "observaciones",
        ]


class Diario(models.Model):
    TIEMPO_ENTREGA_CHOICES = [(f"{i:02d}:00", f"{i:02d}:00") for i in range(24)]

    tiempo_entrega = models.DateTimeField("Día y Hora de Entrega")
    nombre = models.CharField(max_length=200)
    empresa = models.CharField(max_length=200)
    centro_costo = models.CharField(
        max_length=200,
        choices=[
            ("ADMINISTRACIÓN", "ADMINISTRACIÓN"),
            ("PRODUCCION", "PRODUCCION"),
            ("ALEVINERA", "ALEVINERA"),
            ("ECOPEZ", "ECOPEZ"),
            ("FERRY", "FERRY"),
            ("CARRO VNS228", "CARRO VNS228"),
            ("CARRO WGY", "CARRO WGY"),
            ("CARRO THS 473", "CARRO THS 473"),
            ("CARRO PESCA SRP 254", "CARRO PESCA SRP 254"),
            ("TERMOKIN GQZ 727", "TERMOKIN GQZ 727"),
            ("TERMOKIN GRK 030", "TERMOKIN GRK 030"),
            ("THERMO KING THS 592", "THERMO KING THS 592"),
            ("UNIDAD COMERCIALIZACION", "UNIDAD COMERCIALIZACION"),
        ],
    )
    destino = models.CharField(
        max_length=200,
        choices=[
            ("ADMINISTRACIÓN", "ADMINISTRACIÓN"),
            ("PRODUCCION", "PRODUCCION"),
            ("ALEVINERA", "ALEVINERA"),
            ("ECOPEZ", "ECOPEZ"),
            ("FERRY", "FERRY"),
            ("CARRO VNS228", "CARRO VNS228"),
            ("CARRO WGY", "CARRO WGY"),
            ("CARRO THS 473", "CARRO THS 473"),
            ("CARRO PESCA SRP 254", "CARRO PESCA SRP 254"),
            ("TERMOKIN GQZ 727", "TERMOKIN GQZ 727"),
            ("TERMOKIN GRK 030", "TERMOKIN GRK 030"),
            ("THERMO KING THS 592", "THERMO KING THS 592"),
            ("UNIDAD COMERCIALIZACION", "UNIDAD COMERCIALIZACION"),
        ],
    )
    medio_pago = models.CharField(
        max_length=200,
        choices=[
            ("efectivo", "Efectivo"),
            ("tarjeta", "Tarjeta"),
            ("transferencia", "Transferencia"),
        ],
    )
    documento_pdf = models.FileField(
        upload_to="documentos_pdf/", blank=True, null=True
    )  # Campo para PDF

    def __str__(self):
        return f"Diario {self.nombre} - {self.empresa}"
