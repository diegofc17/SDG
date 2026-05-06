from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "dependencia")
    list_filter = ("dependencia",)
    search_fields = ("user__username",)
