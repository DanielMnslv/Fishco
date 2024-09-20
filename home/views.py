from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .models import Diario, Solicitud, Orden, Anticipo, Cotizacion
from django.core.paginator import Paginator
from .forms import (
    AprobacionRechazoForm,
    SolicitudForm,
    DiarioForm,
    AnticipoForm,
    OrdenForm,
    CotizacionForm,
)
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from datetime import datetime



@login_required
def index(request):
    return render(request, "pages/index.html", {"segment": "index"})


@login_required
def tables(request):
    return render(request, "pages/ver_solicitudes.html", {"segment": "tables"})


class SolicitudView(LoginRequiredMixin, View):
    def get(self, request):
        form = SolicitudForm()
        return render(request, "pages/solicitud.html", {"form": form})

    def post(self, request):
        form = SolicitudForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Solicitud creada con éxito.")
            return redirect("index")
        return render(request, "pages/solicitud.html", {"form": form})


class SolicitudDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(instance=solicitud)
        cotizaciones = solicitud.cotizaciones.all()
        cotizacion_aprobada = cotizaciones.filter(estado="aprobada").exists()  # Obtener las cotizaciones relacionadas

        return render(
            request,
            "pages/solicitud_detail.html",
            {
                "form": form,
                "solicitud": solicitud,
                "cotizaciones": cotizaciones,  # Pasar las cotizaciones al contexto
		"cotizacion_aprobada": cotizacion_aprobada,           
 },
        )

    def post(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(request.POST, instance=solicitud)
        if form.is_valid():
            form.save()
            messages.success(request, "Solicitud actualizada con éxito.")
            return redirect("ver_solicitudes")

        cotizaciones = (
            solicitud.cotizaciones.all()
        )  # Obtener las cotizaciones relacionadas

        return render(
            request,
            "pages/solicitud_detail.html",
            {
                "form": form,
                "solicitud": solicitud,
                "cotizaciones": cotizaciones,  # Pasar las cotizaciones al contexto en caso de error
            },
        )

def subir_cotizacion(request, solicitud_id):
    solicitud = get_object_or_404(Solicitud, id=solicitud_id)

    if request.method == "POST":
        form = CotizacionForm(request.POST, request.FILES)
        if form.is_valid():
            cotizacion = form.save(commit=False)
            cotizacion.solicitud = solicitud
            cotizacion.cotizacion_imagen = request.FILES.get("cotizacion_imagen")
            cotizacion.save()
            messages.success(request, "Cotización subida con éxito.")
            return redirect("ver_solicitudes")
    else:
        form = CotizacionForm()

    return render(
        request, "subir_cotizacion.html", {"solicitud": solicitud, "form": form}
    )

def aprobar_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    solicitud = cotizacion.solicitud
    cotizaciones = solicitud.cotizaciones.all()

    # Aquí puedes implementar tu lógica de "aprobación"
    # Por ejemplo, podrías usar una lógica personalizada
    cotizaciones.update(estado_aprobada=False)  # Si añades un campo para estado
    cotizacion.estado_aprobada = True  # Este campo deberías añadirlo
    cotizacion.save()

    messages.success(
        request, f"La cotización de {cotizacion.proveedor} ha sido aprobada."
    )
    return redirect("solicitud_detail", pk=solicitud.id)

class OrdenView(LoginRequiredMixin, View):
    def get(self, request):
        form = OrdenForm()
        return render(request, "pages/orden.html", {"form": form})

    def post(self, request):
        form = OrdenForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Orden creada con éxito.")
            return redirect("index")
        return render(request, "pages/orden.html", {"form": form})


class AprobarOrdenView(LoginRequiredMixin, View):
    def post(self, request, orden_id):
        orden = get_object_or_404(Orden, id=orden_id)
        orden.estado = "APROBADA"
        orden.save()
        messages.success(request, "Orden aprobada con éxito.")
        return redirect("ver_ordenes")


@login_required
def anticipo_view(request):
    if request.method == "POST":
        form = AnticipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Anticipo creado con éxito.")
            return redirect("index")
    else:
        form = AnticipoForm()
    return render(request, "pages/anticipo.html", {"form": form})


@login_required
def diario_view(request):
    if request.method == "POST":
        form = DiarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Diario creado con éxito.")
            return redirect("index")
    else:
        form = DiarioForm()
    return render(request, "pages/diario.html", {"form": form})


@login_required
def ver_solicitudes(request):
    solicitudes = Solicitud.objects.all().order_by('-id')
    # Filtrar por los campos
    id_filtro = request.GET.get("id")
    nombre_filtro = request.GET.get("nombre")
    descripcion_filtro = request.GET.get("descripcion")
    cantidad_filtro = request.GET.get("cantidad")
    destino_filtro = request.GET.get("destino")
    tipo_filtro = request.GET.get("tipo")
    solicitado_filtro = request.GET.get("solicitado")
    imagen_filtro = request.GET.get("imagen")

    if id_filtro:
        solicitudes = solicitudes.filter(id=id_filtro)
    if nombre_filtro:
        solicitudes = solicitudes.filter(nombre__icontains=nombre_filtro)
    if descripcion_filtro:
        solicitudes = solicitudes.filter(descripcion__icontains=descripcion_filtro)
    if cantidad_filtro:
        solicitudes = solicitudes.filter(cantidad=cantidad_filtro)
    if destino_filtro:
        solicitudes = solicitudes.filter(destino__icontains=destino_filtro)
    if tipo_filtro:
        solicitudes = solicitudes.filter(tipo__icontains=tipo_filtro)
    if solicitado_filtro:
        solicitudes = solicitudes.filter(solicitado__icontains=solicitado_filtro)
    if imagen_filtro:
        solicitudes = solicitudes.filter(imagen_icontains=imagen_filtro)

    # Paginación
    paginator = Paginator(solicitudes, 10)  # Muestra 10 solicitudes por página
    page_number = request.GET.get("page")
    solicitudes_page = paginator.get_page(page_number)

    return render(
        request, "pages/ver_solicitudes.html", {"solicitudes": solicitudes_page}
    )


@login_required
def ver_ordenes(request):
    ordenes = Orden.objects.all()
    filters = {
        "id": request.GET.get("id"),
        "descripcion__icontains": request.GET.get("descripcion"),
        "codigo_cotizacion__icontains": request.GET.get("codigo_cotizacion"),
        "precio": request.GET.get("precio"),
        "cantidad": request.GET.get("cantidad"),
        "empresa__icontains": request.GET.get("empresa"),
        "destino__icontains": request.GET.get("destino"),
        "tiempo_entrega__icontains": request.GET.get("tiempo_entrega"),
        "observaciones__icontains": request.GET.get("observaciones"),
    }
    for key, value in filters.items():
        if value:
            ordenes = ordenes.filter(**{key: value})

    paginator = Paginator(ordenes, 10)
    page_number = request.GET.get("page")
    ordenes_page = paginator.get_page(page_number)
    return render(request, "pages/ver_ordenes.html", {"ordenes": ordenes_page})


@login_required
def ver_diario(request):
    diario = Diario.objects.all()
    filters = {
        "id": request.GET.get("id"),
        "tiempo_entrega__icontains": request.GET.get("tiempo_entrega"),
        "nombre__icontains": request.GET.get("nombre"),
        "empresa": request.GET.get("empresa"),
        "centro_costo": request.GET.get("centro_costo"),
        "destino__icontains": request.GET.get("destino"),
        "medio_pago__icontains": request.GET.get("medio_pago"),
        "documento_pdf__icontains": request.GET.get("documento_pdf"),
    }
    for key, value in filters.items():
        if value:
            diario = diario.filter(**{key: value})

    paginator = Paginator(diario, 10)
    page_number = request.GET.get("page")
    diario_page = paginator.get_page(page_number)
    return render(request, "pages/ver_diario.html", {"diario": diario_page})


@login_required
def ver_anticipos(request):
    anticipo = Anticipo.objects.all()
    filters = {
        "id": request.GET.get("id"),
        "centro_costo__icontains": request.GET.get("centro_costo"),
        "nit__icontains": request.GET.get("nit"),
        "nombre": request.GET.get("nombre"),
        "producto_servicio": request.GET.get("producto_servicio"),
        "cantidad__icontains": request.GET.get("cantidad"),
        "vlr_unitario__icontains": request.GET.get("vlr_unitario"),
        "subtotal__icontains": request.GET.get("subtotal"),
        "iva__icontains": request.GET.get("iva"),
        "retencion__icontains": request.GET.get("retencion"),
        "total_pagar__icontains": request.GET.get("total_pagar"),
        "observaciones__icontains": request.GET.get("observaciones"),
        "documento_pdf__icontains": request.GET.get("documento_pdf"),
    }
    for key, value in filters.items():
        if value:
            anticipo = anticipo.filter(**{key: value})

    paginator = Paginator(anticipo, 10)
    page_number = request.GET.get("page")
    anticipo_page = paginator.get_page(page_number)
    return render(request, "pages/ver_anticipos.html", {"anticipo": anticipo_page})


@login_required
def aprobar_anticipo(request, anticipo_id):
    anticipo = get_object_or_404(Anticipo, id=anticipo_id)
    if request.method == "POST":
        anticipo.aprobado = True
        anticipo.save()
        messages.success(request, "Anticipo aprobado con éxito.")
        return redirect("ver_anticipos")
    return render(request, "aprobar_anticipo.html", {"anticipo": anticipo})


def generar_reporte_orden(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)

    # Crear el objeto HttpResponse con el tipo de contenido PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="orden_{orden_id}.pdf"'

    # Crear el objeto SimpleDocTemplate para generar el PDF
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Crear un estilo para los encabezados
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    header_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Título del documento
    title = Paragraph(f"Orden de Compra {orden.id}", title_style)
    elements.append(title)

    # Espacio después del título
    elements.append(Paragraph("<br/>", normal_style))

    # Datos de la orden en una tabla
    data = [
        ["Descripción", orden.descripcion],
	["Fecha", datetime.now().strftime('%Y-%m-%d')],
        ["Código Cotización", orden.codigo_cotizacion],
        ["Precio", f"${orden.precio:,.2f}"],  # Formato de precio con separador de miles y 2 decimales
        ["Cantidad", str(orden.cantidad)],
        ["Empresa", orden.empresa],
        ["Tiempo de Entrega", orden.tiempo_entrega],
        ["Observaciones", orden.observaciones],
        ["Estado", orden.get_estado_display()],
    ]
    
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), "#d0d0d0"),  # Fondo gris claro para la fila del encabezado
                ("TEXTCOLOR", (0, 0), (-1, 0), "#000000"),  # Texto negro para el encabezado
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),  # Alineación del texto a la izquierda
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Fuente en negrita para el encabezado
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),  # Fuente normal para el contenido
                ("BACKGROUND", (0, 1), (-1, -1), "#f9f9f9"),  # Fondo blanco para el resto de las filas
                ("GRID", (0, 0), (-1, -1), 1, "#000000"),  # Rejilla negra alrededor de las celdas
                ("BOX", (0, 0), (-1, -1), 1, "#000000"),  # Borde exterior negro
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Alineación vertical en el medio
                ("ALIGN", (1, 1), (-1, -1), "LEFT"),  # Alineación del texto en el contenido
            ]
        )
    )

    elements.append(table)


    # Construir el documento PDF
    doc.build(elements)

    return response

    
