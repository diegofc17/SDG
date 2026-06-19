from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .utils import log_action


@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    log_action(
        request=request,
        user=user,
        action="LOGIN",
        module="AUTH",
        description=f"El usuario {user.username} ha iniciado sesión con éxito.",
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    if user:
        log_action(
            request=request,
            user=user,
            action="LOGOUT",
            module="AUTH",
            description=f"El usuario {user.username} ha cerrado sesión.",
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username", "desconocido")
    log_action(
        request=request,
        user=None,
        action="LOGIN_FAILED",
        module="AUTH",
        description=f"Intento fallido de inicio de sesión para el usuario: {username}.",
    )
