from django.contrib import admin
from django.urls import path
from perfiles.views import (
    SignUpView,
    BienvenidaView,
    SignInView,
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
    custom_logout,
)
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", BienvenidaView.as_view(), name="bienvenida"),
    path("registrate/", SignUpView.as_view(), name="sign_up"),
    path("login/", SignInView.as_view(), name="login"),
    path("solicitud/", SolicitudView.as_view(), name="solicitud"),
    path("ver_solicitudes/", ver_solicitudes, name="ver_solicitudes"),
    path("solicitud/<int:pk>/", SolicitudDetailView.as_view(), name="solicitud_detail"),
    path("ver_ordenes/", ver_ordenes, name="ver_ordenes"),
    path('aprobar_orden/<int:orden_id>/', AprobarOrdenView.as_view(), name='aprobar_orden'),
    path("ver_diario/", ver_diario, name="ver_diario"),
    path("ver_anticipos/", ver_anticipos, name="ver_anticipos"),
    path("orden/", OrdenView.as_view(), name="orden"),
    path("anticipo/", anticipo_view, name="anticipo"),
    path('aprobar_anticipo/<int:anticipo_id>/', aprobar_anticipo, name='aprobar_anticipo'),
    path("diario/", diario_view, name="diario"),
    path("logout/", custom_logout, name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
