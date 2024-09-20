from django.db import models
from django import forms
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.utils import timezone


class Solicitud(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()
    cantidad = models.IntegerField()
    destino = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50)
    observaciones = models.TextField(blank=True, null=True)
    solicitado = models.CharField(max_length=255)
    imagen = models.ImageField(upload_to="imagenes/", blank=True, null=True)
    estado = models.CharField(
        max_length=50,
        choices=[("pendiente", "Pendiente"), ("aprobado", "Aprobado")],
        default="pendiente",
    )

    def __str__(self):
        return self.nombre

class Cotizacion(models.Model):
    solicitud = models.ForeignKey(
        Solicitud, related_name="cotizaciones", on_delete=models.CASCADE
    )
    proveedor = models.CharField(max_length=255)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    detalles = models.TextField(blank=True, null=True)
    estado = models.CharField(
        max_length=50,
        choices=[("pendiente", "Pendiente"), ("aprobada", "Aprobada")],
        default="pendiente",
    )
    cotizacion_imagen = models.FileField(upload_to="cotizaciones/", blank=True, null=True)
    fecha = models.DateTimeField(default=timezone.now)
    estado_aprobada = models.BooleanField(default=False)  # Asegúrate de que este campo está aquí
    def __str__(self):
        return f"Cotización de {self.proveedor} para {self.solicitud.nombre}"


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
    tiempo_entrega = models.CharField(max_length=255)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')

    def __str__(self):
        return f"{self.codigo_cotizacion} - {self.descripcion}"


class Anticipo(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    nit = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    centro_costo = models.CharField(max_length=50)
    producto_servicio = models.CharField(max_length=100)
    vlr_unitario = models.DecimalField(max_digits=10, decimal_places=3)
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=3, blank=True, null=True
    )
    iva = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True)
    retencion = models.DecimalField(
        max_digits=10, decimal_places=3, blank=True, null=True
    )
    total_pagar = models.DecimalField(
        max_digits=10, decimal_places=3, blank=True, null=True
    )
    observaciones = models.TextField(blank=True, null=True)
    aprobado = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(self.cantidad) * Decimal(self.vlr_unitario)
        if self.iva is not None:
            self.iva = self.subtotal * Decimal(self.iva) / Decimal("100")
        else:
            self.iva = Decimal("0.00")

        if self.retencion is not None:
            self.retencion = self.subtotal * Decimal(self.retencion) / Decimal("100")
        else:
            self.retencion = Decimal("0.00")

        self.total_pagar = self.subtotal + self.iva - self.retencion
        super().save(*args, **kwargs)


class Diario(models.Model):
    TIEMPO_ENTREGA_CHOICES = [(f"{i:02d}:00", f"{i:02d}:00") for i in range(24)]

    tiempo_entrega = models.TimeField("Hora de Entrega")  # Changed to TimeField
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
    documento_pdf = models.FileField(upload_to="documentos_pdf/", blank=True, null=True)

    def __str__(self):
        return f"Diario {self.nombre} - {self.empresa}"
