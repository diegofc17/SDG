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
        return f"{self.dependencia.name} | {self.full_code} - {self.name}"


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


class Expediente(models.Model):
    ESTADO_CHOICES = [
        ("abierto", "Abierto"),
        ("cerrado", "Cerrado"),
        ("archivado", "Archivado"),
    ]

    codigo = models.CharField(max_length=60, db_index=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    dependencia = models.ForeignKey(
        Dependencia, on_delete=models.PROTECT, related_name="expedientes", null=True, blank=True
    )
    serie = models.ForeignKey(
        SerieDocumental, on_delete=models.PROTECT, related_name="expedientes", null=True, blank=True
    )
    subserie = models.ForeignKey(
        SubserieDocumental, on_delete=models.PROTECT, related_name="expedientes", null=True, blank=True
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="abierto", db_index=True)
    fecha_apertura = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="expedientes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("dependencia", "codigo")
        indexes = [
            models.Index(fields=["dependencia", "estado"]),
            models.Index(fields=["dependencia", "created_at"]),
        ]

    def clean(self):
        if self.subserie and self.serie and self.subserie.serie_id != self.serie_id:
            raise ValidationError("La subserie no pertenece a la serie del expediente.")
        if self.fecha_cierre and self.fecha_apertura and self.fecha_cierre < self.fecha_apertura:
            raise ValidationError("La fecha de cierre no puede ser anterior a la fecha de apertura.")

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def estado_label(self):
        return self.get_estado_display()


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
    expediente = models.ForeignKey(
        Expediente, on_delete=models.SET_NULL, related_name="documents", null=True, blank=True
    )
    serie = models.ForeignKey(
        SerieDocumental, on_delete=models.PROTECT, related_name="documents", null=True, blank=True
    )
    subserie = models.ForeignKey(
        SubserieDocumental, on_delete=models.PROTECT, related_name="documents", null=True, blank=True
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
        if self.expediente and self.dependencia and self.expediente.dependencia_id != self.dependencia_id:
            raise ValidationError("El expediente no pertenece a la dependencia del documento.")
        if self.fecha_radicacion and self.fecha_documento and self.fecha_radicacion < self.fecha_documento:
            raise ValidationError("La fecha de radicacion no puede ser anterior a la fecha del documento.")
        if self.subserie and self.serie and self.subserie.serie_id != self.serie_id:
            raise ValidationError("La subserie no pertenece a la serie seleccionada.")


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


class TVDSeccion(models.Model):
    name = models.CharField("nombre", max_length=120, unique=True)
    code = models.CharField("codigo", max_length=20, unique=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["code", "name"]
        verbose_name = "sección TVD"
        verbose_name_plural = "secciones TVD"

    def __str__(self):
        return self.name

    @property
    def display_label(self):
        return f"{self.code} - {self.name}"


class TVDSerie(models.Model):
    seccion = models.ForeignKey(TVDSeccion, on_delete=models.PROTECT, related_name="series", verbose_name="sección")
    code = models.CharField("codigo", max_length=20)
    name = models.CharField("nombre", max_length=200)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["seccion__code", "code", "name"]
        unique_together = ("seccion", "code")
        verbose_name = "serie TVD"
        verbose_name_plural = "series TVD"

    def __str__(self):
        return f"{self.seccion.code}-{self.code} {self.name}"

    @property
    def full_code(self):
        return f"{self.seccion.code}-{self.code}"

    @property
    def display_label(self):
        return f"{self.seccion.name} | {self.full_code} - {self.name}"


class TVDSubserie(models.Model):
    serie = models.ForeignKey(TVDSerie, on_delete=models.PROTECT, related_name="subseries", verbose_name="serie")
    code = models.CharField("codigo", max_length=20)
    name = models.CharField("nombre", max_length=200)
    retention_management = models.PositiveSmallIntegerField("archivo de gestion (años)", default=0)
    retention_central = models.PositiveSmallIntegerField("archivo central (años)", default=0)
    disposition_ct = models.BooleanField("conservacion total (CT)", default=False)
    disposition_e = models.BooleanField("eliminacion (E)", default=False)
    disposition_d = models.BooleanField("digitalizacion (D)", default=False)
    disposition_s = models.BooleanField("seleccion (S)", default=False)
    procedures = models.TextField("procedimientos", blank=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["serie__seccion__code", "serie__code", "code", "name"]
        unique_together = ("serie", "code")
        verbose_name = "subserie TVD"
        verbose_name_plural = "subseries TVD"

    def __str__(self):
        return f"{self.serie.seccion.code}-{self.serie.code}-{self.code} {self.name}"

    @property
    def full_code(self):
        return f"{self.serie.seccion.code}-{self.serie.code}-{self.code}"

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

