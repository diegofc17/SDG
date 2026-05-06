from django.contrib import admin

from .models import Dependencia, Document, SerieDocumental, SubserieDocumental, TipoDocumental


@admin.register(Dependencia)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(SerieDocumental)
class SerieDocumentalAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "dependencia", "is_active")
    list_filter = ("dependencia", "is_active")
    search_fields = ("code", "name", "dependencia__name")


@admin.register(SubserieDocumental)
class SubserieDocumentalAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "serie", "retention_management", "retention_central", "disposition_summary")
    list_filter = (
        "serie__dependencia",
        "disposition_ct",
        "disposition_e",
        "disposition_d",
        "disposition_s",
        "is_active",
    )
    search_fields = ("code", "name", "serie__name", "serie__dependencia__name")


@admin.register(TipoDocumental)
class TipoDocumentalAdmin(admin.ModelAdmin):
    list_display = ("name", "subserie", "is_required", "is_active")
    list_filter = ("subserie__serie__dependencia", "is_required", "is_active")
    search_fields = ("name", "subserie__name", "subserie__serie__name")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "numero_radicado",
        "title",
        "asunto",
        "fecha_radicacion",
        "estado",
        "soporte",
        "dependencia",
        "serie",
        "subserie",
        "tipo_documental",
        "uploaded_by",
    )
    list_filter = ("estado", "soporte", "dependencia", "serie", "fecha_radicacion", "created_at", "uploaded_by")
    search_fields = (
        "numero_radicado",
        "title",
        "asunto",
        "description",
        "serie__name",
        "subserie__name",
        "tipo_documental__name",
    )
