from .models import Jugador
from django.contrib.auth import get_user_model
import pprint
from .utils import crear_jugador_con_datos
def prevent_duplicate_email(backend, details, *args, **kwargs):
    email = details.get('email')
    if not email:
        return
    User = get_user_model()
    try:
        user = User.objects.get(email=email)
        return {'user': user}
    except User.DoesNotExist:
        return


def save_verified_email(strategy, details, user=None, *args, **kwargs):
    if user:
        extra_data = kwargs.get('response', {})
        user.email_verified = extra_data.get('email_verified', True)
        user.picture = extra_data.get('picture')  # URL de imagen de perfil Google
        user.save()
def save_fullname(backend, user, *args, **kwargs):
    response = kwargs.get('response', {})
    details = kwargs.get('details', {})

    full_name = (
        response.get('name') or
        f"{response.get('given_name', '')} {response.get('family_name', '')}".strip() or
        details.get('fullname') or
        f"{details.get('first_name', '')} {details.get('last_name', '')}".strip() or
        user.get_full_name() or
        user.username
    )

    user.full_name = full_name
    user.save()


def crear_jugador(backend, user, *args, **kwargs):
    details = kwargs.get('details', {})
    response = kwargs.get('response', {})

    full_name = (
        response.get('name') or
        f"{response.get('given_name', '')} {response.get('family_name', '')}".strip() or
        details.get('fullname') or
        f"{details.get('first_name', '')} {details.get('last_name', '')}".strip() or
        user.get_full_name() or
        user.username
    )

    picture_url = response.get('picture')
    crear_jugador_con_datos(user, full_name, picture_url)