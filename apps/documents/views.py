import mimetypes

from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt

from apps.accounts.models import Profile

from .forms import DocumentForm, DocumentSearchForm
from .models import Document, SubserieDocumental, TipoDocumental


def _documents_for_user(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    queryset = Document.objects.select_related(
        "dependencia", "serie", "subserie", "tipo_documental", "uploaded_by"
    )
    if user.is_superuser:
        return queryset, profile
    if not profile.dependencia_id:
        return queryset.none(), profile
    return queryset.filter(dependencia=profile.dependencia), profile


@login_required
@permission_required("documents.view_document", raise_exception=True)
def document_list(request):
    docs, profile = _documents_for_user(request.user)
    search_form = DocumentSearchForm(request.GET or None)

    if search_form.is_valid():
        q = search_form.cleaned_data.get("q", "").strip()
        estado = search_form.cleaned_data.get("estado")
        soporte = search_form.cleaned_data.get("soporte")
        fecha_desde = search_form.cleaned_data.get("fecha_desde")
        fecha_hasta = search_form.cleaned_data.get("fecha_hasta")

        if q:
            docs = docs.annotate(
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
                | Q(serie__name__icontains=q)
                | Q(subserie__name__icontains=q)
                | Q(tipo_documental__name__icontains=q)
            )
            docs = docs.order_by("match_priority", "-fecha_radicacion", "-created_at")

        if estado:
            docs = docs.filter(estado=estado)
        if soporte:
            docs = docs.filter(soporte=soporte)
        if fecha_desde:
            docs = docs.filter(fecha_radicacion__gte=fecha_desde)
        if fecha_hasta:
            docs = docs.filter(fecha_radicacion__lte=fecha_hasta)

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
    profile, _ = Profile.objects.get_or_create(user=request.user)
    serie_id = request.GET.get("serie_id")
    queryset = SubserieDocumental.objects.filter(is_active=True, serie_id=serie_id)
    if not request.user.is_superuser and profile.dependencia_id:
        queryset = queryset.filter(serie__dependencia=profile.dependencia)
    data = [{"id": item.id, "name": item.display_label} for item in queryset.order_by("code", "name")]
    return JsonResponse({"results": data})


@login_required
@permission_required("documents.add_document", raise_exception=True)
def tipos_by_subserie(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    subserie_id = request.GET.get("subserie_id")
    queryset = TipoDocumental.objects.filter(is_active=True, subserie_id=subserie_id)
    if not request.user.is_superuser and profile.dependencia_id:
        queryset = queryset.filter(subserie__serie__dependencia=profile.dependencia)
    data = [{"id": item.id, "name": item.display_label} for item in queryset.order_by("name")]
    return JsonResponse({"results": data})
