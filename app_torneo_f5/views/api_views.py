from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from collections import defaultdict
from datetime import date
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from app_torneo_f5.serializers.estadisticas_serializers import CargaEstadisticasPartidoSerializer
from app_torneo_f5.serializers.partido_serializers import (
    MostrarPartidoPorIDSerializer,
    TorneoDePartidoSerializer
)

from app_torneo_f5.models import (
    Partido,
    EstadisticasJugadorPartido,
    EstadisticasEquipoPartido,
    ParticipacionEquipoTorneo,
    Cancha,
    TipoCancha,
    Torneo
)

import json


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cargar_estadisticas_partido_api(request):
    serializer = CargaEstadisticasPartidoSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        partido_id = data["partido_id"]
        jugadores_stats = data["jugadores_stats"]

        try:
            partido = Partido.objects.get(id=partido_id)
        except Partido.DoesNotExist:
            return Response({"error": "Partido no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Actualiza estadísticas del partido
        partido.goles_local = data["goles_local"]
        partido.goles_visitante = data["goles_visitante"]
        partido.save()

        # Guarda posesión para cada equipo
        EstadisticasEquipoPartido.objects.update_or_create(
            partido=partido, equipo=partido.equipo_local,
            defaults={"posesion": data["posesion_local"]}
        )
        EstadisticasEquipoPartido.objects.update_or_create(
            partido=partido, equipo=partido.equipo_visitante,
            defaults={"posesion": data["posesion_visitante"]}
        )

        # Carga estadísticas de jugadores
        for jugador_data in jugadores_stats:
            EstadisticasJugadorPartido.objects.update_or_create(
                partido=partido,
                jugador_id=jugador_data["jugador_id"],
                defaults={
                    "goles": jugador_data["goles"],
                    "asistencias": jugador_data["asistencias"],
                    "atajadas": jugador_data["atajadas"],
                    "faltas_cometidas": jugador_data["faltas_cometidas"],
                    "faltas_recibidas": jugador_data["faltas_recibidas"],
                    "tarjeta_amarilla": jugador_data["tarjeta_amarilla"],
                    "tarjeta_roja": jugador_data["tarjeta_roja"],
                    "jugo": jugador_data["jugo"],
                }
            )

        # (Opcional) Actualizar ParticipacionEquipoTorneo, si corresponde
        # ...

        return Response({"mensaje": "Estadísticas cargadas correctamente."}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

import traceback
@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_partido_por_id(request, partido_id):
    try:
        partido = (
            Partido.objects
            .select_related(
                'cancha', 'tipo_cancha', 'torneo'
            )
            .get(pk=partido_id)
        )
    except Exception as e:
        print("❌ ERROR en obtener_partido_por_id:", e)
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = MostrarPartidoPorIDSerializer(partido)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ------------------------------------------------------------
# 2️⃣  Actualizar configuración del partido
# ------------------------------------------------------------
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def configurar_partido_api(request, partido_id):
    try:
        partido = Partido.objects.get(id=partido_id)
    except Partido.DoesNotExist:
        return Response({'error': 'Partido no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not partido.torneo.encargados_carga.filter(id=user.id).exists():
        return Response({'error': 'No tenés permisos para modificar este partido.'}, status=status.HTTP_403_FORBIDDEN)

    cancha_id   = request.data.get('cancha')
    ubicacion   = request.data.get('ubicacion')
    dia         = request.data.get('dia')
    hora_inicio = request.data.get('hora_inicio')
    # ⛔ ya no usamos duracion del request
    # duracion    = request.data.get('duracion')

    if not all([cancha_id, dia, hora_inicio]):
        return Response({'error': 'Faltan campos obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        cancha = Cancha.objects.get(id=cancha_id)
    except Cancha.DoesNotExist:
        return Response({'error': 'Cancha no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    partido.cancha = cancha
    # ✅ Usar ubicación proporcionada o la de la cancha
    partido.ubicacion  = ubicacion or cancha.ubicacion or cancha.direccion or ""
    partido.dia        = dia
    partido.hora_inicio = hora_inicio

    # ✅ FORZAR siempre a 60 minutos
    partido.duracion = 60

    partido.save()

    return Response({'mensaje': 'Partido configurado correctamente.'}, status=status.HTTP_200_OK)



# ------------------------------------------------------------
# 3️⃣  Listar todas las canchas (para el select del frontend)
# ------------------------------------------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def listar_canchas_api(request):
    canchas = Cancha.objects.all().values('id', 'nombre', 'direccion')
    return Response(list(canchas), status=status.HTTP_200_OK)


# ------------------------------------------------------------
# 4️⃣  Obtener una cancha por ID (para mostrar ubicación)
# ------------------------------------------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_cancha_api(request, cancha_id):
    try:
        cancha = Cancha.objects.prefetch_related('tipo_cancha').get(id=cancha_id)
    except Cancha.DoesNotExist:
        return Response({'error': 'Cancha no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        data = {
            'id': cancha.id,
            'nombre': cancha.nombre,
            'direccion': cancha.direccion or "",
            'ubicacion': cancha.ubicacion or "",
            'tipos_cancha': list(cancha.tipo_cancha.values('id', 'nombre'))  # ManyToMany
        }
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print("❌ Error en obtener_cancha_api:", traceback.format_exc())
        return Response({'error': f'Error interno: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# ------------------------------------------------------------
# Crear una nueva cancha
# ------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_cancha_api(request):
    """
    Permite crear una nueva cancha manualmente desde el frontend.
    """
    nombre = request.data.get("nombre")
    direccion = request.data.get("direccion")
    ubicacion = request.data.get("ubicacion")

    if not nombre:
        return Response({'error': 'El nombre es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

    # Usar ubicación si no hay dirección
    direccion_final = direccion or ubicacion or ""

    cancha, creada = Cancha.objects.get_or_create(
        nombre=nombre, 
        defaults={
            'direccion': direccion_final,
            'ubicacion': ubicacion or direccion_final
        }
    )

    if not creada:
        # Si ya existe, actualizamos dirección/ubicación si estaban vacías
        if not cancha.direccion and direccion_final:
            cancha.direccion = direccion_final
        if not cancha.ubicacion and (ubicacion or direccion_final):
            cancha.ubicacion = ubicacion or direccion_final
        cancha.save()

    return Response({
        'id': cancha.id,
        'nombre': cancha.nombre,
        'direccion': cancha.direccion or "",
        'ubicacion': cancha.ubicacion or "",
        'nueva': creada
    }, status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_torneo_por_id(request, torneo_id):
    try:
        torneo = Torneo.objects.get(pk=torneo_id)
    except Torneo.DoesNotExist:
        return Response({'error': 'Torneo no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    serializer = TorneoDePartidoSerializer(torneo)
    return Response(serializer.data, status=status.HTTP_200_OK)

# ------------------------------------------------------------
# Mostrar tabla de posiciones
# ------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def api_tabla_torneo(request, torneo_id):
    """
    Devuelve la tabla de posiciones por grupo (A, B, etc.)
    con los colores de avance definidos en AvanceEquipos.
    """
    from app_torneo_f5.models import FaseGrupos, AvanceEquipos

    # 1️⃣ Obtener torneo y fase de grupos activa (o la última creada)
    torneo = Torneo.objects.filter(id=torneo_id).first()
    if not torneo:
        return Response({'error': 'Torneo no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    fase_grupos = (
        FaseGrupos.objects
        .filter(torneo=torneo)
        .order_by('-activa', 'orden')
        .first()
    )

    if not fase_grupos:
        return Response({'error': 'El torneo no tiene fase de grupos.'}, status=status.HTTP_404_NOT_FOUND)

    # 2️⃣ Obtener definiciones de avance (Oro, Plata, etc.)
    avances = list(fase_grupos.avances.all())
    # Ejemplo: [AvanceEquipos(nombre='Oro', posiciones=[1,2], color='#3ADF00'), ...]

    participaciones = (
        ParticipacionEquipoTorneo.objects
        .select_related("equipo")
        .filter(torneo_id=torneo_id)
        .order_by("grupo", "-puntos", "-dif", "-gf", "equipo__nombre")
    )

    # 3️⃣ Armar las tablas por grupo
    tablas = {}
    for p in participaciones:
        grupo = getattr(p, "grupo", None) or "-"
        if grupo not in tablas:
            tablas[grupo] = []
        tablas[grupo].append(p)

    data = []
    for grupo, equipos in tablas.items():
        posiciones = []
        for idx, p in enumerate(equipos, start=1):
            # 4️⃣ Buscar si esta posición está incluida en algún AvanceEquipos
            avance_info = None
            # 🔥 Permitir múltiples avances (Oro, Plata, Bronce, etc.)
            avance_match = [av for av in avances if idx in av.posiciones]
            if avance_match:
                # Si hay varios (raro, pero posible), se toma el primero
                av = avance_match[0]
                avance_info = {"nombre": av.nombre, "color": av.color}
            else:
                avance_info = None
            
            posiciones.append({
                "pos": idx,
                "equipo_id": p.equipo.id,
                "equipo": p.equipo.nombre_corto,
                "escudo": p.equipo.escudo.url if p.equipo.escudo else None,
                "pj": p.pj,
                "pg": p.pg,
                "pe": p.pe,
                "pp": p.pp,
                "dif": p.dif,
                "puntos": p.puntos,
                "avance_info": avance_info,  # 👈 se envía al front
            })

        data.append({
            "grupo": grupo,
            "posiciones": posiciones,
        })

    return Response(data, status=status.HTTP_200_OK)

from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from app_torneo_f5.models import (
    Torneo,
    Partido,
    ParticipacionEquipoTorneo,
    EstadisticasEquipoPartido,
    EstadisticasJugadorPartido,
)


@api_view(['GET'])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def api_tabla_posiciones(request, torneo_id: int):
    """
    Tablas por ZONA a partir de PET + partidos de etapa ZONAS.
    Clave de todos los mapas: ParticipacionEquipoTorneo.id (NO equipo.id).

    Reglas:
    - Solo computa partidos jugados o finalizados
    - Excluye interzonales detectando zonas distintas
    - No depende de equipo.id sino de PET.id
    """
    torneo = get_object_or_404(Torneo, pk=torneo_id)

    pets = (
        ParticipacionEquipoTorneo.objects
        .filter(torneo=torneo)
        .select_related("equipo")
    )

    if not pets.exists():
        return Response([], status=status.HTTP_200_OK)

    # mapa PET
    pet_by_id = {pet.id: pet for pet in pets}
    zonas_presentes = {(pet.zona or 1) for pet in pets}

    zonas_stats = {z: {} for z in sorted(zonas_presentes)}
    for pet in pets:
        z = pet.zona or 1
        zonas_stats[z][pet.id] = {
            "pj": 0,
            "pg": 0,
            "pe": 0,
            "pp": 0,
            "gf": 0,
            "gc": 0,
            "puntos": 0,
        }

    ETAPA_ZONAS = Partido.ZONAS

    def _goals_from_stats(p: Partido):
        modo = getattr(p.torneo, "modo_registro_estadisticas", Torneo.POR_PARTIDO)
        gl = gv = None

        if modo == Torneo.POR_EQUIPO:
            rows = (
                EstadisticasEquipoPartido.objects
                .filter(partido=p)
                .values("equipo")
                .annotate(g=Sum("goles"))
            )
            mapa = {r["equipo"]: (r["g"] or 0) for r in rows}
            gl = mapa.get(p.equipo_local_id)
            gv = mapa.get(p.equipo_visitante_id)
        else:
            gl = (
                EstadisticasJugadorPartido.objects
                .filter(
                    partido=p,
                    jugo=True,
                    miembro_equipo__equipo=p.equipo_local.equipo
                )
                .aggregate(s=Sum("goles"))["s"]
            )
            gv = (
                EstadisticasJugadorPartido.objects
                .filter(
                    partido=p,
                    jugo=True,
                    miembro_equipo__equipo=p.equipo_visitante.equipo
                )
                .aggregate(s=Sum("goles"))["s"]
            )

        return gl, gv

    # Solo partidos realmente jugados
    partidos = (
        Partido.objects
        .filter(
            torneo=torneo,
            etapa=ETAPA_ZONAS,
            jugado=True,
        )
        .select_related("equipo_local__equipo", "equipo_visitante__equipo")
    )

    for p in partidos:
        el = p.equipo_local_id
        ev = p.equipo_visitante_id

        if el is None or ev is None:
            continue

        if el not in pet_by_id or ev not in pet_by_id:
            continue

        # excluir cruces entre zonas distintas
        z_local = pet_by_id[el].zona or 1
        z_visit = pet_by_id[ev].zona or 1
        if z_local != z_visit:
            continue

        # si no está realmente cargado el resultado, intentar derivarlo
        gl = p.goles_local
        gv = p.goles_visitante

        # opcional: si ambos son 0 y querés desconfiar del default, podés intentar stats
        if gl is None or gv is None:
            gl, gv = _goals_from_stats(p)
            if gl is None or gv is None:
                continue

        sL = zonas_stats[z_local][el]
        sV = zonas_stats[z_local][ev]

        sL["pj"] += 1
        sV["pj"] += 1

        sL["gf"] += gl
        sL["gc"] += gv
        sV["gf"] += gv
        sV["gc"] += gl

        if gl > gv:
            sL["pg"] += 1
            sL["puntos"] += 3
            sV["pp"] += 1
        elif gv > gl:
            sV["pg"] += 1
            sV["puntos"] += 3
            sL["pp"] += 1
        else:
            sL["pe"] += 1
            sV["pe"] += 1
            sL["puntos"] += 1
            sV["puntos"] += 1

    COLOR_ORO = "#35D07F"
    COLOR_PLATA = "#FFB300"
    CUPOS_AVANCE = 4

    respuesta = []

    for zona in sorted(zonas_stats.keys()):
        equipos_stats = zonas_stats[zona]

        ordenadas = sorted(
            equipos_stats.items(),
            key=lambda kv: (
                -kv[1]["puntos"],
                -(kv[1]["gf"] - kv[1]["gc"]),
                -kv[1]["gf"],
                pet_by_id[kv[0]].equipo.nombre.upper(),
            )
        )

        filas = []
        for idx, (pet_id, s) in enumerate(ordenadas, start=1):
            pet = pet_by_id[pet_id]
            equipo = pet.equipo
            dif = s["gf"] - s["gc"]

            avance_info = None
            if idx <= 4:
                avance_info = {"nombre": "Copa Oro", "color": COLOR_ORO}
            elif idx <= 8:
                avance_info = {"nombre": "Copa Plata", "color": COLOR_PLATA}

            filas.append({
                "pos": idx,
                "equipo_id": pet_id,
                "equipo": getattr(equipo, "nombre_corto", None) or equipo.nombre,
                "escudo": equipo.escudo.url if getattr(equipo, "escudo", None) else "",
                "pj": s["pj"],
                "pg": s["pg"],
                "pe": s["pe"],
                "pp": s["pp"],
                "dif": dif,
                "puntos": s["puntos"],
                "avance_info": avance_info,
            })

        respuesta.append({
            "grupo": zona,
            "cupos_avance": CUPOS_AVANCE,
            "posiciones": filas,
        })

    return Response(respuesta, status=status.HTTP_200_OK)

# app_torneo_f5/views.py (o el archivo donde tengas esta view)
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from app_torneo_f5.tasks import comenzar_partido, finalizar_partido
from proyecto_torneo_f5.celery import app as celery_app


@api_view(['POST'])
@permission_classes([AllowAny])
def partido_celery_definido(request, partido_id):
    """
    POST /api/celery/partido-definido/<partido_id>/

    Body JSON:
    {
      "dia": "2025-11-20",
      "hora": "21:30"
    }
    """
    dia_str = request.data.get("dia")
    hora_str = request.data.get("hora")

    if not dia_str or not hora_str:
        return Response(
            {"error": "Se requieren los campos 'dia' y 'hora'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parsear fecha y hora
    try:
        dia = datetime.strptime(dia_str, "%Y-%m-%d").date()
        hora = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        return Response(
            {"error": "Formato inválido. 'dia' debe ser YYYY-MM-DD y 'hora' HH:MM (24h)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    partido = get_object_or_404(Partido, pk=partido_id)

    # Combinar fecha y hora en datetime aware
    tz = timezone.get_default_timezone()
    inicio_dt = timezone.make_aware(datetime.combine(dia, hora), tz)

    # Guardar inicio
    partido.dia = dia
    partido.hora_inicio = hora
    partido.inicio_datetime = inicio_dt

    # Estado PROGRAMADO si estaba vacío
    if partido.estado in [Partido.VACIO, Partido.INDEFINIDO]:
        partido.estado = Partido.PROGRAMADO

    # Duración SIEMPRE 60 minutos
    duracion_min = 60

    # Calcular fin
    fin_dt = inicio_dt + timedelta(minutes=duracion_min)

    if hasattr(partido, "fin_datetime"):
        partido.fin_datetime = fin_dt

    partido.save()

    ahora = timezone.now()

    # ----------------------------
    #  🔥 PROGRAMAR INICIO DEL PARTIDO
    # ----------------------------
    if inicio_dt <= ahora:
        task_inicio = comenzar_partido.delay(partido.id)
    else:
        # Cancelar programación previa
        if hasattr(partido, "tarea_inicio_celery_id") and partido.tarea_inicio_celery_id:
            celery_app.control.revoke(partido.tarea_inicio_celery_id, terminate=False)

        task_inicio = comenzar_partido.apply_async(
            args=[partido.id],
            eta=inicio_dt
        )

        if hasattr(partido, "tarea_inicio_celery_id"):
            partido.tarea_inicio_celery_id = task_inicio.id

    # ----------------------------
    #  🔥 PROGRAMAR FINAL DEL PARTIDO
    # ----------------------------
    if hasattr(partido, "tarea_fin_celery_id") and partido.tarea_fin_celery_id:
        celery_app.control.revoke(partido.tarea_fin_celery_id, terminate=False)

    task_fin = finalizar_partido.apply_async(
        args=[partido.id],
        eta=fin_dt
    )

    if hasattr(partido, "tarea_fin_celery_id"):
        partido.tarea_fin_celery_id = task_fin.id

    partido.save()

    return Response(
        {
            "ok": True,
            "partido_id": partido.id,
            "programado_inicio": inicio_dt.isoformat(),
            "programado_fin": fin_dt.isoformat(),
            "task_inicio_id": task_inicio.id,
            "task_fin_id": task_fin.id,
            "estado": partido.estado,
        },
        status=status.HTTP_200_OK
    )



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from app_torneo_f5.models import (
    Partido,
    MiembroEquipo,
)

import json
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import api_view, permission_classes, renderer_classes


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@renderer_classes([JSONRenderer])
def cargar_estadisticas_partido_torneo_api(request, partido_id):
    """
    GET  -> devuelve JSON completo para la pantalla de carga de estadísticas
    POST -> imprime JSON recibido en consola (debug)
    """

    # -------------------------------------------------
    # 1️⃣ Obtener partido + PETs
    # -------------------------------------------------
    partido = get_object_or_404(
        Partido.objects.select_related(
            "equipo_local__equipo",
            "equipo_visitante__equipo",
        ),
        id=partido_id
    )

    pet_a = partido.equipo_local
    pet_b = partido.equipo_visitante

    equipo_a = pet_a.equipo
    equipo_b = pet_b.equipo
    encargados = partido.torneo.encargados_carga.all()


    # -------------------------------------------------
    # 2️⃣ GET → JSON para frontend
    # -------------------------------------------------
    if request.method == "GET":

        def serializar_miembro(miembro: MiembroEquipo):
            j = miembro.jugador
            return {
                "miembro_id": miembro.id,
                "jugador_id": j.id,
                "nombre": j.user.get_full_name() or j.user.username,
                "dorsal": miembro.dorsal,
                "estado": miembro.estado,
                "fecha_alta": miembro.fecha_alta,
                "fecha_baja": miembro.fecha_baja,
                "avatar": j.avatar.url if getattr(j, "avatar", None) else None,
            }

        jugadores_a = (
            MiembroEquipo.objects
            .filter(equipo=equipo_a, estado=MiembroEquipo.HABILITADO)
            .select_related("jugador__user")
        )

        jugadores_b = (
            MiembroEquipo.objects
            .filter(equipo=equipo_b, estado=MiembroEquipo.HABILITADO)
            .select_related("jugador__user")
        )

        data = {
            "encargados_del_torneo": [
                {
                    "id": u.id,
                    "username": u.username,
                }
                for u in encargados
            ],

            "nombre_equipo_a": equipo_a.nombre,
            "nombre_equipo_b": equipo_b.nombre,
            "id_equipo_a": equipo_a.id,
            "id_equipo_b": equipo_b.id,


            "jugadores_a_all": [serializar_miembro(m) for m in jugadores_a],
            "jugadores_b_all": [serializar_miembro(m) for m in jugadores_b],

        }
        return Response(data, status=status.HTTP_200_OK)

    # -------------------------------------------------
    # 3️⃣ POST → DEBUG JSON
    # -------------------------------------------------
    if request.method == "POST":

        print("===================================")
        print("📥 JSON RECIBIDO EN BACKEND (DEBUG)")
        print(json.dumps(request.data, indent=2, ensure_ascii=False))
        print("===================================")

        return Response(
            {
                "ok": True,
                "mensaje": "JSON recibido correctamente (ver consola)",
                "partido_id": partido.id
            },
            status=status.HTTP_200_OK
        )

    # -------------------------------------------------
    # 4️⃣ Fallback
    # -------------------------------------------------
    return Response(
        {"error": "Método no permitido"},
        status=status.HTTP_405_METHOD_NOT_ALLOWED
    )



import json
import traceback

from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


def propagar_ganador_a_final(partido):
    if partido.etapa == Partido.ZONAS:
        return
    if partido.ronda != Partido.SEMIFINAL:
        return
    if not partido.equipo_ganador_id:
        return

    final = (Partido.objects
             .select_for_update()
             .filter(
                 torneo=partido.torneo,
                 etapa=partido.etapa,
                 ronda=Partido.FINAL,
             )
             .order_by("id")
             .first())

    if not final:
        return
    if final.jugado or final.estado == Partido.FINALIZADO:
        return

    if final.equipo_local_id == partido.equipo_ganador_id or final.equipo_visitante_id == partido.equipo_ganador_id:
        return

    if final.equipo_local_id is None:
        final.equipo_local = partido.equipo_ganador
    elif final.equipo_visitante_id is None:
        final.equipo_visitante = partido.equipo_ganador
    else:
        return

    if final.equipo_local_id and final.equipo_visitante_id and final.estado in [Partido.VACIO, Partido.INDEFINIDO]:
        final.estado = Partido.PROGRAMADO

    final.save(update_fields=["equipo_local", "equipo_visitante", "estado"]) 


""" def carga_estadistica_final(request, tipo, partido_id):
    try:
        if request.method != "POST":
            return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

        partido = get_object_or_404(Partido, id=partido_id)

        # Bloqueo si el partido ya está finalizado/jugado
        if partido.jugado:
            return JsonResponse(
                {"ok": False, "error": "El partido ya fue finalizado. No se pueden volver a cargar estadísticas."},
                status=400
            )

        # Bloqueo si ya existen estadísticas (anti doble carga)
        if EstadisticasJugadorPartido.objects.filter(partido=partido).exists():
            return JsonResponse(
                {"ok": False, "error": "Las estadísticas ya fueron cargadas para este partido."},
                status=400
            )

        # Parseo JSON
        try:
            raw_body = request.body.decode("utf-8") if request.body else ""
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

        # check partido_id opcional
        try:
            pid_payload = int(payload.get("partido_id", partido.id))
        except Exception:
            pid_payload = None

        if pid_payload is not None and pid_payload != partido.id:
            return JsonResponse({"ok": False, "error": "partido_id no coincide"}, status=400)

        estadisticas = payload.get("estadisticas", [])
        if not isinstance(estadisticas, list):
            return JsonResponse({"ok": False, "error": "estadisticas debe ser una lista"}, status=400)

        local = partido.equipo_local
        visit = partido.equipo_visitante
        if not local or not visit:
            return JsonResponse({"ok": False, "error": "El partido no tiene equipo_local/equipo_visitante asignados"}, status=400)

        # ✅ DETECCIÓN CORRECTA A/B (por tipo real del FK)
        estrategia = None
        path_local = None
        path_visit = None

        # 1) Si MiembroEquipo tiene un FK directo a ParticipacionEquipoTorneo, usamos A
        # probamos una lista de posibles nombres
        candidatos_fk = ["equipo_torneo", "participacion", "participacion_equipo", "equipo_participacion", "participacion_equipo_torneo", "equipo"]
        for fname in candidatos_fk:
            try:
                f = MiembroEquipo._meta.get_field(fname)
                rel_model = getattr(f.remote_field, "model", None)
                if rel_model and isinstance(local, rel_model):
                    estrategia = "A"
                    path_local = {f"miembro_equipo__{fname}": local}
                    path_visit = {f"miembro_equipo__{fname}": visit}
                    break
            except Exception:
                continue

        # 2) Si NO, y MiembroEquipo.equipo apunta a Equipo, usamos B
        if estrategia is None:
            try:
                f = MiembroEquipo._meta.get_field("equipo")
                rel_model = getattr(f.remote_field, "model", None)
            except Exception:
                rel_model = None

            if rel_model and hasattr(local, "equipo") and isinstance(local.equipo, rel_model):
                estrategia = "B"
                path_local = {"miembro_equipo__equipo": local.equipo}
                path_visit = {"miembro_equipo__equipo": visit.equipo}

        if estrategia is None:
            return JsonResponse({"ok": False, "error": "No pude inferir la relación MiembroEquipo -> equipos."}, status=500)

        creadas = 0
        actualizadas = 0
        ignoradas = 0
        errores = []

        with transaction.atomic():
            # Bloqueo por concurrencia
            if EstadisticasJugadorPartido.objects.select_for_update().filter(partido=partido).exists():
                return JsonResponse({"ok": False, "error": "Las estadísticas ya fueron cargadas (concurrencia)."}, status=400)

            # Guardar stats
            for idx, est in enumerate(estadisticas):
                if not isinstance(est, dict):
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "item no es objeto JSON"})
                    continue

                miembro_id = est.get("miembro_equipo")
                if not miembro_id:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "falta miembro_equipo"})
                    continue

                try:
                    miembro = MiembroEquipo.objects.get(id=miembro_id)
                    defaults = {
                        "tarjetas_amarillas": int(est.get("tarjetas_amarillas", 0) or 0),
                        "tarjeta_roja": bool(est.get("tarjeta_roja", False)),
                        "faltas": int(est.get("faltas", 0) or 0),
                        "atajadas": int(est.get("atajadas", 0) or 0),
                        "goles": int(est.get("goles", 0) or 0),
                        "autogoles": int(est.get("autogoles", 0) or 0),
                        "asistencias": int(est.get("asistencias", 0) or 0),
                        "tiros_arco": int(est.get("tiros_arco", 0) or 0),
                        "jugo": bool(est.get("jugo", False)),
                    }

                    estadistica, created = EstadisticasJugadorPartido.objects.update_or_create(
                        partido=partido,
                        miembro_equipo=miembro,
                        defaults=defaults
                    )
                                        
                    jugador = miembro.jugador
                    transaction.on_commit(lambda j=jugador: j.actualizar_valoraciones())
                        
                except MiembroEquipo.DoesNotExist:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": f"MiembroEquipo no existe id={miembro_id}"})
                    continue

                defaults = {
                    "tarjetas_amarillas": int(est.get("tarjetas_amarillas", 0) or 0),
                    "tarjeta_roja": bool(est.get("tarjeta_roja", False)),
                    "faltas": int(est.get("faltas", 0) or 0),
                    "atajadas": int(est.get("atajadas", 0) or 0),
                    "goles": int(est.get("goles", 0) or 0),
                    "autogoles": int(est.get("autogoles", 0) or 0),
                    "asistencias": int(est.get("asistencias", 0) or 0),
                    "tiros_arco": int(est.get("tiros_arco", 0) or 0),
                    "jugo": bool(est.get("jugo", False)),
                }

                try:
                    _, created = EstadisticasJugadorPartido.objects.update_or_create(
                        partido=partido,
                        miembro_equipo=miembro,
                        defaults=defaults
                    )
                    if created:
                        creadas += 1
                    else:
                        actualizadas += 1
                        
                    
                    
                except Exception as e:
                    errores.append({"idx": idx, "error": str(e)})
                    

            # Recalcular goles (DB)
            goles_local = (EstadisticasJugadorPartido.objects
                           .filter(partido=partido, **path_local)
                           .aggregate(total=Sum("goles"))["total"] or 0)

            goles_visitante = (EstadisticasJugadorPartido.objects
                               .filter(partido=partido, **path_visit)
                               .aggregate(total=Sum("goles"))["total"] or 0)

            partido.goles_local = int(goles_local)
            partido.goles_visitante = int(goles_visitante)
            partido.jugado = True
            partido.jugando = False
            partido.estado = Partido.FINALIZADO

            if partido.goles_local > partido.goles_visitante:
                partido.equipo_ganador = partido.equipo_local
            elif partido.goles_visitante > partido.goles_local:
                partido.equipo_ganador = partido.equipo_visitante
            else:
                partido.equipo_ganador = None

            partido.save(update_fields=[
                "goles_local", "goles_visitante",
                "jugado", "jugando", "estado",
                "equipo_ganador"
            ])

            # ✅ Propagar ganador a FINAL si corresponde
            print("PROPAGAR?", partido.id, partido.etapa, partido.ronda, partido.equipo_ganador_id)
            propagar_ganador_a_final(partido)
            

        return JsonResponse({
            "ok": True,
            "partido_id": partido.id,
            "creadas": creadas,
            "actualizadas": actualizadas,
            "ignoradas": ignoradas,
            "errores": errores,
            "goles_local": partido.goles_local,
            "goles_visitante": partido.goles_visitante,
            "estado": partido.estado,
            "jugado": partido.jugado,
            "equipo_ganador": str(partido.equipo_ganador) if partido.equipo_ganador else None,
            "estrategia": estrategia,
        }, status=200)

    except Exception as e:
        # ✅ DEBUG REAL: devolvemos el traceback del error exacto
        return JsonResponse({
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc(),
        }, status=500)


 """
 

""" def carga_estadistica_final(request, tipo, partido_id):
    try:
        if request.method != "POST":
            return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

        partido = get_object_or_404(Partido, id=partido_id)

        # Bloqueo si el partido ya está finalizado/jugado
        if partido.jugado:
            return JsonResponse(
                {"ok": False, "error": "El partido ya fue finalizado. No se pueden volver a cargar estadísticas."},
                status=400
            )

        # Bloqueo anti doble carga
        if EstadisticasJugadorPartido.objects.filter(partido=partido).exists():
            return JsonResponse(
                {"ok": False, "error": "Las estadísticas ya fueron cargadas para este partido."},
                status=400
            )

        # Parseo JSON
        try:
            raw_body = request.body.decode("utf-8") if request.body else ""
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

        # Validación partido_id opcional
        try:
            pid_payload = int(payload.get("partido_id", partido.id))
        except Exception:
            pid_payload = None

        if pid_payload is not None and pid_payload != partido.id:
            return JsonResponse({"ok": False, "error": "partido_id no coincide"}, status=400)

        estadisticas = payload.get("estadisticas", [])
        if not isinstance(estadisticas, list):
            return JsonResponse({"ok": False, "error": "estadisticas debe ser una lista"}, status=400)

        local = partido.equipo_local
        visit = partido.equipo_visitante
        if not local or not visit:
            return JsonResponse({"ok": False, "error": "El partido no tiene equipo_local/equipo_visitante asignados"}, status=400)

        # Detección relación MiembroEquipo -> equipo (estrategia A/B)
        estrategia = None
        path_local = None
        path_visit = None

        candidatos_fk = ["equipo_torneo", "participacion", "participacion_equipo", "equipo_participacion", "participacion_equipo_torneo", "equipo"]
        for fname in candidatos_fk:
            try:
                f = MiembroEquipo._meta.get_field(fname)
                rel_model = getattr(f.remote_field, "model", None)
                if rel_model and isinstance(local, rel_model):
                    estrategia = "A"
                    path_local = {f"miembro_equipo__{fname}": local}
                    path_visit = {f"miembro_equipo__{fname}": visit}
                    break
            except Exception:
                continue

        if estrategia is None:
            try:
                f = MiembroEquipo._meta.get_field("equipo")
                rel_model = getattr(f.remote_field, "model", None)
            except Exception:
                rel_model = None

            if rel_model and hasattr(local, "equipo") and isinstance(local.equipo, rel_model):
                estrategia = "B"
                path_local = {"miembro_equipo__equipo": local.equipo}
                path_visit = {"miembro_equipo__equipo": visit.equipo}

        if estrategia is None:
            return JsonResponse({"ok": False, "error": "No pude inferir la relación MiembroEquipo -> equipos."}, status=500)

        creadas = 0
        actualizadas = 0
        ignoradas = 0
        errores = []

        with transaction.atomic():
            # Bloqueo por concurrencia
            if EstadisticasJugadorPartido.objects.select_for_update().filter(partido=partido).exists():
                return JsonResponse({"ok": False, "error": "Las estadísticas ya fueron cargadas (concurrencia)."}, status=400)

            # Guardar estadísticas
            for idx, est in enumerate(estadisticas):
                if not isinstance(est, dict):
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "item no es objeto JSON"})
                    continue

                miembro_id = est.get("miembro_equipo")
                if not miembro_id:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "falta miembro_equipo"})
                    continue

                try:
                    miembro = MiembroEquipo.objects.get(id=miembro_id)
                except MiembroEquipo.DoesNotExist:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": f"MiembroEquipo no existe id={miembro_id}"})
                    continue

                defaults = {
                    "tarjetas_amarillas": int(est.get("tarjetas_amarillas", 0) or 0),
                    "tarjeta_roja": bool(est.get("tarjeta_roja", False)),
                    "faltas": int(est.get("faltas", 0) or 0),
                    "atajadas": int(est.get("atajadas", 0) or 0),
                    "goles": int(est.get("goles", 0) or 0),
                    "autogoles": int(est.get("autogoles", 0) or 0),
                    "asistencias": int(est.get("asistencias", 0) or 0),
                    "tiros_arco": int(est.get("tiros_arco", 0) or 0),
                    "jugo": bool(est.get("jugo", False)),
                }

                try:
                    estadistica, created = EstadisticasJugadorPartido.objects.update_or_create(
                        partido=partido,
                        miembro_equipo=miembro,
                        defaults=defaults
                    )
                    if created:
                        creadas += 1
                    else:
                        actualizadas += 1

                    miembro.jugador.actualizar_valoraciones()

                except Exception as e:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": str(e)})

            # Recalcular goles
            goles_local = (EstadisticasJugadorPartido.objects
                           .filter(partido=partido, **path_local)
                           .aggregate(total=Sum("goles"))["total"] or 0)

            goles_visitante = (EstadisticasJugadorPartido.objects
                               .filter(partido=partido, **path_visit)
                               .aggregate(total=Sum("goles"))["total"] or 0)

            partido.goles_local = int(goles_local)
            partido.goles_visitante = int(goles_visitante)
            partido.jugado = True
            partido.jugando = False
            partido.estado = Partido.FINALIZADO

            if partido.goles_local > partido.goles_visitante:
                partido.equipo_ganador = partido.equipo_local
            elif partido.goles_visitante > partido.goles_local:
                partido.equipo_ganador = partido.equipo_visitante
            else:
                partido.equipo_ganador = None

            partido.save(update_fields=[
                "goles_local", "goles_visitante",
                "jugado", "jugando", "estado",
                "equipo_ganador"
            ])
            
            ParticipacionEquipoTorneo.recalcular_torneo(partido.torneo)

            # Propagar ganador a FINAL si corresponde
            propagar_ganador_a_final(partido)

        return JsonResponse({
            "ok": True,
            "partido_id": partido.id,
            "creadas": creadas,
            "actualizadas": actualizadas,
            "ignoradas": ignoradas,
            "errores": errores,
            "goles_local": partido.goles_local,
            "goles_visitante": partido.goles_visitante,
            "estado": partido.estado,
            "jugado": partido.jugado,
            "equipo_ganador": str(partido.equipo_ganador) if partido.equipo_ganador else None,
            "estrategia": estrategia,
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc(),
        }, status=500)
    


    # views.py

 """


import json
import traceback

from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

def _to_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

def _to_bool(v, default=False):
    # acepta bool real, 0/1, "true"/"false", "1"/"0"
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "si", "sí", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off", ""):
            return False
    return default

def carga_estadistica_final(request, tipo, partido_id):
    try:
        if request.method != "POST":
            return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

        # Parse JSON ANTES del lock
        try:
            raw_body = request.body.decode("utf-8") if request.body else ""
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

        estadisticas = payload.get("estadisticas", [])
        if not isinstance(estadisticas, list):
            return JsonResponse({"ok": False, "error": "estadisticas debe ser una lista"}, status=400)

        creadas = 0
        ignoradas = 0
        errores = []
        jugadores_para_actualizar = set()

        with transaction.atomic():
            # LOCK LIVIANO: solo bloquea el partido, sin traer torneo/equipos en la misma query
            partido = (
                Partido.objects
                .select_for_update()
                .get(id=partido_id)
            )

            if partido.jugado:
                return JsonResponse(
                    {"ok": False, "error": "El partido ya fue finalizado. No se pueden volver a cargar estadísticas."},
                    status=400
                )

            if EstadisticasJugadorPartido.objects.filter(partido_id=partido.id).exists():
                return JsonResponse(
                    {"ok": False, "error": "Las estadísticas ya fueron cargadas para este partido."},
                    status=400
                )

            # Ahora sí cargamos relaciones, pero ya NO con FOR UPDATE gigante
            partido = (
                Partido.objects
                .select_related("equipo_local__equipo", "equipo_visitante__equipo", "torneo")
                .get(id=partido.id)
            )

            pid_payload = payload.get("partido_id", partido.id)
            try:
                pid_payload = int(pid_payload)
            except Exception:
                pid_payload = None

            if pid_payload is not None and pid_payload != partido.id:
                return JsonResponse({"ok": False, "error": "partido_id no coincide"}, status=400)

            pet_local = partido.equipo_local
            pet_visit = partido.equipo_visitante

            if not pet_local or not pet_visit:
                return JsonResponse({"ok": False, "error": "El partido no tiene equipo_local/equipo_visitante asignados"}, status=400)

            equipo_local = getattr(pet_local, "equipo", None)
            equipo_visit = getattr(pet_visit, "equipo", None)

            if not equipo_local or not equipo_visit:
                return JsonResponse({"ok": False, "error": "No pude obtener equipo real desde PET (equipo_local.equipo)"}, status=500)

            miembros_qs = (
                MiembroEquipo.objects
                .select_related("jugador")
                .filter(
                    equipo__in=[equipo_local, equipo_visit],
                    estado=MiembroEquipo.HABILITADO
                )
            )

            miembros_map = {m.id: m for m in miembros_qs}
            miembros_validos = set(miembros_map.keys())

            stats_a_crear = []

            goles_local = 0
            goles_visit = 0
            autogoles_local = 0
            autogoles_visit = 0

            for idx, est in enumerate(estadisticas):
                if not isinstance(est, dict):
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "item no es objeto JSON"})
                    continue

                miembro_id = est.get("miembro_equipo")
                if not miembro_id:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "falta miembro_equipo"})
                    continue

                miembro_id = _to_int(miembro_id, default=None)
                if not miembro_id:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": "miembro_equipo inválido"})
                    continue

                if miembro_id not in miembros_validos:
                    ignoradas += 1
                    errores.append({"idx": idx, "error": f"MiembroEquipo {miembro_id} no pertenece a este partido"})
                    continue

                miembro = miembros_map[miembro_id]

                goles = _to_int(est.get("goles", 0))
                autogoles = _to_int(est.get("autogoles", 0))

                stat = EstadisticasJugadorPartido(
                    partido_id=partido.id,
                    miembro_equipo=miembro,
                    tarjetas_amarillas=_to_int(est.get("tarjetas_amarillas", 0)),
                    tarjeta_roja=_to_bool(est.get("tarjeta_roja", False)),
                    faltas=_to_int(est.get("faltas", 0)),
                    atajadas=_to_int(est.get("atajadas", 0)),
                    goles=goles,
                    autogoles=autogoles,
                    asistencias=_to_int(est.get("asistencias", 0)),
                    tiros_arco=_to_int(est.get("tiros_arco", 0)),
                    jugo=_to_bool(est.get("jugo", False)),
                )

                stats_a_crear.append(stat)

                if miembro.jugador_id:
                    jugadores_para_actualizar.add(miembro.jugador_id)

                # Calculamos goles sin hacer 4 aggregate después
                if miembro.equipo_id == equipo_local.id:
                    goles_local += goles
                    autogoles_local += autogoles
                elif miembro.equipo_id == equipo_visit.id:
                    goles_visit += goles
                    autogoles_visit += autogoles

            if errores:
                return JsonResponse({
                    "ok": False,
                    "error": "Se recibieron estadísticas con errores. No se finalizó el partido.",
                    "creadas": 0,
                    "actualizadas": 0,
                    "ignoradas": ignoradas,
                    "errores": errores,
                }, status=400)

            if not stats_a_crear:
                return JsonResponse({
                    "ok": False,
                    "error": "No se recibieron estadísticas válidas.",
                }, status=400)

            EstadisticasJugadorPartido.objects.bulk_create(stats_a_crear)
            creadas = len(stats_a_crear)

            partido.goles_local = int(goles_local + autogoles_visit)
            partido.goles_visitante = int(goles_visit + autogoles_local)

            partido.jugado = True
            partido.jugando = False
            partido.estado = Partido.FINALIZADO

            if partido.goles_local > partido.goles_visitante:
                partido.equipo_ganador = partido.equipo_local
            elif partido.goles_visitante > partido.goles_local:
                partido.equipo_ganador = partido.equipo_visitante
            else:
                partido.equipo_ganador = None

            partido.save(update_fields=[
                "goles_local",
                "goles_visitante",
                "jugado",
                "jugando",
                "estado",
                "equipo_ganador",
            ])

            # Lo dejo ADENTRO para no cambiar comportamiento.
            # Si esto tarda mucho, después lo pasamos a on_commit o Celery.
            ParticipacionEquipoTorneo.recalcular_torneo(partido.torneo)
            propagar_ganador_a_final(partido)

        # FUERA del atomic: esto no debería bloquear la finalización del partido
        try:
            jugadores = Jugador.objects.filter(id__in=jugadores_para_actualizar)
            for jugador in jugadores:
                try:
                    jugador.actualizar_valoraciones()
                except Exception:
                    pass
        except Exception as e:
            print("Error actualizando valoraciones:", e)

        return JsonResponse({
            "ok": True,
            "partido_id": partido.id,
            "creadas": creadas,
            "actualizadas": 0,
            "ignoradas": ignoradas,
            "errores": [],
            "goles_local": partido.goles_local,
            "goles_visitante": partido.goles_visitante,
            "estado": partido.estado,
            "jugado": partido.jugado,
            "equipo_ganador": str(partido.equipo_ganador) if partido.equipo_ganador else None,
        }, status=200)

    except Partido.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Partido no encontrado"}, status=404)

    except Exception as e:
        return JsonResponse({
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc(),
        }, status=500)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from app_torneo_f5.models import Partido, MiembroEquipo


from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status

from app_torneo_f5.models import (
    Partido,
    MiembroEquipo,
    EstadisticasJugadorPartido,
)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([JSONRenderer])
def obtener_estadisticas_partido(request, partido_id):
    """
    GET /api/partido/<partido_id>/estadisticas/

    Devuelve:
    - torneo (mínimo)
    - encargados
    - equipo_local + jugadores habilitados + stats
    - equipo_visitante + jugadores habilitados + stats
    """

    partido = get_object_or_404(
        Partido.objects.select_related(
            "torneo",
            "equipo_local__equipo",
            "equipo_visitante__equipo",
        ),
        id=partido_id
    )

    if not partido.equipo_local or not partido.equipo_visitante:
        return Response(
            {"error": "El partido no tiene equipo_local/equipo_visitante asignados."},
            status=status.HTTP_400_BAD_REQUEST
        )

    pet_a = partido.equipo_local
    pet_b = partido.equipo_visitante

    equipo_a = pet_a.equipo
    equipo_b = pet_b.equipo

    encargados = partido.torneo.encargados_carga.all()

    # stats existentes (map por miembro_id)
    stats_qs = EstadisticasJugadorPartido.objects.filter(partido=partido)
    stats_map = {s.miembro_equipo_id: s for s in stats_qs}

    def stats_default():
        return {
            "tarjetas_amarillas": 0,
            "tarjeta_roja": False,
            "faltas": 0,
            "atajadas": 0,
            "goles": 0,
            "autogoles": 0,
            "asistencias": 0,
            "tiros_arco": 0,
            "jugo": False,
        }

    def serializar_stats(stats: EstadisticasJugadorPartido):
        return {
            "tarjetas_amarillas": int(stats.tarjetas_amarillas or 0),
            "tarjeta_roja": bool(stats.tarjeta_roja),
            "faltas": int(stats.faltas or 0),
            "atajadas": int(stats.atajadas or 0),
            "goles": int(stats.goles or 0),
            "autogoles": int(stats.autogoles or 0),
            "asistencias": int(stats.asistencias or 0),
            "tiros_arco": int(stats.tiros_arco or 0),
            "jugo": bool(stats.jugo),
        }

    def safe_img_url(field_file):
        """
        field_file: ImageFieldFile / FileFieldFile
        Devuelve URL o None sin romper si no hay archivo.
        """
        try:
            if field_file and getattr(field_file, "name", ""):
                return field_file.url
        except Exception:
            pass
        return None

    def serializar_miembro(miembro: MiembroEquipo):
        j = miembro.jugador
        u = j.user

        stats = stats_map.get(miembro.id)

        return {
            "miembro_id": miembro.id,
            "jugador_id": j.id,
            "nombre": u.get_full_name() or u.username,
            "dorsal": miembro.dorsal,
            "estado": miembro.estado,

            # ✅ ESTA ES LA CLAVE (antes te daba None)
            "jugador_img": safe_img_url(getattr(j, "avatar", None)),

            "estadisticas": serializar_stats(stats) if stats else stats_default(),
        }

    jugadores_a = (
        MiembroEquipo.objects
        .filter(equipo=equipo_a, estado=MiembroEquipo.HABILITADO)
        .select_related("jugador__user")
        .order_by("dorsal", "id")
    )

    jugadores_b = (
        MiembroEquipo.objects
        .filter(equipo=equipo_b, estado=MiembroEquipo.HABILITADO)
        .select_related("jugador__user")
        .order_by("dorsal", "id")
    )

    data = {
        "partido_id": partido.id,
        "dia": partido.dia.strftime("%d/%m/%Y") if partido.dia else None,

        "torneo": {
            "id": partido.torneo_id,
            "nombre": partido.torneo.nombre,
            "formato": getattr(partido.torneo, "formato", None),
            "cantidad_equipos": getattr(partido.torneo, "cantidad_equipos", None),
        },

        "encargados_del_torneo": [
            {"id": u.id, "username": u.username}
            for u in encargados
        ],

        "equipo_local": {
            "equipo_id": equipo_a.id,
            "nombre": equipo_a.nombre,
            "escudo": safe_img_url(getattr(equipo_a, "escudo", None)),

            # ✅ para el front (capitán por jugador_id)
            "capitan_id": getattr(equipo_a, "capitan_id", None),

            "jugadores_equipo_local": [serializar_miembro(m) for m in jugadores_a],
        },

        "equipo_visitante": {
            "equipo_id": equipo_b.id,
            "nombre": equipo_b.nombre,
            "escudo": safe_img_url(getattr(equipo_b, "escudo", None)),
            "capitan_id": getattr(equipo_b, "capitan_id", None),
            "jugadores_equipo_visitante": [serializar_miembro(m) for m in jugadores_b],
        },
    }

    return Response(data, status=status.HTTP_200_OK)