from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
from apps.accounts.models import Profile


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def log_action(request=None, user=None, action=None, module=None, description="", obj=None):
    """
    Registra una acción en el log de auditoría.
    Permite pasar el request para extraer el usuario, dependencia e IP.
    """
    if request:
        if not user and request.user.is_authenticated:
            user = request.user
        ip_address = get_client_ip(request)
    else:
        ip_address = None

    dependencia = None
    if user and user.is_authenticated:
        try:
            profile = user.profile
            dependencia = profile.dependencia
        except Exception:
            # Si por alguna razón no tiene profile
            profile, _ = Profile.objects.get_or_create(user=user)
            dependencia = profile.dependencia

    object_repr = ""
    object_id = None
    if obj:
        object_repr = str(obj)[:200]
        if hasattr(obj, "pk"):
            object_id = obj.pk

    # Creamos el registro en la base de datos
    log_entry = AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        dependencia=dependencia,
        action=action,
        module=module,
        description=description,
        object_repr=object_repr,
        object_id=object_id,
        ip=ip_address,
    )
    return log_entry
