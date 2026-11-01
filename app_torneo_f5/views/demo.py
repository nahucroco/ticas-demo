"""Acceso de invitado de la demo: entra con el usuario de ejemplo sin pedir contraseña."""

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.management import call_command
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


@require_POST
def demo_login(request):
    User = get_user_model()
    user = User.objects.filter(username=settings.DEMO_USERNAME).first()
    if user is None:
        # Base vacía (por ejemplo, tras un reinicio): se vuelve a cargar la demo.
        call_command("cargar_demo")
        user = User.objects.get(username=settings.DEMO_USERNAME)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("home")
