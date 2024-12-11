from django import forms
from .models import Solicitud, Orden, Anticipo, Diario,Cotizacion,Mensaje,ReporteCombustible
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
            "archivo": forms.ClearableFileInput(attrs={
                "class": "form-control", 
                "accept": ".jpg,.jpeg,.png,.gif,.bmp,.webp,.tiff,.svg,.pdf,.xls,.xlsx"
            }),
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
            "fecha", "centro_costo", "nit", "nombre", 
            "producto_servicio", "cantidad", "subtotal", 
            "iva", "retencion", "reteica", "saldo_a_favor", 
            "observaciones", "total_pagar"
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "centro_costo": forms.TextInput(attrs={"class": "form-control"}),
            "nit": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "producto_servicio": forms.TextInput(attrs={"class": "form-control"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "subtotal": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "iva": forms.Select(attrs={"class": "form-control"}),  # Select para choices de IVA
            "retencion": forms.Select(attrs={"class": "form-control"}),  # Select para choices de Retención
            "reteica": forms.Select(attrs={"class": "form-control"}),  # Select para choices de reteICA
            "saldo_a_favor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "total_pagar": forms.NumberInput(attrs={"class": "form-control", "readonly": True}),
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
    nombre = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"})
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
            "documento",  # Asegúrate de que el campo se llama "documento" ahora
            "observaciones",
        ]
        widgets = {
            "tiempo_entrega": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "empresa": forms.TextInput(attrs={"class": "form-control"}),
            "centro_costo": forms.Select(attrs={"class": "form-control"}),
            "destino": forms.Select(attrs={"class": "form-control"}),
            "medio_pago": forms.Select(attrs={"class": "form-control"}),
            "documento": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.doc,.docx"}  # Permitir múltiples tipos de archivos
            ),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }




class ReporteCombustibleForm(forms.ModelForm):
    class Meta:
        model = ReporteCombustible
        fields = [
            'fecha',
            'combustible',
            'cantidad',
            'codigo_estacion',
            'empresa',
            'centro_costo',
            'destino',
            'conductor',
            'placa'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'combustible': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'codigo_estacion': forms.TextInput(attrs={'class': 'form-control'}),
            'empresa': forms.TextInput(attrs={'class': 'form-control'}),
            'centro_costo': forms.Select(attrs={'class': 'form-control'}),
            'destino': forms.Select(attrs={'class': 'form-control'}),
            'conductor': forms.TextInput(attrs={'class': 'form-control'}),
            'placa': forms.TextInput(attrs={'class': 'form-control'}),
        }
