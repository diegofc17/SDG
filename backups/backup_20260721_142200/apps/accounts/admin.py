from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "get_dependencias")
    search_fields = ("user__username",)
    filter_horizontal = ("dependencias",)

    @admin.display(description="Dependencias")
    def get_dependencias(self, obj):
        return ", ".join(d.display_label for d in obj.dependencias.all()) or "—"
