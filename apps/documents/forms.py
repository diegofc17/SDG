from django import forms

from .models import Dependencia, Document, Expediente, SerieDocumental, SubserieDocumental, TipoDocumental, TVDSubserie


class DocumentForm(forms.ModelForm):
    def __init__(self, *args, dependencia=None, dep_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["serie"].queryset = SerieDocumental.objects.filter(is_active=True).select_related("dependencia")
        self.fields["subserie"].queryset = SubserieDocumental.objects.none()
        self.fields["tipo_documental"].queryset = TipoDocumental.objects.none()
        self.fields["tvd_subserie"].queryset = TVDSubserie.objects.filter(is_active=True).select_related("serie__seccion")
        self.fields["expediente"].queryset = Expediente.objects.none()

        # --- Multi-dependency: inject a selector when user has > 1 dependency ---
        if dep_ids and len(dep_ids) > 1:
            dep_qs = Dependencia.objects.filter(pk__in=dep_ids, is_active=True)
            self.fields["dependencia"] = forms.ModelChoiceField(
                queryset=dep_qs,
                label="Dependencia",
                empty_label="Selecciona una dependencia",
                required=True,
            )
            self.fields["dependencia"].label_from_instance = lambda obj: obj.display_label
            # Move dependencia to top of fields order
            self.fields = {
                "dependencia": self.fields.pop("dependencia"),
                **self.fields,
            }

        if dependencia is not None:
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(is_active=True)
            self.fields["expediente"].queryset = Expediente.objects.filter(
                dependencia=dependencia
            ).exclude(estado="archivado")

        if self.instance.pk:
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(serie=self.instance.serie)
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.filter(subserie=self.instance.subserie)
            self.fields["expediente"].queryset = Expediente.objects.filter(serie=self.instance.serie).exclude(estado="archivado")

        serie_id = self.data.get("serie") or getattr(self.instance, "serie_id", None)
        subserie_id = self.data.get("subserie") or getattr(self.instance, "subserie_id", None)

        if serie_id:
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(
                serie_id=serie_id, is_active=True
            )
            self.fields["expediente"].queryset = Expediente.objects.filter(
                serie_id=serie_id
            ).exclude(estado="archivado")
        else:
            self.fields["subserie"].queryset = SubserieDocumental.objects.none()
            if dependencia is not None:
                self.fields["expediente"].queryset = Expediente.objects.filter(
                    dependencia=dependencia
                ).exclude(estado="archivado")
            else:
                self.fields["expediente"].queryset = Expediente.objects.none()

        if subserie_id:
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.filter(
                subserie_id=subserie_id, is_active=True
            )
        else:
            self.fields["tipo_documental"].queryset = TipoDocumental.objects.none()

        self.fields["serie"].label = "Serie documental"
        self.fields["subserie"].label = "Subserie documental"
        self.fields["subserie"].required = False
        self.fields["tipo_documental"].label = "Tipo documental"
        self.fields["tipo_documental"].required = False
        self.fields["tvd_subserie"].label = "Subserie TVD"
        self.fields["tvd_subserie"].required = False
        self.fields["expediente"].empty_label = "Selecciona un expediente"
        self.fields["serie"].empty_label = "Selecciona una serie"
        self.fields["subserie"].empty_label = "Selecciona una subserie"
        self.fields["tipo_documental"].empty_label = "Selecciona un tipo documental"
        self.fields["tvd_subserie"].empty_label = "Selecciona una subserie TVD"
        self.fields["serie"].label_from_instance = lambda obj: obj.display_label
        self.fields["subserie"].label_from_instance = lambda obj: obj.display_label
        self.fields["tvd_subserie"].label_from_instance = lambda obj: obj.display_label
        self.fields["fecha_documento"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["fecha_radicacion"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["description"].widget = forms.Textarea(attrs={"rows": 3, "placeholder": "Escribe una breve descripción del documento..."})
        self.fields["observaciones"].widget = forms.Textarea(attrs={"rows": 3, "placeholder": "Observaciones o notas adicionales..."})
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
            "expediente",
            "serie",
            "subserie",
            "tipo_documental",
            "tvd_subserie",
            "file",
        ]


class ExpedienteForm(forms.ModelForm):
    def __init__(self, *args, dependencia=None, dep_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["serie"].queryset = SerieDocumental.objects.filter(is_active=True).select_related("dependencia")
        self.fields["subserie"].queryset = SubserieDocumental.objects.none()
        self.fields["tvd_subserie"].queryset = TVDSubserie.objects.filter(is_active=True).select_related("serie__seccion")
        self.fields["fecha_apertura"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["fecha_cierre"].widget = forms.DateInput(attrs={"type": "date"})
        self.fields["descripcion"].widget = forms.Textarea(attrs={"rows": 3})

        # --- Multi-dependency: inject a selector when user has > 1 dependency ---
        if dep_ids and len(dep_ids) > 1:
            dep_qs = Dependencia.objects.filter(pk__in=dep_ids, is_active=True)
            self.fields["dependencia"] = forms.ModelChoiceField(
                queryset=dep_qs,
                label="Dependencia",
                empty_label="Selecciona una dependencia",
                required=True,
            )
            self.fields["dependencia"].label_from_instance = lambda obj: obj.display_label
            self.fields = {
                "dependencia": self.fields.pop("dependencia"),
                **self.fields,
            }

        serie_id = self.data.get("serie") or getattr(self.instance, "serie_id", None)
        if serie_id:
            self.fields["subserie"].queryset = SubserieDocumental.objects.filter(
                serie_id=serie_id, is_active=True
            )

        self.fields["serie"].empty_label = "Selecciona una serie"
        self.fields["subserie"].empty_label = "Selecciona una subserie"
        self.fields["tvd_subserie"].empty_label = "Selecciona una subserie TVD"
        self.fields["serie"].label_from_instance = lambda obj: obj.display_label
        self.fields["subserie"].label_from_instance = lambda obj: obj.display_label
        self.fields["tvd_subserie"].label_from_instance = lambda obj: obj.display_label
        self.fields["tvd_subserie"].label = "Subserie TVD"
        self.fields["tvd_subserie"].required = False

    def clean(self):
        cleaned_data = super().clean()
        fecha_apertura = cleaned_data.get("fecha_apertura")
        fecha_cierre = cleaned_data.get("fecha_cierre")
        serie = cleaned_data.get("serie")
        subserie = cleaned_data.get("subserie")

        if serie and subserie and subserie.serie_id != serie.id:
            self.add_error("subserie", "La subserie no pertenece a la serie seleccionada.")
        if fecha_apertura and fecha_cierre and fecha_cierre < fecha_apertura:
            self.add_error("fecha_cierre", "La fecha de cierre no puede ser anterior a la apertura.")

        return cleaned_data

    class Meta:
        model = Expediente
        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "serie",
            "subserie",
            "tvd_subserie",
            "estado",
            "fecha_apertura",
            "fecha_cierre",
        ]


class ExpedienteDocumentForm(forms.Form):
    documento = forms.ModelChoiceField(queryset=Document.objects.none(), label="Documento")

    def __init__(self, *args, dependencia=None, expediente=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Document.objects.filter(expediente__isnull=True)
        if dependencia is not None:
            queryset = queryset.filter(dependencia=dependencia)
        if expediente is not None and expediente.serie_id:
            queryset = queryset.filter(serie=expediente.serie)
        if expediente is not None and expediente.subserie_id:
            queryset = queryset.filter(subserie=expediente.subserie)
        self.fields["documento"].queryset = queryset.order_by("-created_at")
        self.fields["documento"].empty_label = "Selecciona un documento"


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
