from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render

from .forms import SignUpForm


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada correctamente. Ya puedes iniciar sesion.")
            return redirect("login")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})

def cerrar_sesion(request):
    logout(request)  # elimina la sesión del usuario
    return redirect('login')  # redirige a la vista de login
