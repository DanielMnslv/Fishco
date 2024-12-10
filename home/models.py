from django.db import models
from django import forms
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model


class Solicitud(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()
    cantidad = models.IntegerField()
    destino = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50)
    observaciones = models.TextField(blank=True, null=True)
    archivo = models.FileField(
        upload_to='archivos/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg', 
            'pdf', 'xls', 'xlsx'
        ])]  # Agrega extensiones adicionales si es necesario
    )
    oculto = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=50,
        choices=[
            ("pendiente", "Pendiente"),
            ("aprobado", "Aprobado"),
            ("rechazado", "Rechazado")  
        ],
        default="pendiente",
    )
    # Relacionamos la solicitud con el usuario que la creó
    usuario = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name="solicitudes"  # Usamos 'solicitudes' como el nombre para la relación inversa
    )

    def __str__(self):
        return f"{self.nombre} - {self.cantidad}"


class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("aprobada", "Aprobada"),
    ]

    solicitud = models.ForeignKey(Solicitud, related_name="cotizaciones", on_delete=models.CASCADE)
    proveedor = models.CharField(max_length=255)
    precio = models.DecimalField(max_digits=20, decimal_places=2)
    detalles = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default="pendiente")
    
    # Cambiar el campo para aceptar múltiples tipos de archivos
    archivo = models.FileField(
        upload_to="cotizaciones_archivos/", 
        blank=True, 
        null=True, 
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "jpeg", "png", "xls", "xlsx", "doc", "docx"])]
    )
    
    estado_aprobada = models.BooleanField(default=False)
    fecha = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Si la cotización ha sido aprobada, actualizar el estado de la solicitud
        if self.estado == "aprobada":
            self.solicitud.estado = "aprobado"
            self.solicitud.save()

    def __str__(self):
        return f"{self.proveedor} - {self.precio}"


class Mensaje(models.Model):
    solicitud = models.ForeignKey(
        Solicitud, related_name="mensajes", on_delete=models.CASCADE
    )
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.CASCADE, null=True, blank=True
    )
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Mensaje de {self.remitente.username} en {self.solicitud.nombre}"


class Orden(models.Model):
    descripcion = models.TextField()
    codigo_cotizacion = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=15, decimal_places=2)
    cantidad = models.IntegerField()
    empresa = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    tiempo_entrega = models.CharField(max_length=255)
    observaciones = models.TextField(blank=True, null=True)
    
    # Elimina el campo estado y sus opciones
    # estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')

    def __str__(self):
        return f"{self.codigo_cotizacion} - {self.descripcion}"



class Anticipo(models.Model):
    IVA_CHOICES = [
        (0, "Sin IVA"),
        (5, "5%"),
        (19, "19%"),
    ]
    RETENCION_CHOICES = [
        (0, "Sin Retención"),
        (0.625, "0.625%"),
        (0.1, "0.1%"),
        (2, "2%"),
        (2.5, "2.5%"),
        (3.5, "3.5%"),
        (4, "4%"),
        (6, "6%"),
        (10, "10%"),
        (11, "11%"),
    ]
    RETEICA_CHOICES = [
        ("0", "Sin ReteICA"),
        ("0.003", "0.3%"),
        ("0.004", "0.4%"),
        ("0.005", "0.5%"),
        ("0.006", "0.6%"),
        ("0.007", "0.7%"),
        ("0.010", "0.10%"),
    ]

    fecha = models.DateField()
    centro_costo = models.CharField(max_length=50)
    nit = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    producto_servicio = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    iva = models.DecimalField(max_digits=5, decimal_places=2, choices=IVA_CHOICES, blank=True, null=True)
    retencion = models.DecimalField(max_digits=5, decimal_places=2, choices=RETENCION_CHOICES, blank=True, null=True)
    reteica = models.CharField(max_length=10, choices=RETEICA_CHOICES, default="0")
    saldo_a_favor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    valor_iva = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_retencion = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_reteica = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_pagar = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    aprobado = models.BooleanField(default=False)
    oculto = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.subtotal:
            # Convertir reteica de cadena a decimal
            reteica_decimal = Decimal(self.reteica)

            # Calcular valores
            self.valor_iva = (self.subtotal * (self.iva or 0) / 100).quantize(Decimal("0.01"))
            self.valor_retencion = (self.subtotal * (self.retencion or 0) / 100).quantize(Decimal("0.01"))
            self.valor_reteica = (self.subtotal * reteica_decimal).quantize(Decimal("0.01"))
            self.total_pagar = (
                (self.subtotal * self.cantidad) +
                self.valor_iva -
                self.valor_retencion -
                self.valor_reteica -
                self.saldo_a_favor
            ).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)


class Diario(models.Model):
    TIEMPO_ENTREGA_CHOICES = [(f"{i:02d}:00", f"{i:02d}:00") for i in range(24)]

    # Cambiar a DateTimeField o TimeField si prefieres tener horas específicas
    tiempo_entrega = models.DateField("Fecha de Entrega")

    nombre = models.CharField(max_length=200)
    empresa = models.CharField(max_length=200)

    centro_costo = models.CharField(
        max_length=200,
        choices=[
            ("ADMINISTRACIÓN", "ADMINISTRACIÓN"),
            ("PRODUCCION", "PRODUCCIÓN"),
            ("ALEVINERA", "ALEVINERA"),
            ("ECOPEZ", "ECOPEZ"),
            ("FERRY", "FERRY"),
            ("CARRO PESCA NVS 228", "CARRO PESCA NVS 228"),
            ("CARRO PESCA WGY 964", "CARRO PESCA WGY 964"),
            ("CARRO PESCA THS 473", "CARRO PESCA THS 473"),
            ("CARRO PESCA SRP 254", "CARRO PESCA SRP 254"),
            ("CARRO EXPORTACION GQZ 727", "CARRO EXPORTACIÓN GQZ 727"),
            ("CARRO EXPORTACION GRK 030", "CARRO EXPORTACIÓN GRK 030"),
            ("CARRO EXPORTACION THS 592", "CARRO EXPORTACIÓN THS 592"),
            ("UNIDAD COMERCIALIZACION", "UNIDAD COMERCIALIZACIÓN"),
        ],
    )

    destino = models.CharField(
        max_length=200,
        choices=[
            ("ADMINISTRACIÓN", "ADMINISTRACIÓN"),
            ("PRODUCCION", "PRODUCCIÓN"),
            ("ALEVINERA", "ALEVINERA"),
            ("ECOPEZ", "ECOPEZ"),
            ("FERRY", "FERRY"),
            ("CARRO PESCA NVS 228", "CARRO PESCA NVS 228"),
            ("CARRO PESCA WGY 964", "CARRO PESCA WGY 964"),
            ("CARRO PESCA THS 473", "CARRO PESCA THS 473"),
            ("CARRO PESCA SRP 254", "CARRO PESCA SRP 254"),
            ("CARRO EXPORTACION GQZ 727", "CARRO EXPORTACIÓN GQZ 727"),
            ("CARRO EXPORTACION GRK 030", "CARRO EXPORTACIÓN GRK 030"),
            ("CARRO EXPORTACION THS 592", "CARRO EXPORTACIÓN THS 592"),
            ("UNIDAD COMERCIALIZACION", "UNIDAD COMERCIALIZACIÓN"),
        ],
    )

    medio_pago = models.CharField(
        max_length=200,
        choices=[
            ("cuentas_por_pagar", "Cuentas por Pagar"),
            ("caja_compra", "Caja de Compra"),
            ("tarjeta_debito", "Tarjeta Débito"),
            ("caja_paula", "Caja de Paula"),
        ],
    )

    # Cambiar el nombre del campo para algo más genérico como "documento"
    documento = models.FileField(
        upload_to="documentos/",  # Ruta donde se almacenarán los archivos
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])]  # Extensiones permitidas
    )
    oculto = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Diario {self.nombre} - {self.empresa}"
    

class ReporteCombustible(models.Model):
    COMBUSTIBLE_CHOICES = [
        ('GASOLINA', 'Gasolina'),
        ('ACPM', 'ACPM'),
    ]

    CENTRO_COSTO_CHOICES = [
        ('ADMINISTRACIÓN', 'ADMINISTRACIÓN'),
        ('PRODUCCION', 'PRODUCCIÓN'),
        ('ALEVINERA', 'ALEVINERA'),
        ('ECOPEZ', 'ECOPEZ'),
        ('FERRY', 'FERRY'),
        ('CARRO PESCA NVS 228', 'CARRO PESCA NVS 228'),
        ('CARRO PESCA WGY 964', 'CARRO PESCA WGY 964'),
        ('CARRO PESCA THS 473', 'CARRO PESCA THS 473'),
        ('CARRO PESCA SRP 254', 'CARRO PESCA SRP 254'),
        ('CARRO EXPORTACION GQZ 727', 'CARRO EXPORTACIÓN GQZ 727'),
        ('CARRO EXPORTACION GRK 030', 'CARRO EXPORTACIÓN GRK 030'),
        ('CARRO EXPORTACION THS 592', 'CARRO EXPORTACIÓN THS 592'),
        ('UNIDAD COMERCIALIZACION', 'UNIDAD COMERCIALIZACIÓN'),
    ]

    DESTINO_CHOICES = [
        ('PRODUCCION', 'PRODUCCIÓN'),
        ('ECOPEZ', 'ECOPEZ'),
        ('FERRY', 'FERRY'),
    ]

    fecha = models.DateField()
    combustible = models.CharField(max_length=10, choices=COMBUSTIBLE_CHOICES)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    codigo_estacion = models.CharField(max_length=50)
    empresa = models.CharField(max_length=100)
    centro_costo = models.CharField(max_length=50, choices=CENTRO_COSTO_CHOICES)
    destino = models.CharField(max_length=50, choices=DESTINO_CHOICES)
    conductor = models.CharField(max_length=100)
    placa = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.fecha} - {self.empresa} - {self.cantidad} galones"


