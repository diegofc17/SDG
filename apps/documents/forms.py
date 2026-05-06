from django import forms

from .models import Document, SerieDocumental, SubserieDocumental, TipoDocumental


class DocumentForm(forms.ModelForm):
    def __init__(self, *args, dependencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["serie"].queryset = SerieDocumental.objects.none()
        self.fields["subserie"].queryset = SubserieDocumental.objects.none()
        self.fields["tipo_documental"].queryset = TipoDocumental.objects.none()

        if dependencia is not None:
            self.fields["serie"].queryset = SerieDocumental.objects.filter(
                dependencia=dependencia, is_active=True
            )
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(is_active=True)
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.filter(is_active=True)

        if self.instance.pk:
            self.fields["serie"].queryset = SerieDocumental.objects.filter(
                dependencia=self.instance.dependencia
            )
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(serie=self.instance.serie)
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.filter(subserie=self.instance.subserie)

        serie_id = self.data.get("serie") or getattr(self.instance, "serie_id", None)
        if serie_id:
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(
                serie_id=serie_id, is_active=True
            )
        else:
            self.fields["subserie"].queryset = SubserieDocumental.objects.none()

        subserie_id = self.data.get("subserie") or getattr(self.instance, "subserie_id", None)
        if subserie_id:
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.filter(
                subserie_id=subserie_id, is_active=True
            )
        else:
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.none()

        self.fields["serie"].label = "Serie documental"
        self.fields["subserie"].label = "Subserie documental"
        self.fields["tipo_documental"].label = "Tipo documental"
        self.fields["serie"].empty_label = "Selecciona una serie"
        self.fields["subserie"].empty_label = "Selecciona una subserie"
        self.fields["tipo_documental"].empty_label = "Selecciona un tipo documental"
        self.fields["serie"].label_from_instance = lambda obj: obj.display_label
        self.fields["subserie"].label_from_instance = lambda obj: obj.display_label
        self.fields["tipo_documental"].label_from_instance = lambda obj: obj.display_label
        self.fields["fecha_documento"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["fecha_radicacion"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["numero_radicado"].help_text = "Opcional. Usa el consecutivo o codigo interno de radicacion si existe."
        self.fields["asunto"].help_text = "Resume el tema principal del documento."
        self.fields["estado"].help_text = "Indica en que fase se encuentra el documento."
        self.fields["soporte"].help_text = "Define si existe en medio fisico, digital o ambos."
        self.fields["fecha_radicacion"].help_text = "Opcional. Registra la fecha solo cuando el documento tenga radicado."

    def clean(self):
        cleaned_data = super().clean()
        fecha_documento = cleaned_data.get("fecha_documento")
        fecha_radicacion = cleaned_data.get("fecha_radicacion")
        serie = cleaned_data.get("serie")
        subserie = cleaned_data.get("subserie")
        tipo_documental = cleaned_data.get("tipo_documental")

        if not fecha_documento:
            self.add_error("fecha_documento", "Debes indicar la fecha del documento.")
        if not serie:
            self.add_error("serie", "Debes seleccionar una serie documental.")
        if not subserie:
            self.add_error("subserie", "Debes seleccionar una subserie documental.")
        if not tipo_documental:
            self.add_error("tipo_documental", "Debes seleccionar un tipo documental.")

        if fecha_documento and fecha_radicacion and fecha_radicacion < fecha_documento:
            self.add_error("fecha_radicacion", "La fecha de radicacion no puede ser anterior a la del documento.")
        if serie and subserie and subserie.serie_id != serie.id:
            self.add_error("subserie", "La subserie no pertenece a la serie seleccionada.")
        if subserie and tipo_documental and tipo_documental.subserie_id != subserie.id:
            self.add_error("tipo_documental", "El tipo documental no pertenece a la subserie seleccionada.")

        return cleaned_data

    class Meta:
        model = Document
        fields = [
            "numero_radicado",
            "title",
            "asunto",
            "fecha_documento",
            "fecha_radicacion",
            "estado",
            "soporte",
            "description",
            "observaciones",
            "serie",
            "subserie",
            "tipo_documental",
            "file",
        ]


class DocumentSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Busqueda",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Radicado, titulo, asunto o texto del documento",
            }
        ),
    )
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados"), *Document.ESTADO_CHOICES])
    soporte = forms.ChoiceField(required=False, choices=[("", "Todos los soportes"), *Document.SOPORTE_CHOICES])
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
