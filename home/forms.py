from django import forms
from .models import Solicitud, Orden, Anticipo, Diario,Cotizacion,Mensaje
from decimal import Decimal, ROUND_HALF_UP


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = [
            "fecha",
            "nombre",
            "descripcion",
            "cantidad",
            "destino",
            "tipo",
            "observaciones",
            "archivo",
        ]
        widgets = {
            "fecha": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "nombre": forms.TextInput(
                attrs={"class": "form-control", "required": True}
            ),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "required": True}
            ),
            "cantidad": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "required": True}
            ),
            "destino": forms.TextInput(
                attrs={"class": "form-control", "required": True}
            ),
            "tipo": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.pdf,.xls,.xlsx"}),
        }


class AprobacionRechazoForm(forms.ModelForm):
    comentarios = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), required=False
    )

    class Meta:
        model = Solicitud
        fields = ["estado", "comentarios"]
        widgets = {
            "estado": forms.Select(attrs={"class": "form-control"}),
        }


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = [
            "proveedor",
            "precio",
            "detalles",
            "estado",
            "archivo",  # Cambiamos cotizacion_pdf por archivo para aceptar múltiples tipos
        ]
        widgets = {
            "proveedor": forms.TextInput(attrs={"class": "form-control"}),
            "precio": forms.NumberInput(attrs={"class": "form-control"}),
            "detalles": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.xls,.xlsx,.doc,.docx"}),
        }


class MensajeForm(forms.ModelForm):
    class Meta:
        model = Mensaje
        fields = ["contenido"]
        widgets = {
            "contenido": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Escribe tu mensaje...",
                }
            ),
        }


class OrdenForm(forms.ModelForm):
    class Meta:
        model = Orden
        fields = [
            "descripcion",
            "codigo_cotizacion",
            "precio",
            "cantidad",
            "empresa",
            "destino",
            "tiempo_entrega",
            "observaciones",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "codigo_cotizacion": forms.TextInput(attrs={"class": "form-control"}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "empresa": forms.TextInput(attrs={"class": "form-control"}),
            "destino": forms.TextInput(attrs={"class": "form-control"}),
            "tiempo_entrega": forms.TextInput(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class AnticipoForm(forms.ModelForm):
    class Meta:
        model = Anticipo
        fields = [
            "fecha",
            "nit",
            "nombre",
            "cantidad",
            "centro_costo",
            "producto_servicio",
            "subtotal",
            "iva",
            "valor_iva",  # Mostrar el valor calculado del IVA
            "retencion",
            "valor_retencion",  # Mostrar el valor calculado de la retención
            "total_pagar",
            "observaciones",
        ]
        widgets = {
            "fecha": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "nit": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "centro_costo": forms.Select(
                choices=[
                    ("ADMINISTRACIÓN", "ADMINISTRACIÓN"),
                    ("PRODUCCION", "PRODUCCIÓN"),
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
                    ("UNIDAD COMERCIALIZACION", "UNIDAD COMERCIALIZACIÓN"),
                ],
                attrs={"class": "form-control"},
            ),
            "producto_servicio": forms.TextInput(attrs={"class": "form-control"}),
            "subtotal": forms.NumberInput(attrs={"class": "form-control"}),
            "iva": forms.Select(
                choices=[(0, "Sin IVA"), (5, "5%"), (19, "19%")],
                attrs={"class": "form-control"},
            ),
            "valor_iva": forms.NumberInput(
                attrs={"class": "form-control", "readonly": True}
            ),  # Solo lectura
            "retencion": forms.Select(
                choices=[
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
                ],
                attrs={"class": "form-control"},
            ),
            "valor_retencion": forms.NumberInput(
                attrs={"class": "form-control", "readonly": True}
            ),  # Solo lectura
            "total_pagar": forms.NumberInput(
                attrs={"class": "form-control", "readonly": True}
            ),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AnticipoSearchForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )


class DiarioForm(forms.ModelForm):
    class Meta:
        model = Diario
        fields = [
            "tiempo_entrega",
            "nombre",
            "empresa",
            "centro_costo",
            "destino",
            "medio_pago",
            "documento_pdf",
	    "observaciones",
        ]
        widgets = {
            "tiempo_entrega": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "empresa": forms.TextInput(attrs={"class": "form-control"}),
            "centro_costo": forms.Select(attrs={"class": "form-control"}),
            "destino": forms.Select(attrs={"class": "form-control"}),
            "medio_pago": forms.Select(attrs={"class": "form-control"}),
            "documento_pdf": forms.ClearableFileInput(attrs={"class": "form-control"}),
	    "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

