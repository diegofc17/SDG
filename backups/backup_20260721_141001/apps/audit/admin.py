from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "user",
        "dependencia",
        "action",
        "module",
        "description",
        "ip",
    )
    list_filter = ("action", "module", "fecha", "dependencia")
    search_fields = ("user__username", "description", "object_repr", "ip")
    date_hierarchy = "fecha"

    # Hacemos que sea de solo lectura en el admin para preservar la integridad de los logs
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
