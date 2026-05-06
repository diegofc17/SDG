from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from pathlib import Path


User = get_user_model()


class Dependencia(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "dependencias"

    def __str__(self):
        return self.name

    @property
    def display_label(self):
        return f"{self.code} - {self.name}"


class SerieDocumental(models.Model):
    dependencia = models.ForeignKey(Dependencia, on_delete=models.PROTECT, related_name="series")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["dependencia__code", "code", "name"]
        unique_together = ("dependencia", "code")
        verbose_name = "serie documental"
        verbose_name_plural = "series documentales"

    def __str__(self):
        return f"{self.dependencia.code}-{self.code} {self.name}"

    @property
    def full_code(self):
        return f"{self.dependencia.code}-{self.code}"

    @property
    def display_label(self):
        return f"{self.full_code} - {self.name}"


class SubserieDocumental(models.Model):
    serie = models.ForeignKey(SerieDocumental, on_delete=models.PROTECT, related_name="subseries")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    retention_management = models.PositiveSmallIntegerField("archivo de gestion", default=0)
    retention_central = models.PositiveSmallIntegerField("archivo central", default=0)
    disposition_ct = models.BooleanField("conservacion total", default=False)
    disposition_e = models.BooleanField("eliminacion", default=False)
    disposition_d = models.BooleanField("digitalizacion", default=False)
    disposition_s = models.BooleanField("seleccion", default=False)
    procedures = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["serie__dependencia__code", "serie__code", "code", "name"]
        unique_together = ("serie", "code")
        verbose_name = "subserie documental"
        verbose_name_plural = "subseries documentales"

    def __str__(self):
        return f"{self.serie.dependencia.code}-{self.serie.code}-{self.code} {self.name}"

    @property
    def full_code(self):
        return f"{self.serie.dependencia.code}-{self.serie.code}-{self.code}"

    @property
    def display_label(self):
        return f"{self.full_code} - {self.name}"

    @property
    def disposition_summary(self):
        flags = []
        if self.disposition_ct:
            flags.append("CT")
        if self.disposition_e:
            flags.append("E")
        if self.disposition_d:
            flags.append("D")
        if self.disposition_s:
            flags.append("S")
        return ", ".join(flags) if flags else "-"


class TipoDocumental(models.Model):
    subserie = models.ForeignKey(SubserieDocumental, on_delete=models.PROTECT, related_name="tipos")
    name = models.CharField(max_length=200)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["subserie__serie__dependencia__code", "subserie__serie__code", "subserie__code", "name"]
        unique_together = ("subserie", "name")
        verbose_name = "tipo documental"
        verbose_name_plural = "tipos documentales"

    def __str__(self):
        return self.name

    @property
    def display_label(self):
        return f"{self.subserie.full_code} / {self.name}"


class Document(models.Model):
    ESTADO_CHOICES = [
        ("radicado", "Radicado"),
        ("en_tramite", "En tramite"),
        ("cerrado", "Cerrado"),
        ("archivado", "Archivado"),
    ]

    SOPORTE_CHOICES = [
        ("fisico", "Fisico"),
        ("digital", "Digital"),
        ("hibrido", "Hibrido"),
    ]

    title = models.CharField(max_length=180, db_index=True)
    numero_radicado = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    asunto = models.CharField(max_length=255, blank=True)
    fecha_documento = models.DateField(null=True, blank=True)
    fecha_radicacion = models.DateField(null=True, blank=True, db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="radicado", db_index=True)
    soporte = models.CharField(max_length=20, choices=SOPORTE_CHOICES, default="digital", db_index=True)
    description = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    dependencia = models.ForeignKey(
        Dependencia, on_delete=models.PROTECT, related_name="documents", null=True, blank=True
    )
    serie = models.ForeignKey(
        SerieDocumental, on_delete=models.PROTECT, related_name="documents", null=True, blank=True
    )
    subserie = models.ForeignKey(
        SubserieDocumental, on_delete=models.PROTECT, related_name="documents", null=True, blank=True
    )
    tipo_documental = models.ForeignKey(
        TipoDocumental, on_delete=models.PROTECT, related_name="documents", null=True, blank=True
    )
    file = models.FileField(upload_to="documents/%Y/%m/")
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["dependencia", "fecha_radicacion"]),
            models.Index(fields=["dependencia", "estado"]),
            models.Index(fields=["dependencia", "created_at"]),
        ]

    def clean(self):
        if self.fecha_radicacion and self.fecha_documento and self.fecha_radicacion < self.fecha_documento:
            raise ValidationError("La fecha de radicacion no puede ser anterior a la fecha del documento.")
        if self.serie and self.dependencia and self.serie.dependencia_id != self.dependencia_id:
            raise ValidationError("La serie no pertenece a la dependencia seleccionada.")
        if self.subserie and self.serie and self.subserie.serie_id != self.serie_id:
            raise ValidationError("La subserie no pertenece a la serie seleccionada.")
        if self.tipo_documental and self.subserie and self.tipo_documental.subserie_id != self.subserie_id:
            raise ValidationError("El tipo documental no pertenece a la subserie seleccionada.")

    def __str__(self):
        return self.title

    @property
    def estado_label(self):
        return self.get_estado_display()

    @property
    def soporte_label(self):
        return self.get_soporte_display()

    @property
    def file_extension(self):
        if not self.file:
            return ""
        return Path(self.file.name).suffix.lower()

    @property
    def is_previewable_pdf(self):
        return self.file_extension == ".pdf"

    @property
    def is_previewable_image(self):
        return self.file_extension in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
