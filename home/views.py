from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
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
    AnticipoSearchForm,
)
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse,JsonResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.units import inch
from datetime import datetime
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date



@login_required
def index(request):
    return render(request, "pages/index.html", {"segment": "index"})


@login_required
def tables(request):
    return render(request, "pages/ver_solicitudes.html", {"segment": "tables"})

# Vista para superusuarios
class SuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

# Vista para usuarios con rol de staff
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

# Decorador para superusuarios
def superuser_required(function):
    return user_passes_test(lambda u: u.is_superuser)(function)

# Decorador para staff
def staff_required(function):
    return user_passes_test(lambda u: u.is_staff)(function)


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


class SolicitudDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff
    def get(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(instance=solicitud)
        cotizaciones = solicitud.cotizaciones.all()
	# Formatear el precio de las cotizaciones
        for cotizacion in cotizaciones:
            cotizacion.precio_formateado = "${:,.2f}".format(cotizacion.precio).replace(',', 'X').replace('.', ',').replace('X', '.')
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
	
	# Formatear el precio de las cotizaciones
        for cotizacion in cotizaciones:
            cotizacion.precio_formateado = "${:,.2f}".format(cotizacion.precio).replace(',', 'X').replace('.', ',').replace('X', '.')

        return render(
            request,
            "pages/solicitud_detail.html",
            {
                "form": form,
                "solicitud": solicitud,
                "cotizaciones": cotizaciones,  # Pasar las cotizaciones al contexto en caso de error
            },
        )

@superuser_required  # solo superusuarios deben subir cotizaciones
@login_required
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

# Vista para aprobar cotización (solo usuarios con permisos específicos)
@user_passes_test(lambda u: u.id in [31, 33])  # IDs permitidos
@login_required
@login_required
def aprobar_cotizacion(request, cotizacion_id):
    # Verificar si el usuario tiene los ID permitidos
    if request.user.id not in [31, 33]:
        messages.error(request, "No tienes permiso para aprobar cotizaciones.")
        return redirect("ver_solicitudes")

    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    solicitud = cotizacion.solicitud
    cotizaciones = solicitud.cotizaciones.all()

    # Cambiar el estado de todas las cotizaciones a "Pendiente" excepto la aprobada
    cotizaciones.update(estado="pendiente", estado_aprobada=False)

    # Actualizar la cotización aprobada
    cotizacion.estado_aprobada = True  # Marca que esta cotización está aprobada
    cotizacion.estado = "aprobada"  # Cambia el estado a "aprobada"
    cotizacion.save()

    messages.success(
        request, f"La cotización de {cotizacion.proveedor} ha sido aprobada."
    )
    return redirect("solicitud_detail", pk=solicitud.id)


@superuser_required  # O @staff_required, dependiendo de quién deba poder ocultar solicitudes
@login_required
def ocultar_solicitud(request, id):
    # Obtener la solicitud por su ID
    solicitud = get_object_or_404(Solicitud, id=id)
    # Marcar la solicitud como oculta
    solicitud.oculto = True
    solicitud.save()
    # Retornar una respuesta JSON para confirmar la acción
    return JsonResponse({"success": True})


class OrdenView(LoginRequiredMixin, SuperUserRequiredMixin, View):
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


class AprobarOrdenView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, orden_id):
        # Verificar si el usuario tiene los ID permitidos
        if request.user.id not in [31, 33, 32]:
            messages.error(request, "No tienes permiso para aprobar órdenes.")
            return redirect("ver_ordenes")
        
        orden = get_object_or_404(Orden, id=orden_id)
        orden.estado = "APROBADA"
        orden.save()
        messages.success(request, "Orden aprobada con éxito.")
        return redirect("ver_ordenes")


@staff_required
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

@staff_required
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

# Vista para ver solicitudes (solo superusuarios)
@superuser_required
@login_required
def ver_solicitudes(request):
    solicitudes = Solicitud.objects.filter(oculto=False)

    # Filtrar por los campos
    id_filtro = request.GET.get("id")
    nombre_filtro = request.GET.get("nombre")
    descripcion_filtro = request.GET.get("descripcion")
    cantidad_filtro = request.GET.get("cantidad")
    destino_filtro = request.GET.get("destino")
    tipo_filtro = request.GET.get("tipo")
    solicitado_filtro = request.GET.get("solicitado")
    imagen_filtro = request.GET.get("imagen")

    for solicitud in solicitudes:
        solicitud.cotizacion_aprobada = solicitud.cotizaciones.filter(
            estado="aprobada"
        ).first()

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

    # Aquí removemos la lógica de paginación para que se muestren todas las solicitudes
    return render(
        request, "pages/ver_solicitudes.html", {"solicitudes": solicitudes}
    )


# Vista para ver órdenes (solo superusuarios)
@superuser_required
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


@staff_required
@login_required
def ver_diario(request):
    diario = Diario.objects.all()

    # Obtener fechas de inicio y fin de los filtros
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    # Verificar que las fechas sean válidas y no nulas
    if fecha_inicio and fecha_fin:
        try:
            # Convertir las fechas a objetos datetime
            fecha_inicio = parse_date(fecha_inicio)
            fecha_fin = parse_date(fecha_fin)

            # Filtrar usando las fechas
            if fecha_inicio and fecha_fin:
                diario = diario.filter(tiempo_entrega__range=[fecha_inicio, fecha_fin])
        except ValueError:
            pass  # Si ocurre un error con las fechas, no filtrar

    # Paginación si es necesario
    paginator = Paginator(diario, 10)
    page_number = request.GET.get("page")
    diario_page = paginator.get_page(page_number)

    return render(request, "pages/ver_diario.html", {"diario": diario_page})


@staff_required
@login_required
def ver_anticipos(request):
    anticipos = Anticipo.objects.filter(oculto=False)  # Filtrar anticipos no ocultos
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            anticipos = anticipos.filter(fecha__range=(fecha_inicio, fecha_fin))
        except ValueError:
            anticipos = anticipos.none()
    elif fecha_inicio:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            anticipos = anticipos.filter(fecha__gte=fecha_inicio)
        except ValueError:
            anticipos = anticipos.none()
    elif fecha_fin:
        try:
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            anticipos = anticipos.filter(fecha__lte=fecha_fin)
        except ValueError:
            anticipos = anticipos.none()

    return render(request, "pages/ver_anticipos.html", {"anticipos": anticipos})


# Vista para aprobar anticipo (solo usuarios con permisos específicos)
@user_passes_test(lambda u: u.id in [31, 33])  # IDs permitidos
@login_required
def aprobar_anticipo(request, anticipo_id):
    # Verificar si el usuario tiene los ID permitidos
    if request.user.id not in [31, 33]:
        messages.error(request, "No tienes permiso para aprobar anticipos.")
        return redirect("ver_anticipos")

    anticipo = get_object_or_404(Anticipo, id=anticipo_id)

    if request.method == "POST":
        anticipo.aprobado = True
        anticipo.save()
        messages.success(request, "Anticipo aprobado con éxito.")
        return redirect("ver_anticipos")

    return render(request, "aprobar_anticipo.html", {"anticipo": anticipo})


# Vista para aprobar anticipos masivamente (solo usuarios con permisos específicos)
@user_passes_test(lambda u: u.id in [31, 33])  # IDs permitidos
@login_required
def aprobar_anticipos_masivamente(request):
    # Verificar si el usuario tiene los ID permitidos
    if request.user.id not in [31, 33]:
        messages.error(request, "No tienes permiso para aprobar anticipos.")
        return redirect("ver_anticipos")
    
    if request.method == "POST":
        anticipo_ids = request.POST.getlist("anticipo_ids")
        # Aprobamos los anticipos seleccionados
        Anticipo.objects.filter(id__in=anticipo_ids).update(aprobado=True)

        messages.success(request, "Anticipos aprobados con éxito.")
    return redirect("ver_anticipos")


class AnticipoListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Anticipo
    template_name = "anticipo_list.html"
    context_object_name = "anticipos"

    def get_queryset(self):
        queryset = super().get_queryset()
        fecha_inicio = self.request.GET.get("fecha_inicio")
        fecha_fin = self.request.GET.get("fecha_fin")

        # Filtrar por rango de fechas
        if fecha_inicio and fecha_fin:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
                queryset = queryset.filter(fecha__range=(fecha_inicio, fecha_fin))
            except ValueError:
                queryset = (
                    queryset.none()
                )  # Devolver queryset vacío si hay error en fechas
        elif fecha_inicio:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                queryset = queryset.filter(fecha__gte=fecha_inicio)
            except ValueError:
                queryset = queryset.none()
        elif fecha_fin:
            try:
                fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
                queryset = queryset.filter(fecha__lte=fecha_fin)
            except ValueError:
                queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = AnticipoSearchForm(self.request.GET)
        return context

@staff_required  # O @superuser_required, dependiendo del nivel de restricción
@login_required
@csrf_exempt
def ocultar_anticipo(request, anticipo_id):
    try:
        anticipo = get_object_or_404(Anticipo, id=anticipo_id)
        anticipo.oculto = True  # Cambiar el estado del anticipo a "oculto"
        anticipo.save()
        return JsonResponse({"success": True}, status=200)
    except Anticipo.DoesNotExist:
        return JsonResponse({"error": "Anticipo no encontrado"}, status=404)


@superuser_required  # O @staff_required, dependiendo del nivel de restricción
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


@staff_required  # O @superuser_required, dependiendo del nivel de restricción    
@login_required
def generar_pdf_anticipos_aprobados(request):
    # Obtener las fechas de inicio y fin del filtro
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    # Verificar que se proporcionen las fechas
    if not fecha_inicio or not fecha_fin:
        messages.error(
            request, "Debes seleccionar un rango de fechas para descargar el PDF."
        )
        return redirect("ver_anticipos")

    try:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha inválido.")
        return redirect("ver_anticipos")

    # Filtrar anticipos aprobados por las fechas
    anticipos_aprobados = Anticipo.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin), aprobado=True
    )

    if not anticipos_aprobados.exists():
        messages.error(
            request, "No hay anticipos aprobados en el rango de fechas seleccionado."
        )
        return redirect("ver_anticipos")

    # Crear la respuesta HTTP para descargar el PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="anticipos_aprobados_{fecha_inicio}_{fecha_fin}.pdf"'
    )

    # Crear el documento PDF con formato apaisado
    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    elements = []

    # Encabezado del PDF
    styles = getSampleStyleSheet()
    elements.append(
        Paragraph(
            f"Anticipos Aprobados desde {fecha_inicio} hasta {fecha_fin}",
            styles["Title"],
        )
    )

    # Crear una tabla con los datos de los anticipos aprobados
    data = [
        [
            "Centro de Costo",
            "NIT",
            "Nombre",
            "Producto/Servicio",
            "Cantidad",
            "Subtotal",
            "IVA",
            "Retención",
            "Total a Pagar",
            "Observaciones",
        ]
    ]

    # Llenar la tabla con los datos
    for anticipo in anticipos_aprobados:
        data.append(
            [
                anticipo.centro_costo,
                anticipo.nit,
                anticipo.nombre,
                anticipo.producto_servicio,
                str(anticipo.cantidad),
                f"${anticipo.subtotal:,.2f}",
                f"${anticipo.valor_iva:,.2f}",
                f"${anticipo.valor_retencion:,.2f}",
                f"${anticipo.total_pagar:,.2f}",
                anticipo.observaciones or "N/A",
            ]
        )

    # Crear la tabla sin especificar colWidths para que ajuste automáticamente
    table = Table(data)
    
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),  # Fondo gris para el encabezado
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),  # Color de texto blanco en el encabezado
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # Alinear todo al centro
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # Fuente en negrita para el encabezado
                ("FONTSIZE", (0, 0), (-1, 0), 10),  # Tamaño de fuente para el encabezado
                ("FONTSIZE", (0, 1), (-1, -1), 8),  # Tamaño de fuente reducido para el contenido
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),  # Espacio debajo del encabezado
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),  # Fondo beige para el resto de las filas
                ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Cuadrícula negra
            ]
        )
    )

    # Añadir la tabla a los elementos
    elements.append(table)

    # Construir el PDF
    doc.build(elements)

    return response

           
