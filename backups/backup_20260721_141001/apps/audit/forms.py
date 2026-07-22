from django import forms
from django.contrib.auth import get_user_model
from .models import AuditLog
from apps.documents.models import Dependencia

User = get_user_model()


class AuditSearchForm(forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all().order_by("username"),
        required=False,
        empty_label="Todos los usuarios",
    )
    dependencia = forms.ModelChoiceField(
        queryset=Dependencia.objects.filter(is_active=True).order_by("code"),
        required=False,
        empty_label="Todas las dependencias",
    )
    accion = forms.ChoiceField(
        choices=[("", "Todas las acciones")] + AuditLog.ACTION_CHOICES,
        required=False,
    )
    modulo = forms.ChoiceField(
        choices=[("", "Todos los módulos")] + AuditLog.MODULE_CHOICES,
        required=False,
    )
    fecha_desde = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
