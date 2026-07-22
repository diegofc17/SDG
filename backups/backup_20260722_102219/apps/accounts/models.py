from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    dependencias = models.ManyToManyField(
        "documents.Dependencia",
        related_name="profiles_m2m",
        blank=True,
        verbose_name="dependencias",
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"

    # ---------------------------------------------------------------
    # Convenience helpers used across the codebase
    # ---------------------------------------------------------------
    @property
    def dependencia(self):
        """Return the first assigned dependency (backwards-compat helper)."""
        return self.dependencias.first()

    @property
    def dependencia_id(self):
        """Return the PK of the first dependency, or None."""
        dep = self.dependencia
        return dep.pk if dep else None

    def get_dependencias_ids(self):
        """Return a QuerySet of dependency PKs assigned to this profile."""
        return self.dependencias.values_list("id", flat=True)
