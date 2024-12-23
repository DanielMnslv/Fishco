from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token  # <-- NEW
from django.conf.urls.static import static
from django.conf import settings

from home.views import (
    SolicitudView,
    OrdenView,
    SolicitudDetailView,
    anticipo_view,
    diario_view,
    ver_solicitudes,
    ver_ordenes,
    ver_diario,
    ver_anticipos,
    aprobar_anticipo,
    subir_cotizacion,
    aprobar_cotizacion,
    ocultar_solicitud,
    aprobar_anticipos_masivamente,
    generar_pdf_anticipos_aprobados,
    ocultar_anticipos,
    mis_solicitudes,
    ocultar_diario,
    generar_pdf_diarios,
    generar_reporte_orden,  # <--- aquí también está 'generar_reporte_orden'
    reporte_combustible,
    ver_reporte_combustible,
    guardar_reporte_combustible,
    generar_pdf_combustible,
    generar_pdf_combustible2,
)



urlpatterns = [
    path("", include("home.urls")),
    path("admin/", admin.site.urls),
    path("", include("admin_datta.urls")),
    path("", include("django_dyn_dt.urls")),  # <-- NEW: Dynamic_DT Routing
    path("solicitud/", SolicitudView.as_view(), name="solicitud"),
    path("ver_solicitudes/", ver_solicitudes, name="ver_solicitudes"),
    path("solicitud/<int:pk>/", SolicitudDetailView.as_view(), name="solicitud_detail"),
    path('mis-solicitudes/', mis_solicitudes, name='mis_solicitudes'),
    path(
        "subir_cotizacion/<int:solicitud_id>/",
        subir_cotizacion,
        name="subir_cotizacion",
    ),
    path(
        "aprobar_cotizacion/<int:cotizacion_id>/",
        aprobar_cotizacion,
        name="aprobar_cotizacion",
    ),
    path("ver_ordenes/", ver_ordenes, name="ver_ordenes"),
    path(
        "generar_reporte_orden/<int:orden_id>/",
        generar_reporte_orden,
        name="generar_reporte_orden",
    ),
    path('reporte_combustible/', reporte_combustible, name='reporte_combustible'),
    path('guardar_reporte_combustible/', guardar_reporte_combustible, name='guardar_reporte_combustible'),
    path('ver_reporte_combustible/', ver_reporte_combustible, name='ver_reporte_combustible'),
    path('generar_pdf_combustible/', generar_pdf_combustible, name='generar_pdf_combustible'),
    path('generar_pdf_combustible2/<int:reporte_id>/', generar_pdf_combustible2, name='generar_pdf_combustible2'),
    path("ver_diario/", ver_diario, name="ver_diario"),
    path("ver_anticipos/", ver_anticipos, name="ver_anticipos"),
    path("orden/", OrdenView.as_view(), name="orden"),
    path("anticipo/", anticipo_view, name="anticipo"),
    path(
        "aprobar_anticipo/<int:anticipo_id>/", aprobar_anticipo, name="aprobar_anticipo"
    ),
    path(
        "aprobar_anticipos_masivamente/",
        aprobar_anticipos_masivamente,
        name="aprobar_anticipos_masivamente",
    ),
    path(
        "generar_pdf_anticipos_aprobados/",
        generar_pdf_anticipos_aprobados,
        name="generar_pdf_anticipos_aprobados",
    ),
    path("diario/", diario_view, name="diario"),
    path('generar_pdf_diarios/', generar_pdf_diarios, name='generar_pdf_diarios'),
    path("ocultar_solicitud/<int:id>/", ocultar_solicitud, name="ocultar_solicitud"),
    path('ocultar_anticipos/', ocultar_anticipos, name='ocultar_anticipos'),
    path('ocultar_diario/', ocultar_diario, name='ocultar_diario'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



