from django.urls import path

from .views import (
    document_create,
    document_detail,
    document_list,
    document_preview,
    document_update,
    subseries_by_serie,
    tipos_by_subserie,
)

urlpatterns = [
    path("", document_list, name="document_list"),
    path("nuevo/", document_create, name="document_create"),
    path("<int:pk>/", document_detail, name="document_detail"),
    path("<int:pk>/editar/", document_update, name="document_update"),
    path("<int:pk>/preview/", document_preview, name="document_preview"),
    path("api/subseries/", subseries_by_serie, name="subseries_by_serie"),
    path("api/tipos-documentales/", tipos_by_subserie, name="tipos_by_subserie"),
]
