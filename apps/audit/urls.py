from django.urls import path
from .views import audit_list, audit_export

urlpatterns = [
    path("", audit_list, name="audit_list"),
    path("exportar/", audit_export, name="audit_export"),
]
