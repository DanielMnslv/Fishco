from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token  # <-- NEW

from home.views import (
    SolicitudView,
    OrdenView,
    AprobarOrdenView,
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
)
from django.conf.urls.static import static
from django.conf import settings
from home.views import generar_reporte_orden


urlpatterns = [
    path("", include("home.urls")),
    path("admin/", admin.site.urls),
    path("", include("admin_datta.urls")),
    path("", include("django_dyn_dt.urls")),  # <-- NEW: Dynamic_DT Routing
    path("solicitud/", SolicitudView.as_view(), name="solicitud"),
    path("ver_solicitudes/", ver_solicitudes, name="ver_solicitudes"),
    path("solicitud/<int:pk>/", SolicitudDetailView.as_view(), name="solicitud_detail"),
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
        "aprobar_orden/<int:orden_id>/",
        AprobarOrdenView.as_view(),
        name="aprobar_orden",
    ),
    path(
        "generar_reporte_orden/<int:orden_id>/",
        generar_reporte_orden,
        name="generar_reporte_orden",
    ),
    path("ver_diario/", ver_diario, name="ver_diario"),
    path("ver_anticipos/", ver_anticipos, name="ver_anticipos"),
    path("orden/", OrdenView.as_view(), name="orden"),
    path("anticipo/", anticipo_view, name="anticipo"),
    path(
        "aprobar_anticipo/<int:anticipo_id>/", aprobar_anticipo, name="aprobar_anticipo"
    ),
    path("diario/", diario_view, name="diario"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

