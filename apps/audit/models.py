from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("LOGIN", "Inicio de sesión"),
        ("LOGOUT", "Cierre de sesión"),
        ("LOGIN_FAILED", "Intento fallido de inicio"),
        ("CREATE", "Creación"),
        ("UPDATE", "Modificación"),
        ("DELETE", "Eliminación"),
        ("VIEW", "Consulta"),
        ("DOWNLOAD", "Descarga / Previsualización"),
        ("EXPORT", "Exportación de datos"),
    ]

    MODULE_CHOICES = [
        ("AUTH", "Autenticación"),
        ("DOCUMENTOS", "Documentos"),
        ("EXPEDIENTES", "Expedientes"),
        ("TRD", "Estructura TRD"),
        ("SISTEMA", "Sistema"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    dependencia = models.ForeignKey(
        "documents.Dependencia",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        db_index=True,
    )
    module = models.CharField(
        max_length=30,
        choices=MODULE_CHOICES,
        db_index=True,
    )
    description = models.TextField()
    object_repr = models.CharField(
        max_length=200,
        blank=True,
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["dependencia", "timestamp"]),
            models.Index(fields=["module", "action", "timestamp"]),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else "Anónimo"
        return f"{self.timestamp} - {user_str} - {self.get_action_display()} - {self.module}"
