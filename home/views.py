from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from .models import Diario, Solicitud, Orden, Anticipo, Cotizacion, Mensaje
from django.core.paginator import Paginator
from .forms import (
    AprobacionRechazoForm,
    SolicitudForm,
    DiarioForm,
    AnticipoForm,
    OrdenForm,
    CotizacionForm,
    AnticipoSearchForm,
    MensajeForm,
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
from django.views.decorators.csrf import csrf_exempt,csrf_protect
from django.utils.dateparse import parse_date
import os
from django.conf import settings
from django.db.models import Max
from django.core.cache import cache
from django.core.mail import send_mail


@login_required
def index(request):
    # Obtener estadísticas de Solicitudes
    total_solicitudes = Solicitud.objects.count()
    solicitudes_aprobadas = Solicitud.objects.filter(estado="aprobado").count()

    # Obtener estadísticas de Cotizaciones
    total_cotizaciones = Cotizacion.objects.count()
    cotizaciones_aprobadas = Cotizacion.objects.filter(estado="aprobada").count()

    # Obtener estadísticas de Anticipos
    total_anticipos = Anticipo.objects.count()
    anticipos_aprobados = Anticipo.objects.filter(aprobado=True).count()

    # Obtener estadísticas de Órdenes
    total_ordenes = Orden.objects.count()
    ordenes_aprobadas = Orden.objects.filter(estado="APROBADA").count()

    # Calcular porcentajes
    porcentaje_solicitudes_aprobadas = (solicitudes_aprobadas / total_solicitudes * 100) if total_solicitudes > 0 else 0
    porcentaje_cotizaciones_aprobadas = (cotizaciones_aprobadas / total_cotizaciones * 100) if total_cotizaciones > 0 else 0
    porcentaje_anticipos_aprobados = (anticipos_aprobados / total_anticipos * 100) if total_anticipos > 0 else 0
    porcentaje_ordenes_aprobadas = (ordenes_aprobadas / total_ordenes * 100) if total_ordenes > 0 else 0

    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'porcentaje_solicitudes_aprobadas': porcentaje_solicitudes_aprobadas,

        'total_cotizaciones': total_cotizaciones,
        'cotizaciones_aprobadas': cotizaciones_aprobadas,
        'porcentaje_cotizaciones_aprobadas': porcentaje_cotizaciones_aprobadas,

        'total_anticipos': total_anticipos,
        'anticipos_aprobados': anticipos_aprobados,
        'porcentaje_anticipos_aprobados': porcentaje_anticipos_aprobados,

        'total_ordenes': total_ordenes,
        'ordenes_aprobadas': ordenes_aprobadas,
        'porcentaje_ordenes_aprobadas': porcentaje_ordenes_aprobadas,
    }

    return render(request, "pages/index.html", context)


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
            solicitud = form.save(commit=False)  # No guardar aún, para asignar el usuario
            solicitud.usuario = request.user  # Asignar el usuario autenticado
            solicitud.save()  # Ahora sí, guardar con el usuario asignado

            # Enviar notificación por correo a múltiples destinatarios
            subject = f'Nueva solicitud creada: {solicitud.nombre}'
            message = f'Una nueva solicitud ha sido creada por {request.user.username}.\n\n' \
                      f'Detalles:\n' \
                      f'Nombre: {solicitud.nombre}\n' \
                      f'Destino: {solicitud.destino}\n' \
                      f'Tipo: {solicitud.tipo}\n\n' \
                      f'Ver más en la plataforma.'
            
            # Lista de destinatarios
            recipient_list = ["gestiondocumental.pfishco@gmail.com"]
            from_email = settings.DEFAULT_FROM_EMAIL  # El correo configurado como remitente

            # Enviar el correo
            send_mail(subject, message, from_email, recipient_list)

            messages.success(request, "Solicitud creada con éxito y notificación enviada.")
            return redirect("index")
        return render(request, "pages/solicitud.html", {"form": form})


class SolicitudDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    # Solo superusuario o staff pueden acceder a esta vista
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(instance=solicitud)
        mensaje_form = MensajeForm()
        mensajes = solicitud.mensajes.all().order_by("fecha_envio")
        cotizaciones = solicitud.cotizaciones.all()

        # Formatear el precio de las cotizaciones
        for cotizacion in cotizaciones:
            cotizacion.precio_formateado = (
                "${:,.2f}".format(cotizacion.precio)
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        cotizacion_aprobada = cotizaciones.filter(estado="aprobada").exists()

        return render(
            request,
            "pages/solicitud_detail.html",
            {
                "form": form,
                "mensaje_form": mensaje_form,
                "mensajes": mensajes,
                "solicitud": solicitud,
                "cotizaciones": cotizaciones,
                "cotizacion_aprobada": cotizacion_aprobada,
            },
        )

    def post(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(request.POST, instance=solicitud)
        mensaje_form = MensajeForm(request.POST)

        # Guardar el formulario de mensaje
        if mensaje_form.is_valid():
            nuevo_mensaje = mensaje_form.save(commit=False)
            nuevo_mensaje.solicitud = solicitud
            nuevo_mensaje.remitente = request.user  # Aquí asignas el remitente
            nuevo_mensaje.save()
            messages.success(request, "Mensaje enviado con éxito.")
            return redirect("solicitud_detail", pk=solicitud.id)

        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Solicitud actualizada con éxito.")
                return redirect("ver_solicitudes")
            except Exception as e:
                messages.error(request, f"Ocurrió un error al guardar: {str(e)}")
        else:
            messages.error(
                request, "Hubo un error en el formulario. Por favor verifica los datos."
            )

        cotizaciones = solicitud.cotizaciones.all()
        for cotizacion in cotizaciones:
            cotizacion.precio_formateado = (
                "${:,.2f}".format(cotizacion.precio)
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        mensajes = solicitud.mensajes.all().order_by("fecha_envio")
        return render(
            request,
            "pages/solicitud_detail.html",
            {
                "form": form,
                "mensaje_form": mensaje_form,
                "mensajes": mensajes,
                "solicitud": solicitud,
                "cotizaciones": cotizaciones,
            },
        )

@login_required
@superuser_required
def subir_cotizacion(request, solicitud_id):
    solicitud = get_object_or_404(Solicitud, id=solicitud_id)

    if request.method == "POST":
        form = CotizacionForm(request.POST, request.FILES)
        if form.is_valid():
            cotizacion = form.save(commit=False)
            cotizacion.solicitud = solicitud
            cotizacion.archivo = request.FILES.get("archivo")  # Guardar el archivo subido
            cotizacion.save()
            messages.success(request, "Cotización subida con éxito.")
            return redirect("ver_solicitudes")
    else:
        form = CotizacionForm()

    return render(request, "subir_cotizacion.html", {"solicitud": solicitud, "form": form})

# Vista para aprobar cotización (solo usuarios con permisos específicos)
@user_passes_test(lambda u: u.id in [31, 33])  # IDs permitidos
@login_required
def aprobar_cotizacion(request, cotizacion_id):
    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    solicitud = cotizacion.solicitud
    cotizaciones = solicitud.cotizaciones.all()

    # Cambiar el estado de todas las cotizaciones a "Pendiente" excepto la aprobada
    cotizaciones.update(estado="pendiente", estado_aprobada=False)

    # Actualizar la cotización aprobada
    cotizacion.estado_aprobada = True  # Marca que esta cotización está aprobada
    cotizacion.estado = "aprobada"  # Cambia el estado a "aprobada"
    cotizacion.save()

    # Enviar notificación por correo a los destinatarios
    subject = f'Cotización aprobada para la solicitud: {solicitud.nombre}'
    message = f'Se ha aprobado una cotización de {cotizacion.proveedor} para la solicitud "{solicitud.nombre}".\n\n' \
              f'Detalles de la cotización:\n' \
              f'Proveedor: {cotizacion.proveedor}\n' \
              f'Precio: ${cotizacion.precio:,.2f}\n' \
              f'Solicitud: {solicitud.nombre}\n\n' \
              f'Ver más detalles en la plataforma.'

    # Lista de destinatarios
    recipient_list = ["auxcompras@cifishco.com.co", "gestiondocumental.pfishco@gmail.com"]
    from_email = settings.DEFAULT_FROM_EMAIL

    # Enviar el correo
    send_mail(subject, message, from_email, recipient_list)

    messages.success(request, f"La cotización de {cotizacion.proveedor} ha sido aprobada y se ha notificado por correo.")
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
    # Obtener todas las solicitudes que no están ocultas
    solicitudes_con_cotizacion = Solicitud.objects.filter(
        oculto=False, cotizaciones__isnull=False
    ).distinct().prefetch_related('mensajes', 'cotizaciones').order_by('fecha')

    solicitudes_sin_cotizacion = Solicitud.objects.filter(
        oculto=False, cotizaciones__isnull=True
    ).distinct().prefetch_related('mensajes').order_by('fecha')

    # Concatenar ambas consultas: primero las que tienen cotización, luego las que no
    solicitudes = list(solicitudes_con_cotizacion) + list(solicitudes_sin_cotizacion)

    # Guardar las solicitudes en cache durante 10 minutos
    cache.set('solicitudes', solicitudes, 600)

    # Aplicar los filtros en las solicitudes
    id_filtro = request.GET.get("id")
    nombre_filtro = request.GET.get("nombre")
    descripcion_filtro = request.GET.get("descripcion")
    cantidad_filtro = request.GET.get("cantidad")
    destino_filtro = request.GET.get("destino")
    tipo_filtro = request.GET.get("tipo")
    solicitado_filtro = request.GET.get("solicitado")

    # Aplicar los filtros en las solicitudes
    if id_filtro:
        solicitudes = [sol for sol in solicitudes if str(sol.id) == id_filtro]
    if nombre_filtro:
        solicitudes = [sol for sol in solicitudes if nombre_filtro.lower() in sol.nombre.lower()]
    if descripcion_filtro:
        solicitudes = [sol for sol in solicitudes if descripcion_filtro.lower() in sol.descripcion.lower()]
    if cantidad_filtro:
        solicitudes = [sol for sol in solicitudes if sol.cantidad == int(cantidad_filtro)]
    if destino_filtro:
        solicitudes = [sol for sol in solicitudes if destino_filtro.lower() in sol.destino.lower()]
    if tipo_filtro:
        solicitudes = [sol for sol in solicitudes if tipo_filtro.lower() in sol.tipo.lower()]
    if solicitado_filtro:
        solicitudes = [sol for sol in solicitudes if solicitado_filtro.lower() in sol.solicitado.lower()]

    # Añadir información extra a cada solicitud
    for solicitud in solicitudes:
        # Último mensaje relacionado
        solicitud.ultimo_mensaje = solicitud.mensajes.order_by('-fecha_envio').first()

        # Cotización aprobada
        solicitud.cotizacion_aprobada = solicitud.cotizaciones.filter(estado="aprobada").first()

        # Si la cotización aprobada tiene un archivo
        if solicitud.cotizacion_aprobada and solicitud.cotizacion_aprobada.archivo:
            solicitud.cotizacion_pdf_url = solicitud.cotizacion_aprobada.archivo
        else:
            solicitud.cotizacion_pdf_url = None

    # Paginación: mostrar 31 solicitudes por página
    paginator = Paginator(solicitudes, 70)  # Ajusta este número según lo necesites
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Renderizar la plantilla con las solicitudes filtradas y paginadas
    return render(request, "pages/ver_solicitudes.html", {"solicitudes": page_obj})



@login_required
def mis_solicitudes(request):
    # Obtener las solicitudes del usuario autenticado
    solicitudes = Solicitud.objects.filter(usuario=request.user).prefetch_related('mensajes', 'cotizaciones')

    # Para cada solicitud, obtener el último mensaje y el estado calculado
    for solicitud in solicitudes:
        solicitud.ultimo_mensaje = solicitud.mensajes.order_by('-fecha_envio').first()  # Obtener el mensaje más reciente
        
        # Lógica para calcular el estado de la solicitud basado en las cotizaciones
        cotizaciones = solicitud.cotizaciones.all()
        
        if cotizaciones.exists():  # Si tiene cotizaciones
            if cotizaciones.filter(estado='aprobada').exists():
                solicitud.estado = "aprobado"
            else:
                solicitud.estado = "revisado por compras"
        else:
            solicitud.estado = "pendiente"

    context = {
        'solicitudes': solicitudes,
    }

    return render(request, 'pages/mis_solicitudes.html', context)


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
    # Filtrar solo los diarios que no estén ocultos
    diarios = Diario.objects.filter(oculto=False)

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
                diarios = diarios.filter(tiempo_entrega__range=[fecha_inicio, fecha_fin])
        except ValueError:
            pass  # Si ocurre un error con las fechas, no filtrar

    # Paginación si es necesario
    paginator = Paginator(diarios, 50)
    page_number = request.GET.get("page")
    diario_page = paginator.get_page(page_number)

    return render(request, "pages/ver_diario.html", {"diarios": diario_page})


@login_required
@staff_required
def ocultar_diario(request):
    if request.method == "POST":
        diarios_ids = request.POST.get("diarios_ids", "")
        if diarios_ids:
            diarios_ids = diarios_ids.split(",")
            Diario.objects.filter(id__in=diarios_ids).update(oculto=True)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "No se seleccionaron diarios."})
    return JsonResponse({"success": False, "error": "Método no permitido"})

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


@user_passes_test(lambda u: u.id in [31, 33])  # IDs permitidos
@login_required
def aprobar_anticipos_masivamente(request):
    if request.method == "POST":
        anticipo_ids = request.POST.getlist("anticipo_ids")
        print(f"IDs recibidos desde el frontend: {anticipo_ids}")  # Depuración: Verificar qué IDs llegan

        if anticipo_ids:
            try:
                anticipo_ids = [int(id) for id in anticipo_ids]  # Asegurarse de que los IDs son enteros
                print(f"IDs seleccionados (convertidos a enteros): {anticipo_ids}")  # Verificación adicional
                anticipos_aprobados = Anticipo.objects.filter(id__in=anticipo_ids)

                if anticipos_aprobados.exists():
                    anticipos_aprobados.update(aprobado=True)
                    messages.success(request, "Anticipos aprobados con éxito.")
                else:
                    messages.error(request, "No se encontraron anticipos válidos para aprobar.")
            except ValueError as e:
                messages.error(request, f"Error al convertir los IDs de anticipos: {str(e)}")
        else:
            messages.error(request, "No se seleccionaron anticipos para aprobar.")
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



@login_required
@csrf_protect
def ocultar_anticipos(request):
    if request.method == 'POST':
        anticipos_ids = request.POST.get("anticipos_ids", "").split(",")
        if anticipos_ids:
            # Verificar si se encontraron anticipos con esos IDs
            updated_count = Anticipo.objects.filter(id__in=anticipos_ids).update(oculto=True)
            if updated_count > 0:
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"success": False, "error": "No se encontraron anticipos con los IDs proporcionados"})
        return JsonResponse({"success": False, "error": "No se seleccionaron anticipos"})





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

    # Añadir el logo al encabezado
    logo_path = os.path.join(
        settings.MEDIA_ROOT, "imagenes/Logo.png"
    )  # Asegúrate de que la imagen del logo esté en esta ruta
    logo = Image(logo_path, width=100, height=50)  # Ajusta el tamaño del logo
    elements.append(logo)

    # Añadir el texto del encabezado
    header_text = Paragraph(
        "ORDEN DE COMPRA O SERVICIO - C.I. PISCÍCOLA FISHCO S.A.S.", header_style
    )
    elements.append(header_text)

    # Espacio después del encabezado
    elements.append(Paragraph("<br/>", normal_style))

    # Título del documento
    title = Paragraph(f"Orden de Compra {orden.id}", title_style)
    elements.append(title)

    # Espacio después del título
    elements.append(Paragraph("<br/>", normal_style))

    # Datos de la orden en una tabla
    data = [
        ["Descripción", orden.descripcion],
        ["Fecha", datetime.now().strftime("%Y-%m-%d")],
        ["Código Cotización", orden.codigo_cotizacion],
        [
            "Precio",
            f"${orden.precio:,.2f}",
        ],  # Formato de precio con separador de miles y 2 decimales
        ["Cantidad", str(orden.cantidad)],
        ["Empresa", orden.empresa],
        ["Tiempo de Entrega", orden.tiempo_entrega],
        ["Observaciones", orden.observaciones],
    ]

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    "#d0d0d0",
                ),  # Fondo gris claro para la fila del encabezado
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    "#000000",
                ),  # Texto negro para el encabezado
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "LEFT",
                ),  # Alineación del texto a la izquierda
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),  # Fuente en negrita para el encabezado
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica",
                ),  # Fuente normal para el contenido
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    "#f9f9f9",
                ),  # Fondo blanco para el resto de las filas
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    1,
                    "#000000",
                ),  # Rejilla negra alrededor de las celdas
                ("BOX", (0, 0), (-1, -1), 1, "#000000"),  # Borde exterior negro
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),  # Alineación vertical en el medio
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "LEFT",
                ),  # Alineación del texto en el contenido
            ]
        )
    )

    elements.append(table)

    # Añadir espacio antes de la firma
    elements.append(Paragraph("<br/><br/>", normal_style))

    # Incluir la imagen de la firma
    firma_path = os.path.join(settings.MEDIA_ROOT, "imagenes/Firma.jpeg")
    firma = Image(
        firma_path, width=150, height=75
    )  # Ajustar tamaño para ser más proporcional
    elements.append(firma)

    # Espacio y nombre del responsable de la firma
    elements.append(Paragraph("", header_style))

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

    # Llenar la tabla con los datos y aplicar saltos de línea en las columnas largas
    for anticipo in anticipos_aprobados:
        data.append(
            [
                Paragraph(anticipo.centro_costo, styles["Normal"]),  # Salto de línea para centro de costo
                anticipo.nit,
                Paragraph(anticipo.nombre, styles["Normal"]),  # Salto de línea para nombre
                Paragraph(anticipo.producto_servicio, styles["Normal"]),  # Salto de línea para producto/servicio
                str(anticipo.cantidad),
                f"${anticipo.subtotal:,.2f}",
                f"${anticipo.valor_iva:,.2f}",
                f"${anticipo.valor_retencion:,.2f}",
                f"${anticipo.total_pagar:,.2f}",
                Paragraph(anticipo.observaciones or "N/A", styles["Normal"]),  # Salto de línea para observaciones
            ]
        )

    # Ajustar el ancho de las columnas
    col_widths = [80, 80, 100, 100, 60, 80, 80, 80, 80, 100]
    table = Table(data, colWidths=col_widths)

    # Estilos de la tabla
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

    # Devolver la respuesta
    return response  # Este es el return que faltaba


@login_required
@staff_required
def generar_pdf_diarios(request):
    # Obtener las fechas de inicio y fin del filtro
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    # Verificar que se proporcionen las fechas
    if not fecha_inicio or not fecha_fin:
        messages.error(request, "Debes seleccionar un rango de fechas para descargar el PDF.")
        return redirect("ver_diario")

    try:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha inválido.")
        return redirect("ver_diario")

    # Filtrar diarios por las fechas
    diarios_filtrados = Diario.objects.filter(tiempo_entrega__range=(fecha_inicio, fecha_fin))

    if not diarios_filtrados.exists():
        messages.error(request, "No hay órdenes diarias en el rango de fechas seleccionado.")
        return redirect("ver_diario")

    # Crear la respuesta HTTP para descargar el PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ordenes_diarias_{fecha_inicio}_{fecha_fin}.pdf"'

    # Crear el documento PDF en formato apaisado
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), leftMargin=0.5 * inch, rightMargin=0.5 * inch)
    elements = []

    # Encabezado del PDF
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Órdenes Diarias desde {fecha_inicio} hasta {fecha_fin}", styles["Title"]))

    # Crear una tabla con los datos de las órdenes diarias
    data = [
        [
            Paragraph("ID", styles["Heading4"]), 
            Paragraph("Tiempo de Entrega", styles["Heading4"]), 
            Paragraph("Nombre", styles["Heading4"]), 
            Paragraph("Empresa", styles["Heading4"]), 
            Paragraph("Centro de Costo", styles["Heading4"]), 
            Paragraph("Destino", styles["Heading4"]), 
            Paragraph("Medio de Pago", styles["Heading4"]), 
            Paragraph("Documento PDF", styles["Heading4"])
        ]
    ]

    # Llenar la tabla con los datos y aplicar saltos de línea en las columnas largas
    for diario in diarios_filtrados:
        data.append([
            diario.id,
            diario.tiempo_entrega.strftime("%Y-%m-%d"),  # Formatear la fecha
            Paragraph(diario.nombre, styles["Normal"]),  # Salto de línea para nombre
            Paragraph(diario.empresa, styles["Normal"]),  # Salto de línea para empresa
            Paragraph(diario.centro_costo, styles["Normal"]),  # Salto de línea para centro de costo
            Paragraph(diario.destino, styles["Normal"]),  # Salto de línea para destino
            diario.medio_pago,
            "Disponible" if diario.documento_pdf else "No disponible"
        ])

    # Ajustar el ancho de las columnas para adaptarse mejor al contenido
    col_widths = [40, 80, 150, 150, 100, 100, 100, 100]  # Ajusta los tamaños según necesites
    table = Table(data, colWidths=col_widths)

    # Estilos de la tabla
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Alineación vertical en el medio
        ("ROWSPACING", (0, 0), (-1, -1), 5),  # Espacio adicional entre filas
    ]))

    # Añadir la tabla a los elementos
    elements.append(table)

    # Construir el PDF
    doc.build(elements)

    # Devolver la respuesta
    return response
