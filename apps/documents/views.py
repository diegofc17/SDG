import mimetypes
import csv
import datetime
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt

from apps.accounts.models import Profile

from .forms import DocumentForm, DocumentSearchForm, ExpedienteDocumentForm, ExpedienteForm
from .models import Document, Expediente, SubserieDocumental, TipoDocumental


def _documents_for_user(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    queryset = Document.objects.select_related(
        "dependencia", "expediente", "serie", "subserie", "tipo_documental", "uploaded_by"
    )
    if user.is_superuser:
        return queryset, profile
    if not profile.dependencia_id:
        return queryset.none(), profile
    return queryset.filter(dependencia=profile.dependencia), profile


def _expedientes_for_user(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    queryset = Expediente.objects.select_related("dependencia", "serie", "subserie", "created_by")
    if user.is_superuser:
        return queryset, profile
    if not profile.dependencia_id:
        return queryset.none(), profile
    return queryset.filter(dependencia=profile.dependencia), profile


def _apply_document_search_filters(queryset, search_form):
    if not search_form.is_valid():
        return queryset

    q = (search_form.cleaned_data.get("q") or "").strip()
    estado = search_form.cleaned_data.get("estado")
    soporte = search_form.cleaned_data.get("soporte")
    fecha_desde = search_form.cleaned_data.get("fecha_desde")
    fecha_hasta = search_form.cleaned_data.get("fecha_hasta")

    if q:
        queryset = queryset.annotate(
            match_priority=Case(
                When(numero_radicado__iexact=q, then=Value(0)),
                When(numero_radicado__istartswith=q, then=Value(1)),
                When(title__istartswith=q, then=Value(2)),
                When(asunto__istartswith=q, then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        ).filter(
            Q(numero_radicado__icontains=q)
            | Q(title__icontains=q)
            | Q(asunto__icontains=q)
            | Q(description__icontains=q)
            | Q(observaciones__icontains=q)
            | Q(expediente__codigo__icontains=q)
            | Q(expediente__nombre__icontains=q)
            | Q(serie__name__icontains=q)
            | Q(subserie__name__icontains=q)
            | Q(tipo_documental__name__icontains=q)
        )
        queryset = queryset.order_by("match_priority", "-fecha_radicacion", "-created_at")

    if estado:
        queryset = queryset.filter(estado=estado)
    if soporte:
        queryset = queryset.filter(soporte=soporte)
    if fecha_desde:
        queryset = queryset.filter(fecha_radicacion__gte=fecha_desde)
    if fecha_hasta:
        queryset = queryset.filter(fecha_radicacion__lte=fecha_hasta)

    return queryset


@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_list(request):
    docs, profile = _documents_for_user(request.user)
    search_form = DocumentSearchForm(request.GET or None)
    docs = _apply_document_search_filters(docs, search_form)

    paginator = Paginator(docs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "documents/list.html",
        {
            "documents": page_obj.object_list,
            "page_obj": page_obj,
            "search_form": search_form,
            "user_dependencia": profile.dependencia,
        },
    )


@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_export(request):
    docs, _ = _documents_for_user(request.user)
    search_form = DocumentSearchForm(request.GET or None)
    docs = _apply_document_search_filters(docs, search_form)

    export_format = (request.GET.get("format") or "csv").lower()
    if export_format not in {"csv", "xlsx"}:
        raise Http404("Formato no soportado.")

    fields = [
        ("numero_radicado", "Radicado"),
        ("title", "Titulo"),
        ("asunto", "Asunto"),
        ("fecha_documento", "Fecha documento"),
        ("fecha_radicacion", "Fecha radicacion"),
        ("estado_label", "Estado"),
        ("soporte_label", "Soporte"),
        ("dependencia", "Dependencia"),
        ("expediente", "Expediente"),
        ("serie", "Serie"),
        ("subserie", "Subserie"),
        ("tipo_documental", "Tipo documental"),
        ("uploaded_by", "Usuario"),
        ("created_at", "Creado"),
    ]

    filename = f"reporte_documentos.{export_format}"
    if export_format == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")  # Excel-friendly UTF-8 BOM
        writer = csv.writer(response)
        writer.writerow([label for _, label in fields])
        for doc in docs.iterator(chunk_size=1000):
            row = []
            for attr, _label in fields:
                value = getattr(doc, attr, "")
                if callable(value):
                    value = value()
                row.append(str(value) if value is not None else "")
            writer.writerow(row)
        return response

    # XLSX export uses openpyxl if available.
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError as exc:
        return HttpResponse(
            "No se puede exportar a Excel porque falta la dependencia 'openpyxl'. "
            "Instala con: pip install openpyxl",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Documentos"
    ws.append([label for _, label in fields])
    for doc in docs.iterator(chunk_size=1000):
        row = []
        for attr, _label in fields:
            value = getattr(doc, attr, "")
            if callable(value):
                value = value()
            if value is None:
                row.append("")
            elif isinstance(value, (datetime.datetime, datetime.date)):
                row.append(value.isoformat(sep=" ") if isinstance(value, datetime.datetime) else value.isoformat())
            else:
                row.append(str(value))
        ws.append(row)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@permission_required("documents.view_document", raise_exception=True)
def expediente_list(request):
    expedientes, profile = _expedientes_for_user(request.user)
    return render(
        request,
        "documents/expedientes/list.html",
        {
            "expedientes": expedientes.annotate(document_count=Count("documents")),
            "user_dependencia": profile.dependencia,
        },
    )


@login_required
@permission_required("documents.add_document", raise_exception=True)
def expediente_create(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.dependencia_id:
        return render(
            request,
            "documents/expedientes/form.html",
            {"form": None, "missing_dependencia": True},
        )

    dependencia = profile.dependencia
    if request.method == "POST":
        form = ExpedienteForm(request.POST, dependencia=dependencia)
        if form.is_valid():
            expediente = form.save(commit=False)
            expediente.dependencia = dependencia
            expediente.created_by = request.user
            expediente.save()
            return redirect("expediente_detail", pk=expediente.pk)
    else:
        form = ExpedienteForm(dependencia=dependencia)

    return render(
        request,
        "documents/expedientes/form.html",
        {"form": form, "missing_dependencia": False},
    )


@login_required
@permission_required("documents.change_document", raise_exception=True)
def expediente_update(request, pk):
    expedientes, profile = _expedientes_for_user(request.user)
    expediente = get_object_or_404(expedientes, pk=pk)

    if not request.user.is_superuser and expediente.created_by_id != request.user.id:
        raise PermissionDenied("Solo puedes editar expedientes creados por tu propio usuario.")

    if request.method == "POST":
        form = ExpedienteForm(request.POST, instance=expediente, dependencia=profile.dependencia or expediente.dependencia)
        if form.is_valid():
            updated_expediente = form.save(commit=False)
            updated_expediente.dependencia = expediente.dependencia
            updated_expediente.created_by = expediente.created_by
            updated_expediente.save()
            return redirect("expediente_detail", pk=expediente.pk)
    else:
        form = ExpedienteForm(instance=expediente, dependencia=profile.dependencia or expediente.dependencia)

    return render(
        request,
        "documents/expedientes/form.html",
        {
            "form": form,
            "missing_dependencia": False,
            "is_edit": True,
            "expediente": expediente,
        },
    )


@login_required
@permission_required("documents.view_document", raise_exception=True)
def expediente_detail(request, pk):
    expedientes, profile = _expedientes_for_user(request.user)
    expediente = get_object_or_404(expedientes, pk=pk)
    documents = expediente.documents.select_related("uploaded_by", "serie", "subserie").order_by("-created_at")
    add_document_form = ExpedienteDocumentForm(dependencia=expediente.dependencia, expediente=expediente)

    return render(
        request,
        "documents/expedientes/detail.html",
        {
            "expediente": expediente,
            "documents": documents,
            "add_document_form": add_document_form,
            "can_manage": request.user.is_superuser
            or (request.user.has_perm("documents.change_document") and profile.dependencia_id == expediente.dependencia_id),
        },
    )


@login_required
@permission_required("documents.change_document", raise_exception=True)
def expediente_add_document(request, pk):
    expedientes, _ = _expedientes_for_user(request.user)
    expediente = get_object_or_404(expedientes, pk=pk)

    if request.method != "POST":
        return redirect("expediente_detail", pk=expediente.pk)

    form = ExpedienteDocumentForm(request.POST, dependencia=expediente.dependencia, expediente=expediente)
    if form.is_valid():
        document = form.cleaned_data["documento"]
        document.expediente = expediente
        document.save(update_fields=["expediente", "updated_at"])

    return redirect("expediente_detail", pk=expediente.pk)


@login_required
@permission_required("documents.add_document", raise_exception=True)
def document_create(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if not profile.dependencia_id:
        return render(
            request,
            "documents/create.html",
            {"form": None, "missing_dependencia": True},
        )

    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, dependencia=profile.dependencia)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.dependencia = profile.dependencia
            doc.save()
            return redirect("document_list")
    else:
        form = DocumentForm(dependencia=profile.dependencia)

    return render(request, "documents/create.html", {"form": form, "missing_dependencia": False})


@login_required
@permission_required("documents.change_document", raise_exception=True)
def document_update(request, pk):
    queryset, profile = _documents_for_user(request.user)
    document = get_object_or_404(queryset, pk=pk)

    if not request.user.is_superuser and document.uploaded_by_id != request.user.id:
        raise PermissionDenied("Solo puedes editar documentos cargados por tu propio usuario.")

    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES,
            instance=document,
            dependencia=profile.dependencia or document.dependencia,
        )
        if form.is_valid():
            updated_document = form.save(commit=False)
            updated_document.uploaded_by = document.uploaded_by
            updated_document.dependencia = document.dependencia
            updated_document.save()
            return redirect("document_detail", pk=document.pk)
    else:
        form = DocumentForm(instance=document, dependencia=profile.dependencia or document.dependencia)

    return render(
        request,
        "documents/create.html",
        {
            "form": form,
            "missing_dependencia": False,
            "is_edit": True,
            "document": document,
        },
    )


@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_detail(request, pk):
    queryset, _ = _documents_for_user(request.user)
    document = get_object_or_404(queryset, pk=pk)
    return render(request, "documents/detail.html", {"document": document})


@xframe_options_exempt
@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_preview(request, pk):
    queryset, _ = _documents_for_user(request.user)
    document = get_object_or_404(queryset, pk=pk)
    if not document.file:
        raise Http404("El documento no tiene archivo asociado.")

    guessed_type, _ = mimetypes.guess_type(document.file.name)
    content_type = guessed_type or "application/octet-stream"
    response = FileResponse(document.file.open("rb"), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{document.file.name.split("/")[-1]}"'
    return response


@login_required
@permission_required("documents.add_document", raise_exception=True)
def subseries_by_serie(request):
    serie_id = request.GET.get("serie_id")
    queryset = SubserieDocumental.objects.filter(is_active=True, serie_id=serie_id)
    data = [{"id": item.id, "name": item.display_label} for item in queryset.order_by("code", "name")]
    return JsonResponse({"results": data})


@login_required
@permission_required("documents.add_document", raise_exception=True)
def tipos_by_subserie(request):
    subserie_id = request.GET.get("subserie_id")
    queryset = TipoDocumental.objects.filter(is_active=True, subserie_id=subserie_id)
    data = [{"id": item.id, "name": item.display_label} for item in queryset.order_by("name")]
    return JsonResponse({"results": data})
