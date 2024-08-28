from django import forms
from .models import Solicitud, Orden, Anticipo, Diario
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
            "solicitado",
            "imagen",
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
            "solicitado": forms.TextInput(
                attrs={"class": "form-control", "required": True}
            ),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
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
            "vlr_unitario",
            "iva",
            "retencion",
            "total_pagar",
            "observaciones",
            "aprobado",
        ]
        widgets = {
            "fecha": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "nit": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "centro_costo": forms.Select(attrs={"class": "form-control"}),
            "producto_servicio": forms.TextInput(attrs={"class": "form-control"}),
            "vlr_unitario": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": "0.01"}
            ),
            "iva": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "retencion": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "total_pagar": forms.NumberInput(
                attrs={"class": "form-control", "readonly": True}
            ),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "aprobado": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


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
        ]
        widgets = {
            "tiempo_entrega": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "empresa": forms.TextInput(attrs={"class": "form-control"}),
            "centro_costo": forms.Select(attrs={"class": "form-control"}),
            "destino": forms.Select(attrs={"class": "form-control"}),
            "medio_pago": forms.Select(attrs={"class": "form-control"}),
            "documento_pdf": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
