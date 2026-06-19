from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models.functions import ExtractYear

from apps.accounts.models import Profile
from apps.documents.models import Document, Expediente


def home(request):
    return render(request, "home.html")


@login_required
def dashboard(request):
    docs = Document.objects.select_related("dependencia", "uploaded_by")
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.user.is_superuser:
        scope_docs = docs
        scope_expedientes = Expediente.objects.all()
        scope_label = "General (todas las dependencias)"
    else:
        dep_ids = list(profile.get_dependencias_ids())
        if dep_ids:
            scope_docs = docs.filter(dependencia_id__in=dep_ids)
            scope_expedientes = Expediente.objects.filter(dependencia_id__in=dep_ids)
            dep_labels = ", ".join(d.display_label for d in profile.dependencias.all())
            scope_label = dep_labels
        else:
            scope_docs = docs.none()
            scope_expedientes = Expediente.objects.none()
            scope_label = "Sin dependencia asignada"

    totals = scope_docs.aggregate(
        total=Count("id"),
        con_radicado=Count("id", filter=Q(numero_radicado__isnull=False) & ~Q(numero_radicado="")),
        sin_radicado=Count("id", filter=Q(numero_radicado__isnull=True) | Q(numero_radicado="")),
    )

    expedientes_totals = scope_expedientes.aggregate(
        total=Count("id"),
        abiertos=Count("id", filter=Q(estado="abierto")),
        cerrados=Count("id", filter=Q(estado="cerrado")),
        archivados=Count("id", filter=Q(estado="archivado")),
    )

    by_estado = {key: 0 for key, _ in Document.ESTADO_CHOICES}
    for row in scope_docs.values("estado").annotate(c=Count("id")):
        by_estado[row["estado"]] = row["c"]

    by_soporte = {key: 0 for key, _ in Document.SOPORTE_CHOICES}
    for row in scope_docs.values("soporte").annotate(c=Count("id")):
        by_soporte[row["soporte"]] = row["c"]

    year_rows = (
        scope_docs.annotate(year=ExtractYear("fecha_documento"))
        .values("year")
        .annotate(total=Count("id"))
        .order_by("-year")
    )

    dependency_rows = (
        scope_docs.annotate(year=ExtractYear("fecha_documento"))
        .values("year", "dependencia__code", "dependencia__name")
        .annotate(total=Count("id"))
        .order_by("-year", "dependencia__code", "dependencia__name")
    )
    dependencies_by_year = {}
    for row in dependency_rows:
        year_key = row["year"] or "Sin fecha documento"
        dependencia = (
            f"{row['dependencia__code']} - {row['dependencia__name']}"
            if row["dependencia__code"] and row["dependencia__name"]
            else "Sin dependencia"
        )
        dependencies_by_year.setdefault(year_key, []).append(
            {"dependencia": dependencia, "total": row["total"]}
        )

    by_year = []
    for row in year_rows:
        year_key = row["year"] or "Sin fecha documento"
        count = row["total"]
        by_year.append(
            {
                "year": year_key,
                "total": count,
                "dependencias": dependencies_by_year.get(year_key, []),
            }
        )

    recientes = scope_docs.order_by("-created_at")[:8]

    recent_logs = []
    if request.user.is_superuser:
        from apps.audit.models import AuditLog
        recent_logs = AuditLog.objects.select_related("user", "dependencia").order_by("-timestamp")[:10]

    return render(
        request,
        "dashboard.html",
        {
            "scope_label": scope_label,
            "profile_dependencias": profile.dependencias.all(),
            "totals": totals,
            "expedientes_totals": expedientes_totals,
            "by_estado": by_estado,
            "by_soporte": by_soporte,
            "by_year": by_year,
            "recientes": recientes,
            "recent_logs": recent_logs,
        },
    )
