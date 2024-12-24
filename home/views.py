from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from .models import Diario, Solicitud, Orden, Anticipo, Cotizacion, Mensaje,ReporteCombustible
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
    ReporteCombustibleForm,
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
from django.db.models.functions import TruncMonth
from pathlib import Path
from django.db.models import Q
from datetime import date
import matplotlib
matplotlib.use('Agg')  # Establecer el backend sin interfaz gráfica (ideal para servidores)

import matplotlib.pyplot as plt
from io import BytesIO
from django.db.models import Sum


@login_required
def index(request):
    # Obtener estadísticas generales
    total_solicitudes = Solicitud.objects.count()
    solicitudes_aprobadas = Solicitud.objects.filter(cotizaciones__estado="aprobada").distinct().count()

    # Solicitudes por usuario
    solicitudes_por_usuario = Solicitud.objects.values('usuario__username').annotate(total=Count('id')).order_by('-total')
    usuarios = [item['usuario__username'] for item in solicitudes_por_usuario]
    solicitudes_totales = [item['total'] for item in solicitudes_por_usuario]

    # Tendencia de solicitudes por mes
    solicitudes_por_mes = (
        Solicitud.objects.annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    labels_solicitudes_meses = [item['mes'].strftime('%Y-%m') for item in solicitudes_por_mes]
    data_solicitudes_meses = [item['total'] for item in solicitudes_por_mes]

    # Contexto para los gráficos
    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'usuarios': usuarios,
        'solicitudes_totales': solicitudes_totales,
        'labels_solicitudes_meses': labels_solicitudes_meses,
        'data_solicitudes_meses': data_solicitudes_meses,
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
            try:
                cotizacion = form.save(commit=False)
                cotizacion.solicitud = solicitud
                cotizacion.archivo = request.FILES.get("archivo")  # Guardar el archivo subido
                cotizacion.save()
                messages.success(request, "Cotización subida con éxito.")
                return redirect("ver_solicitudes")
            except Exception as e:
                # Registrar cualquier error de excepción en los mensajes
                messages.error(request, f"Ocurrió un error al subir la cotización: {e}")
        else:
            # Si el formulario es inválido, mostrar los errores de cada campo
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")

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


@login_required
@superuser_required
def anticipo_view(request):
    if request.method == "POST":
        form = AnticipoForm(request.POST)
        if form.is_valid():
            anticipo = form.save()
            messages.success(request, "Anticipo creado con éxito.")
            return redirect("index")
        else:
            for field, errors in form.errors.items():
                messages.error(request, f"Error en {field}: {', '.join(errors)}")
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
    ordenes = Orden.objects.all().order_by('id')  # Añadir ordenamiento por 'id'
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

    paginator = Paginator(ordenes, 100)
    page_number = request.GET.get("page")
    ordenes_page = paginator.get_page(page_number)
    return render(request, "pages/ver_ordenes.html", {"ordenes": ordenes_page})

@login_required
@superuser_required
def reporte_combustible(request):
    return render(request, 'pages/reporte_combustible.html')



@login_required
@user_passes_test(lambda u: u.is_superuser)
def guardar_reporte_combustible(request):
    if request.method == 'POST':
        form = ReporteCombustibleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Reporte de combustible guardado exitosamente.")
            return redirect('reporte_combustible')
        else:
            messages.error(request, "Por favor revisa los datos ingresados.")
    else:
        form = ReporteCombustibleForm()
    return render(request, 'pages/reporte_combustible.html', {'form': form})


from django.db.models import Sum
def ver_reporte_combustible(request):
    # Inicia una consulta base
    reportes = ReporteCombustible.objects.all()
    filters = Q()

    # Filtrar por rango de fechas
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    if fecha_inicio and fecha_fin:
        filters &= Q(fecha__range=[fecha_inicio, fecha_fin])
    elif fecha_inicio:
        filters &= Q(fecha__gte=fecha_inicio)
    elif fecha_fin:
        filters &= Q(fecha__lte=fecha_fin)

    # Filtrar por tipo de combustible
    combustible = request.GET.get("combustible")
    if combustible:
        filters &= Q(combustible__icontains=combustible)

    # Filtrar por cantidad
    cantidad = request.GET.get("cantidad")
    if cantidad:
        try:
            cantidad = float(cantidad)
            filters &= Q(cantidad=cantidad)
        except ValueError:
            pass  # Ignorar si el valor no es válido

    # Filtrar por código de estación
    codigo_estacion = request.GET.get("codigo_estacion")
    if codigo_estacion:
        filters &= Q(codigo_estacion__icontains=codigo_estacion)

    # Filtrar por empresa
    empresa = request.GET.get("empresa")
    if empresa:
        filters &= Q(empresa__icontains=empresa)

    # Filtrar por centro de costo
    centro_costo = request.GET.get("centro_costo")
    if centro_costo:
        filters &= Q(centro_costo__icontains=centro_costo)

    # Filtrar por destino
    destino = request.GET.get("destino")
    if destino:
        filters &= Q(destino__icontains=destino)

    # Filtrar por conductor
    conductor = request.GET.get("conductor")
    if conductor:
        filters &= Q(conductor__icontains=conductor)

    # Filtrar por placa
    placa = request.GET.get("placa")
    if placa:
        filters &= Q(placa__icontains=placa)

    # Aplicar filtros dinámicos
    reportes = reportes.filter(filters)

    # Paginación
    paginator = Paginator(reportes, 1000)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pages/ver_reporte_combustible.html', {
        'reportes': page_obj,
        'filtros': request.GET,  # Para mostrar los valores en el frontend
    })


@login_required
@staff_required
def ver_diario(request):
    diarios = Diario.objects.filter(oculto=False).order_by('tiempo_entrega')

    # Construir el filtro dinámico usando Q
    filtros = Q()
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    # Filtrado por rango de fechas
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            filtros &= Q(tiempo_entrega__range=(fecha_inicio, fecha_fin))
        except ValueError:
            pass  # Ignora el filtrado si hay error en el formato de fecha

    # Aplicar filtros adicionales de campos texto
    filtros_texto = {
        'tiempo_entrega': request.GET.get('tiempo_entrega'),
        'nombre': request.GET.get('nombre'),
        'empresa': request.GET.get('empresa'),
        'centro_costo': request.GET.get('centro_costo'),
        'destino': request.GET.get('destino'),
        'observaciones': request.GET.get('observaciones')
    }

    for campo, valor in filtros_texto.items():
        if valor:
            filtros &= Q(**{f"{campo}__icontains": valor})

    # Filtrar por medio de pago con ajuste de valores
    medio_pago = request.GET.get('medio_pago')
    if medio_pago:
        opciones_medio_pago = {
            "Cuentas por Pagar": "cuentas_por_pagar",
            "Caja de Compra": "caja_compra",
            "Tarjeta Débito": "tarjeta_debito",
            "Caja de Paula": "caja_paula"
        }
        valor_medio_pago = opciones_medio_pago.get(medio_pago, medio_pago)
        filtros &= Q(medio_pago__iexact=valor_medio_pago)

    # Aplicar todos los filtros al queryset
    diarios = diarios.filter(filtros)

    # Paginación
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

@login_required
@staff_required
def generar_pdf_anticipos_aprobados(request):
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    if not fecha_inicio or not fecha_fin:
        messages.error(request, "Debes seleccionar un rango de fechas para descargar el PDF.")
        return redirect("ver_anticipos")

    try:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha inválido.")
        return redirect("ver_anticipos")

    anticipos_aprobados = Anticipo.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin), aprobado=True
    )

    if not anticipos_aprobados.exists():
        messages.error(request, "No hay anticipos aprobados en el rango de fechas seleccionado.")
        return redirect("ver_anticipos")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="anticipos_aprobados_{fecha_inicio}_{fecha_fin}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    elements = []

    # Estilos para el texto
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", fontSize=7, leading=8))  # Tamaño reducido

    # Encabezado
    elements.append(Paragraph(f"Anticipos Aprobados desde {fecha_inicio} hasta {fecha_fin}", styles["Title"]))

    # Cabecera de la tabla
    data = [
        [
            "Cent_C", "NIT", "Nombre", "Prod/Serv", "Cant", "Subt", 
            "IVA", "Retención", "ReteICA", "Saldo_F", "Total_P", "Observ"
        ]
    ]

    # Acumular el total a pagar
    total_pagar_sum = 0

    # Llenar la tabla
    for anticipo in anticipos_aprobados:
        subtotal = anticipo.subtotal or 0
        valor_iva = anticipo.valor_iva or 0
        valor_retencion = anticipo.valor_retencion or 0
        valor_reteica = anticipo.valor_reteica or 0
        saldo_a_favor = anticipo.saldo_a_favor or 0
        total_pagar = anticipo.total_pagar or 0

        total_pagar_sum += total_pagar

        data.append([
            Paragraph(anticipo.centro_costo, styles["Small"]),
            anticipo.nit,
            Paragraph(anticipo.nombre, styles["Small"]),
            Paragraph(anticipo.producto_servicio, styles["Small"]),
            str(anticipo.cantidad),
            f"${subtotal:,.2f}",
            f"${valor_iva:,.2f}",
            f"${valor_retencion:,.2f}",
            f"${valor_reteica:,.2f}",
            f"${saldo_a_favor:,.2f}",
            f"${total_pagar:,.2f}",
            Paragraph(anticipo.observaciones or "N/A", styles["Small"]),
        ])

    # Fila de total
    data.append([
        "Total", "", "", "", "", "", "", "", "", "", f"${total_pagar_sum:,.2f}", ""
    ])

    # Ajustar el ancho de las columnas
    col_widths = [
        70,  # Centro de Costo
        60,  # NIT
        100,  # Nombre
        130,  # Producto/Servicio
        40,  # Cantidad
        60,  # Subtotal
        50,  # IVA
        50,  # Retención
        50,  # ReteICA
        50,  # Saldo a Favor
        70,  # Total a Pagar
        120  # Observaciones
    ]

    # Crear la tabla
    table = Table(data, colWidths=col_widths)

    # Estilos de la tabla
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),  # Encabezados ligeramente más grandes
        ("FONTSIZE", (0, 1), (-1, -1), 7),  # Reducir tamaño para el contenido
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    return response


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
            "Disponible" if diario.documento else "No disponible"
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



def generar_pdf_combustible(request):
    # Obtener los filtros desde la solicitud
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    combustible = request.GET.get("combustible")
    cantidad = request.GET.get("cantidad")
    codigo_estacion = request.GET.get("codigo_estacion")
    empresa = request.GET.get("empresa")
    centro_costo = request.GET.get("centro_costo")
    destino = request.GET.get("destino")
    conductor = request.GET.get("conductor")
    placa = request.GET.get("placa")

    # Construir el filtro dinámico
    filters = Q()
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            filters &= Q(fecha__range=(fecha_inicio, fecha_fin))
        except ValueError:
            return HttpResponse("Formato de fecha inválido.", status=400)

    if combustible:
        filters &= Q(combustible__iexact=combustible)
    if cantidad:
        try:
            filters &= Q(cantidad=float(cantidad))
        except ValueError:
            return HttpResponse("Cantidad inválida.", status=400)
    if codigo_estacion:
        filters &= Q(codigo_estacion__icontains=codigo_estacion)
    if empresa:
        filters &= Q(empresa__icontains=empresa)
    if centro_costo:
        filters &= Q(centro_costo__iexact=centro_costo)
    if destino:
        filters &= Q(destino__iexact=destino)
    if conductor:
        filters &= Q(conductor__icontains=conductor)
    if placa:
        filters &= Q(placa__icontains=placa)

    # Obtener los reportes filtrados
    reportes = ReporteCombustible.objects.filter(filters)

    if not reportes.exists():
        return HttpResponse("No se encontraron datos con los filtros seleccionados.", status=404)

    # Calcular el total de combustible
    total_combustible = sum(reporte.cantidad for reporte in reportes)

    # Crear la respuesta para el archivo PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_combustible_filtros.pdf"'

    # Configurar el documento PDF
    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    elements = []

    # Añadir el logo al encabezado
    logo_path = os.path.join(settings.MEDIA_ROOT, "imagenes/Logo.png")
    try:
        logo = Image(logo_path, width=100, height=50)
        elements.append(logo)
    except FileNotFoundError:
        elements.append(Paragraph("LOGO NO DISPONIBLE", getSampleStyleSheet()['Normal']))

    # Estilo y título
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Reporte de Combustible", styles['Title']))

    # Encabezados de la tabla
    data = [["Fecha", "Combustible", "Cantidad", "Código Estación", "Empresa", "Centro de Costo", "Destino", "Conductor", "Placa"]]

    # Agregar los datos de los reportes filtrados
    for reporte in reportes:
        data.append([
            reporte.fecha.strftime("%Y-%m-%d"),
            reporte.combustible,
            f"{reporte.cantidad:.2f}",
            reporte.codigo_estacion,
            reporte.empresa,
            reporte.centro_costo,
            reporte.destino,
            reporte.conductor,
            reporte.placa
        ])

    # Agregar la fila con el total de combustible
    data.append([
        "", "", f"Total: {total_combustible:.2f}", "", "", "", "", "", ""
    ])

    # Configuración de la tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (2, -1), (2, -1), "RIGHT")
    ]))
    elements.append(table)

    # Agrupar los datos por mes y centro de costo
    consumo_mensual_cc = reportes.annotate(
        mes=TruncMonth('fecha')
    ).values(
        'mes', 'centro_costo'
    ).annotate(
        total=Sum('cantidad')
    ).filter(
        centro_costo__in=['FERRY', 'ECOPEZ', 'PRODUCCION']
    ).order_by('mes', 'centro_costo')

    # Preparar los datos para el gráfico
    meses = sorted(set(item['mes'] for item in consumo_mensual_cc))
    meses_labels = [mes.strftime('%B %Y') for mes in meses]
    centros_costo = ['FERRY', 'ECOPEZ', 'PRODUCCION']

    # Traducir los meses al español
    meses_esp = {
        'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril', 'May': 'Mayo',
        'June': 'Junio', 'July': 'Julio', 'August': 'Agosto', 'September': 'Septiembre', 'October': 'Octubre',
        'November': 'Noviembre', 'December': 'Diciembre'
    }
    meses_labels = [meses_esp[mes.strftime('%B')] + ' ' + str(mes.year) for mes in meses]

    # Crear los datos por centro de costo
    data_cc = {cc: [0] * len(meses) for cc in centros_costo}
    for item in consumo_mensual_cc:
        mes_index = meses.index(item['mes'])
        data_cc[item['centro_costo']][mes_index] = item['total']

    # Crear el gráfico
    x = range(len(meses))
    width = 0.25
    fig, ax = plt.subplots(figsize=(14, 8))

    for i, cc in enumerate(centros_costo):
        ax.bar([p + i * width for p in x], data_cc[cc], width, label=cc)

    ax.set_title('Consumo Mensual de Combustible por Centro de Costo', fontsize=16)
    ax.set_xlabel('Mes', fontsize=12)
    ax.set_ylabel('Cantidad (galones)', fontsize=12)
    ax.set_xticks([p + width for p in x])
    ax.set_xticklabels(meses_labels, rotation=45, ha='right')
    ax.legend(title='Centro de Costo')

    # Guardar el gráfico en un buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    # Añadir el gráfico al PDF
    elements.append(Image(buffer, width=600, height=350))

    # Construir el documento PDF
    doc.build(elements)

    return response



def generar_pdf_combustible2(request):
    # Obtener las fechas de inicio y fin del filtro desde la solicitud
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    # Verificar que se proporcionen las fechas
    if not fecha_inicio or not fecha_fin:
        return HttpResponse("Debes seleccionar un rango de fechas.", status=400)

    try:
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("Formato de fecha inválido.", status=400)

    # Filtrar los reportes por las fechas proporcionadas
    reportes = ReporteCombustible.objects.filter(fecha__range=(fecha_inicio, fecha_fin))

    if not reportes.exists():
        return HttpResponse("No se encontraron datos en el rango de fechas seleccionado.", status=404)

    # Crear la respuesta para el archivo PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_combustible_{fecha_inicio}_a_{fecha_fin}.pdf"'

    # Configurar el documento PDF
    doc = SimpleDocTemplate(response, pagesize=landscape(A4))
    elements = []

    # Estilo y título
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Reporte de Combustible", styles['Title']))
    elements.append(Paragraph(f"Desde: {fecha_inicio} Hasta: {fecha_fin}", styles['Normal']))
    elements.append(Paragraph("<br/>", styles['Normal']))

    # Encabezados de la tabla
    data = [["Fecha", "Combustible", "Cantidad", "Código Estación", "Empresa", "Centro de Costo", "Destino", "Conductor", "Placa"]]

    # Agregar los datos de los reportes filtrados
    for reporte in reportes:
        data.append([
            reporte.fecha.strftime("%Y-%m-%d"),
            reporte.combustible,
            f"{reporte.cantidad:.2f}",
            reporte.codigo_estacion,
            reporte.empresa,
            reporte.centro_costo,
            reporte.destino,
            reporte.conductor,
            reporte.placa
        ])

    # Configuración de la tabla
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    # Construir el documento PDF
    doc.build(elements)

    return response
