from .models import Invitacion, InvitacionEquipo, Jugador
from django.db.models import Q

def notificaciones_context(request):
    if not request.user.is_authenticated:
        return {}

    try:
        jugador = Jugador.objects.get(user=request.user)

        cantidad_partido = Invitacion.objects.filter(
            jugador=jugador,
            aceptada=False
        ).filter(~Q(partido__jugadores=jugador)).count()

        cantidad_equipo = InvitacionEquipo.objects.filter(
            jugador=jugador,
            aceptada=False
        ).count()

        return {'cantidad_notificaciones': cantidad_partido + cantidad_equipo}
    except Jugador.DoesNotExist:
        return {}
