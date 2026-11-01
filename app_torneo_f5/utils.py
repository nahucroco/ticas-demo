from django.db.models import Q
from .models import Partido, Torneo, Participacion
# utils.py
from .models import Jugador
from django.core.files.base import ContentFile
import requests
import os


def actualizar_estadisticas_equipo(equipo):
    # Obtener todos los torneos donde jugó ese equipo (como local o visitante)
    torneos = set(
        Partido.objects.filter(Q(equipo_1=equipo) | Q(equipo_2=equipo))
        .values_list('torneo_id', flat=True)
    )

    for torneo_id in torneos:
        try:
            torneo = Torneo.objects.get(id=torneo_id)
        except Torneo.DoesNotExist:
            continue  # Si por algún motivo el torneo no existe, lo salteamos

        # Obtener o crear la participación de ese equipo en ese torneo
        participacion, _ = Participacion.objects.get_or_create(
            equipo=equipo,
            torneo=torneo
        )

        # Filtrar los partidos jugados por ese equipo en ese torneo
        partidos = Partido.objects.filter(
            torneo=torneo,
            jugado=True
        ).filter(Q(equipo_1=equipo) | Q(equipo_2=equipo))

        # Inicializar estadísticas
        pj = partidos.count()
        pg = pe = pp = gf = gc = 0

        for partido in partidos:
            if partido.equipo_1 == equipo:
                goles_favor = partido.goles_equipo_1 or 0
                goles_contra = partido.goles_equipo_2 or 0
            else:
                goles_favor = partido.goles_equipo_2 or 0
                goles_contra = partido.goles_equipo_1 or 0

            gf += goles_favor
            gc += goles_contra

            if goles_favor > goles_contra:
                pg += 1
            elif goles_favor == goles_contra:
                pe += 1
            else:
                pp += 1

        puntos = pg * 3 + pe
        diferencia = gf - gc

        # Guardar estadísticas
        participacion.pj = pj
        participacion.pg = pg
        participacion.pe = pe
        participacion.pp = pp
        participacion.gf = gf
        participacion.gc = gc
        participacion.dif = diferencia
        participacion.puntos = puntos
        participacion.save()



from .models import Jugador
from django.core.files.base import ContentFile
import requests
import os

def crear_jugador_con_datos(user, full_name=None, picture_url=None):
    if Jugador.objects.filter(user=user).exists():
        return None  # Ya existe

    foto_content = None
    if picture_url:
        try:
            response_foto = requests.get(picture_url)
            if response_foto.status_code == 200:
                extension = os.path.splitext(picture_url)[-1] or '.jpg'
                nombre_archivo = f"{user.username}_foto{extension}"
                foto_content = ContentFile(response_foto.content, name=nombre_archivo)
        except Exception as e:
            print("❌ Error al descargar la imagen:", e)

    jugador = Jugador.objects.create(
        user=user,
        nombre=f"{user.first_name} {user.last_name}".strip() or user.username,
        edad=0,
        altura=None,
        pie_preferido=None,
        posicion_preferida=None,
        genero='otro',
        fortalezas=None,
        debilidades=None,
        mundiales_ganados=0,
        horario_disponible='No definido',
        ciudad=None,
        contacto=user.email,
        partidos_jugados=0,
        goles_totales=0,
        goles_promedio=0,
        asistencias_totales=0,
        asistencias_promedio=0,
        atajadas_totales=0,
        atajadas_promedio=0,
        participaciones_gol=0,
        ultimos_partidos='Sin registro'
    )
    return jugador


RONDA_LABEL = {
    Partido.CUARTOS: "Cuartos",
    Partido.SEMIFINAL: "Semis",
    Partido.FINAL: "Final",
}

def get_etapa_activa_label(torneo):
    # 1) ¿Sigue activa la fase de grupos/ligas (ZONAS)?
    zonas_pend = Partido.objects.filter(
        torneo=torneo, etapa=Partido.ZONAS, jugado=False, cancelado=False
    )
    if zonas_pend.exists():
        total = (
            Partido.objects.filter(torneo=torneo, etapa=Partido.ZONAS)
            .values_list("fecha", flat=True)
            .distinct()
            .count()
        ) or 0
        actual = zonas_pend.order_by("fecha").values_list("fecha", flat=True).first() or 1
        return f"Fecha {actual} ({total})"

    # 2) Si no hay ZONAS, mostrar la primera copa pendiente (prioridad Oro, luego Plata)
    for etapa, nombre in ((Partido.COPAORO, "Copa Oro"), (Partido.COPAPLATA, "Copa Plata")):
        for ronda in (Partido.CUARTOS, Partido.SEMIFINAL, Partido.FINAL):
            if Partido.objects.filter(
                torneo=torneo, etapa=etapa, ronda=ronda, jugado=False, cancelado=False
            ).exists():
                return f"{nombre} – {RONDA_LABEL[ronda]}"

    # 3) Nada pendiente
    if Partido.objects.filter(torneo=torneo).exists():
        return "Finalizado"
    return "A definir"