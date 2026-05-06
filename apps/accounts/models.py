from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    dependencia = models.ForeignKey(
        "documents.Dependencia",
        on_delete=models.PROTECT,
        related_name="profiles",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"
