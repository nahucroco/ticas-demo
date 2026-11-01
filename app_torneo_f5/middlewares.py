from django.shortcuts import redirect
from django.conf import settings
from django.urls import resolve

EXEMPT_URLS = [
    'login', 'logout', 'registro_usuario', 'admin:index',  # Agregá más si lo necesitás
]

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resolver = resolve(request.path_info)
        if not request.user.is_authenticated and resolver.url_name not in EXEMPT_URLS:
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)
