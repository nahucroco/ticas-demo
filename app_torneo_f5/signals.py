from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model
from django.apps import apps
from .services import avanzar_copas

from .models import (
    Partido, PartidoAmistoso, Propuesta,
    Jugador, PerfilUsuario,
    MiembroEquipo,
    ParticipacionEquipoTorneo,
    ParticipacionJugadorTorneo,   
    EstadisticasJugadorPartido,
    EstadisticaAmistosa,
    EstadisticaJugador,
    Torneo,
    EstadisticasEquipoPartido
)

FINISHED_STATES = (
    Partido.FINALIZADO,
    Partido.EN_PENALES,
    Partido.TIEMPO_EXTRA,
)

@receiver(post_save, sender=Partido)
def actualizar_estadisticas_al_guardar_partido(sender, instance: Partido, created, **kwargs):
    # 1) Evitar correr al crear (fixture/seed)
    if created:
        return

    # 2) Equipos presentes
    local = getattr(instance, "equipo_local", None) or getattr(instance, "equipo_1", None)
    visi  = getattr(instance, "equipo_visitante", None) or getattr(instance, "equipo_2", None)
    if not local or not visi:
        return

    # 3) Solo si son PET (tu modelo nuevo)
    if not isinstance(local, ParticipacionEquipoTorneo) or not isinstance(visi, ParticipacionEquipoTorneo):
        return

    # 4) Goles válidos (y opcionalmente, partido cerrado)
    gl = getattr(instance, "goles_local", None)
    gv = getattr(instance, "goles_visitante", None)
    if gl is None or gv is None:
        return

    # Opcional: solo cuando esté finalizado
    # if instance.estado not in (Partido.FINALIZADO, Partido.EN_PENALES, Partido.TIEMPO_EXTRA):
    #     return

    # 5) Determinar ganador
    nuevo_ganador = None
    if gl > gv:
        nuevo_ganador = local
    elif gv > gl:
        nuevo_ganador = visi

    # 6) Actualizar sin disparar signals (evita recursión)
    #    Solo si cambió el valor
    if instance.equipo_ganador_id != (nuevo_ganador.id if nuevo_ganador else None):
        Partido.objects.filter(pk=instance.pk).update(
            equipo_ganador=nuevo_ganador
        )

@receiver(post_save, sender=PartidoAmistoso)
def actualizar_estadisticas_al_guardar_amistoso(sender, instance, **kwargs):
    jugadores = Jugador.objects.filter(
        estadisticas_amistosas__partido=instance,
        estadisticas_amistosas__jugo=True
    ).distinct()

    for jugador in jugadores:
        stats = EstadisticaAmistosa.objects.filter(jugador=jugador, jugo=True)

        jugador.goles = stats.aggregate(Sum('goles'))['goles__sum'] or 0
        jugador.asistencias = stats.aggregate(Sum('asistencias'))['asistencias__sum'] or 0
        jugador.atajadas = stats.aggregate(Sum('atajadas'))['atajadas__sum'] or 0
        jugador.partidos_jugados = (
            EstadisticaJugador.objects.filter(jugador=jugador, jugo=True).values('partido').distinct().count()
            +
            EstadisticaAmistosa.objects.filter(jugador=jugador, jugo=True).values('partido').distinct().count()
        )

        jugador.save()

User = get_user_model()

@receiver(post_save, sender=EstadisticaAmistosa)
def actualizar_estadisticas_jugador_amistoso(sender, instance, **kwargs):
    jugador = instance.jugador
    if not jugador:
        return

    stats_amistosas = EstadisticaAmistosa.objects.filter(jugador=jugador, jugo=True)
    stats_torneos = EstadisticaJugador.objects.filter(jugador=jugador, jugo=True)

    goles_amistosos = stats_amistosas.aggregate(Sum('goles'))['goles__sum'] or 0
    goles_torneo = stats_torneos.aggregate(Sum('goles'))['goles__sum'] or 0

    jugador.goles = goles_amistosos + goles_torneo
    jugador.partidos_jugados = (
        stats_amistosas.values('partido').distinct().count()
        + stats_torneos.values('partido').distinct().count()
    )

    jugador.save()
    
User = get_user_model()

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    try:
        instance.perfilusuario.save()
    except PerfilUsuario.DoesNotExist:
        pass

@receiver(post_save, sender=Partido)
def ensure_propuesta_for_partido(sender, instance: Partido, created, **kwargs):
    """
    Antes chequeaba instance.fase.tipo == 'ELIMINATORIA'.
    Ahora:
      - Si es placeholder (sin equipos) y estado INDEFINIDO => NO hacemos nada.
      - Si el torneo no usa PROPUESTA => NO hacemos nada.
      - Si el modelo Propuesta no existe (lo tenés comentado) => NO hacemos nada.
      - Caso contrario, podés mantener tu lógica de crear Propuesta.
    """
    # 1) Placeholders de seed (sin equipos, estado INDEFINIDO): ignorar
    if (instance.estado == Partido.INDEFINIDO and
        not instance.equipo_local_id and
        not instance.equipo_visitante_id):
        return

    # 2) Si el torneo no usa propuestas, no hagas nada
    if instance.torneo.modo_seleccion_partido != Torneo.PROPUESTA:
        return

    # 3) Intentar cargar el modelo Propuesta solo si existe
    try:
        Propuesta = apps.get_model('app_torneo_f5', 'Propuesta')
    except LookupError:
        # No existe el modelo Propuesta (está comentado) => salir silenciosamente
        return

    # 4) (Opcional) Si querés limitar a copas:
    # if instance.etapa not in (Partido.COPAORO, Partido.COPAPLATA):
    #     return

    # 5) Si no hay propuesta, crear una mínima (ajustá defaults si tu modelo los exige)
    Propuesta.objects.get_or_create(partido=instance)

        
        
def _get_or_create_pjt_from_stat(stat: EstadisticasJugadorPartido):
    t = stat.partido.torneo
    j = stat.miembro_equipo.jugador
    pjt, _ = ParticipacionJugadorTorneo.objects.get_or_create(
        torneo=t,
        jugador=j,
        defaults={'miembro_equipo': stat.miembro_equipo}
    )
    # Intentamos setear equipo_torneo y grupo si no estaban
    if not pjt.equipo_torneo_id:
        pet = ParticipacionEquipoTorneo.objects.filter(
            torneo=t, equipo=stat.miembro_equipo.equipo
        ).first()
        if pet:
            pjt.equipo_torneo = pet
            pjt.grupo = pet.grupo
            pjt.save(update_fields=['equipo_torneo', 'grupo'])
    return pjt


@receiver(post_save, sender=EstadisticasJugadorPartido)
def actualizar_pjt_on_save(sender, instance, **kwargs):
    pjt = _get_or_create_pjt_from_stat(instance)
    pjt.recompute_from_partidos().save(update_fields=[
        'pj', 'goles', 'asistencias', 'atajadas', 'tiros_arco',
        'tarjetas_amarillas', 'tarjetas_rojas', 'faltas_cometidas',  # <- CORREGIDO
        'prom_goles', 'prom_asistencias', 'prom_atajadas',
        'equipo_torneo', 'grupo', 'updated_at'
    ])


@receiver(post_delete, sender=EstadisticasJugadorPartido)
def actualizar_pjt_on_delete(sender, instance, **kwargs):
    pjt = _get_or_create_pjt_from_stat(instance)
    pjt.recompute_from_partidos().save(update_fields=[
        'pj', 'goles', 'asistencias', 'atajadas', 'tiros_arco',
        'tarjetas_amarillas', 'tarjetas_rojas', 'faltas_cometidas',  # <- CORREGIDO
        'prom_goles', 'prom_asistencias', 'prom_atajadas',
        'equipo_torneo', 'grupo', 'updated_at'
    ])

    
# ---------- Helpers ----------
def _ensure_pjt(torneo, pet: ParticipacionEquipoTorneo, miembro: MiembroEquipo):
    """
    Crea/asegura la ficha ParticipacionJugadorTorneo para (torneo, jugador).
    Sincroniza miembro_equipo, equipo_torneo y grupo.
    """
    pjt, _ = ParticipacionJugadorTorneo.objects.get_or_create(
        torneo=torneo,
        jugador=miembro.jugador,
        defaults={
            'miembro_equipo': miembro,
            'equipo_torneo': pet,
            'grupo': pet.grupo,
        }
    )
    changed = False
    if pjt.miembro_equipo_id != miembro.id:
        pjt.miembro_equipo = miembro; changed = True
    if pjt.equipo_torneo_id != pet.id:
        pjt.equipo_torneo = pet; changed = True
    if pjt.grupo != pet.grupo:
        pjt.grupo = pet.grupo; changed = True
    if changed:
        pjt.save(update_fields=['miembro_equipo', 'equipo_torneo', 'grupo'])
    return pjt


# ---------- Crear PJT cuando se crea una PET ----------
@receiver(post_save, sender=ParticipacionEquipoTorneo)
def crear_pjt_al_crear_pet(sender, instance: ParticipacionEquipoTorneo, created, **kwargs):
    """
    Cuando un equipo entra a un torneo (PET), crear/sincronizar PJT para todos los miembros del equipo.
    También actualiza el grupo si cambia.
    """
    pet = instance
    torneo = pet.torneo
    for miembro in pet.equipo.miembroequipo_set.all():
        _ensure_pjt(torneo, pet, miembro)


# ---------- Crear PJT cuando se crea un MiembroEquipo ----------
@receiver(post_save, sender=MiembroEquipo)
def crear_pjt_al_crear_miembro(sender, instance: MiembroEquipo, created, **kwargs):
    """
    Cuando un jugador se suma a un equipo, crear/sincronizar PJT para cada torneo donde participa ese equipo.
    """
    miembro = instance
    # Todas las PET (torneos) del equipo de ese miembro
    pets = miembro.equipo.participacionequipotorneo_set.select_related('torneo', 'equipo')
    for pet in pets:
        _ensure_pjt(pet.torneo, pet, miembro)


# ---------- Cruces por defecto (Oro/Plata) ----------

@receiver([post_save, post_delete], sender=EstadisticasJugadorPartido)
def _on_change_stats_jugador(sender, instance, **kwargs):
    avanzar_copas(instance.partido.torneo)

@receiver([post_save, post_delete], sender=EstadisticasEquipoPartido)
def _on_change_stats_equipo(sender, instance, **kwargs):
    avanzar_copas(instance.partido.torneo)