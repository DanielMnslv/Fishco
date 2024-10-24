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
import json


from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import TruncMonth



@login_required
def index(request):
    # Obtener estadísticas de Solicitudes
    total_solicitudes = Solicitud.objects.count()

    # Solicitudes aprobadas (tienen al menos una cotización aprobada)
    solicitudes_aprobadas = Solicitud.objects.filter(cotizaciones__estado="aprobada").distinct().count()

    solicitudes_pendientes = total_solicitudes - solicitudes_aprobadas
    solicitudes_rechazadas = 0  # Si tienes algún campo o estado para solicitudes rechazadas, puedes ajustarlo

    # Obtener estadísticas de Cotizaciones
    total_cotizaciones = Cotizacion.objects.count()
    cotizaciones_aprobadas = Cotizacion.objects.filter(estado="aprobada").count()

    # Obtener estadísticas de Anticipos
    total_anticipos = Anticipo.objects.count()
    anticipos_aprobados = Anticipo.objects.filter(aprobado=True).count()

    # Obtener estadísticas de Órdenes (solo el total, ya que no tienen estado)
    total_ordenes = Orden.objects.count()

    # Obtener solicitudes por categoría
    solicitudes_productos = Solicitud.objects.filter(tipo="producto").count()
    solicitudes_servicios = Solicitud.objects.filter(tipo="servicio").count()

    # Obtener solicitudes por destino
    solicitudes_por_destino = Solicitud.objects.values('destino').annotate(total=Count('id')).order_by('-total')

    # Tendencia de solicitudes en la última semana
    now = timezone.now()
    last_week = now - timedelta(days=7)
    solicitudes_ultima_semana = Solicitud.objects.filter(fecha__gte=last_week).count()

    # Tiempo promedio de aprobación de solicitudes (promedio del tiempo de aprobación de cotizaciones)
    solicitudes_aprobadas_duracion = Cotizacion.objects.filter(estado="aprobada").annotate(
        tiempo_aprobacion=ExpressionWrapper(
            F('fecha') - F('solicitud__fecha'),
            output_field=DurationField()
        )
    ).aggregate(promedio=Avg('tiempo_aprobacion'))

    # Obtener solicitudes por usuario
    solicitudes_por_usuario = Solicitud.objects.values('usuario__username').annotate(total=Count('id')).order_by('-total')

    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_rechazadas': solicitudes_rechazadas,

        'total_cotizaciones': total_cotizaciones,
        'cotizaciones_aprobadas': cotizaciones_aprobadas,

        'total_anticipos': total_anticipos,
        'anticipos_aprobados': anticipos_aprobados,

        'total_ordenes': total_ordenes,

        'solicitudes_productos': solicitudes_productos,
        'solicitudes_servicios': solicitudes_servicios,

        'solicitudes_por_destino': solicitudes_por_destino,
        'solicitudes_ultima_semana': solicitudes_ultima_semana,

        'solicitudes_aprobadas_duracion': solicitudes_aprobadas_duracion['promedio'],
        'solicitudes_por_usuario': solicitudes_por_usuario,
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
            solicitud.save()  # Guardar la solicitud con el usuario asignado

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

            # Mensaje de éxito
            messages.success(request, "Solicitud creada con éxito y notificación enviada.")
            
            # Reiniciar el formulario después de envío exitoso
            form = SolicitudForm()
        else:
            # Mensaje de error con los detalles del formulario inválido
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")

        # Si el formulario es válido o no, se renderiza la misma página con los mensajes correspondientes
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

@login_required
@staff_required
def diario_view(request):
    if request.method == "POST":
        form = DiarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Diario creado con éxito.")
            return redirect("diario")  # Redirecciona tras el éxito
        else:
            # Imprimir errores del formulario
            print(form.errors)
            messages.error(request, "Hubo un error al registrar el diario. Verifica los datos.")
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


from pathlib import Path
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date

@login_required
@staff_required
def ver_diario(request):
    # Filtrar solo los diarios que no estén ocultos
    diarios = Diario.objects.filter(oculto=False).order_by('tiempo_entrega')

    # Obtener los filtros del GET
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    tiempo_entrega = request.GET.get("tiempo_entrega")
    nombre = request.GET.get("nombre")
    empresa = request.GET.get("empresa")
    centro_costo = request.GET.get("centro_costo")
    destino = request.GET.get("destino")
    medio_pago = request.GET.get("medio_pago")
    observaciones = request.GET.get("observaciones")

    # Filtrar por fechas si están presentes
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = parse_date(fecha_inicio)
            fecha_fin = parse_date(fecha_fin)
            if fecha_inicio and fecha_fin:
                diarios = diarios.filter(tiempo_entrega__range=[fecha_inicio, fecha_fin])
        except ValueError:
            pass  # Si ocurre un error con las fechas, no filtrar

    # Filtrar por Tiempo de Entrega
    if tiempo_entrega:
        diarios = diarios.filter(tiempo_entrega__icontains(tiempo_entrega))

    # Filtrar por Nombre
    if nombre:
        diarios = diarios.filter(nombre__icontains(nombre))

    # Filtrar por Empresa
    if empresa:
        diarios = diarios.filter(empresa__icontains(empresa))

    # Filtrar por Centro de Costo
    if centro_costo:
        diarios = diarios.filter(centro_costo__icontains(centro_costo))

    # Filtrar por Destino
    if destino:
        diarios = diarios.filter(destino__icontains(destino))

    # Filtrar por Medio de Pago
    if medio_pago:
        diarios = diarios.filter(medio_pago__icontains(medio_pago))

    # Filtrar por Observaciones
    if observaciones:
        diarios = diarios.filter(observaciones__icontains(observaciones))

    # Modificar cada diario para incluir información del tipo de documento
    for diario in diarios:
        if diario.documento:
            extension = Path(diario.documento).suffix.lower()  # Obtiene la extensión del archivo en minúsculas
            if extension == '.pdf':
                diario.tipo_documento = 'pdf'
            elif extension in ['.jpg', '.jpeg', '.png']:
                diario.tipo_documento = 'imagen'
            else:
                diario.tipo_documento = 'otro'
        else:
            diario.tipo_documento = 'no_disponible'

    # Paginación si es necesario
    paginator = Paginator(diarios, 50)
    page_number = request.GET.get("page")
    diario_page = paginator.get_page(page_number)

    return render(request, "pages/ver_diario.html", {"diarios": diario_page})
_




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
    
    # Obtener valores de los filtros desde el request
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    nombre = request.GET.get("nombre")
    id = request.GET.get("id")
    centro_costo = request.GET.get("centro_costo")
    nit = request.GET.get("nit")
    producto_servicio = request.GET.get("producto_servicio")
    cantidad = request.GET.get("cantidad")
    subtotal = request.GET.get("subtotal")
    iva = request.GET.get("iva")
    retencion = request.GET.get("retencion")
    total_pagar = request.GET.get("total_pagar")
    observaciones = request.GET.get("observaciones")

    # Aplicar filtros según se necesiten
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

    # Filtro por otros campos
    if nombre:
        anticipos = anticipos.filter(nombre__icontains=nombre)
    if id:
        anticipos = anticipos.filter(id=id)
    if centro_costo:
        anticipos = anticipos.filter(centro_costo__icontains=centro_costo)
    if nit:
        anticipos = anticipos.filter(nit__icontains=nit)
    if producto_servicio:
        anticipos = anticipos.filter(producto_servicio__icontains=producto_servicio)
    if cantidad:
        anticipos = anticipos.filter(cantidad=cantidad)
    if subtotal:
        anticipos = anticipos.filter(subtotal=subtotal)
    if iva:
        anticipos = anticipos.filter(valor_iva=iva)
    if retencion:
        anticipos = anticipos.filter(valor_retencion=retencion)
    if total_pagar:
        anticipos = anticipos.filter(total_pagar=total_pagar)
    if observaciones:
        anticipos = anticipos.filter(observaciones__icontains=observaciones)

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


from django.core.mail import send_mail
from django.conf import settings

@user_passes_test(lambda u: u.id in [31, 33])  # IDs permitidos
@login_required
def aprobar_anticipos_masivamente(request):
    if request.method == "POST":
        anticipo_ids = request.POST.get("anticipo_ids")  # Recibe la cadena de IDs

        if anticipo_ids:
            # Convertir la cadena de IDs en una lista de enteros
            anticipo_ids = [int(id) for id in anticipo_ids.split(",")]

            # Filtrar los anticipos seleccionados
            anticipos_aprobados = Anticipo.objects.filter(id__in=anticipo_ids)

            if anticipos_aprobados.exists():
                # Aprobar masivamente los anticipos seleccionados
                anticipos_aprobados.update(aprobado=True)

                # Crear el mensaje de correo con los detalles de los anticipos aprobados
                anticipo_list = ""
                for anticipo in anticipos_aprobados:
                    anticipo_list += f"ID: {anticipo.id}, Nombre: {anticipo.nombre}, Total: {anticipo.total_pagar}\n"

                # Crear el contenido del correo
                subject = "Anticipos Aprobados Masivamente"
                message = f"Se han aprobado los siguientes anticipos:\n\n{anticipo_list}"

                # Enviar el correo a los destinatarios
                recipient_list = ["auxcompras@cifishco.com.co", "gestiondocumental.pfishco@gmail.com", "tesoreria@cifishco.com.co"]  # Destinatarios
                from_email = settings.DEFAULT_FROM_EMAIL

                try:
                    send_mail(subject, message, from_email, recipient_list)
                    messages.success(request, "Anticipos aprobados con éxito. Notificación enviada por correo.")
                except Exception as e:
                    messages.error(request, f"Anticipos aprobados, pero hubo un error al enviar el correo: {e}")
            else:
                messages.error(request, "No se encontraron anticipos válidos para aprobar.")
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
        data = json.loads(request.body)  # Leer el cuerpo como JSON
        anticipos_ids = data.get("anticipos_ids", [])
        anticipos_ids = [id for id in anticipos_ids if id.isdigit()]  # Filtrar los IDs vacíos

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
