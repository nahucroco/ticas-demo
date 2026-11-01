# app_torneo_f5/services.py
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django_celery_beat.models import ClockedSchedule, PeriodicTask
import logging

log = logging.getLogger(__name__)

def _clocked_for(dt_aware):
    # dt_aware debe venir aware en TZ de Django; beat lo guarda en UTC
    return ClockedSchedule.objects.get_or_create(clocked_time=dt_aware)[0]

def _name_with_pk_or_uuid(prefix, partido):
    uid = getattr(partido, "uuid", None)
    return f"{prefix}_{uid}" if uid else f"{prefix}_pk{partido.id}"

def programar_inicio_partido(partido):
    if not partido.dia or not partido.hora_inicio or not (partido.duracion or 0) > 0:
        borrar_tasks_partido(partido)
        return

    tz = timezone.get_current_timezone()
    inicio_local = datetime.combine(partido.dia, partido.hora_inicio)
    inicio_aware = timezone.make_aware(inicio_local, tz)
    fin_aware    = inicio_aware + timedelta(minutes=int(partido.duracion or 0))

    start_name = _name_with_pk_or_uuid("marcar_jugando", partido)
    end_name   = _name_with_pk_or_uuid("finalizar", partido)

    # 🔥 borrar por nombre y por args (por si quedó basura con convención vieja)
    PeriodicTask.objects.filter(name__in=[start_name, end_name]).delete()
    PeriodicTask.objects.filter(args__contains=f"[{partido.id}]").delete()

    # Log de control (aparece en worker/beat)
    log.info("Reprogramando partido %s: inicio %s / fin %s (TZ=%s)",
             partido.id, inicio_aware, fin_aware, tz)

    # INICIO
    if inicio_aware <= timezone.now():
        from app_torneo_f5.tasks import marcar_partido_jugando
        marcar_partido_jugando.delay(partido.id)
    else:
        PeriodicTask.objects.create(
            name=start_name,
            task="app_torneo_f5.tasks.marcar_partido_jugando",
            args=json.dumps([partido.id]),
            clocked=_clocked_for(inicio_aware),
            one_off=True,
            enabled=True,
        )

    # FIN
    if fin_aware <= timezone.now():
        from app_torneo_f5.tasks import marcar_partido_finalizado
        marcar_partido_finalizado.delay(partido.id)
    else:
        PeriodicTask.objects.create(
            name=end_name,
            task="app_torneo_f5.tasks.marcar_partido_finalizado",
            args=json.dumps([partido.id]),
            clocked=_clocked_for(fin_aware),
            one_off=True,
            enabled=True,
        )

def borrar_tasks_partido(partido):
    nombres = [
        _name_with_pk_or_uuid("marcar_jugando", partido),
        _name_with_pk_or_uuid("finalizar", partido),

        # si alguna vez usaste otros prefijos, dejá estos para limpieza:
        _name_with_pk_or_uuid("primer_tiempo_fin", partido),
        _name_with_pk_or_uuid("segundo_tiempo_fin", partido),
        _name_with_pk_or_uuid("half_start", partido),
        _name_with_pk_or_uuid("half_end", partido),
    ]
    PeriodicTask.objects.filter(name__in=nombres).delete()
    # Fallback: por args (si quedaron tareas con convención distinta)
    PeriodicTask.objects.filter(args__contains=f"[{partido.id}]").delete()


# app_torneo_f5/services/avances_copas.py

from typing import List, Tuple
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from app_torneo_f5.models import (
    Torneo, Partido, ParticipacionEquipoTorneo as PET,
    EstadisticasJugadorPartido, EstadisticasEquipoPartido
)

# =============== NUEVO: detección de "stats completas" por partido ===============

def _stats_completas_por_partido(m: Partido) -> bool:
    """
    Consideramos "stats completas" cuando:
      - Hay equipos asignados, y
      - Modo POR_EQUIPO: existen 2 filas en EstadisticasEquipoPartido (una por cada PET del match), o
      - Modo POR_PARTIDO: existe al menos una estadística con jugo=True para algún jugador del local
        y al menos una para algún jugador del visitante.
    """
    if not (m.equipo_local_id and m.equipo_visitante_id):
        return False

    modo = getattr(m.torneo, 'modo_registro_estadisticas', Torneo.POR_PARTIDO)

    if modo == Torneo.POR_EQUIPO:
        equipos_qs = EstadisticasEquipoPartido.objects.filter(
            partido=m, equipo__in=[m.equipo_local, m.equipo_visitante]
        )
        return equipos_qs.count() == 2

    # POR_PARTIDO (default)
    # Al menos una estadística de alguien que jugó del local y una del visitante
    local_ok = EstadisticasJugadorPartido.objects.filter(
        partido=m, jugo=True, miembro_equipo__equipo=m.equipo_local.equipo
    ).exists()
    visit_ok = EstadisticasJugadorPartido.objects.filter(
        partido=m, jugo=True, miembro_equipo__equipo=m.equipo_visitante.equipo
    ).exists()
    return local_ok and visit_ok


def _recalcular_desde_stats_si_corresponde(m: Partido) -> bool:
    """
    Si el partido tiene stats completas, recalcula goles/ganador desde las estadísticas.
    Devuelve True si recalculó (o sea, si las stats estaban completas).
    """
    if not _stats_completas_por_partido(m):
        return False

    # Recalcular desde las stats (tu método ya lo hace)
    m.actualizar_resultado()

    # Sellamos estado (opcional pero recomendado para dejarlo coherente)
    if m.estado != Partido.FINALIZADO:
        m.estado = Partido.FINALIZADO
    if not m.jugado:
        m.jugado = True
    m.save(update_fields=['estado', 'jugado', 'goles_local', 'goles_visitante', 'equipo_ganador'])
    return True


def _zonas_con_stats_completas(torneo: Torneo) -> bool:
    """
    True si TODOS los partidos de ZONAS del torneo tienen stats completas (según reglas de arriba).
    """
    partidos = Partido.objects.filter(torneo=torneo, etapa=Partido.ZONAS)

    # Atajo: si no hay partidos, no está completo
    if not partidos.exists():
        return False

    for m in partidos.select_related('equipo_local__equipo', 'equipo_visitante__equipo', 'torneo'):
        if not _stats_completas_por_partido(m):
            return False
    return True


def _recalcular_todos_los_partidos_de_zonas(torneo: Torneo) -> None:
    """
    Recorre todos los partidos de ZONAS y, si tienen stats completas, recalcula resultado.
    (No obliga a que estén TODOS completos; sólo recalcula los que ya lo están.)
    """
    for m in (Partido.objects
              .filter(torneo=torneo, etapa=Partido.ZONAS)
              .select_related('equipo_local__equipo', 'equipo_visitante__equipo', 'torneo')):
        _recalcular_desde_stats_si_corresponde(m)

# ========================= Helpers previos (sin cambios funcionales fuertes) =========================

def _orden_por_posicion(o: List[PET]) -> List[PET]:
    if o and all(p.posicion for p in o):
        return sorted(o, key=lambda p: p.posicion)
    return sorted(
        o,
        key=lambda p: (-(p.puntos or 0), -(p.dif or 0), -(p.gf or 0), -(p.pg or 0))
    )

def _tabla_por_zona(torneo: Torneo, zona: str) -> List[PET]:
    return _orden_por_posicion(
        list(PET.objects.select_related('equipo').filter(torneo=torneo, zona=zona))
    )

def _qf_oro(torneo: Torneo) -> List[Partido]:
    return list(Partido.objects.filter(
        torneo=torneo, etapa=Partido.COPAORO, ronda=Partido.CUARTOS
    ).order_by('fecha', 'id'))

def _qf_plata(torneo: Torneo) -> List[Partido]:
    return list(Partido.objects.filter(
        torneo=torneo, etapa=Partido.COPAPLATA, ronda=Partido.CUARTOS
    ).order_by('fecha', 'id'))

def _set_etiqueta(pet: PET, etiqueta: str):
    if pet.etiqueta != etiqueta:
        pet.etiqueta = etiqueta
        pet.save(update_fields=['etiqueta'])

def _asegurar_indefinido_si_faltan_equipos(m: Partido):
    if not (m.equipo_local_id and m.equipo_visitante_id):
        if m.estado != Partido.INDEFINIDO:
            m.estado = Partido.INDEFINIDO
            m.save(update_fields=['estado'])

# ========================= Siembra (igual que antes, pero exige stats completas) =========================

@transaction.atomic
def sembrar_copas_desde_zonas(torneo: Torneo) -> dict:
    """
    - Requiere que ZONAS esté COMPLETA EN STATS.
    - Antes de sembrar, recalcula todos los resultados de ZONAS desde stats.
    """
    _recalcular_todos_los_partidos_de_zonas(torneo)
    if not _zonas_con_stats_completas(torneo):
        return {'ok': False, 'msg': 'La fase de ZONAS aún no tiene todas las estadísticas cargadas.'}

    tabla_A = _tabla_por_zona(torneo, PET.A)
    tabla_B = _tabla_por_zona(torneo, PET.B)
    if len(tabla_A) < 6 or len(tabla_B) < 6:
        return {'ok': False, 'msg': 'Faltan equipos en alguna zona para sembrar Oro/Plata.'}

    # QF Oro: A1-B4, A2-B3, B1-A4, B2-A3
    semillas_oro: List[Tuple[PET, str]] = [
        (tabla_A[0], 'C1'), (tabla_B[3], 'C2'),
        (tabla_A[1], 'C3'), (tabla_B[2], 'C4'),
        (tabla_B[0], 'C5'), (tabla_A[3], 'C6'),
        (tabla_B[1], 'C7'), (tabla_A[2], 'C8'),
    ]
    qf_oro = _qf_oro(torneo)
    if len(qf_oro) != 4:
        return {'ok': False, 'msg': 'Se esperaban 4 partidos de Cuartos de Copa Oro.'}

    for i, match in enumerate(qf_oro):
        local_pet, local_tag = semillas_oro[2*i]
        visit_pet, visit_tag = semillas_oro[2*i + 1]
        cambio = False
        if not match.equipo_local_id:
            match.equipo_local = local_pet
            cambio = True
        if not match.equipo_visitante_id:
            match.equipo_visitante = visit_pet
            cambio = True
        if cambio:
            match.save(update_fields=['equipo_local', 'equipo_visitante'])
        _set_etiqueta(local_pet, local_tag)
        _set_etiqueta(visit_pet, visit_tag)

    # QF Plata (pre-siembra locales): A5, A6, B5, B6
    semillas_plata_locales: List[Tuple[PET, str]] = [
        (tabla_A[4], 'C1'), (tabla_A[5], 'C2'),
        (tabla_B[4], 'C3'), (tabla_B[5], 'C4'),
    ]
    qf_plata = _qf_plata(torneo)
    if len(qf_plata) != 4:
        return {'ok': False, 'msg': 'Se esperaban 4 partidos de Cuartos de Copa Plata.'}

    for i, match in enumerate(qf_plata):
        local_pet, local_tag = semillas_plata_locales[i]
        if not match.equipo_local_id:
            match.equipo_local = local_pet
            match.save(update_fields=['equipo_local'])
        _set_etiqueta(local_pet, local_tag)
        _asegurar_indefinido_si_faltan_equipos(match)

    # Puestos 7+8 fuera de competencia
    for pet in tabla_A[6:] + tabla_B[6:]:
        if pet.sigue_en_competencia:
            pet.sigue_en_competencia = False
            pet.save(update_fields=['sigue_en_competencia'])

    return {'ok': True, 'msg': 'Siembra inicial de Oro y Plata realizada con estadísticas cerradas.'}

# ========================= Bajada de perdedores (se mantiene, pero asegura resultado por stats) =========================

@transaction.atomic
def completar_plata_con_perdedores_de_oro(torneo: Torneo) -> dict:
    """
    Para cada QF de Oro, si las estadísticas del partido están completas,
    recalcula resultado (si faltaba) y baja el perdedor al QF de Plata correspondiente.
    """
    qf_oro = _qf_oro(torneo)
    qf_plata = _qf_plata(torneo)
    if len(qf_oro) != 4 or len(qf_plata) != 4:
        return {'ok': False, 'msg': 'Se requieren 4 QF de Oro y 4 QF de Plata.'}

    etiquetas_bajan = ['C5', 'C6', 'C7', 'C8']
    cambios = 0

    for idx in range(4):
        m_oro: Partido = qf_oro[idx]
        m_plata: Partido = qf_plata[idx]

        # Asegurar resultado desde stats si ya están completas
        _recalcular_desde_stats_si_corresponde(m_oro)

        ganador = m_oro.equipo_ganador
        if not ganador:
            # Aún no definido (pudo quedar empate en oro si no cargaron penales/definición)
            continue

        # Perdedor = el otro
        if m_oro.equipo_local_id == ganador.id:
            perdedor = m_oro.equipo_visitante
        else:
            perdedor = m_oro.equipo_local
        if not perdedor:
            continue

        # Asignar como visitante en QF Plata correspondiente
        if not m_plata.equipo_visitante_id:
            m_plata.equipo_visitante = perdedor
            m_plata.save(update_fields=['equipo_visitante'])
            _asegurar_indefinido_si_faltan_equipos(m_plata)
            _set_etiqueta(perdedor, etiquetas_bajan[idx])
            cambios += 1

        if not perdedor.sigue_en_competencia:
            perdedor.sigue_en_competencia = True
            perdedor.save(update_fields=['sigue_en_competencia'])

    return {'ok': True, 'msg': f'Perdedores bajados a Plata: {cambios} asignaciones.'}

# ========================= Orquestador =========================

def avanzar_copas(torneo: Torneo) -> dict:
    """
    1) Recalcula resultados de ZONAS desde stats (lo que esté listo).
    2) Si TODAS las ZONAS tienen stats completas, siembra Oro/Plata.
    3) Intenta bajar perdedores de QF Oro a QF Plata, recalculando desde stats.
    """
    _recalcular_todos_los_partidos_de_zonas(torneo)
    res1 = {}
    if _zonas_con_stats_completas(torneo):
        res1 = sembrar_copas_desde_zonas(torneo)
    res2 = completar_plata_con_perdedores_de_oro(torneo)
    return {'siembra': res1, 'bajada_oro_a_plata': res2}
