from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import CreateView, TemplateView

from .models import Perfil

from .forms import SignUpForm
from django.contrib.auth.views import LoginView
from django.db import IntegrityError
from django.db import transaction
from django.urls import reverse_lazy
from django.urls import reverse
from .models import Solicitud
from .models import Orden
from .forms import SolicitudForm
from .forms import OrdenForm
from django.views import View
from .forms import AnticipoForm
from .forms import DiarioForm
from .models import Anticipo
from .forms import DiarioForm
from .models import Diario
from django.core.paginator import Paginator
from .forms import AprobacionRechazoForm


class SignUpView(CreateView):
    model = Perfil
    form_class = SignUpForm
    template_name = "registration/register.html"

    def form_valid(self, form):
        try:
            # Save the user first
            user = form.save()

            # Check if the profile already exists
            if not Perfil.objects.filter(usuario=user).exists():
                # Create the profile for the user
                Perfil.objects.create(
                    usuario=user,
                    rut=form.cleaned_data.get("rut"),
                    camara_comercio=form.cleaned_data.get("camara_comercio"),
                    cedula_rl=form.cleaned_data.get("cedula_rl"),
                    certificado_bancario=form.cleaned_data.get("certificado_bancario"),
                )

            # Authenticate the user
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(self.request, user)
                return redirect("/")

        except IntegrityError:
            # Handle or log the exception
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("login")


class BienvenidaView(LoginRequiredMixin, TemplateView):
    template_name = "perfiles/bienvenida.html"


class SignInView(LoginView):
    template_name = "perfiles/iniciar_sesion.html"

    def get_success_url(self):
        return reverse_lazy("bienvenida")


class SolicitudView(LoginRequiredMixin, View):
    template_name = "perfiles/solicitud.html"


class OrdenView(LoginRequiredMixin, View):
    template_name = "perfiles/orden.html"


class AnticipoView(LoginRequiredMixin, TemplateView):
    template_name = "perfiles/anticipo.html"


class DiarioView(LoginRequiredMixin, TemplateView):
    template_name = "perfiles/diario.html"


class SolicitudView(LoginRequiredMixin, View):
    def get(self, request):
        form = SolicitudForm()
        return render(request, "perfiles/solicitud.html", {"form": form})

    def post(self, request):
        form = SolicitudForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("bienvenida")
        return render(request, "perfiles/solicitud.html", {"form": form})


class SolicitudDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(instance=solicitud)
        return render(
            request, "solicitud_detail.html", {"form": form, "solicitud": solicitud}
        )

    def post(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = AprobacionRechazoForm(request.POST, instance=solicitud)
        if form.is_valid():
            form.save()
            return redirect("ver_solicitudes")
        return render(
            request, "solicitud_detail.html", {"form": form, "solicitud": solicitud}
        )


class OrdenView(LoginRequiredMixin, View):
    def get(self, request):
        form = OrdenForm()
        return render(request, "perfiles/orden.html", {"form": form})

    def post(self, request):
        form = OrdenForm(
            request.POST, request.FILES
        )  # Asegúrate de incluir request.FILES
        if form.is_valid():
            form.save()
            return redirect("bienvenida")
        return render(request, "perfiles/orden.html", {"form": form})


class AprobarOrdenView(LoginRequiredMixin, View):
    def post(self, request, orden_id):
        orden = get_object_or_404(Orden, id=orden_id)
        orden.estado = "APROBADA"
        orden.save()
        return redirect("ver_ordenes")


@login_required
def anticipo_view(request):
    if request.method == "POST":
        form = AnticipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("bienvenida")  # Ensure this URL exists in your project
        else:
            print(form.errors)  # Debug any form errors
    else:
        form = AnticipoForm()

    return render(request, "perfiles/anticipo.html", {"form": form})


@login_required
def diario_view(request):
    if request.method == "POST":
        form = DiarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(
                "bienvenida"
            )  # Redirige a una página de éxito o lista de órdenes
    else:
        form = DiarioForm()

    return render(request, "perfiles/diario.html", {"form": form})


@login_required
def ver_solicitudes(request):
    solicitudes = Solicitud.objects.all()

    # Filtrar por los campos
    id_filtro = request.GET.get("id")
    nombre_filtro = request.GET.get("nombre")
    descripcion_filtro = request.GET.get("descripcion")
    cantidad_filtro = request.GET.get("cantidad")
    destino_filtro = request.GET.get("destino")
    tipo_filtro = request.GET.get("tipo")
    solicitado_filtro = request.GET.get("solicitado")

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

    # Paginación
    paginator = Paginator(solicitudes, 10)  # Muestra 10 solicitudes por página
    page_number = request.GET.get("page")
    solicitudes_page = paginator.get_page(page_number)

    return render(request, "ver_solicitudes.html", {"solicitudes": solicitudes_page})


@login_required
def ver_ordenes(request):
    ordenes = Orden.objects.all()

    # Filtrar por los campos
    id_filtro = request.GET.get("id")
    descripcion_filtro = request.GET.get("descripcion")
    codigo_cotizacion_filtro = request.GET.get("codigo_cotizacion")
    precio_filtro = request.GET.get("precio")
    cantidad_filtro = request.GET.get("cantidad")
    empresa_filtro = request.GET.get("empresa")
    destino_filtro = request.GET.get("destino")
    tiempo_entrega_filtro = request.GET.get("tiempo_entrega")
    observaciones_filtro = request.GET.get("observaciones")

    if id_filtro:
        ordenes = ordenes.filter(id=id_filtro)
    if descripcion_filtro:
        ordenes = ordenes.filter(descripcion__icontains=descripcion_filtro)
    if codigo_cotizacion_filtro:
        ordenes = ordenes.filter(codigo_cotizacion__icontains=codigo_cotizacion_filtro)
    if precio_filtro:
        ordenes = ordenes.filter(precio=precio_filtro)
    if cantidad_filtro:
        ordenes = ordenes.filter(cantidad=cantidad_filtro)
    if empresa_filtro:
        ordenes = ordenes.filter(empresa__icontains=empresa_filtro)
    if destino_filtro:
        ordenes = ordenes.filter(destino__icontains=destino_filtro)
    if tiempo_entrega_filtro:
        ordenes = ordenes.filter(tiempo_entrega__icontains=tiempo_entrega_filtro)
    if observaciones_filtro:
        ordenes = ordenes.filter(observaciones__icontains=observaciones_filtro)

    # Paginación
    paginator = Paginator(ordenes, 10)  # Muestra 10 órdenes por página
    page_number = request.GET.get("page")
    ordenes_page = paginator.get_page(page_number)

    return render(request, "ver_ordenes.html", {"ordenes": ordenes_page})


@login_required
def ver_diario(request):
    diario = Diario.objects.all()

    # Filtrar por los campos
    id_filtro = request.GET.get("id")
    tiempo_entrega_filtro = request.GET.get("tiempo_entrega")
    nombre_filtro = request.GET.get("nombre")
    empresa_filtro = request.GET.get("empresa")
    centro_costo_filtro = request.GET.get("centro_costo")
    destino_filtro = request.GET.get("destino")
    medio_pago_filtro = request.GET.get("medio_pago")
    documento_pdf_filtro = request.GET.get("documento_pdf")

    if id_filtro:
        diario = diario.filter(id=id_filtro)
    if tiempo_entrega_filtro:
        diario = diario.filter(tiempo_entrega__icontains=tiempo_entrega_filtro)
    if nombre_filtro:
        diario = diario.filter(nombre__icontains=nombre_filtro)
    if empresa_filtro:
        diario = diario.filter(empresa=empresa_filtro)
    if centro_costo_filtro:
        diario = diario.filter(centro_costo=centro_costo_filtro)
    if destino_filtro:
        diario = diario.filter(destino__icontains=destino_filtro)
    if medio_pago_filtro:
        diario = diario.filter(medio_pago__icontains=medio_pago_filtro)
    if tiempo_entrega_filtro:
        diario = diario.filter(tiempo_entrega__icontains=tiempo_entrega_filtro)
    if documento_pdf_filtro:
        diario = diario.filter(documento_pdf__icontains=documento_pdf_filtro)

    # Paginación
    paginator = Paginator(diario, 10)  # Muestra 10 órdenes por página
    page_number = request.GET.get("page")
    diario_page = paginator.get_page(page_number)

    return render(request, "ver_diario.html", {"diario": diario_page})


@login_required
def ver_anticipos(request):
    anticipo = Anticipo.objects.all()

    # Filtrar por los campos
    id_filtro = request.GET.get("id")
    centro_costo_filtro = request.GET.get("centro_costo")
    nit_filtro = request.GET.get("nit")
    nombre_filtro = request.GET.get("nombre")
    producto_servicio_filtro = request.GET.get("producto_servicio")
    cantidad_filtro = request.GET.get("cantidad")
    vlr_unitario_filtro = request.GET.get("vlr_unitario")
    subtotal_filtro = request.GET.get("subtotal")
    iva_filtro = request.GET.get("iva")
    retencion_filtro = request.GET.get("retencion")
    total_pagar_filtro = request.GET.get("total_pagar")
    observaciones_filtro = request.GET.get("observaciones")
    documento_pdf_filtro = request.GET.get("documento_pdf")

    if id_filtro:
        anticipo = anticipo.filter(id=id_filtro)
    if centro_costo_filtro:
        anticipo = anticipo.filter(centro_costo__icontains=centro_costo_filtro)
    if nit_filtro:
        anticipo = anticipo.filter(nit__icontains=nit_filtro)
    if nombre_filtro:
        anticipo = anticipo.filter(nombre=nombre_filtro)
    if producto_servicio_filtro:
        anticipo = anticipo.filter(producto_servicio=producto_servicio_filtro)
    if cantidad_filtro:
        anticipo = anticipo.filter(cantidad__icontains=cantidad_filtro)
    if vlr_unitario_filtro:
        anticipo = anticipo.filter(vlr_unitario__icontains=vlr_unitario_filtro)
    if subtotal_filtro:
        anticipo = anticipo.filter(subtotal__icontains=subtotal_filtro)
    if iva_filtro:
        anticipo = anticipo.filter(iva__icontains=iva_filtro)
    if retencion_filtro:
        anticipo = anticipo.filter(retencion__icontains=retencion_filtro)
    if total_pagar_filtro:
        anticipo = anticipo.filter(total_pagar__icontains=total_pagar_filtro)
    if observaciones_filtro:
        anticipo = anticipo.filter(observaciones__icontains=observaciones_filtro)
    if documento_pdf_filtro:
        anticipo = anticipo.filter(documento_pdf__icontains=documento_pdf_filtro)

    # Paginación
    paginator = Paginator(anticipo, 10)  # Muestra 10 órdenes por página
    page_number = request.GET.get("page")
    anticipo_page = paginator.get_page(page_number)

    return render(request, "ver_anticipos.html", {"anticipo": anticipo_page})


@login_required
def aprobar_anticipo(request, anticipo_id):
    anticipo = get_object_or_404(Anticipo, id=anticipo_id)
    if request.method == "POST":
        anticipo.aprobado = True
        anticipo.save()
        return redirect("ver_anticipos")  # Redirige a la lista de anticipos
    return render(request, "aprobar_anticipo.html", {"anticipo": anticipo})


def custom_logout(request):
    logout(request)
    return redirect("login")
