from django.urls import path

from .views import (
    document_create,
    document_detail,
    document_export,
    document_list,
    document_preview,
    document_update,
    expediente_add_document,
    expediente_create,
    expediente_detail,
    expediente_list,
    expediente_update,
    subseries_by_serie,
    trd_list,
    tvd_list,
)

urlpatterns = [
    path("", document_list, name="document_list"),
    path("export/", document_export, name="document_export"),
    path("nuevo/", document_create, name="document_create"),
    path("trd/", trd_list, name="trd_list"),
    path("tvd/", tvd_list, name="tvd_list"),
    path("expedientes/", expediente_list, name="expediente_list"),
    path("expedientes/nuevo/", expediente_create, name="expediente_create"),
    path("expedientes/<int:pk>/", expediente_detail, name="expediente_detail"),
    path("expedientes/<int:pk>/editar/", expediente_update, name="expediente_update"),
    path("expedientes/<int:pk>/agregar-documento/", expediente_add_document, name="expediente_add_document"),
    path("<int:pk>/", document_detail, name="document_detail"),
    path("<int:pk>/editar/", document_update, name="document_update"),
    path("<int:pk>/preview/", document_preview, name="document_preview"),
    path("api/subseries/", subseries_by_serie, name="subseries_by_serie"),
]

