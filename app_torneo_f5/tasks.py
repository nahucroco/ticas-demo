# app_torneo_f5/tasks.py
from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from app_torneo_f5.models import (
    PartidoAmistoso, Partido, Inscripcion, Jugador, Notificacion
)

# ========== Helpers comunes ==========

DEFAULT_DURACION_TORNEO_MIN = 3  # Cambiá por tu duración por defecto del torneo

def hora_fin_amistoso(p: PartidoAmistoso) -> datetime | None:
    if not p.dia or not p.hora_inicio or not p.duracion:
        return None
    inicio = timezone.make_aware(
        datetime.combine(p.dia, p.hora_inicio),
        timezone.get_current_timezone()
    )
    return inicio + timedelta(minutes=int(p.duracion))


def get_duracion_torneo(p: Partido) -> int:
    dur = getattr(getattr(p, "torneo", None), "duracion", None)
    try:
        return int(dur) if dur is not None else DEFAULT_DURACION_TORNEO_MIN
    except Exception:
        return DEFAULT_DURACION_TORNEO_MIN


def hora_fin_torneo(p: Partido):
    if not p.dia or not p.hora_inicio or p.duracion in (None, 0):
        return None
    inicio_naive = datetime.combine(p.dia, p.hora_inicio)
    inicio = timezone.make_aware(inicio_naive, timezone.get_current_timezone())
    dur = int(p.duracion)
    return inicio + timedelta(minutes=dur)


def jugadores_de_equipo(equipo):
    return list(
        Jugador.objects.filter(inscripcion__equipo=equipo)
        .select_related("user")
        .distinct()
    )


def notificar_estadistica(user, partido, prefijo):
    if user:
        Notificacion.objects.create(
            usuario=user,
            mensaje=f"{prefijo} #{partido.id} ha finalizado. ¡Cargá tu estadística! 🎯",
            tipo="estadistica",
            extra_id=partido.id,
        )


def notificar_estadistica_amistoso(user, partido_amistoso):
    if user:
        Notificacion.objects.create(
            usuario=user,
            mensaje=f"El partido amistoso #{partido_amistoso.id} ha finalizado. ¡Cargá tu estadística! ⚽",
            tipo="estadistica",
            extra_id=partido_amistoso.id,
        )


# ========== AMISTOSOS ==========

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def marcar_partido_jugando(self, partido_id: int):
    try:
        with transaction.atomic():
            p = PartidoAmistoso.objects.select_for_update().get(id=partido_id)

            if p.jugado or p.cancelado:
                from .services import borrar_tasks_partido
                transaction.on_commit(lambda: borrar_tasks_partido(p))
                return f"Partido {p.id} no marcado (jugado/cancelado). Tasks borradas."

            cant_local = p.equipo_local.count()
            cant_visitante = p.equipo_visitante.count()

            if cant_local > 0 and cant_visitante > 0:
                p.jugando = True
                p.save(update_fields=["jugando"])
                return (
                    f"Partido {p.id} marcado como 'jugando'. "
                    f"Local={cant_local}, Visitante={cant_visitante}"
                )
            else:
                p.cancelado = True
                p.jugando = False
                p.jugado = False
                p.save(update_fields=["cancelado", "jugando", "jugado"])

                from .services import borrar_tasks_partido
                transaction.on_commit(lambda: borrar_tasks_partido(p))
                transaction.on_commit(
                    lambda: notificar_cancelacion_amistoso(p, cant_local, cant_visitante)
                )

                return (
                    f"Partido {p.id} cancelado automáticamente "
                    f"(Local={cant_local}, Visitante={cant_visitante}). "
                    f"Tasks borradas y notificaciones enviadas."
                )

    except PartidoAmistoso.DoesNotExist:
        return f"Partido {partido_id} no existe."
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def marcar_partido_finalizado(self, partido_id: int):
    try:
        with transaction.atomic():
            p = PartidoAmistoso.objects.select_for_update().get(id=partido_id)

            if p.cancelado or p.jugado:
                from .services import borrar_tasks_partido
                transaction.on_commit(lambda: borrar_tasks_partido(p))
                return f"Partido {p.id} no finaliza (cancelado o ya jugado). Tasks borradas."

            p.jugando = False
            p.jugado = True
            p.save(update_fields=["jugando", "jugado"])

            from .services import borrar_tasks_partido
            transaction.on_commit(lambda: borrar_tasks_partido(p))

            return f"Partido {p.id} marcado como finalizado. Tasks borradas."

    except PartidoAmistoso.DoesNotExist:
        return f"Partido {partido_id} no existe."
    except Exception as exc:
        raise self.retry(exc=exc)


def notificar_cancelacion_amistoso(partido, cant_local, cant_visitante):
    mensaje = (
        f"El partido amistoso #{partido.id} fue cancelado automáticamente , "
        f"Procure hacer equipos antes de la hora de inicio."
    )

    for jugador in partido.equipo_local.all():
        if getattr(jugador, "user", None):
            Notificacion.objects.create(
                usuario=jugador.user,
                mensaje=mensaje,
                tipo="partido_cancelado",
                extra_id=partido.id,
            )

    for jugador in partido.equipo_visitante.all():
        if getattr(jugador, "user", None):
            Notificacion.objects.create(
                usuario=jugador.user,
                mensaje=mensaje,
                tipo="partido_cancelado",
                extra_id=partido.id,
            )

    if hasattr(partido, "creador") and partido.creador:
        Notificacion.objects.create(
            usuario=partido.creador,
            mensaje=mensaje,
            tipo="partido_cancelado",
            extra_id=partido.id,
        )


# ========== TORNEO: comenzar_partido ==========

@shared_task(bind=True, max_retries=3)
def comenzar_partido(self, partido_id: int):
    """
    Task que se ejecuta cuando llega la fecha/hora programada.
    Pone el partido EN_CURSO, marca jugando=True, jugado=False
    y setea inicio_datetime = ahora.
    """
    try:
        partido = Partido.objects.get(pk=partido_id)
    except Partido.DoesNotExist:
        return f"Partido {partido_id} no existe"

    if partido.cancelado or partido.estado in [
        Partido.CANCELADO,
        Partido.FINALIZADO,
        Partido.SUSPENDIDO,
    ]:
        return f"Partido {partido_id} está en estado {partido.estado}, no se activa."

    ahora = timezone.now()

    partido.estado = Partido.EN_CURSO
    partido.jugando = True
    partido.jugado = False
    partido.inicio_datetime = ahora
    partido.save(update_fields=["estado", "jugando", "jugado", "inicio_datetime"])

    return f"Partido {partido_id} puesto EN_CURSO a las {ahora.isoformat()}"


@shared_task
def finalizar_partido(partido_id):
    from app_torneo_f5.models import Partido
    partido = Partido.objects.get(id=partido_id)
    partido.estado = Partido.FINALIZADO
    partido.save()
    return f"Partido {partido_id} marcado como FINALIZADO"