from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .models import Diario, Solicitud, Orden, Anticipo
from django.core.paginator import Paginator
from .forms import (
    AprobacionRechazoForm,
    SolicitudForm,
    DiarioForm,
    AnticipoForm,
    OrdenForm,
)
from django.contrib import messages
from django.utils import timezone


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
        return render(
            request,
            "pages/solicitud_detail.html",
            {"form": form, "solicitud": solicitud},
        )

    def post(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(request.POST, instance=solicitud)
        if form.is_valid():
            form.save()
            messages.success(request, "Solicitud actualizada con éxito.")
            return redirect("ver_solicitudes")
        return render(
            request,
            "pages/solicitud_detail.html",
            {"form": form, "solicitud": solicitud},
        )


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
    solicitudes = Solicitud.objects.all()
    solicitudes_page = paginate_and_filter(solicitudes, request)
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


def paginate_and_filter(queryset, request, per_page=10):
    # Filtrando el queryset
    filters = {}
    for key in request.GET:
        if key in [field.name for field in queryset.model._meta.fields]:
            filters[key + "__icontains"] = request.GET[key]

    queryset = queryset.filter(**filters)

    # Paginando el queryset
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)
