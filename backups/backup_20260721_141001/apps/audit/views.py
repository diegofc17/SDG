import csv
import datetime
from io import BytesIO
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import render
from .models import AuditLog
from .forms import AuditSearchForm


def superuser_required(user):
    if not user.is_superuser:
        raise PermissionDenied("Acceso restringido solo para administradores / superusuarios.")
    return True


@login_required
@user_passes_test(superuser_required)
def audit_list(request):
    logs = AuditLog.objects.select_related("user", "dependencia").order_by("-fecha")
    
    form = AuditSearchForm(request.GET or None)
    if form.is_valid():
        usuario = form.cleaned_data.get("usuario")
        dependencia = form.cleaned_data.get("dependencia")
        accion = form.cleaned_data.get("accion")
        modulo = form.cleaned_data.get("modulo")
        fecha_desde = form.cleaned_data.get("fecha_desde")
        fecha_hasta = form.cleaned_data.get("fecha_hasta")

        if usuario:
            logs = logs.filter(user=usuario)
        if dependencia:
            logs = logs.filter(dependencia=dependencia)
        if accion:
            logs = logs.filter(action=accion)
        if modulo:
            logs = logs.filter(module=modulo)
        if fecha_desde:
            logs = logs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            logs = logs.filter(fecha__date__lte=fecha_hasta)

    paginator = Paginator(logs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "audit/list.html",
        {
            "logs": page_obj.object_list,
            "page_obj": page_obj,
            "form": form,
        },
    )


@login_required
@user_passes_test(superuser_required)
def audit_export(request):
    logs = AuditLog.objects.select_related("user", "dependencia").order_by("-fecha")
    
    form = AuditSearchForm(request.GET or None)
    if form.is_valid():
        usuario = form.cleaned_data.get("usuario")
        dependencia = form.cleaned_data.get("dependencia")
        accion = form.cleaned_data.get("accion")
        modulo = form.cleaned_data.get("modulo")
        fecha_desde = form.cleaned_data.get("fecha_desde")
        fecha_hasta = form.cleaned_data.get("fecha_hasta")

        if usuario:
            logs = logs.filter(user=usuario)
        if dependencia:
            logs = logs.filter(dependencia=dependencia)
        if accion:
            logs = logs.filter(action=accion)
        if modulo:
            logs = logs.filter(module=modulo)
        if fecha_desde:
            logs = logs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            logs = logs.filter(fecha__date__lte=fecha_hasta)

    export_format = (request.GET.get("format") or "csv").lower()
    if export_format not in {"csv", "xlsx"}:
        raise Http404("Formato no soportado.")

    fields = [
        ("fecha", "Fecha y Hora"),
        ("user", "Usuario"),
        ("dependencia", "Dependencia"),
        ("get_action_display", "Acción"),
        ("get_module_display", "Módulo"),
        ("description", "Descripción"),
        ("object_repr", "Objeto afectado"),
        ("object_id", "ID Objeto"),
        ("ip", "Dirección IP"),
    ]

    filename = f"reporte_auditoria_{datetime.date.today().isoformat()}.{export_format}"

    if export_format == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")  # BOM para Excel
        writer = csv.writer(response)
        writer.writerow([label for _, label in fields])
        
        for log in logs.iterator(chunk_size=1000):
            row = []
            for attr, _ in fields:
                if attr == "user":
                    val = log.user.username if log.user else "Anónimo"
                elif attr == "dependencia":
                    val = log.dependencia.name if log.dependencia else "-"
                elif attr == "get_action_display":
                    val = log.get_action_display()
                elif attr == "get_module_display":
                    val = log.get_module_display()
                elif attr == "fecha":
                    val = log.fecha.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    val = getattr(log, attr, "")
                
                row.append(str(val) if val is not None else "")
            writer.writerow(row)
        return response

    # Exportación XLSX
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError:
        return HttpResponse(
            "No se puede exportar a Excel porque falta la dependencia 'openpyxl'. "
            "Instala con: pip install openpyxl",
            status=400,
            content_type="text/plain; charset=utf-8",
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoría"
    ws.append([label for _, label in fields])

    for log in logs.iterator(chunk_size=1000):
        row = []
        for attr, _ in fields:
            if attr == "user":
                val = log.user.username if log.user else "Anónimo"
            elif attr == "dependencia":
                val = log.dependencia.name if log.dependencia else "-"
            elif attr == "get_action_display":
                val = log.get_action_display()
            elif attr == "get_module_display":
                val = log.get_module_display()
            elif attr == "fecha":
                # openpyxl maneja datetime nativo, pero sin timezone para evitar líos
                val = log.fecha.astimezone().replace(tzinfo=None)
            else:
                val = getattr(log, attr, "")
            
            row.append(val)
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
