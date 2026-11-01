from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import logout, login
from ..models import InvitacionEquipo, ParticipacionJugadorTorneo, Cancha, TipoCancha, MiembroEquipo, IntegranteEquipo, Equipo, Jugador, Participacion, Torneo, EstadisticaJugador, Partido, PartidoAmistoso, PerfilUsuario, Inscripcion, ParticipacionEquipoTorneo
from django.db.models import Sum, Q, Count, F, ExpressionWrapper, FloatField, Prefetch
from django.db.models.functions import Coalesce, NullIf
from ..forms import PartidoAmistosoForm, EstadisticaAmistosaForm, RegistroManualForm, CrearPerfil1Form, CrearPerfil2Form, CrearPerfil3Form, CrearPerfil4Form, JugadorForm  
from django.urls import reverse, NoReverseMatch
from django.contrib import messages
User = get_user_model()
from django.shortcuts import get_object_or_404, redirect
from ..models import PartidoAmistoso, Jugador, Invitacion
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from datetime import date
from django.utils.http import urlencode
from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
from django.utils.timezone import localtime
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from datetime import datetime, time
import random
from django.http import Http404
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt  # solo si no usás el token correctamente
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from itertools import chain
from operator import attrgetter
from app_torneo_f5.models import Notificacion  # ajustá según tu estructura
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from ..models import PartidoAmistoso, Jugador
from django.db.models import Q, Value, CharField, IntegerField, Case, When, F
from ..forms import LoginForm  # 👈 importa el custom
from ..models import MagicLoginToken
from collections import OrderedDict, defaultdict
from types import SimpleNamespace
from ..utils import *


@require_GET
def offline(request):
    return render(request, "offline.html", status=200)

# Alias público para que lo importen las urls



def atajo_instagram(request):
    return render(request, 'atajo_instagram.html', {
        "ocultar_navbar": True
        })

@login_required
def vista_bienvenida(request):
    perfil = request.user.perfilusuario
    if perfil.es_primer_ingreso:
        perfil.es_primer_ingreso = False
        perfil.save()
    context = {
        'ocultar_navbar': True,
    }
    return render(request, 'bienvenido/bienvenido.html', context)

@login_required
def home(request):
    perfil = request.user.perfilusuario
    if perfil.es_primer_ingreso:
        return redirect('bienvenido')

        

    jugador = get_object_or_404(Jugador, user=request.user)
    equipos_jugador = Inscripcion.objects.filter(jugador=jugador).values_list('equipo_id', flat=True)

    participaciones_jugador = (
        ParticipacionEquipoTorneo.objects
        .filter(equipo_id__in=equipos_jugador)
        .values_list('id', flat=True)
    )
    participaciones_ids = (
        ParticipacionEquipoTorneo.objects
        .filter(equipo__inscripcion__jugador=jugador)
        .values_list('id', flat=True)
        .distinct()
    )

    # --- Partidos jugados
    partidos_amistosos = (
        PartidoAmistoso.objects
        .filter(jugado=True, jugadores=jugador, cancelado=False)
    )

    # --- Sin stats del jugador
    # --- Último amistoso jugado sin estadísticas cargadas
    partidos_amistosos_sin_stats = (
        PartidoAmistoso.objects
        .filter(
            jugado=True,
            jugadores=jugador,
            cancelado=False
        )
        .exclude(
            estadisticas__jugador=jugador,
            estadisticas__cargada=True
        )
        .order_by('-dia', '-hora_inicio')
    )

    ultimo_partido_sin_estadisticas = partidos_amistosos_sin_stats.first()
    ultimo_partido_tipo = "amistoso" if ultimo_partido_sin_estadisticas else None

    # --- Combinar y ordenar
    partidos_sin_stats_ordenados = sorted(
        partidos_amistosos_sin_stats,
        key=lambda p: (
            datetime.combine(
                getattr(p, 'dia', None) or date.min,
                getattr(p, 'hora_inicio', None) or time.min
            )
        ),
        reverse=True
    )
    ultimo_partido_sin_estadisticas = (
        partidos_sin_stats_ordenados[0]
        if partidos_sin_stats_ordenados
        else None
    )

    # ------ Buscar vencimiento (igual que tenías)
    ultimo = (
        EstadisticaAmistosa.objects
        .filter(jugador=jugador, cargada=False, partido__jugado=True, partido__cancelado=False)
        .order_by('-partido__dia')
        .only('fecha_vencimiento')
        .first()
    )
    fecha_vencimiento = ultimo.fecha_vencimiento if ultimo else None

    # ---- Datos del último partido para la card
    equipo_del_ultimo = None
    equipo_ganador = None

    if ultimo_partido_sin_estadisticas:
        partido = ultimo_partido_sin_estadisticas

        if partido.equipo_local.filter(id=jugador.id).exists():
            equipo_del_ultimo = partido.equipo_local
        elif partido.equipo_visitante.filter(id=jugador.id).exists():
            equipo_del_ultimo = partido.equipo_visitante

        if partido.goles_equipo_local > partido.goles_equipo_visitante:
            equipo_ganador = partido.equipo_local
        elif partido.goles_equipo_local < partido.goles_equipo_visitante:
            equipo_ganador = partido.equipo_visitante

    # ---- Próximos partidos
    hoy = timezone.localdate()

    # Obtener participaciones del jugador en torneos
    participaciones_ids = ParticipacionEquipoTorneo.objects.filter(
        equipo_id__in=equipos_jugador
    ).values_list('id', flat=True)
    
    proximos_torneo = Partido.objects.filter(
        Q(equipo_local_id__in=participaciones_ids) |
        Q(equipo_visitante_id__in=participaciones_ids),
        jugado=False
    )
    proximos_amistosos = (
        PartidoAmistoso.objects
        .filter(jugadores=jugador, cancelado=False)
        .filter(Q(jugado=False) | Q(jugado__isnull=True))
        .filter(Q(dia__gte=hoy) | Q(dia__isnull=True))
        .annotate(
            tipo=Value('amistoso', output_field=CharField()),
            tiene_dia=Case(When(Q(dia__isnull=True), then=0), default=1, output_field=IntegerField()),
            tiene_hora=Case(When(hora_inicio__isnull=True), then=0, default=1, output_field=IntegerField()),
        )
    )
    
    print("TORNEO:", list(proximos_torneo.values_list("id", "dia", "jugado")))
    print("EQUIPOS_JUGADOR:", list(equipos_jugador))
    print("PARTIDOS TORNEO TOTALES:",
      list(Partido.objects.values_list("id", "equipo_local_id", "equipo_visitante_id", "jugado")))

    proximos_mix = list(chain(proximos_torneo, proximos_amistosos))
    proximos_mix.sort(key=lambda p: (
        0 if getattr(p, 'tiene_dia', 1) else 1,
        getattr(p, 'dia', None) or date.max,
        0 if getattr(p, 'tiene_hora', 1) else 1,
        getattr(p, 'hora_inicio', None) or time.max,
        p.id
    ))
    proximos_para_home = proximos_mix[:5]

    # 👉 DEFINIR antes de usar
    proximo_partido = proximos_para_home[0] if proximos_para_home else None
    proximo_partido_tipo = "amistoso" if isinstance(proximo_partido, PartidoAmistoso) else ("torneo" if proximo_partido else None)
    
    tiene_propuesta_abierta = False

    if proximo_partido_tipo == "torneo" and proximo_partido:
        try:
            propuesta = proximo_partido.propuesta
            if propuesta and not propuesta.cerrada:
                tiene_propuesta_abierta = True
        except:
            tiene_propuesta_abierta = False

    # ---- Escudos para HOME (después de definir proximo_partido)
    ultimo_escudos = {'local': None, 'visitante': None}
    if ultimo_partido_sin_estadisticas and isinstance(ultimo_partido_sin_estadisticas, PartidoAmistoso):
        color_local = getattr(ultimo_partido_sin_estadisticas, 'color_equipo_local', 'bg-d-equipo1') or 'bg-d-equipo1'
        e1, e2 = escudos_por_color(color_local)
        ultimo_escudos = {'local': e1, 'visitante': e2}

    proximo_escudos = {'local': None, 'visitante': None}
    if proximo_partido and isinstance(proximo_partido, PartidoAmistoso):
        color_local = getattr(proximo_partido, 'color_equipo_local', 'bg-d-equipo1') or 'bg-d-equipo1'
        e1, e2 = escudos_por_color(color_local)
        proximo_escudos = {'local': e1, 'visitante': e2}

    # ---- Torneo actual / participación (igual)
    torneo_actual = Torneo.objects.filter(inscripcion__jugador=jugador).distinct().first()
    equipo_jugador = None
    participacion_equipo = None
    if torneo_actual:
        inscripcion = Inscripcion.objects.filter(jugador=jugador, torneo=torneo_actual).first()
        if inscripcion:
            equipo_jugador = inscripcion.equipo
            participacion_equipo = Participacion.objects.filter(equipo=equipo_jugador, torneo=torneo_actual).first()

    context = {
        'jugador': jugador,
        'ultimo_partido_sin_estadisticas': ultimo_partido_sin_estadisticas,
        'ultimo_partido_tipo': ultimo_partido_tipo,
        'equipo_jugador': equipo_del_ultimo,
        'equipo_ganador': equipo_ganador,
        'proximo_partido': proximo_partido,
        'proximo_partido_tipo': proximo_partido_tipo,
        'torneo_actual': torneo_actual,
        'participacion_equipo': participacion_equipo,
        'ahora_iso': fecha_vencimiento,
        'tiene_propuesta_abierta': tiene_propuesta_abierta,
        'home_escudos': {
            'ultimo': ultimo_escudos,
            'proximo': proximo_escudos,
        },
    }
    return render(request, 'app_torneo_f5/home.html', context)

def adelantos(request):
    previous_url = request.META.get('HTTP_REFERER', '/')
    return render(request, 'app_torneo_f5/adelantos.html', {
        'ocultar_navbar': True,
        'previous_url': previous_url,
    })
    


@login_required
def crear_perfil_1(request):
    jugador = request.user.jugador

    if request.method == 'POST':
        form = CrearPerfil1Form(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            form.save()
            jugador.paso_perfil = max(jugador.paso_perfil, 1)
            jugador.save()
            return redirect('crear_perfil_2')
        else:
            print("❌ Errores en crear_perfil_1:", form.errors)
    else:
        form = CrearPerfil1Form(instance=jugador)

    return render(request, 'perfil/crear_perfil_1.html', {
        'jugador': jugador,
        'form': form,
        'ocultar_navbar': True,
    })

@login_required
def crear_perfil_2(request):
    jugador = request.user.jugador

    if request.method == 'POST':
        form = CrearPerfil2Form(request.POST, instance=jugador)
        if form.is_valid():
            jugador.paso_perfil = max(jugador.paso_perfil, 2)
            jugador.save()
            form.save()
            return redirect('crear_perfil_3')
        else:
            print("❌ Errores en crear_perfil_2:", form.errors)
    else:
        form = CrearPerfil2Form(instance=jugador)

    return render(request, 'perfil/crear_perfil_2.html', {
        'jugador': jugador,
        'form': form,
        'ocultar_navbar': True,
    })

@login_required
def crear_perfil_3(request):
    jugador = request.user.jugador

    if request.method == 'POST':
        form = CrearPerfil3Form(request.POST, instance=jugador)
        if form.is_valid():
            jugador.paso_perfil = max(jugador.paso_perfil, 3)
            jugador.save()
            form.save()
            return redirect('crear_perfil_4')
        else:
            print("❌ Errores en crear_perfil_3:", form.errors)
    else:
        form = CrearPerfil3Form(instance=jugador)

    return render(request, 'perfil/crear_perfil_3.html', {
        'jugador': jugador,
        'form': form,
        'ocultar_navbar': True,
    })

@login_required
def crear_perfil_4(request):
    jugador = request.user.jugador

    if request.method == 'POST':
        form = CrearPerfil4Form(request.POST, instance=jugador)
        if form.is_valid():
            jugador.paso_perfil = max(jugador.paso_perfil, 4)
            jugador.save()
            form.save()
            return redirect('home')
        else:
            print("❌ Errores en crear_perfil_4:", form.errors)
    else:
        form = CrearPerfil4Form(instance=jugador)

    return render(request, 'perfil/crear_perfil_4.html', {
        'jugador': jugador,
        'form': form,
        'ocultar_navbar': True,
    })
    
#####################################################################################

""" Funciones auxiliares para la carga de estadisticas """

def get_partido_y_estadisticas(tipo, partido_id):
    if tipo == 'amistoso':
        partido = get_object_or_404(PartidoAmistoso, id=partido_id)
        EstadisticaModel = EstadisticaAmistosa
    elif tipo == 'torneo':
        partido = get_object_or_404(Partido, id=partido_id)
        EstadisticaModel = EstadisticaJugador
    else:
        raise Http404("Tipo de partido inválido")
    
    return partido, EstadisticaModel

def obtener_jugadores_del_partido(partido, tipo):
    if tipo == 'amistoso':
        # En partidos amistosos hay un ManyToMany con jugadores
        return list(partido.jugadores.all())

    elif tipo == 'torneo':
        jugadores_equipo_1 = Jugador.objects.filter(inscripcion__equipo=partido.equipo_1).distinct()
        jugadores_equipo_2 = Jugador.objects.filter(inscripcion__equipo=partido.equipo_2).distinct()
        return list(jugadores_equipo_1 | jugadores_equipo_2)

    return []

#####################################################################################

from django.db.models import Avg

@login_required
def estadisticas_paso1(request, tipo, partido_id):
    partido, EstadisticaModel = get_partido_y_estadisticas(tipo, partido_id)
    jugador_actual = Jugador.objects.get(user=request.user) 

    notis = Notificacion.objects.filter(usuario=request.user, tipo='estadistica', extra_id=str(partido_id))
    notis.update(leida=True)
    print(notis.values('id', 'leida'))

    # Determinar el equipo del jugador
    if tipo == 'amistoso':
        if partido.equipo_local.filter(id=jugador_actual.id).exists():
            equipo_propio = partido.equipo_local.all()
        elif partido.equipo_visitante.filter(id=jugador_actual.id).exists():
            equipo_propio = partido.equipo_visitante.all()
        else:
            equipo_propio = Jugador.objects.none()

    else:
        if Inscripcion.objects.filter(jugador=jugador_actual, equipo=partido.equipo_1).exists():
            equipo_propio = Jugador.objects.filter(inscripcion__equipo=partido.equipo_1)
        elif Inscripcion.objects.filter(jugador=jugador_actual, equipo=partido.equipo_2).exists():
            equipo_propio = Jugador.objects.filter(inscripcion__equipo=partido.equipo_2)
        else:
            equipo_propio = []
        
    if request.method == 'POST':
        for companero in equipo_propio.exclude(id=jugador_actual.id):
            calificacion_str = request.POST.get(f"calificacion_{companero.id}")
            if calificacion_str:
                calificacion = int(calificacion_str)
                if calificacion == 0:
                    continue  # No guardar calificaciones en cero
                
                estadistica = EstadisticaModel.objects.filter(partido=partido, jugador=companero).first()
                
                if estadistica:
                    if estadistica.calificacion is not None:
                        total = estadistica.calificacion * estadistica.cantidad_calificaciones
                        total += calificacion
                        estadistica.cantidad_calificaciones += 1
                        estadistica.calificacion = round(total / estadistica.cantidad_calificaciones, 1)
                    else:
                        estadistica.calificacion = calificacion
                        estadistica.cantidad_calificaciones = 1
                else:
                    estadistica = EstadisticaModel(
                        partido=partido,
                        jugador=companero,
                        calificacion=calificacion,
                        cantidad_calificaciones=1
                    )
                estadistica.save()
        


        return redirect('estadisticas_paso2', tipo=tipo, partido_id=partido.id)

    return render(request, 'carga_estadisticas/carga_estadisticas_1.html', {
        'partido': partido,
        'jugadores': equipo_propio.exclude(id=jugador_actual.id),
        'tipo': tipo
    })
 
@login_required
def estadisticas_paso2(request, tipo, partido_id):
    partido, EstadisticaModel = get_partido_y_estadisticas(tipo, partido_id)
    jugadores_ids = request.session.get('jugadores_seleccionados', [])
    jugadores = Jugador.objects.filter(id__in=jugadores_ids)

    jugador_logueado = Jugador.objects.get(user=request.user)

    if request.method == 'POST':
        calificacion_defensivo = request.POST.get("calificacion_defensivo")
        calificacion_manejo = request.POST.get("calificacion_manejo")

        estadistica = EstadisticaModel.objects.filter(partido=partido, jugador=jugador_logueado).first()
        if not estadistica:
            estadistica = EstadisticaModel(partido=partido, jugador=jugador_logueado)

        if calificacion_defensivo:
            estadistica.calificacion_defensa = int(calificacion_defensivo)
        if calificacion_manejo:
            estadistica.calificacion_manejo = int(calificacion_manejo)
        estadistica.save()

        return redirect('estadisticas_paso3', tipo=tipo, partido_id=partido.id)

    return render(request, 'carga_estadisticas/carga_estadisticas_2.html', {
        'partido': partido,
        'jugadores': jugadores,
        'tipo': tipo,
    })
    
from app_torneo_f5.models import EstadisticaJugador, EstadisticaAmistosa  # asegurate de importar esto si no está

def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0

@login_required
def estadisticas_paso3(request, tipo, partido_id):
    partido, EstadisticaModel = get_partido_y_estadisticas(tipo, partido_id)
    jugador = Jugador.objects.get(user=request.user)

    session_key = f'ultima_frase_{partido.id}'

    if request.method == 'POST':
        ultima = request.POST.get("ultima_frase", "") or ""
        goles = _to_int(request.POST.get('goles'))
        asistencias = _to_int(request.POST.get('asistencias'))
        atajadas = _to_int(request.POST.get('atajadas'))

        estadistica, creada = EstadisticaModel.objects.get_or_create(
            partido=partido,
            jugador=jugador
        )
        estadistica.goles = goles
        estadistica.asistencias = asistencias
        estadistica.atajadas = atajadas
        estadistica.jugo = True
        estadistica.cargada = True
        estadistica.save()

        # ⬇️⬇️ SNAPSHOT *ANTES* de actualizar al jugador (esto captura el "antes" real)
        snapshot_key = f'snapshot_stats_{partido.id}'
        request.session[snapshot_key] = {
            'valoraciones': {
                'ataque': jugador.valoracion_ataque or 0,
                'defensa': jugador.valoracion_defensa or 0,
                'creatividad': jugador.valoracion_creatividad or 0,
                'portero': jugador.valoracion_portero or 0,
                'habilidad': jugador.valoracion_habilidad or 0,
            },
            'totales': {
                'goles': jugador.goles_totales or 0,
                'asistencias': jugador.asistencias_totales or 0,
                'atajadas': jugador.atajadas_totales or 0,
            },
            'partidos_totales': getattr(jugador, 'partidos_totales', None)
        }

        # ✅ Ahora sí, actualizar una sola vez
        jugador.actualizar_valoraciones()

        if tipo == 'amistoso':
            from django.db.models import Sum
            goles_local = EstadisticaAmistosa.objects.filter(
                partido=partido, jugador__in=partido.equipo_local.all(), jugo=True
            ).aggregate(total=Sum('goles'))['total'] or 0
            goles_visitante = EstadisticaAmistosa.objects.filter(
                partido=partido, jugador__in=partido.equipo_visitante.all(), jugo=True
            ).aggregate(total=Sum('goles'))['total'] or 0
            partido.goles_equipo_local = goles_local
            partido.goles_equipo_visitante = goles_visitante
            partido.save()

        request.session[session_key] = ultima
        return redirect('estadisticas_pasofinal', tipo=tipo, partido_id=partido.id)

    # GET: limpiar
    request.session.pop(session_key, None)

    return render(request, 'carga_estadisticas/carga_estadisticas_3.html', {
        'partido': partido,
        'tipo': tipo,
    })

def _pick_max_positive(d):
    if not d:
        return (None, 0)
    k, v = max(d.items(), key=lambda x: x[1])
    return (k, v) if v > 0 else (None, 0)

def add_mock_context(ctx, scenario='both'):
    # ---------- muestras base ----------
    # Valoraciones ANTES y NUEVAS
    v_ant = {
        'ataque': 6.2, 'defensa': 5.1, 'creatividad': 6.9, 'portero': 3.4, 'habilidad': 6.0
    }
    v_new = {
        'ataque': 6.5, 'defensa': 6.0, 'creatividad': 7.1, 'portero': 3.4, 'habilidad': 6.2
    }
    dv = {k: round(v_new[k] - v_ant[k], 2) for k in v_ant}  # deltas valoraciones

    # Totales ANTES y deltas del partido (confiable)
    t_ant = {'goles': 10, 'asistencias': 7, 'atajadas': 1}
    dt_part = {'goles': 2, 'asistencias': 1, 'atajadas': 0}
    t_new = {k: t_ant[k] + dt_part[k] for k in t_ant}

    # ---------- aplicar según escenario ----------
    if scenario in ('both', 'valor'):
        ctx['valoraciones_anteriores'] = v_ant
        ctx['valoraciones_nuevas'] = v_new
        ctx['deltas_val'] = dv
        mk, md = _pick_max_positive(dv)
        ctx['mejor_valoracion'] = {
            'tipo': mk, 'anterior': v_ant.get(mk, 0) if mk else 0,
            'nuevo': v_new.get(mk, 0) if mk else 0,
            'delta': md
        } if mk else None

    if scenario in ('both', 'total'):
        ctx['totales_anteriores'] = t_ant
        ctx['totales_nuevos'] = t_new
        ctx['deltas_tot'] = dt_part
        mk, md = _pick_max_positive(dt_part)
        ctx['mejor_total'] = {
            'tipo': mk, 'anterior': t_ant.get(mk, 0) if mk else 0,
            'nuevo': (t_ant.get(mk, 0) + md) if mk else 0,
            'delta': md
        } if mk else None

    if scenario == 'none':
        # Fuerza el fallback
        ctx['mejor_valoracion'] = None
        ctx['mejor_total'] = None
        ctx['deltas_val'] = {k: 0 for k in ('ataque','defensa','creatividad','portero','habilidad')}
        ctx['deltas_tot'] = {k: 0 for k in ('goles','asistencias','atajadas')}
        # (opcional) totales y valoraciones para el template
        ctx['valoraciones_anteriores'] = v_ant
        ctx['valoraciones_nuevas'] = v_ant
        ctx['totales_anteriores'] = t_ant
        ctx['totales_nuevos'] = t_ant

    # Flag de fallback
    ctx['solo_partido_sumado'] = (ctx.get('mejor_valoracion') is None and ctx.get('mejor_total') is None)
    # Un número simpático para el mensaje
    ctx['partidos_totales_nuevos'] = ctx.get('partidos_totales_nuevos') or 23

    # Frase de arriba (por si querés que aparezca siempre algo)
    ctx['ultima_frase'] = ctx.get('ultima_frase') or '¡Estadísticas registradas!'

    return ctx

@login_required
def estadisticas_pasofinal(request, tipo, partido_id):
    partido, EstadisticaModel = get_partido_y_estadisticas(tipo, partido_id)
    jugador = Jugador.objects.get(user=request.user)

    # Frase final desde sesión
    session_key_ultima = f'ultima_frase_{partido.id}'
    ultima = request.session.pop(session_key_ultima, "")

    # Snapshot previo (tomado en paso3) desde sesión
    snapshot_key = f'snapshot_stats_{partido.id}'
    snapshot = request.session.pop(snapshot_key, None) or {}

    # ⚠️ PRIMERO: obtener la estadística del partido del jugador
    estadistica = EstadisticaModel.objects.filter(partido=partido, jugador=jugador).first()

    # Asegurarnos de tener los valores actuales del jugador
    try:
        jugador.refresh_from_db()
    except Exception:
        pass

    # Valores NUEVOS (post-actualización)
    valoraciones_nuevas = {
        'ataque': getattr(jugador, 'valoracion_ataque', 0) or 0,
        'defensa': getattr(jugador, 'valoracion_defensa', 0) or 0,
        'creatividad': getattr(jugador, 'valoracion_creatividad', 0) or 0,
        'portero': getattr(jugador, 'valoracion_portero', 0) or 0,
        'habilidad': getattr(jugador, 'valoracion_habilidad', 0) or 0,
    }
    totales_nuevos = {
        'goles': getattr(jugador, 'goles_totales', 0) or 0,
        'asistencias': getattr(jugador, 'asistencias_totales', 0) or 0,
        'atajadas': getattr(jugador, 'atajadas_totales', 0) or 0,
    }

    # Valores ANTERIORES (del snapshot) o fallback a los nuevos
    valoraciones_anteriores = snapshot.get('valoraciones', {k: valoraciones_nuevas[k] for k in valoraciones_nuevas})
    totales_anteriores = snapshot.get('totales', {k: totales_nuevos[k] for k in totales_nuevos})

    # DELTAS de valoraciones = nuevos - anteriores
    deltas_val = {
        k: round((valoraciones_nuevas[k] or 0) - (valoraciones_anteriores.get(k, valoraciones_nuevas[k]) or 0), 2)
        for k in valoraciones_nuevas
    }

    # DELTAS de TOTALES basados en ESTE partido (confiable)
    if estadistica:
        deltas_tot_partido = {
            'goles': int(getattr(estadistica, 'goles', 0) or 0),
            'asistencias': int(getattr(estadistica, 'asistencias', 0) or 0),
            'atajadas': int(getattr(estadistica, 'atajadas', 0) or 0),
        }
    else:
        deltas_tot_partido = {'goles': 0, 'asistencias': 0, 'atajadas': 0}

    def pick_max_positive(d):
        if not d: return (None, 0)
        k, v = max(d.items(), key=lambda x: x[1])
        return (k, v) if v > 0 else (None, 0)

    # Mejor valoración
    mejor_val_key, mejor_val_delta = pick_max_positive(deltas_val)
    mejor_valoracion = None
    if mejor_val_key:
        mejor_valoracion = {
            'tipo': mejor_val_key,
            'anterior': valoraciones_anteriores.get(mejor_val_key, 0) or 0,
            'nuevo': valoraciones_nuevas.get(mejor_val_key, 0) or 0,
            'delta': mejor_val_delta,
        }

    # Mejor total (por partido)
    mejor_tot_key, mejor_tot_delta = pick_max_positive(deltas_tot_partido)
    mejor_total = None
    if mejor_tot_key:
        # usar snapshot si existe; si no, reconstruir anterior desde "nuevos - delta"
        if snapshot:
            anterior = int(totales_anteriores.get(mejor_tot_key, 0) or 0)
        else:
            anterior = max(0, int(totales_nuevos.get(mejor_tot_key, 0) or 0) - int(mejor_tot_delta or 0))
        nuevo = anterior + mejor_tot_delta
        mejor_total = {
            'tipo': mejor_tot_key,
            'anterior': anterior,
            'nuevo': nuevo,
            'delta': mejor_tot_delta,
        }
    

    solo_partido_sumado = (mejor_valoracion is None and mejor_total is None)
    partidos_totales_nuevos = getattr(jugador, 'partidos_totales', None)
    
    context = {
        'ocultar_navbar': True,
        'partido': partido,
        'estadistica': estadistica,
        'tipo': tipo,
        'ultima_frase': ultima,

        # tarjetas
        'mejor_valoracion': mejor_valoracion,
        'mejor_total': mejor_total,
        'solo_partido_sumado': solo_partido_sumado,
        'partidos_totales_nuevos': partidos_totales_nuevos,

        # opcional para debug
        'valoraciones_anteriores': valoraciones_anteriores,
        'valoraciones_nuevas': valoraciones_nuevas,
        'totales_anteriores': totales_anteriores,
        'totales_nuevos': totales_nuevos,
        'deltas_val': deltas_val,
        'deltas_tot': deltas_tot_partido,
    }

    # Activa mock con ?mock=...
    mock_mode = (request.GET.get('mock') or '').lower().strip()
    if mock_mode in ('both', 'valor', 'total', 'none'):
        context = add_mock_context(context, scenario=mock_mode)
    elif mock_mode == '1' or mock_mode == 'true':
        context = add_mock_context(context, scenario='both')  # por defecto

    return render(request, 'carga_estadisticas/carga_estadisticas_final.html', context)

@login_required
def amistosos(request):
    return render(request, 'app_torneo_f5/amistosos.html')
from urllib.parse import quote as urlquote
def auth(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.GET.get('logged_out') == '1':
        messages.info(request, "Sesión cerrada correctamente.")

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not getattr(user, 'email_verified', False):
                logout(request)
                messages.error(request, "Debes verificar tu correo antes de iniciar sesión.", extra_tags='username')
                return redirect('login')

            login(request, user)
            return redirect(next_url or 'home')

        # Si el form es inválido, pasamos errores como messages con tags
        for field, errs in form.errors.items():
            for err in errs:
                messages.error(request, err, extra_tags=field)
        return redirect('login')

    form = LoginForm()
    google_enabled = bool(settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY)
    return render(request, 'app_torneo_f5/login.html', {'form': form, 'google_enabled': google_enabled})

""" @login_required
def torneos_del_usuario(request):
    jugador = get_object_or_404(Jugador, user=request.user)

    # Opcional: filtrar membresías activas del jugador (estado HABILITADO y sin baja)
    membresias_activas = MiembroEquipo.objects.filter(
        jugador=jugador,
        estado=MiembroEquipo.HABILITADO,
        fecha_baja__isnull=True,
    ).select_related('equipo')

    # Torneos donde participa al menos un equipo en el que el jugador es miembro activo
    torneos = (
        Torneo.objects
        .filter(participacionequipotorneo__equipo__miembroequipo__in=membresias_activas)
        .distinct()
        .prefetch_related(
            Prefetch(
                'participacionequipotorneo_set',
                queryset=ParticipacionEquipoTorneo.objects.select_related('equipo'),
            )
        )
    )

    return render(request, 'mis_torneos/torneos_usuario.html', {'torneos': torneos}) """
    
from django.contrib.auth.decorators import login_required
from django.db.models import Q

@login_required
def torneos_del_usuario(request):
    user = request.user

    # jugador (si existe)
    jugador = Jugador.objects.filter(user=user).first()

    q_publicos = Q(visibilidad=Torneo.PUBLICO)

    q_privados = (
        Q(visibilidad=Torneo.PRIVADO) &
        (
            Q(creador=user) |
            Q(encargados_carga=user) |
            (Q(inscripcion__jugador=jugador) if jugador else Q(pk__isnull=True))
        )
    )

    torneos = (
        Torneo.objects
        .filter(q_publicos | q_privados)
        .distinct()
        .order_by('-dia_inicio')
    )

    return render(request, 'mis_torneos/torneos_usuario.html', {
        'torneos': torneos
    })



from django.db import transaction
from django.core.mail import send_mail

# views.py
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.core.mail import send_mail

from ..forms import RegistroManualForm
from ..models import PerfilUsuario, Jugador  # tus modelos
from django.core.mail import send_mail
from django.conf import settings

def registro_usuario(request):
    if request.method == 'POST':
        form = RegistroManualForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()


# views.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from app_torneo_f5.forms import RegistroManualForm
from app_torneo_f5.models import PerfilUsuario, Jugador
from app_torneo_f5.tokens import email_verification_token   # lo que definimos antes

def _send_verification_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token  = email_verification_token.make_token(user)

    site_url = getattr(settings, "SITE_URL", request.build_absolute_uri("/").rstrip("/"))
    verify_path = reverse('confirmar_registro', kwargs={'uidb64': uidb64, 'token': token})
    verify_url  = f"{site_url}{verify_path}"

    subject = "🎉 Bienvenido a Ticas — Verificá tu correo"
    text = f"""Hola {user.first_name or user.username},

Gracias por registrarte en Ticas. Para activar tu cuenta, verificá tu correo con este enlace:

{verify_url}

Si no creaste esta cuenta, ignorá este mensaje.
"""
    html = f"""
    <p>Hola <b>{user.first_name or user.username}</b>,</p>
    <p>Gracias por registrarte en <b>Ticas</b>. Para activar tu cuenta, hacé clic en el botón:</p>
    <p><a href="{verify_url}" target="_blank" 
          style="display:inline-block;padding:12px 20px;background:#4F9639;color:#fff;
                 text-decoration:none;border-radius:6px;font-weight:600;">
        Verificar mi correo
    </a></p>
    <p>O copiá y pegá este link en tu navegador:<br>
    <a href="{verify_url}">{verify_url}</a></p>
    """

    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


def registro_usuario(request):
    if request.method == 'POST':
        form = RegistroManualForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.email_verified = False  # 👈 aseguramos que arranca no verificado
                user.save()

                PerfilUsuario.objects.get_or_create(user=user)
                Jugador.objects.get_or_create(
                    user=user,
                    defaults=dict(
                        nombre=(f"{user.first_name} {user.last_name}".strip() or user.username),
                        genero='otro',
                        provincia="Sin definir",
                        ciudad="Sin definir",
                        contacto=user.email,
                    )
                )

            # ✅ Envío del mail de verificación
            if user.email:
                _send_verification_email(request, user)

            # redirigimos al login con query param para mostrar modal
            url = reverse('login') + '?register=ok'
            return redirect(url)
    else:
        form = RegistroManualForm()

    return render(request, 'app_torneo_f5/registro_usuario.html', {'form': form})


# views.py
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from app_torneo_f5.models import CustomUser
from app_torneo_f5.tokens import email_verification_token


def confirmar_registro(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=["email_verified"])

        # 👇 indicar backend explícitamente
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        return redirect("home")
    else:
        return render(request, "app_torneo_f5/confirmar_error.html", {
            "mensaje": "El enlace de verificación no es válido o ya fue usado."
        })

    
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from ..models import PartidoAmistoso, Partido, EstadisticaAmistosa, EstadisticaJugador, Inscripcion, Participacion, Jugador
from ..graficos import obtener_promedios_mensuales_amistoso, generar_radar_valoraciones, generar_grafico_resultados, generar_grafico_calificaciones, obtener_promedios_mensuales_torneo

@login_required
def mi_perfil(request):
    """Redirige al perfil del jugador logueado."""
    jugador_id = request.user.jugador.id
    return redirect('perfil', jugador_id=jugador_id)

    
@login_required
def perfil(request, jugador_id):
    from django.utils.safestring import mark_safe
    jugador = get_object_or_404(Jugador, id=jugador_id)
    
    # ¿El perfil es del usuario logueado?
    es_propio = hasattr(request.user, 'jugador') and request.user.jugador.id == jugador.id
    # URL de configuración solo si es propio
    url_config = reverse('configuracion_perfil', args=[jugador.id]) if es_propio else None
    
    partidos_jugador = PartidoAmistoso.objects.filter(jugadores=jugador)
    radar_base64 = generar_radar_valoraciones(jugador)
    if jugador.provincia:
        iniciales_provincia = ''.join([w[0].upper() for w in jugador.provincia.split()])
    else:
        iniciales_provincia = ""
    
    url_config = reverse('configuracion_perfil', args=[jugador.id])
    # PARTIDOS AMISTOSOS
    partidos_amistosos_jugados = jugador.partidoamistoso_set.filter(
        jugado=True,
        cancelado=False
    )
    
    ganados_amistosos = sum(
        1 for p in partidos_amistosos_jugados
        if (p.goles_equipo_local > p.goles_equipo_visitante and p.equipo_local.filter(id=jugador.id).exists())
        or (p.goles_equipo_visitante > p.goles_equipo_local and p.equipo_visitante.filter(id=jugador.id).exists())
    )
    
    empatados_amistosos = sum(1 for p in partidos_amistosos_jugados if p.goles_equipo_local == p.goles_equipo_visitante)
    perdidos_amistosos = partidos_amistosos_jugados.count() - ganados_amistosos - empatados_amistosos

    # PARTIDOS DE TORNEO
    from django.db.models import Q

    partidos_torneo_jugados = Partido.objects.filter(
        jugado=True,
        estadisticasjugadorpartido__miembro_equipo__jugador=jugador,
        estadisticasjugadorpartido__jugo=True
    ).distinct()
    
    ganados_torneos = 0

    for p in partidos_torneo_jugados:

        # ¿En qué equipo jugó el jugador?
        estadistica = EstadisticasJugadorPartido.objects.filter(
            partido=p,
            miembro_equipo__jugador=jugador,
            jugo=True
        ).select_related("miembro_equipo__equipo").first()

        if not estadistica:
            continue

        participacion = estadistica.miembro_equipo.equipo

        if participacion == p.equipo_local and p.goles_local > p.goles_visitante:
            ganados_torneos += 1
        elif participacion == p.equipo_visitante and p.goles_visitante > p.goles_local:
            ganados_torneos += 1
    
    empatados_torneos = sum(
        1 for p in partidos_torneo_jugados
        if p.goles_local == p.goles_visitante
    )
    
    perdidos_torneos = len(partidos_torneo_jugados) - ganados_torneos - empatados_torneos
    
    for p in partidos_jugador:
        p.marcar_como_jugado_si_finalizado()

    default_logo = 'static/jugador.png'

    def get_nombre_logo(participacion):
        if participacion and participacion.equipo:
            equipo = participacion.equipo
            return (
                equipo.nombre,
                equipo.escudo.url if equipo.escudo else default_logo
            )
        return "Equipo", default_logo

    def construir_datos_partido_amistoso(partido):
        nombre1 = "Equipo 1"
        logo1 = 'static/jugador.png'  # tu default
        nombre2 = "Equipo 2"
        logo2 = 'static/jugador.png'
        partidos = jugador.partidoamistoso_set.filter(jugado=True)
    
        # Equipo del jugador en ese partido (1 local / 2 visitante)
        equipo_jugador = None
        if partido.equipo_local.filter(id=jugador.id).exists():
            equipo_jugador = 1
        elif partido.equipo_visitante.filter(id=jugador.id).exists():
            equipo_jugador = 2
    
        # Ganador
        if (partido.goles_equipo_local or 0) < (partido.goles_equipo_visitante or 0):
            equipo_ganador = 2
        elif (partido.goles_equipo_local or 0) > (partido.goles_equipo_visitante or 0):
            equipo_ganador = 1
        else:
            equipo_ganador = 0
    
        # 👇 NUEVO: escudos por color del local
        esc_local, esc_visit = escudos_por_color(getattr(partido, 'color_equipo_local', 'bg-d-equipo1'))
    
        return {
            'id': partido.id,
            'dia': partido.dia,
            'url_configuracion': url_config,
            'color_equipo_local': partido.color_equipo_local,
            'color_equipo_visitante': partido.color_equipo_visitante,
            'hora_inicio': partido.hora_inicio,
            'nombre_cancha': partido.cancha or "Sin definir",
    
            # Nombres y LOGOS (para amistosos usamos escudos por color)
            'equipo_1_nombre': nombre1,
            'equipo_1_logo': esc_local,        # <— usar en el template con {% static ... %}
            'equipo_1_goles': partido.goles_equipo_local or 0,
    
            'equipo_2_nombre': nombre2,
            'equipo_2_logo': esc_visit,        # <— usar en el template con {% static ... %}
            'equipo_2_goles': partido.goles_equipo_visitante or 0,
    
            'equipo_jugador': equipo_jugador,
            'partidos': partidos,
            'ganados': ganados_amistosos,
            'empatados': empatados_amistosos,
            'perdidos': perdidos_amistosos,
            'equipo_ganador': equipo_ganador,
            'goles_jugador': EstadisticaAmistosa.objects.filter(
                partido=partido,
                jugador=jugador,
                jugo=True
            ).aggregate(total=Coalesce(Sum('goles'), 0))['total'],
        }
    

    def construir_datos_partido_torneo(partido):
        nombre1, logo1 = get_nombre_logo(partido.equipo_local)
        nombre2, logo2 = get_nombre_logo(partido.equipo_visitante)
        partidos = Partido.objects.filter(
            estadisticas__jugador=jugador,
            jugado=True
        ).distinct()

        equipo_jugador = None
        estadistica = EstadisticasJugadorPartido.objects.filter(
            partido=partido,
            miembro_equipo__jugador=jugador,
            jugo=True
        ).select_related("miembro_equipo__equipo").first()
        
        equipo_jugador = None
        
        if estadistica:
            participacion = estadistica.miembro_equipo.equipo
        
            if participacion == partido.equipo_local:
                equipo_jugador = 1
            elif participacion == partido.equipo_visitante:
                equipo_jugador = 2
            
        if partido.goles_local < partido.goles_visitante:    
            equipo_ganador = 2
        elif partido.goles_local > partido.goles_visitante:
            equipo_ganador = 1
        else:
            equipo_ganador = 0

        return {
            'id': partido.id,
            'dia': partido.dia,
            'hora_inicio': partido.hora_inicio,
            'nombre_cancha': partido.cancha or "Sin definir",
            'equipo_1_nombre': nombre1,
            'equipo_1_logo': logo1,
            'equipo_1_goles': partido.goles_local or 0,
            'equipo_2_nombre': nombre2,
            'equipo_2_logo': logo2,
            'equipo_2_goles': partido.goles_visitante or 0,
            'equipo_jugador': equipo_jugador,
            'partidos': partidos,
            'ganados': ganados_torneos,
            'empatados': empatados_torneos,
            'perdidos': perdidos_torneos,
            'equipo_ganador': equipo_ganador,
            'goles_jugador': EstadisticasJugadorPartido.objects.filter(
                partido=partido,
                miembro_equipo__jugador=jugador,
                jugo=True
            ).aggregate(
                total=Coalesce(Sum('goles'), 0)
            )['total'],
        }
        
    for p in PartidoAmistoso.objects.filter(jugadores=jugador, cancelado=False):
        p.marcar_como_jugado_si_finalizado()

    ultimos_amistosos = [
        construir_datos_partido_amistoso(p)
        for p in PartidoAmistoso.objects
                .filter(jugadores=jugador, jugado=True, cancelado=False)
                .order_by('-dia')[:5]
    ]

    partidos_torneo = Partido.objects.filter(
        jugado=True,
        estadisticasjugadorpartido__miembro_equipo__jugador=jugador,
        estadisticasjugadorpartido__jugo=True
    ).distinct().order_by('-dia')[:5]


    ultimos_torneos = [construir_datos_partido_torneo(p) for p in partidos_torneo]
    stats_amistosos = EstadisticaAmistosa.objects.filter(jugador=jugador)
    stats_torneos = EstadisticasJugadorPartido.objects.filter(
        miembro_equipo__jugador=jugador,
        partido__torneo__isnull=False,
        partido__jugado=True,
        jugo=True
    )

    def calcular_totales(stats):
        return {
            'partidos': stats.count(),
            'goles': sum(s.goles for s in stats),
            'atajadas': sum(getattr(s, 'atajadas', 0) for s in stats),
            'asistencias': sum(s.asistencias for s in stats),
        }

    inscripcion = Inscripcion.objects.filter(jugador=jugador).order_by('-id').first()
    equipo_actual = inscripcion.equipo if inscripcion else None
    torneo_actual = inscripcion.torneo if inscripcion else None
    participacion = Participacion.objects.filter(equipo=equipo_actual, torneo=torneo_actual).first()

    if participacion:
        todas = Participacion.objects.filter(torneo=torneo_actual).order_by('-puntos', '-dif', '-gf')
        posicion = list(todas).index(participacion) + 1
    else:
        posicion = "?"
        
    grafico_resultados_amistosos = generar_grafico_resultados(
        ganados_amistosos, empatados_amistosos, perdidos_amistosos
    )

    grafico_resultados_torneos = generar_grafico_resultados(
        ganados_torneos, empatados_torneos, perdidos_torneos
    )
    
    def calcular_promedio(total, partidos):
        if partidos == 0:
            return 0
        porcentaje = (total / partidos) * 100
        return int(porcentaje) if porcentaje.is_integer() else round(porcentaje, 2)

    promedios_torneo = obtener_promedios_mensuales_torneo(jugador)
    img_base64_torneo = generar_grafico_calificaciones(promedios_torneo) if promedios_torneo else None
    
    promedios_amistoso = obtener_promedios_mensuales_amistoso(jugador) 
    img_base64_amistoso = generar_grafico_calificaciones(promedios_amistoso) if promedios_amistoso else None

    print(es_propio)
    context = {
        'jugador': jugador,
        'url_config': url_config,
        'es_propio': es_propio,
        'iniciales_provincia': iniciales_provincia,
        'ultimos_partidos': ultimos_amistosos[:3],
        'estadisticas_amistosos': calcular_totales(stats_amistosos),
        'estadisticas_torneos': calcular_totales(stats_torneos),
        'equipo_actual': equipo_actual,
        'torneo_actual': torneo_actual,
        'posicion_actual': posicion,
        'ultimos_amistosos': ultimos_amistosos,
        'ultimos_torneos': ultimos_torneos,
        'radar_chart': radar_base64,
        'grafico_resultados_amistosos': grafico_resultados_amistosos,
        'grafico_resultados_torneos': grafico_resultados_torneos,
        
        'grafico_calificaciones_torneo': mark_safe(img_base64_torneo),
        'grafico_calificaciones_amistoso': mark_safe(img_base64_amistoso),
        
        'ganados_amistosos': ganados_amistosos,
        'promedio_ganados_amistosos': calcular_promedio(ganados_amistosos, partidos_amistosos_jugados.count()),
        'empatados_amistosos': empatados_amistosos,
        'promedio_empatados_amistosos': calcular_promedio(empatados_amistosos, partidos_amistosos_jugados.count()),
        'perdidos_amistosos': perdidos_amistosos,
        'promedio_perdidos_amistosos': calcular_promedio(perdidos_amistosos, partidos_amistosos_jugados.count()),
        
        'ganados_torneos': ganados_torneos,
        'promedio_ganados_torneos': calcular_promedio(ganados_torneos, partidos_torneo_jugados.count()),
        'empatados_torneos': empatados_torneos,
        'promedio_empatados_torneos': calcular_promedio(empatados_torneos, partidos_torneo_jugados.count()),
        'perdidos_torneos': perdidos_torneos,
        'promedio_perdidos_torneos': calcular_promedio(perdidos_torneos, partidos_torneo_jugados.count()),
    } 
    return render(request, 'perfil/mi_perfil.html', context)

@login_required
def configuracion_perfil(request, pk):
    jugador = get_object_or_404(Jugador, id=pk, user=request.user)
    posicion_choices = Jugador._meta.get_field('posicion_preferida').choices
    pie_choices = Jugador._meta.get_field('pie_preferido').choices

    if request.method == 'POST':
        form = JugadorForm(request.POST, request.FILES, instance=jugador)
        if form.is_valid():
            jugador = form.save(commit=False)
    
            if jugador.fecha_nacimiento:
                hoy = date.today()
                jugador.edad = (
                    hoy.year - jugador.fecha_nacimiento.year
                    - ((hoy.month, hoy.day) < (jugador.fecha_nacimiento.month, jugador.fecha_nacimiento.day))
                )
    
            jugador.save()
            return redirect('mi_perfil')
    else:
        form = JugadorForm(instance=jugador)

    context = {
        'jugador': jugador,
        'posicion_choices': posicion_choices,
        'pie_choices': pie_choices,
        'form': form,
        'ocultar_navbar': True,
        'url_volver': reverse('mi_perfil'),
    }
    return render(request, 'perfil/configuracion_perfil.html', context)

def logout_view(request):
    logout(request)
    return redirect('login')

""" @login_required
def equipos_del_usuario(request):
    # Buscamos el Jugador asociado al user logueado
    jugador = Jugador.objects.filter(user=request.user).first()
    if not jugador:
        # Si el usuario aún no tiene perfil Jugador, devolvemos vacío
        return render(request, 'mis_equipos/equipos_usuario.html', {'equipos': Equipo.objects.none()})

    # Trae sólo equipos donde ese Jugador está inscripto
    equipos = (
        Equipo.objects
        .filter(inscripcion__jugador=jugador)  # reverse a través de Inscripcion (FK equipo)
        .distinct()
        .order_by('nombre')
    )

    return render(request, 'mis_equipos/equipos_usuario.html', {
        'equipos': equipos
    }) """
    
@login_required
def equipos_del_usuario(request):

    # Si el usuario es encargado de carga en algún torneo
    """ if request.user.torneos_carga.exists():
        equipos = Equipo.objects.all().order_by('nombre')
    else:
        jugador = Jugador.objects.filter(user=request.user).first()

        if not jugador:
            equipos = Equipo.objects.none()
        else:
            equipos = (
                Equipo.objects
                .filter(inscripcion__jugador=jugador)
                .distinct()
                .order_by('nombre')
            ) """
    
    equipos = Equipo.objects.all().order_by('nombre')

    return render(request, 'mis_equipos/equipos_usuario.html', {
        'equipos': equipos
    })

 
# ---- Etiquetas y orden de rondas ----
RONDA_LABEL = {
    Partido.CUARTOS:   "Cuartos",
    Partido.SEMIFINAL: "Semis",
    Partido.FINAL:     "Final",
}
COPA_LABEL = {
    Partido.COPAORO:   "Copa Oro",
    Partido.COPAPLATA: "Copa AniVersario",
}
# Para ordenar: FINAL < SEMIS < CUARTOS
RONDA_ORDER = {
    Partido.FINAL: 0,
    Partido.SEMIFINAL: 1,
    Partido.CUARTOS: 2,
    'NONE': 99,
}

from django.urls import reverse, NoReverseMatch
from types import SimpleNamespace

def _url_partido(p):
    try:
        return reverse("detalle_partido", args=[p.id])
    except NoReverseMatch:
        return "#"

def _team_dict(pet):
    if not pet:
        return {"escudo": "", "nombre": "A confirmar"}
    eq = pet.equipo
    return {
        "escudo": (getattr(eq, "escudo", None).url if getattr(eq, "escudo", None) else ""),
        "nombre": eq.nombre or "A confirmar",
    }

def _serialize_partido(p):
    return {
        "url_detalle": _url_partido(p),
        "equipo_1": _team_dict(p.equipo_local),
        "equipo_2": _team_dict(p.equipo_visitante),
        "jugado": p.jugado,
        "goles_equipo_1": p.goles_local,
        "goles_equipo_2": p.goles_visitante,
        "cancha": {"nombre": p.cancha.nombre} if p.cancha else None,
        "dia": p.dia,
        "hora_inicio": p.hora_inicio,
    }

# ---------------------------------------------------------

@login_required
def detalle_torneo(request, torneo_id):
    from collections import defaultdict, OrderedDict
    from datetime import date

    torneo = get_object_or_404(Torneo, id=torneo_id)
    jugador_actual = get_object_or_404(Jugador, user=request.user)

    inscripcion = (
        Inscripcion.objects
        .filter(jugador=jugador_actual)
        .order_by('-id')
        .first()
    )
    equipo_actual = inscripcion.equipo if inscripcion else None

    # ===============================
    # Partidos del torneo (nuevo esquema)
    # ===============================
    partidos_qs = (
        Partido.objects
        .filter(torneo=torneo)
        .select_related('equipo_local__equipo', 'equipo_visitante__equipo', 'cancha')
        .order_by('etapa', 'fecha', 'dia', 'hora_inicio', 'id')
    )

    # --- Estructuras para el front
    partidos_grupo_por_fecha = defaultdict(list)
    partidos_oro_por_ronda   = defaultdict(list)
    partidos_plata_por_ronda = defaultdict(list)
    partidos_otros = []

    fechas_grupos = set()
    rondas_oro = set()
    rondas_plata = set()

    # permisos
    es_encargado = torneo.encargados_carga.filter(pk=request.user.pk).exists()

    for p in partidos_qs:
        # Aliases usados en el template
        p.equipo_1 = getattr(p.equipo_local, "equipo", None)
        p.equipo_2 = getattr(p.equipo_visitante, "equipo", None)
        p.goles_equipo_1 = p.goles_local
        p.goles_equipo_2 = p.goles_visitante
        p.propuesta_fake = getattr(p, "propuesta", SimpleNamespace(cerrada=True))
        p.propuesta_info = p.propuesta_fake

        # permisos/URLs
        def es_capitan_de(pet):
            try:
                return bool(pet and pet.equipo and pet.equipo.capitan and
                            pet.equipo.capitan.jugador_id == jugador_actual.id)
            except Exception:
                return False

        es_capitan = es_capitan_de(getattr(p, 'equipo_local', None)) or es_capitan_de(getattr(p, 'equipo_visitante', None))
        faltan_datos = (not p.dia) or (not p.hora_inicio) or (not p.cancha)
        p.puede_proponer = (
            faltan_datos and (
                (torneo.modo_seleccion_partido == Torneo.POR_DEFECTO and es_encargado) or
                (torneo.modo_seleccion_partido == Torneo.PROPUESTA and es_capitan)
            )
        )

        if p.jugado:
            p.url_detalle = reverse('detalle_partido', args=['torneo', p.id])
        elif not p.dia or not p.hora_inicio or not p.cancha:
            p.url_detalle = reverse('detalle_propuesta', args=[p.id])
        else:
            p.url_detalle = reverse('detalle_partido', args=['torneo', p.id])
            
        # --- ganador: 1 (local), 2 (visitante), 0 (empate), None (sin definir)
        g1 = p.goles_equipo_1
        g2 = p.goles_equipo_2
        p.ganador = None
        try:
            if p.jugado and g1 is not None and g2 is not None:
                if int(g1) > int(g2):
                    p.ganador = 1
                elif int(g2) > int(g1):
                    p.ganador = 2
                else:
                    p.ganador = 0
        except (TypeError, ValueError):
            p.ganador = None

        # === Clasificación
        if p.etapa == Partido.ZONAS:
            if p.equipo_local_id and p.equipo_visitante_id:
                f = int(p.fecha or 1)
                partidos_grupo_por_fecha[f].append(p)
                fechas_grupos.add(f)

        elif p.etapa == Partido.COPAORO:
            r = p.ronda or 'NONE'
            partidos_oro_por_ronda[r].append(p)
            rondas_oro.add(r)

        elif p.etapa == Partido.COPAPLATA:
            r = p.ronda or 'NONE'
            partidos_plata_por_ronda[r].append(p)
            rondas_plata.add(r)

        else:
            partidos_otros.append(p)

    # ---- Ordenar grupos por fecha y hora
    fechas_grupos = sorted(fechas_grupos)
    partidos_grupo_por_fecha = OrderedDict(
        (f, sorted(partidos_grupo_por_fecha[f],
                   key=lambda x: (x.dia or date.min, x.hora_inicio or None, x.id)))
        for f in fechas_grupos
    )

    # ---- Ordenar rondas de copas
    rondas_oro = sorted(rondas_oro, key=lambda r: RONDA_ORDER.get(r, 99))
    rondas_plata = sorted(rondas_plata, key=lambda r: RONDA_ORDER.get(r, 99))

    # ===============================
    # ETAPA ACTIVA (única, para el header)
    # ===============================
    # Si hay partidos de ZONAS pendientes => mostrar "Fecha X (Total)"
    etapa_activa_label = "—"
    if fechas_grupos:
        total_fechas = max(fechas_grupos)
        # primera fecha con partidos sin jugar
        pendiente = next(
            (f for f in fechas_grupos if any(not p.jugado for p in partidos_grupo_por_fecha.get(f, []))),
            None
        )
        if pendiente is not None and any(partidos_grupo_por_fecha.get(pendiente, [])):
            etapa_activa_label = f"Fecha {pendiente} ({total_fechas})"
        elif any(partidos_grupo_por_fecha.get(fechas_grupos[-1], [])):
            # si no hay pendientes, muestro la última
            etapa_activa_label = f"Fecha {fechas_grupos[-1]} ({total_fechas})"

    RONDA_SEQ = [Partido.CUARTOS, Partido.SEMIFINAL, Partido.FINAL]

    def _ronda_activa_por_finalizacion(lista_partidos_por_ronda):
        """
        Devuelve la ronda actual (CUARTOS/SEMIFINAL/FINAL) según progreso real:
        - La ronda activa es la PRIMERA ronda que no está COMPLETAMENTE FINALIZADA.
        - Una ronda se considera finalizada si TODOS sus partidos tienen estado FINALIZADO.
        """
        rondas_presentes = [r for r in RONDA_SEQ if lista_partidos_por_ronda.get(r)]
        if not rondas_presentes:
            return None

        for r in rondas_presentes:
            partidos = lista_partidos_por_ronda[r]
            ronda_terminada = all(p.estado == Partido.FINALIZADO for p in partidos)
            if not ronda_terminada:
                return r

        return rondas_presentes[-1]

    if etapa_activa_label == "—":
        r_oro = _ronda_activa_por_finalizacion(partidos_oro_por_ronda)
        if r_oro:
            etapa_activa_label = RONDA_LABEL.get(r_oro, str(r_oro))
        else:
            r_plata = _ronda_activa_por_finalizacion(partidos_plata_por_ronda)
            if r_plata:
                etapa_activa_label = RONDA_LABEL.get(r_plata, str(r_plata))


    # Para compatibilidad con el template que itera fases_detalle:
    fases_detalle = [{"etapa": etapa_activa_label}]

    # ===============================
    # Selectores (COMBINADO: Fechas + Copas)
    # ===============================
    selector_etapas = []
    for f in fechas_grupos:
        selector_etapas.append({"tipo": "grupo", "nombre": f"Fecha {f}", "numero": f})

    es_eliminacion_directa = not fechas_grupos

    for r in (Partido.CUARTOS, Partido.SEMIFINAL, Partido.FINAL):
        if r in rondas_oro:
            nombre = RONDA_LABEL[r] if es_eliminacion_directa else \
                     f"{RONDA_LABEL[r]} ({COPA_LABEL[Partido.COPAORO]})"

            selector_etapas.append({
                "tipo": "copa",
                "copa": Partido.COPAORO,
                "ronda": r,
                "numero": r,
                "nombre": nombre,
            })

    for r in (Partido.CUARTOS, Partido.SEMIFINAL, Partido.FINAL):
        if r in rondas_plata:
            nombre = RONDA_LABEL[r] if es_eliminacion_directa else \
                     f"{RONDA_LABEL[r]} ({COPA_LABEL[Partido.COPAPLATA]})"

            selector_etapas.append({
                "tipo": "copa",
                "copa": Partido.COPAPLATA,
                "ronda": r,
                "numero": r,
                "nombre": nombre,
            })

    # ===============================
    # CANTIDAD DE EQUIPOS
    # ===============================
    cantidad_equipos = (
        ParticipacionEquipoTorneo.objects
        .filter(torneo=torneo, estado=ParticipacionEquipoTorneo.HABILITADO)
        .count()
    )

    # ===============================
    # Rankings (igual que antes)
    # ===============================
    base_stats = (
        ParticipacionJugadorTorneo.objects
        .filter(torneo=torneo)
        .select_related("jugador", "equipo_torneo__equipo")
    )
    goleadores = base_stats.order_by("-goles", "equipo_torneo__equipo__nombre", "jugador__nombre")[:5]
    asistidores = base_stats.order_by("-asistencias", "equipo_torneo__equipo__nombre", "jugador__nombre")[:5]
    arqueros   = base_stats.order_by("-atajadas", "equipo_torneo__equipo__nombre", "jugador__nombre")[:5]

    # Compatibilidad con claves previas “fase”, “fase_tipo”, etc.
    fase = {"nombre": "Fase de grupos", "tipo": "GRUPOS",
            "etapa": (f"Fecha {min(fechas_grupos)}" if fechas_grupos else "—")}
    fase_tipo = "GRUPOS"
    es_eliminatoria = False

    torneo_empezado = bool(torneo.dia_inicio) and (torneo.dia_inicio <= date.today())

    # helpers legibles para el template
    oro_cuartos = partidos_oro_por_ronda.get(Partido.CUARTOS, [])
    oro_semis   = partidos_oro_por_ronda.get(Partido.SEMIFINAL, [])
    oro_final   = partidos_oro_por_ronda.get(Partido.FINAL, [])

    plata_cuartos = partidos_plata_por_ronda.get(Partido.CUARTOS, [])
    plata_semis   = partidos_plata_por_ronda.get(Partido.SEMIFINAL, [])
    plata_final   = partidos_plata_por_ronda.get(Partido.FINAL, [])


    context = {
        "torneo": torneo,
        "equipo_actual": equipo_actual,
        "fases_detalle": fases_detalle,         # ← ahora trae SOLO una etiqueta (activa)
        "etapa_activa_label": etapa_activa_label,
        "cantidad_equipos": cantidad_equipos,

        # compat
        "fase": fase,
        "fase_real_obj": None,
        "fase_tipo": fase_tipo,
        "es_eliminatoria": es_eliminatoria,

        # agrupaciones listas para pintar
        "partidos_grupo_por_fecha": partidos_grupo_por_fecha,        # {fecha: [Partido,...]}
        "partidos_oro_por_ronda": dict(partidos_oro_por_ronda),      # {ronda: [Partido,...]}
        "partidos_plata_por_ronda": dict(partidos_plata_por_ronda),  # {ronda: [Partido,...]}
        "tabla_plata": dict(partidos_plata_por_ronda),
        "partidos": partidos_otros,

        # selector combinado (fechas + copas)
        "selector_etapas": selector_etapas,

        "torneo_empezado": torneo_empezado,

        # rankings
        "goleadores": goleadores,
        "asistidores": asistidores,
        "arqueros": arqueros,
        
        "oro_cuartos": oro_cuartos,
        "oro_semis": oro_semis,
        "oro_final": oro_final,
        "plata_cuartos": plata_cuartos,
        "plata_semis": plata_semis,
        "plata_final": plata_final,
    }

    return render(request, "mis_torneos/detalle_torneo.html", context)


 
@login_required
def descripcion_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    context = {
        'torneo': torneo,
    }
    return render(request, 'mis_torneos/descripcion_torneo.html', context)

from app_torneo_f5.models import PartidoAmistoso
@login_required
def amistosos_disponibles(request):
    usuario = request.user

    try:
        jugador_actual = Jugador.objects.get(user=usuario)
    except Jugador.DoesNotExist:
        jugador_actual = None

    ya_cargados = EstadisticaAmistosa.objects.filter(jugador=jugador_actual).values_list('partido_id', flat=True)

    # Incluimos TODOS los partidos visibles para el usuario, sin filtrar por jugado todavía
    partidos_queryset = PartidoAmistoso.objects.annotate(num_jugadores=Count('jugadores')).filter(
        Q(num_jugadores__lt=F('max_jugadores')) |
        Q(creador=usuario) |
        Q(jugadores=jugador_actual)
    ).distinct()

    # 🔁 Marcar como jugados los que ya finalizaron
    for p in partidos_queryset:
        p.marcar_como_jugado_si_finalizado()

    # ✅ Mostrar todos excepto los finalizados donde el jugador ya cargó estadísticas
    partidos = [
        p for p in partidos_queryset
        if not (p.finalizado and p.id in ya_cargados)
    ]

    invitacion = request.GET.get('invitacion')
    partido = None
    if invitacion:
        partido = get_object_or_404(PartidoAmistoso, uuid=invitacion)

    return render(request, 'partidos_amistosos/lista_amistosos.html', {
        'partidos': partidos,
        'partido': partido,
        'jugador_actual': jugador_actual,
    })

    
@login_required
def crear_partido_amistoso(request):
    if request.method == 'POST':
        form = PartidoAmistosoForm(request.POST)
        if form.is_valid():
            partido = form.save(commit=False)
            partido.creador = request.user
            partido.save()
            return redirect('editar_partido_amistoso', pk=partido.pk)
        else:
            print("⚠️ Formulario inválido:", form.errors)
    else:
        form = PartidoAmistosoForm()
    return render(request, 'partidos_amistosos/crear_amistoso.html', {'form': form})

@login_required
def editar_partido_amistoso(request, pk):
    partido = get_object_or_404(PartidoAmistoso, pk=pk, creador=request.user)

    if request.method == 'POST':
        form = PartidoAmistosoForm(request.POST, instance=partido)
        if form.is_valid():
            partido = form.save(commit=False)
            equipo1_tipo = request.POST.get('tipo_equipo_1')
            equipo2_tipo = request.POST.get('tipo_equipo_2')

            if equipo1_tipo == 'jugadores':
                jugadores_equipo_1 = request.POST.getlist('jugadores_equipo_1')
            else:
                jugadores_equipo_1 = []

            if equipo2_tipo == 'jugadores':
                jugadores_equipo_2 = request.POST.getlist('jugadores_equipo_2')
            else:
                jugadores_equipo_2 = []

            todos_jugadores = jugadores_equipo_1 + jugadores_equipo_2
            partido.save()
            form.save_m2m()
            partido.jugadores.set(Jugador.objects.filter(id__in=todos_jugadores))

            return redirect('amistosos')
    else:
        form = PartidoAmistosoForm(instance=partido)

    jugadores = Jugador.objects.all()
    jugadores_ids = partido.jugadores.values_list('id', flat=True)

    return render(request, 'partidos_amistosos/editar_amistoso.html', {
        'form': form,
        'partido': partido,
        'jugadores': jugadores,
        'jugadores_ids': jugadores_ids
    })


@login_required
def aceptar_invitacion(request, uuid):
    jugador = Jugador.objects.filter(user=request.user).first()
    partido = get_object_or_404(PartidoAmistoso, uuid=uuid)

    if not jugador:
        messages.error(request, "No estás registrado como jugador.")
        return redirect('amistosos')

    invitacion, creada = Invitacion.objects.get_or_create(
        partido=partido,
        jugador=jugador,
        defaults={'enviado_por': partido.creador}
    )

    if not invitacion.aceptada:
        invitacion.aceptada = True
        invitacion.save()
        partido.jugadores.add(jugador)
        messages.success(request, "Te uniste al partido.")
    else:
        messages.info(request, "Ya aceptaste esta invitación.")

    return redirect('detalle_partido', tipo='amistoso', partido_id=partido.id)
    

def confirmar_invitacion(request, uuid):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")

    partido = get_object_or_404(PartidoAmistoso, uuid=uuid)
    if request.user not in partido.jugadores.all():
        partido.jugadores.add(request.user)
        messages.success(request, 'Te inscribiste al partido exitosamente.')
    else:
        messages.info(request, 'Ya estás inscrito en este partido.')

    return redirect('amistosos')

from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Value, CharField
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

# Modelos que usás en esta vista
from ..models import (
    Equipo, Participacion, Torneo, Partido, Propuesta,
    Jugador, EstadisticaJugador, PartidoAmistoso, Cancha
)

User = get_user_model()


@login_required
def detalle_amistoso(request, partido_id):
    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    jugadores = partido.jugadores.all()

    return render(request, 'partidos_amistosos/detalle_amistoso.html', {
        'partido': partido,
        'jugadores': jugadores,
    })


def detalle_equipo(request, pk):
    equipo = get_object_or_404(Equipo, id=pk)

    # integrantes aceptados
    integrantes = equipo.integrantes.all()

    # iniciales de provincia con resguardo si es None o vacío
    provincia = (equipo.provincia or "").strip()
    iniciales_provincia = ''.join(w[0].upper() for w in provincia.split()) if provincia else ""

    # participaciones activas y totales
    participaciones_activas = Participacion.objects.filter(
        equipo=equipo, sigue_en_competencia=True
    )
    torneos_activos = [p.torneo for p in participaciones_activas]

    # TODO: ajustar criterio real de victoria
    torneos_ganados = Participacion.objects.filter(equipo=equipo, puntos=100).count()

    total_partidos = sum(p.pj for p in participaciones_activas)
    total_goles = sum(p.gf for p in participaciones_activas)

    url_config = reverse('configuracion_equipo', args=[pk])

    # --- Participación y posición actual (si hay torneo activo)
    participacion = None
    posicion = "?"
    if torneos_activos:
        torneo_actual = torneos_activos[0]
        participacion = Participacion.objects.filter(
            equipo=equipo, torneo=torneo_actual
        ).first()
        if participacion:
            todas = Participacion.objects.filter(
                torneo=torneo_actual
            ).order_by('-puntos', '-dif', '-gf')
            posicion = list(todas).index(participacion) + 1

    # --- Próximo partido (solo con fecha definida a futuro y sin jugar)
    hoy = timezone.localdate()
    partidos_torneo = (
        Partido.objects
        .filter(
            Q(equipo_local__equipo=equipo) |
            Q(equipo_visitante__equipo=equipo),
            Q(jugado=False) | Q(jugado__isnull=True),
            dia__gte=hoy,
        )
        .annotate(tipo=Value('torneo', output_field=CharField()))
        .order_by('dia', 'id')
    )
    proximo_partido_obj = partidos_torneo.first()
    proximo_partido = None

    if proximo_partido_obj:
        proximo_partido = {
            'id': proximo_partido_obj.id,
            'equipo_1': proximo_partido_obj.equipo_local.equipo if proximo_partido_obj.equipo_local else None,
            'equipo_2': proximo_partido_obj.equipo_visitante.equipo if proximo_partido_obj.equipo_visitante else None,
            'goles_equipo_1': proximo_partido_obj.goles_local,
            'goles_equipo_2': proximo_partido_obj.goles_visitante,
            'dia': proximo_partido_obj.dia,
            'hora_inicio': proximo_partido_obj.hora_inicio,
            'cancha': proximo_partido_obj.cancha,
            'jugado': proximo_partido_obj.jugado,
        }

    # Propuesta: sólo si hay partido. Usamos el reverse accessor del OneToOne
    propuesta = None
    url_destino = None
    if proximo_partido_obj:
        try:
            propuesta = proximo_partido_obj.propuesta
        except Propuesta.DoesNotExist:
            propuesta = Propuesta.objects.create(partido=proximo_partido_obj)

        url_destino = (
            reverse("detalle_propuesta", args=[proximo_partido_obj.id])
            if not propuesta.cerrada
            else reverse("detalle_partido", args=["torneo", proximo_partido_obj.id])
        )
        
    if proximo_partido_obj:
        proximo_partido = {
            'id': proximo_partido_obj.id,
            'equipo_1': proximo_partido_obj.equipo_local.equipo if proximo_partido_obj.equipo_local else None,
            'equipo_2': proximo_partido_obj.equipo_visitante.equipo if proximo_partido_obj.equipo_visitante else None,
            'goles_equipo_1': proximo_partido_obj.goles_local,
            'goles_equipo_2': proximo_partido_obj.goles_visitante,
            'dia': proximo_partido_obj.dia,
            'hora_inicio': proximo_partido_obj.hora_inicio,
            'cancha': proximo_partido_obj.cancha,
            'jugado': proximo_partido_obj.jugado,
        }

    # --- Jugadores por posición (sobre integrantes del equipo)
    jugadores = Jugador.objects.filter(user__in=integrantes)

    delanteros = jugadores.filter(posicion_preferida='Delantero')
    mediocampistas = jugadores.filter(posicion_preferida='Mediocampista')
    defensores = jugadores.filter(posicion_preferida='Defensa')
    arqueros = jugadores.filter(posicion_preferida='Arquero')
    versatiles = jugadores.filter(posicion_preferida='Versátil')

    # --- Estadísticas de resultados del equipo (partidos jugados)
    partidos_qs = Partido.objects.filter(jugado=True).filter(
        Q(equipo_local__equipo=equipo) | Q(equipo_visitante__equipo=equipo)
    )
    n_partidos = partidos_qs.count()

    ganados = sum(
        1 for p in partidos_qs if (
            (p.equipo_local and p.equipo_local.equipo == equipo and p.goles_local > p.goles_visitante) or
            (p.equipo_visitante and p.equipo_visitante.equipo == equipo and p.goles_visitante > p.goles_local)
        )
    )
    empatados = sum(1 for p in partidos_qs if p.goles_local == p.goles_visitante)
    perdidos = n_partidos - ganados - empatados

    grafico_resultados = generar_grafico_resultados(ganados, empatados, perdidos)

    def calcular_porcentaje(total, total_partidos):
        if total_partidos == 0:
            return 0
        porcentaje = (total / total_partidos) * 100
        return int(porcentaje) if porcentaje.is_integer() else round(porcentaje, 2)

    # --- Estadísticas de jugadores (modelo real) usando miembro_equipo -> jugador
    estadisticas_equipo = EstadisticasJugadorPartido.objects.filter(
        partido__in=partidos_qs,
        miembro_equipo__equipo=equipo,
    ).select_related("miembro_equipo__jugador")  # ✅ evita queries extra

    agg = estadisticas_equipo.aggregate(
        total_asistencias=Coalesce(Sum("asistencias"), 0),
        total_atajadas=Coalesce(Sum("atajadas"), 0),
    )

    total_asistencias = agg["total_asistencias"]
    total_atajadas = agg["total_atajadas"]

    def prom(total_dato, total_partidos):
        return 0 if total_partidos == 0 else total_dato / total_partidos

    # Goleador
    goles_por_jugador = defaultdict(int)
    for e in estadisticas_equipo:
        goles_por_jugador[e.miembro_equipo.jugador] += (e.goles or 0)

    goleador = None
    goles_goleador = 0
    if goles_por_jugador:
        j_max, g = max(goles_por_jugador.items(), key=lambda x: x[1])
        if g > 0:
            goleador, goles_goleador = j_max, g

    # Asistidor
    asist_por_jugador = defaultdict(int)
    for e in estadisticas_equipo:
        asist_por_jugador[e.miembro_equipo.jugador] += (e.asistencias or 0)

    asistidor = None
    asistencias_asistidor = 0
    if asist_por_jugador:
        j_max, a = max(asist_por_jugador.items(), key=lambda x: x[1])
        if a > 0:
            asistidor, asistencias_asistidor = j_max, a

    # Arquero (atajadas)
    atajadas_por_jugador = defaultdict(int)
    for e in estadisticas_equipo:
        atajadas_por_jugador[e.miembro_equipo.jugador] += (e.atajadas or 0)

    arquero = None
    atajadas_arquero = 0
    if atajadas_por_jugador:
        j_max, at = max(atajadas_por_jugador.items(), key=lambda x: x[1])
        if at > 0:
            arquero, atajadas_arquero = j_max, at

    # --- Historial de partidos (jugados)
    partidos_raw = Partido.objects.filter(
        Q(equipo_local__equipo=equipo) |
        Q(equipo_visitante__equipo=equipo),
        jugado=True
    ).order_by('-fecha', '-hora_inicio')

    partidos_jugados = []
    for p in partidos_raw:
        if p.equipo_local and p.equipo_local.equipo == equipo:
            goles_propios = p.goles_local
            goles_rival = p.goles_visitante
        else:
            goles_propios = p.goles_visitante
            goles_rival = p.goles_local

        if goles_propios > goles_rival:
            resultado = 'V'
        elif goles_propios == goles_rival:
            resultado = 'E'
        else:
            resultado = 'D'

        partidos_jugados.append({
            'id': p.id,
            'equipo_1': p.equipo_local.equipo,
            'equipo_2': p.equipo_visitante.equipo,
            'equipo_1_logo': (
                p.equipo_local.equipo.escudo.url
                if p.equipo_local.equipo.escudo
                else '/static/images/placeholder.png'
            ),
            'equipo_2_logo': (
                p.equipo_visitante.equipo.escudo.url
                if p.equipo_visitante.equipo.escudo
                else '/static/images/placeholder.png'
            ),
            'goles_equipo_1': p.goles_local,
            'goles_equipo_2': p.goles_visitante,
            'resultado': resultado,
            'dia': p.dia,
            'hora_inicio': p.hora_inicio,
        })

    # --- Torneos del equipo
    torneos_del_equipo = Torneo.objects.filter(
        participacionequipotorneo__equipo=equipo
    ).distinct().order_by('-dia_inicio')

    cantidad_jugadores = equipo.integrantes.count()

    # ¿el usuario logueado es el capitán?
    es_capitan = False
    if request.user.is_authenticated:
        try:
            es_capitan = (request.user.jugador == equipo.capitan)
        except Jugador.DoesNotExist:
            pass

    context = {
        'url_destino_proximo_partido': url_destino,
        'es_capitan': es_capitan,
        'equipo': equipo,
        'delanteros': delanteros,
        'mediocampistas': mediocampistas,
        'defensores': defensores,
        'arqueros': arqueros,
        'versatiles': versatiles,
        'integrantes': integrantes,
        'proximo_partido': proximo_partido,
        'torneo_activo': torneos_activos[0] if torneos_activos else None,
        'torneos_ganados': torneos_ganados,
        'total_partidos': total_partidos,
        'total_goles': total_goles,
        'goles_promedio': round(total_goles / total_partidos, 2) if total_partidos else 0,
        'total_asistencias': total_asistencias,
        'asistencias_promedio': round(prom(total_asistencias, total_partidos), 2),
        'total_atajadas': total_atajadas,
        'atajadas_promedio': round(prom(total_atajadas, total_partidos), 2),
        'posicion': posicion,
        'partidos': n_partidos,
        'iniciales_provincia': iniciales_provincia,
        'url_configuracion': url_config,
        'ganados': ganados,
        'empatados': empatados,
        'perdidos': perdidos,
        'promedio_ganados': calcular_porcentaje(ganados, n_partidos),
        'promedio_empatados': calcular_porcentaje(empatados, n_partidos),
        'promedio_perdidos': calcular_porcentaje(perdidos, n_partidos),
        'grafico_resultados': grafico_resultados,
        'promedio_goles': round(prom(total_goles, total_partidos), 2),
        'goleador': goleador,
        'goles_goleador': goles_goleador,
        'asistidor': asistidor,
        'asistencias_asistidor': asistencias_asistidor,
        'arquero': arquero,
        'atajadas_arquero': atajadas_arquero,
        'partidos_jugados': partidos_jugados,
        'torneos_del_equipo': torneos_del_equipo,
        'cantidad_jugadores': cantidad_jugadores,
    }
    return render(request, 'mis_equipos/detalle_equipo.html', context)


@login_required
def configuracion_equipo(request, pk):
    equipo = get_object_or_404(Equipo, id=pk)
    url_volver = reverse('detalle_equipo', args=[equipo.id])
    usuarios_integrantes = equipo.integrantes.all()
    capitan = equipo.capitan
    url_invitar = reverse('invitar_jugadores_equipo', args=[equipo.id])

    if request.method == 'POST':
        # 1. Eliminar jugadores si vienen marcados
        jugadores_eliminados = request.POST.get('jugadores_eliminados', '')
        if jugadores_eliminados:
            ids = [int(i) for i in jugadores_eliminados.split(',') if i.isdigit()]
            jugadores = Jugador.objects.filter(id__in=ids)
            for jugador in jugadores:
                if jugador.user in equipo.integrantes.all():
                    equipo.integrantes.remove(jugador.user)

        # 2. Actualizar datos del equipo si vienen
        nombre = request.POST.get('nombre_equipo', '').strip()
        tag = request.POST.get('tag_equipo', '').strip()
        ciudad = request.POST.get('ciudad_equipo', '').strip()

        if nombre:
            equipo.nombre = nombre
        if tag:
            equipo.nombre_corto = tag
        if ciudad:
            equipo.ciudad = ciudad

        equipo.save()
        return redirect('detalle_equipo', pk=equipo.id)

    jugadores_equipo = Jugador.objects.filter(user__in=equipo.integrantes.all())

    context = {
        'equipo': equipo,
        'ocultar_navbar': True,
        'url_volver': url_volver,
        'jugadores_equipo': jugadores_equipo,
        'capitan': capitan,
        'url_invitar': url_invitar,
    }
    return render(request, 'mis_equipos/configuracion_equipo.html', context)

@login_required
def invitar_jugadores_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)

    query = request.GET.get('q', '')

    # Excluir integrantes del equipo
    jugadores = Jugador.objects.exclude(id__in=equipo.integrantes.values_list('id', flat=True))

    if query:
        jugadores = jugadores.filter(nombre__icontains=query)

    # ❗ Excluir jugadores ya invitados (pendientes o aceptados)
    jugadores = jugadores.exclude(
        id__in=InvitacionEquipo.objects.filter(
            equipo=equipo
        ).values_list('jugador__id', flat=True)
    )

    invitados_pendientes = InvitacionEquipo.objects.filter(
        equipo=equipo,
        aceptada__isnull=True
    )

    context = {
        'equipo': equipo,
        'jugadores': jugadores,
        'invitados_pendientes': invitados_pendientes,
        'query': query,
        'ocultar_navbar': True,
    }

    return render(request, 'mis_equipos/invitar_jugadores_equipo.html', context)



from django.template.loader import render_to_string
from django.db import IntegrityError

@login_required
def buscar_jugadores_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)

    if request.method == 'POST':
        jugador_id = request.POST.get('jugador_id')
        accion = request.POST.get('accion')  # 'invitar' o 'eliminar'

        try:
            jugador = Jugador.objects.get(id=jugador_id)

            if accion == 'invitar':
                InvitacionEquipo.objects.create(
                    equipo=equipo,
                    jugador=jugador,
                    enviado_por=request.user
                )
            elif accion == 'eliminar':
                InvitacionEquipo.objects.filter(
                    equipo=equipo,
                    jugador=jugador
                ).delete()
            else:
                return JsonResponse({'success': False, 'error': 'Acción inválida'})

        except Jugador.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Jugador no encontrado'})
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'Ya fue invitado'})

        # Actualizar listas luego de invitar o eliminar
        jugadores = Jugador.objects.exclude(id__in=equipo.integrantes.values_list('id', flat=True))
        jugadores = jugadores.exclude(
            id__in=InvitacionEquipo.objects.filter(equipo=equipo).values_list('jugador__id', flat=True)
        )

        html = render_to_string('mis_equipos/_lista_jugadores.html', {'jugadores': jugadores})
        invitados_html = render_to_string('mis_equipos/_lista_invitados.html', {
            'invitados': InvitacionEquipo.objects.filter(equipo=equipo, aceptada__isnull=True)
        })

        return JsonResponse({'success': True, 'html': html, 'invitados_html': invitados_html})

    # Búsqueda GET
    query = request.GET.get('q', '')
    jugadores = Jugador.objects.exclude(id__in=equipo.integrantes.values_list('id', flat=True))

    if query:
        jugadores = jugadores.filter(nombre__icontains=query)

    jugadores = jugadores.exclude(
        id__in=InvitacionEquipo.objects.filter(equipo=equipo).values_list('jugador__id', flat=True)
    )

    html = render_to_string('mis_equipos/_lista_jugadores.html', {
        'jugadores': jugadores,
    })
    
    invitados_html = render_to_string('mis_equipos/_lista_invitados.html', {
        'invitados': InvitacionEquipo.objects.filter(equipo=equipo, aceptada__isnull=True)
    })
    
    invitados_ids = list(
        InvitacionEquipo.objects.filter(equipo=equipo, aceptada__isnull=True).values_list('jugador__id', flat=True)
    )

    return JsonResponse({
        'html': html, 
        'invitados_html': invitados_html,
    })


@login_required
def invitar_jugador(request, partido_id, jugador_id):
    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    jugador = get_object_or_404(Jugador, id=jugador_id)

    if request.user != partido.creador:
        return JsonResponse({'error': 'No tenés permiso para invitar jugadores.'}, status=403)

    if Invitacion.objects.filter(partido=partido, jugador=jugador).exists():
        return JsonResponse({'mensaje': 'Este jugador ya fue invitado.'})

    Invitacion.objects.create(
        partido=partido,
        jugador=jugador,
        enviado_por=request.user
    )
    return JsonResponse({'mensaje': 'Invitación enviada correctamente.'})
    
    
from itertools import chain
from operator import attrgetter

@login_required
def notificaciones_usuario(request):
    jugador = get_object_or_404(Jugador, user=request.user)

    invitaciones_partido = Invitacion.objects.filter(
        jugador=jugador
    ).select_related('partido', 'enviado_por')

    invitaciones_equipo = InvitacionEquipo.objects.filter(
        jugador=jugador
    ).select_related('equipo', 'enviado_por')

    otras_notificaciones = Notificacion.objects.filter(
        usuario=request.user
    ).order_by('-fecha')

    for inv in invitaciones_partido:
        inv.tipo = 'partido'
        inv.fecha = inv.fecha_envio

    for inv in invitaciones_equipo:
        inv.tipo = 'equipo'
        inv.fecha = inv.fecha_envio

    for notif in otras_notificaciones:
        notif.tipo = 'sistema'
        notif.fecha = notif.fecha  # ya tiene campo fecha

    notificaciones = sorted(
        chain(invitaciones_partido, invitaciones_equipo, otras_notificaciones),
        key=attrgetter('fecha'),
        reverse=True
    )

    return render(request, 'invitaciones/invitaciones.html', {
        'notificaciones': notificaciones,
        'ocultar_navbar': True
    })


@csrf_exempt
@login_required
def marcar_invitacion_vista(request, tipo, id):
    jugador = get_object_or_404(Jugador, user=request.user)

    modelo = Invitacion if tipo == 'partido' else InvitacionEquipo if tipo == 'equipo' else None
    if not modelo:
        return JsonResponse({'error': 'Tipo inválido'}, status=400)

    try:
        invitacion = modelo.objects.get(id=id, jugador=jugador)
        invitacion.vista = True
        invitacion.save()
        return JsonResponse({'ok': True})
    except modelo.DoesNotExist:
        return JsonResponse({'error': 'Invitación no encontrada'}, status=404)


# views.py
from itertools import chain
from operator import itemgetter
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from app_torneo_f5.models import (
    Jugador, Invitacion, InvitacionEquipo, Notificacion
)
from django.urls import reverse
from urllib.parse import urlencode

@login_required
def mis_invitaciones(request):
    jugador = get_object_or_404(Jugador, user=request.user)

    # 1) Marcar como leídas/vistas
    Invitacion.objects.filter(jugador=jugador, vista=False).update(vista=True)
    InvitacionEquipo.objects.filter(jugador=jugador, vista=False).update(vista=True)
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)

    # 2) Querysets válidos (sin campos inexistentes)
    invitaciones_partido_qs = (
        Invitacion.objects
        .filter(
            jugador=jugador,
            partido__cancelado=False,
            partido__jugado=False
        )
        .select_related('partido', 'enviado_por')
        .only(
            'id', 'vista', 'fecha_envio',
            'enviado_por__first_name', 'enviado_por__last_name', 'enviado_por__username',
            'partido__id', 'partido__cancha'
        )
    )

    invitaciones_equipo_qs = (
        InvitacionEquipo.objects
        .filter(jugador=jugador)
        .select_related('equipo', 'enviado_por')
        .only(
            'id', 'vista', 'fecha_envio',
            'enviado_por__first_name', 'enviado_por__last_name', 'enviado_por__username',
            'equipo__id', 'equipo__nombre'
        )
    )

    notificaciones_sistema_qs = (
    Notificacion.objects
    .filter(usuario=request.user)
    .only('id', 'tipo', 'leida', 'fecha', 'extra_id', 'mensaje')  # ← agregar mensaje
)
    # 3) Normalizadores → dict homogéneo
    def full_name_or_username(u):
        fn = (u.first_name or '').strip()
        ln = (u.last_name or '').strip()
        if fn or ln:
            return f"{fn} {ln}".strip()
        return u.username

    def map_inv_partido(inv):
        p = inv.partido
        url = reverse('detalle_partido', args=('amistoso', p.id))
        qs = urlencode({'invitacion_pendiente': '1'})
        return {
            "tipo": "partido",
            "fecha": inv.fecha_envio,
            "visto": inv.vista,
            "titulo": "¡Te invitaron a jugar!",
            "mensaje": f"{full_name_or_username(inv.enviado_por)} te invitó a un partido en {p.cancha or 'una cancha'}.",
            "url": f"{url}?{qs}",
        }

    def map_inv_equipo(inv):
        e = inv.equipo
        url = reverse('detalle_equipo', args=(e.id,))  # ajustá el name si difiere
        return {
            "tipo": "equipo",
            "fecha": inv.fecha_envio,
            "visto": inv.vista,
            "titulo": "¡Quieren ficharte!",
            "mensaje": f"{full_name_or_username(inv.enviado_por)} quiere ficharte en {e.nombre}.",
            "url": url,
        }

    def map_notif(n):
        tipo = (n.tipo or "").lower()

        # título por tipo
        titulos = {
            "partido_creado": "Partido creado",
            "partido_en_juego": "¡Comenzó tu partido!",
            "partido_finalizado": "Partido finalizado",
            "partido_cancelado": "Partido cancelado",
            "estadistica": "Tu juego ya quedó registrado",
            "sistema": "Notificación",
        }
        titulo = titulos.get(tipo, "Notificación")

        # etiqueta de cabecera (columna izquierda)
        header = "Sistema"
        if tipo.startswith("partido") or tipo in {"estadistica"}:
            header = "Partido"

        # posibles URLs
        url = None
        if tipo.startswith("partido") and n.extra_id:
            # si extra_id es el ID del partido amistoso
            from django.urls import reverse
            url = reverse('detalle_partido', args=('amistoso', n.extra_id))
        elif tipo == "estadistica" and n.extra_id:
            from django.urls import reverse
            url = reverse('estadisticas_paso1', args=('amistoso', n.extra_id))

        return {
            "tipo": tipo or "sistema",
            "header": header,           # ← para el template
            "fecha": n.fecha,
            "visto": n.leida,
            "titulo": titulo,           # ← no viene del modelo
            "mensaje": n.mensaje or "", # ← tu texto real
            "url": url,
        }

    invitaciones_partido = [map_inv_partido(x) for x in invitaciones_partido_qs]
    invitaciones_equipo  = [map_inv_equipo(x) for x in invitaciones_equipo_qs]
    notificaciones_sistema = [map_notif(x) for x in notificaciones_sistema_qs]

    # 4) Merge + orden
    notificaciones = list(chain(invitaciones_partido, invitaciones_equipo, notificaciones_sistema))
    notificaciones.sort(key=itemgetter("fecha"), reverse=True)

    # 5) Paginación (opcional)
    page_obj = Paginator(notificaciones, 20).get_page(request.GET.get("page", 1))

    return render(request, "invitaciones/invitaciones.html", {
        "notificaciones": page_obj.object_list,
        "page_obj": page_obj,
        "ocultar_navbar": True,
    })


def busqueda_jugadores(request):
    return render(request, 'jugadores/busqueda_jugadores.html')


def busqueda(request):
    return render(request, 'busqueda/busqueda.html')


# Provincias con código IATA
PROVINCIAS_IATA = {
    "Buenos Aires": "BA",
    "Catamarca": "CT",
    "Chaco": "CC",
    "Chubut": "CH",
    "Córdoba": "CB",
    "Corrientes": "CR",
    "Entre Ríos": "ER",
    "Formosa": "FO",
    "Jujuy": "JY",
    "La Pampa": "LP",
    "La Rioja": "LR",
    "Mendoza": "MZA",
    "Misiones": "MI",
    "Neuquén": "NQ",
    "Río Negro": "RN",
    "Salta": "SA",
    "San Juan": "SJ",
    "San Luis": "SL",
    "Santa Cruz": "SC",
    "Santa Fe": "SF",
    "Santiago del Estero": "SE",
    "Tierra del Fuego": "TF",
    "Tucumán": "TM",
    "Sin definir": "ND"
}

def obtener_codigo_provincia(nombre):
    return PROVINCIAS_IATA.get(nombre, "ND")

@login_required
@require_GET
def busqueda_jugadores(request):
    jugadores = Jugador.objects.select_related('user').exclude(user=request.user)

    data = []
    for jugador in jugadores:
        codigo_prov = obtener_codigo_provincia(jugador.provincia)
        data.append({
            "id": jugador.id,
            "nombre": jugador.nombre,
            "posicion_preferida": jugador.posicion_preferida,
            "provincia": codigo_prov,
            "ciudad": jugador.ciudad,
            "img_path": jugador.foto.url if jugador.foto else None
        })

    return JsonResponse(data, safe=False)

@login_required
@require_GET
def busqueda_jugadores_invitar(request):
    q = request.GET.get("q", "")
    partido_id = request.GET.get("partido_id")

    jugadores = Jugador.objects.select_related('user').exclude(user=request.user)

    if q:
        jugadores = jugadores.filter(nombre__icontains=q)

    # Cast partido_id a int si viene, sino None
    try:
        partido_id = int(partido_id)
    except (TypeError, ValueError):
        partido_id = None

    # Obtener invitaciones existentes para ese partido
    invitaciones = {}
    if partido_id:
        invitaciones_qs = Invitacion.objects.filter(partido_id=partido_id)
        for inv in invitaciones_qs:
            invitaciones[inv.jugador_id] = {
                "invitado": True,
                "aceptada": inv.aceptada
            }

    # Armar respuesta
    data = []
    for jugador in jugadores:
        estado = invitaciones.get(jugador.id, {"invitado": False, "aceptada": False})

        if estado["aceptada"]:
            continue

        codigo_prov = obtener_codigo_provincia(jugador.provincia)

        data.append({
            "id": jugador.id,
            "nombre": jugador.nombre,
            "posicion_preferida": jugador.posicion_preferida,
            "provincia": codigo_prov,
            "ciudad": jugador.ciudad,
            "img_path": jugador.foto.url if jugador.foto else None,
            "invitado": estado["invitado"],
            "aceptada": estado["aceptada"],
        })

    return JsonResponse(data, safe=False)
from django.http import JsonResponse
from django.templatetags.static import static
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
def _safe_file_url(filefield, default_url=None):
    """
    Devuelve filefield.url si existe y es accesible.
    Nunca explota: atrapa ValueError y cualquier otra excepción.
    """
    if not default_url:
        default_url = static("img/escudos/placeholder-escudo.svg")
    try:
        # Si no hay archivo, .url levanta ValueError -> lo capturamos
        return filefield.url
    except Exception:
        return default_url

@login_required
@require_GET
def busqueda_equipos(request):
    q = (request.GET.get('q') or '').strip()
    qs = Equipo.objects.all()
    if q:
        qs = qs.filter(nombre__icontains=q)

    results = []
    for e in qs[:20]:
        img_url = _safe_file_url(getattr(e, "escudo", None))
        results.append({
            "id": e.id,
            "nombre": e.nombre,
            "img_path": img_url,      # Siempre string (placeholder) — nunca explota
            "has_escudo": (img_url is not None) and ("placeholder" not in img_url),
        })

    return JsonResponse({"results": results})


@login_required
@require_GET
def busqueda_torneos(request):
    torneos = Torneo.objects.all()
    data = []

    for torneo in torneos:
        data.append({
            "id": torneo.id,
            "nombre": torneo.nombre,
            "participantes": torneo.cant_equipos,
            "img_path": "{% static '/media/fotos_jugadores/defaultmen.png' %}"
        })

    return JsonResponse(data, safe=False)


@login_required
def partidos(request):
    user = request.user
    try:
        jugador = Jugador.objects.get(user=user)
    except Jugador.DoesNotExist:
        jugador = None

    # Filtrar partidos amistosos NO cancelados y NO jugados
    partidos_creados = PartidoAmistoso.objects.filter(creador=user, cancelado=False, jugado=False)
    partidos_aceptados = PartidoAmistoso.objects.filter(jugadores=jugador, cancelado=False, jugado=False) if jugador else PartidoAmistoso.objects.none()
    partidos_amistosos = (partidos_creados | partidos_aceptados).distinct().order_by('dia', 'hora_inicio')
    
    # Filtrar partidos de torneo NO jugados
    partidos_torneo = (Partido.objects
        .filter(
            jugado=False,
            cancelado=False,
            torneo__inscripcion__jugador__user=request.user  # pertenece al torneo
        )
        .select_related('equipo_local','equipo_visitante','cancha','torneo')
        .distinct()
    )
    
        
    return render(request, 'partidos_amistosos/partidos.html', {
        'partidos': partidos_amistosos,
        'partidos_torneo': partidos_torneo,
    })

    
@login_required
def detalle_partido(request, partido_id, tipo):
    invitacion_pendiente = request.GET.get('invitacion_pendiente') == '1'
    
    if tipo == 'amistoso':
        # Inicialización preventiva
        jugadores_equipo_1 = []
        jugadores_equipo_2 = []
        partido = get_object_or_404(PartidoAmistoso, id=partido_id)
        partido_nombre=partido.cancha
        estadisticas = EstadisticaAmistosa.objects.filter(partido=partido, goles__gt=0)
        template = 'partidos_amistosos/editar_partido.html'
        jugadores = list(partido.jugadores.all())
        pertenece = Jugador.objects.filter(user=request.user, id__in=partido.jugadores.values_list('id', flat=True)).exists()
        url_config = reverse('configuracion_partido', kwargs={'tipo': 'amistoso', 'partido_id': partido_id})
        uuid_url = request.build_absolute_uri(reverse('aceptar_invitacion_uuid', args=[partido.uuid]))
        equipo_local = partido.equipo_local.all()
        equipo_visitante = partido.equipo_visitante.all()
        
        """ Escudos """
        if partido.color_equipo_local == 'bg-a-equipo1':
            url_escudo_1 = 'images/escudo-equipo/a-equipo1.jpg'
            url_escudo_2 = 'images/escudo-equipo/a-equipo2.jpg'
        elif partido.color_equipo_local == 'bg-b-equipo1':
            url_escudo_1 = 'images/escudo-equipo/b-equipo1.jpg'
            url_escudo_2 = 'images/escudo-equipo/b-equipo2.jpg'
        elif partido.color_equipo_local == 'bg-c-equipo1':
            url_escudo_1 = 'images/escudo-equipo/c-equipo1.jpg'
            url_escudo_2 = 'images/escudo-equipo/c-equipo2.jpg'
        else:
            url_escudo_1 = 'images/escudo-equipo/d-equipo1.jpg'
            url_escudo_2 = 'images/escudo-equipo/d-equipo2.jpg'

        goleadores_equipo_1 = estadisticas.filter(jugador__in=partido.equipo_local.all()).order_by('-goles')
        goleadores_equipo_2 = estadisticas.filter(jugador__in=partido.equipo_visitante.all()).order_by('-goles')
        es_creador = request.user == partido.creador
        ahora = localtime().time()
        horainferior = partido.hora_inicio > ahora if partido.hora_inicio else False
        
        goles_equipo_1 = estadisticas.filter(jugador__in=partido.equipo_local.all()).aggregate(Sum('goles'))['goles__sum'] or 0
        goles_equipo_2 = estadisticas.filter(jugador__in=partido.equipo_visitante.all()).aggregate(Sum('goles'))['goles__sum'] or 0

        existe_equipos = partido.equipo_local.exists() or partido.equipo_visitante.exists()

        partido_cancelado = partido.cancelado

        jugador = Jugador.objects.filter(user=request.user).first()
        pertenece = jugador in partido.jugadores.all() if jugador else False

        if not es_creador and not pertenece and not invitacion_pendiente:
            return redirect('partidos')

        jugadores = list(partido.jugadores.all())
        jugadores.sort(key=lambda j: 0 if j.user == partido.creador else 1)

        cantidad_jugadores = len(jugadores)

        if jugador and invitacion_pendiente:
            # Crear invitación solo si no existe
            Invitacion.objects.get_or_create(
                partido=partido,
                jugador=jugador,
                defaults={'enviado_por': partido.creador}
            )
        Invitacion.objects.filter(partido=partido, jugador=jugador).update(vista=True)

        precio_por_jugador = (
            round(partido.precio_total / partido.max_jugadores, 2)
            if partido.max_jugadores > 0 else 0
        )

        uuid_url = request.build_absolute_uri(
            reverse('aceptar_invitacion_uuid', args=[partido.uuid])
        )

        url_config = reverse('configuracion_partido', kwargs={'tipo': 'amistoso', 'partido_id': partido_id})
        
        jugadores_equipo_1 = None
        jugadores_equipo_2 = None

    elif tipo == 'torneo':
        partido = get_object_or_404(Partido, id=partido_id)
        torneo = partido.torneo
        user = request.user
        jugador = Jugador.objects.filter(user=user).first()

        # 🔹 Determinar modos
        modo_registro = torneo.modo_registro_estadisticas     # POR_EQUIPO o POR_PARTIDO
        modo_seleccion = torneo.modo_seleccion_partido        # POR_DEFECTO o PROPUESTA
        modo_creacion = torneo.modo_creacion_partidos         # MANUAL o AUTOMATICA

        # 🔹 Determinar roles
        es_encargado = user in torneo.encargados_carga.all()
        es_capitan_local = (
            partido.equipo_local
            and partido.equipo_local.encargado_carga == user
        )
        
        es_capitan_visitante = (hasattr(partido.equipo_visitante, 'encargado_carga') 
                                and partido.equipo_visitante.encargado_carga == user)
        es_capitan = es_capitan_local or es_capitan_visitante

        # 🔹 Verificar si el usuario pertenece al partido
        equipos_ids = []

        if partido.equipo_local and partido.equipo_local.equipo:
            equipos_ids.append(partido.equipo_local.equipo_id)

        if partido.equipo_visitante and partido.equipo_visitante.equipo:
            equipos_ids.append(partido.equipo_visitante.equipo_id)

        pertenece = IntegranteEquipo.objects.filter(
            usuario=user,
            equipo_id__in=equipos_ids
        ).exists()

        # 🔹 Determinar permisos
        puede_cargar_estadisticas = (
            modo_registro == Torneo.POR_PARTIDO and es_encargado
        ) or (
            modo_registro == Torneo.POR_EQUIPO and es_capitan
        )

        puede_proponer = (
            modo_seleccion == Torneo.PROPUESTA and es_capitan
        )

        # 🔹 Determinar acciones visibles
        acciones = {
            'editar': puede_cargar_estadisticas,
            'proponer': puede_proponer,
            'ver_solo': not (puede_cargar_estadisticas or puede_proponer),
        }

        context = {
            'tipo': tipo,
            'partido_id': partido.id,     # Usado para fetch del API
            'pertenece': pertenece,
            'acciones': acciones,
            'modo_registro': modo_registro,
            'modo_seleccion': modo_seleccion,
            'modo_creacion': modo_creacion,
            'es_encargado': es_encargado,
            'es_capitan': es_capitan,
            
        }
        
        definido = partido.dia is not None and partido.hora_inicio is not None
        
        if not partido.jugado:
            if partido.jugando:
                # Partido en curso
                return render(request, 'partido_torneo/detalle_programado.html', context)
            elif definido:  
                # Nuevo estado: partido definido
                return render(request, 'partido_torneo/detalle_programado.html', context)
            else:
                # Aún no definido ni jugado
                return render(request, 'partido_torneo/detalle_propuesta.html', context)
        else:
            # Partido ya finalizado
            return render(request, 'partido_torneo/detalle_finalizado.html', context)

    else:
        return redirect('partidos')

    context = {
        'tipo': tipo,
        'partido': partido,
        'es_creador': es_creador,
        'precio_por_jugador': precio_por_jugador,
        'cantidad_jugadores': cantidad_jugadores,
        'jugadores_ordenados': jugadores,
        'uuid_url': uuid_url,
        'equipo_1': equipo_local,  
        'equipo_2': equipo_visitante,
        'goleadores_equipo_1': goleadores_equipo_1,
        'goleadores_equipo_2': goleadores_equipo_2,
        'goles_equipo_1': goles_equipo_1,
        'goles_equipo_2': goles_equipo_2,   
        'existe_equipos': existe_equipos,
        'horainferior': horainferior,
        'url_configuracion': url_config,
        'invitacion_pendiente': invitacion_pendiente,
        'pertenece': pertenece,
        'jugadores_equipo_1': jugadores_equipo_1,
        'jugadores_equipo_2': jugadores_equipo_2,
        'partido_cancelado' : partido_cancelado,
        'partido_nombre' : partido_nombre,
        'url_escudo_1': url_escudo_1,
        'url_escudo_2': url_escudo_2,
    }

    return render(request, template, context)


@login_required
def invitar_jugadores_vista(request, partido_id):
    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    
    
    if request.user != partido.creador:
        return redirect('detalle_partido', partido_id=partido.id)
    
    jugadores = Jugador.objects.exclude(id__in=partido.jugadores.values_list('id', flat=True))
    
    invitados = Invitacion.objects.filter(partido=partido)
    
    return render(request, 'partidos_amistosos/invitar_jugadores.html', {
        'partido': partido,
        'jugadores': jugadores,
        'invitados': invitados,
    })


@login_required
def invitar_jugadores(request, partido_id):
    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    jugadores = Jugador.objects.exclude(user=request.user)
    invitados = Jugador.objects.filter(invitacion__partido=partido)

    uuid_url = request.build_absolute_uri(reverse('aceptar_invitacion', args=[partido.uuid]))

    return render(request, 'partidos_amistosos/invitar_jugadores.html', {
        'jugadores': jugadores,
        'invitados': invitados,
        'uuid_url': uuid_url,
    })


def aceptar_invitacion_uuid(request, uuid):
    return redirect(f"{reverse('amistosos')}?invitacion={uuid}")


@login_required
def nuevas_invitaciones(request):
    jugador = Jugador.objects.get(user=request.user)
    nuevas = Invitacion.objects.filter(jugador=jugador, aceptada=False).count()
    return JsonResponse({'nuevas': nuevas})

@login_required
def detalle_partido_por_codigo(request, codigo_invitacion):
    partido = get_object_or_404(PartidoAmistoso, codigo_invitacion=codigo_invitacion)
    jugador = Jugador.objects.filter(user=request.user).first()

    if not jugador:
        messages.error(request, "No estás registrado como jugador.")
        return redirect('home')

    if partido.jugado:
        messages.warning(request, "Este partido ya fue jugado.")
        return redirect('detalle_partido', tipo='amistoso', partido_id=partido.id)

    # ✅ Crear invitación si no existe
    invitacion = Invitacion.objects.filter(partido=partido, jugador=jugador).first()
    if not invitacion:
        invitacion = Invitacion.objects.create(
            partido=partido,
            jugador=jugador,
            enviado_por=partido.creador,
            aceptada=False
        )
        print("✅ Invitación creada")
    else:
        print("ℹ️ Invitación ya existía")

    # ✅ Redirigir con el flag
    return redirect(f"{reverse('detalle_partido', args=['amistoso', partido.id])}?invitacion_pendiente=1")


@login_required
def armar_equipos(request, partido_id):
    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    es_creador = request.user == partido.creador

    jugador = Jugador.objects.filter(user=request.user).first()
    pertenece = jugador in partido.jugadores.all() if jugador else False

    if not es_creador and not pertenece:
        return redirect('partidos')

    jugadores = list(partido.jugadores.all())
    jugadores.sort(key=lambda j: 0 if j.user == partido.creador else 1)

    cantidad_jugadores = len(jugadores)
    if cantidad_jugadores < 2:
        messages.warning(request, "Necesitás al menos 2 jugadores para armar equipos.")
        return redirect('detalle_partido', partido_id=partido.id)

    precio_por_jugador = (
        round(partido.precio_total / partido.max_jugadores, 2)
        if partido.max_jugadores > 0 else 0
    )

    uuid_url = request.build_absolute_uri(
        reverse('aceptar_invitacion_uuid', args=[partido.uuid])
    )
    for j in jugadores:
        partes = j.nombre.strip().split()
        j.nombre = partes[0]
        j.apellido = " ".join(partes[1:]) if len(partes) > 1 else ""

    return render(request, 'partidos_amistosos/armar_equipos.html', {
        'partido': partido,
        'es_creador': es_creador,
        'precio_por_jugador': precio_por_jugador,
        'cantidad_jugadores': cantidad_jugadores,
        'jugadores_ordenados': jugadores,
        'uuid_url': uuid_url  ,
        'color_equipo_local': partido.color_equipo_local,  # 👈 agregás esto
        'color_equipo_visitante': partido.color_equipo_visitante
    })



@csrf_exempt 
@login_required
def confirmar_equipos(request, partido_id):
    if request.method == 'POST':
        partido = get_object_or_404(PartidoAmistoso, id=partido_id)
        data = json.loads(request.body)

        ids_local = data.get('equipo_a', [])
        ids_visitante = data.get('equipo_b', [])

        jugadores_local = Jugador.objects.filter(id__in=ids_local)
        jugadores_visitante = Jugador.objects.filter(id__in=ids_visitante)

        partido.equipo_local.set(jugadores_local)
        partido.equipo_visitante.set(jugadores_visitante)

        partido.jugando = False  # ← ahora sí arranca el partido al confirmar equipos
        partido.jugado = False  # por si estaba en True accidentalmente
        partido.save()

        return JsonResponse({'status': 'ok'})
    return HttpResponseNotAllowed(['POST'])




    
    
def crear_partido_1(request):
    canchas_qs = Cancha.objects.prefetch_related('tipo_cancha').all()
    
    canchas_json = {
        str(cancha.id): {
            "nombre": cancha.nombre,
            "direccion": cancha.direccion or "",
            "tipos": [tc.nombre for tc in cancha.tipo_cancha.all()]
        }
        for cancha in canchas_qs
    }

    return render(request, 'crear_partido/crear_partido_1.html', {
        'canchas': canchas_qs,
        'canchas_json': json.dumps(canchas_json, cls=DjangoJSONEncoder),
    })
    
@login_required 
def crear_partido_2(request):
    return render(request, 'crear_partido/crear_partido_2.html')
    
@login_required
def crear_partido_3(request):
    return render(request, 'crear_partido/crear_partido_3.html')

from decimal import Decimal
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.db import IntegrityError
from app_torneo_f5.models import PartidoAmistoso
from ..services import programar_inicio_partido

def escudos_por_color(color_local: str):
    mapping = {
        'bg-a-equipo1': ('images/escudo-equipo/a-equipo1.jpg', 'images/escudo-equipo/a-equipo2.jpg'),
        'bg-b-equipo1': ('images/escudo-equipo/b-equipo1.jpg', 'images/escudo-equipo/b-equipo2.jpg'),
        'bg-c-equipo1': ('images/escudo-equipo/c-equipo1.jpg', 'images/escudo-equipo/c-equipo2.jpg'),
        'bg-d-equipo1': ('images/escudo-equipo/d-equipo1.jpg', 'images/escudo-equipo/d-equipo2.jpg'),
    }
    return mapping.get(color_local, mapping['bg-d-equipo1'])

@login_required
def crear_partido_final(request):
    colores_pareja = [
        ['bg-d-equipo1', 'bg-d-equipo2'],
        ['bg-c-equipo1', 'bg-c-equipo2'],
        ['bg-b-equipo1', 'bg-b-equipo2'],
        ['bg-a-equipo1', 'bg-a-equipo2'],
    ]

    if request.method == 'POST':
        # 1) Intento JSON; si falla, uso request.POST
        try:
            data = json.loads(request.body or "{}")
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            data = {}

        if not data:
            data = {k: (v or "").strip() for k, v in request.POST.items()}

        usuario = request.user

        # Parsear fecha y hora
        try:
            fecha = datetime.strptime((data.get('fecha') or '').strip(), "%Y-%m-%d").date()
            hora  = datetime.strptime((data.get('hora') or '').strip(), "%H:%M").time()
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha u hora inválido'}, status=400)

        # Strings obligatorios
        tipo_cancha_txt = (data.get('formato') or '').strip()
        cancha_txt      = (data.get('cancha') or '').strip()
        ubicacion_txt   = (data.get('ubicacion') or '').strip()

        if not tipo_cancha_txt:
            return JsonResponse({'error': 'Tipo de cancha inválido'}, status=400)
        if not cancha_txt:
            return JsonResponse({'error': 'Cancha no encontrada'}, status=400)

        # Helpers numéricos
        def _to_int(v, default=0):
            try:
                return int(v)
            except (TypeError, ValueError):
                return default

        def _to_decimal(v, default=Decimal('0.0')):
            try:
                return Decimal(str(v))
            except (TypeError, ValueError, ArithmeticError):
                return default

        duracion      = _to_int(data.get('duracion', 60), 60)
        precio_total  = _to_decimal(data.get('precio', '0.0'), Decimal('0.0'))
        max_jugadores = _to_int(data.get('jugadores', 0), 0)

        # Colores (evitar None)
        color_local     = (data.get('color_local') or default_color_local).strip()
        color_visitante = (data.get('color_visitante') or default_color_visit).strip()

        # Escudos según color_local
        url_escudo_1, url_escudo_2 = escudos_por_color(color_local)

        try:
            partido = PartidoAmistoso.objects.create(
                creador=usuario,
                dia=fecha,
                hora_inicio=hora,
                duracion=duracion,
                tipo_cancha=tipo_cancha_txt,
                cancha=cancha_txt,
                ubicacion=ubicacion_txt,
                precio_total=precio_total,
                max_jugadores=max_jugadores,
                color_equipo_local=color_local,
                color_equipo_visitante=color_visitante,
            )
            programar_inicio_partido(partido)
        except IntegrityError as e:
            return JsonResponse({'error': f'Error de integridad: {str(e)}'}, status=400)

        # Agregar jugador creador al partido (si existe)
        try:
            jugador = Jugador.objects.get(user=usuario)
            partido.jugadores.add(jugador)
        except Jugador.DoesNotExist:
            return JsonResponse({
                'success': True,
                'id': partido.id,
                'warning': 'Partido creado pero el creador no está registrado como Jugador.'
            }, status=201)

        return JsonResponse({'success': True, 'id': partido.id}, status=201)

    # ===== GET =====
    # Elegir un par aleatorio
    par_aleatorio = random.choice(colores_pareja)
    color_local, color_visitante = par_aleatorio

    # Escudos en base al color local
    url_escudo_1, url_escudo_2 = escudos_por_color(color_local)
    
    
    return render(request, 'crear_partido/crear_partido_final.html', {
        'colores_pareja': json.dumps(colores_pareja),
        'color_local': color_local,
        'color_visitante': color_visitante,
        'url_escudo_1': url_escudo_1,
        'url_escudo_2': url_escudo_2,
    })
    
from decimal import Decimal, InvalidOperation

def configuracion_partido(request, tipo, partido_id):
    partido = get_object_or_404(PartidoAmistoso, pk=partido_id)

    # Aún podemos usar Cancha/TipoCancha como catálogo de sugerencias
    canchas = Cancha.objects.all()
    canchas_qs = Cancha.objects.prefetch_related('tipo_cancha').all()
    url_volver = reverse('detalle_partido', kwargs={'tipo': tipo, 'partido_id': partido.id})

    # AHORA indexamos por nombre (string) para que el front haga lookup por texto
    canchas_qs = Cancha.objects.prefetch_related('tipo_cancha').all()
    canchas_json = {
        cancha.nombre: {
            "nombre": cancha.nombre,
            "direccion": cancha.direccion or "",
            "tipos": [tc.nombre for tc in cancha.tipo_cancha.all()]
        }
        for cancha in canchas_qs
    }
    
    if request.method == 'POST':
        # Cancha (string)
        cancha_post = request.POST.get('cancha')
        if not cancha_post:
            cancha_list = request.POST.getlist('cancha')
            cancha_post = cancha_list[0] if cancha_list else ''
        partido.cancha = (cancha_post or '').strip() or None

        # Tipo cancha (string)
        tipo_post = request.POST.get('tipo_cancha')
        if not tipo_post:
            tipo_list = request.POST.getlist('tipo_cancha')
            tipo_post = tipo_list[0] if tipo_list else ''
        partido.tipo_cancha = (tipo_post or '').strip() or None

        # Ubicación (string)
        partido.ubicacion = (request.POST.get('ubicacion') or '').strip() or None

        # Fecha y hora (compatibles con flatpickr)
        partido.dia = request.POST.get('dia') or None
        partido.hora_inicio = request.POST.get('hora_inicio') or None

        # Duración (entero)
        duracion = request.POST.get('duracion') or 0
        try:
            partido.duracion = int(duracion)
        except (TypeError, ValueError):
            partido.duracion = 0

        # Precio total → Decimal
        precio_raw = request.POST.get('precio_total') or '0'
        # Por si llega con formateo (puntos miles, coma decimal)
        precio_normalizado = precio_raw.replace('.', '').replace(',', '.')
        try:
            partido.precio_total = Decimal(precio_normalizado)
        except (InvalidOperation, TypeError):
            partido.precio_total = Decimal('0')

        # Máximo de jugadores
        max_j = request.POST.get('max_jugadores') or partido.max_jugadores
        try:
            partido.max_jugadores = int(max_j)
        except (TypeError, ValueError):
            pass

        # Switch
        partido.permite_invitaciones = 'permite_invitaciones' in request.POST
         # capturamos valores previos
        old_dia = partido.dia
        old_hora = partido.hora_inicio
        old_duracion = partido.duracion
        partido.save()
        cambio_horario = (
            partido.dia != old_dia or
            partido.hora_inicio != old_hora or
            (partido.duracion or 0) != (old_duracion or 0)
        )
        from ..services import programar_inicio_partido, borrar_tasks_partido

        def _horario_valido(p):
            return bool(p.dia and p.hora_inicio and (p.duracion or 0) > 0)

        # 🔧 fuerza reprogramación limpia en cada guardado
        if _horario_valido(partido):
            borrar_tasks_partido(partido)       # primero borro todo lo viejo
            # MUY IMPORTANTE: asegurar que hora/fecha están normalizados en el objeto
            partido.refresh_from_db(fields=['dia', 'hora_inicio', 'duracion'])
            programar_inicio_partido(partido)   # y creo tasks nuevas
        else:
            borrar_tasks_partido(partido)       # si quedó incompleto, limpia tasks

        messages.success(request, "Configuración guardada correctamente.")
        return redirect('detalle_partido', tipo=tipo, partido_id=partido.id)

    return render(request, 'crear_partido/configurar_partido.html', {
        'ocultar_navbar': True,
        'partido_id': partido_id,
        'partido': partido,
        'canchas': canchas,                      # catálogo para sugerencias
        'canchas_json': json.dumps(canchas_json, cls=DjangoJSONEncoder),
        'url_volver': url_volver,
        'permite_invitaciones_checked': 'checked' if partido.permite_invitaciones else ''
    })

from ..services import borrar_tasks_partido
from django.core.exceptions import FieldError

@login_required
@require_POST
def borrar_partido(request, partido_id):
    partido = get_object_or_404(PartidoAmistoso, id=partido_id, creador=request.user)

    with transaction.atomic():
        # 1) Borrar todas las invitaciones ligadas a este partido
        inv_deleted, _ = Invitacion.objects.filter(partido=partido).delete()

        # 1.b) (Opcional) si InvitacionEquipo también referencia un partido
        try:
            from app_torneo_f5.models import InvitacionEquipo
            extra_deleted = 0
            # Solo si el modelo tiene el campo partido
            if 'partido' in [f.name for f in InvitacionEquipo._meta.get_fields()]:
                extra_deleted, _ = InvitacionEquipo.objects.filter(partido=partido).delete()
        except (ImportError, FieldError):
            extra_deleted = 0  # ignoramos si no existe o no tiene ese campo

        # 2) Borrar tasks programadas (inicio/fin/etc.)
        borrar_tasks_partido(partido)

        # 3) Borrar el partido
        partido.delete()

    total_deleted = inv_deleted + (extra_deleted or 0)
    messages.success(
        request,
        f"Partido eliminado. Invitaciones borradas: {total_deleted}. Tareas programadas limpiadas."
    )
    return redirect('partidos')  # ajustá al nombre de tu listado



@login_required
def unirse_a_partido(request, partido_id):

    # 🚫 Si entra por GET → volver atrás
    if request.method == "GET":
        return redirect(request.META.get("HTTP_REFERER", "partidos"))

    # 🚫 Si entra por otro método raro
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # ===== POST real =====

    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    jugador = Jugador.objects.filter(user=request.user).first()

    if not jugador:
        messages.error(request, 'No sos jugador')
        return redirect('partidos')

    invitacion = Invitacion.objects.filter(partido=partido, jugador=jugador).first()
    if not invitacion:
        messages.error(request, 'No tenés invitación para este partido')
        return redirect('partidos')

    if partido.jugado:
        messages.error(request, 'El partido ya fue jugado')
        return redirect('partidos')

    if partido.jugadores.filter(id=jugador.id).exists():
        messages.info(request, 'Ya estás en el partido')
        return redirect('detalle_partido', partido_id=partido.id, tipo='amistoso')

    if partido.jugadores.count() >= partido.max_jugadores:
        messages.error(request, 'El partido está completo')
        return redirect('detalle_partido', partido_id=partido.id, tipo='amistoso')

    partido.jugadores.add(jugador)

    invitacion.aceptada = True
    invitacion.save()

    messages.success(request, 'Te uniste correctamente al partido')
    return redirect('detalle_partido', partido_id=partido.id, tipo='amistoso')


@require_POST
@csrf_exempt  # ⚠️ usalo solo si no estás enviando el CSRF token desde JS
def cancelar_partido(request, partido_id):
    try:
        partido = PartidoAmistoso.objects.get(pk=partido_id)

        # Actualizar todos los estados
        partido.cancelado = True
        partido.permitir_invitaciones = False
        partido.jugando = False
        partido.jugado = False
        partido.save()

        return JsonResponse({'status': 'ok', 'message': 'Partido cancelado correctamente'})

    except PartidoAmistoso.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Partido no encontrado'}, status=404)
    
    
@login_required
def detalle_propuesta(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    jugador = Jugador.objects.get(user=request.user)
    propuesta = getattr(partido, 'propuesta', None)
    url_volver = reverse('detalle_torneo', kwargs={'torneo_id': partido.torneo.id})
    torneo = partido.torneo
    modo_seleccion = torneo.modo_seleccion_partido

    # Validar que el partido no esté jugado
    if partido.jugado:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)
    
    # Calcular precio unitario de cada cancha
    precio_unitario1 = None
    precio_unitario2 = None

    if propuesta:
        if propuesta.precio1 is not None:
            precio_unitario1 = "{:,.2f}".format(propuesta.precio1 / 10).replace(",", "X").replace(".", ",").replace("X", ".")
        if propuesta.precio2 is not None:
            precio_unitario2 = "{:,.2f}".format(propuesta.precio2 / 10).replace(",", "X").replace(".", ",").replace("X", ".")


    # ---------- Lógica de PROUESTA (modo entre capitanes) ---------->
    if modo_seleccion == "PROPUESTA":
        # ¿El jugador pertenece a alguno de los equipos del partido?
        pertenece_equipo_1 = (
            partido.equipo_local.equipo.integrantes.filter(pk=jugador.user_id).exists()
            or Inscripcion.objects.filter(jugador=jugador, equipo=partido.equipo_local.equipo, torneo=partido.torneo).exists()
        )

        pertenece_equipo_2 = (
            partido.equipo_visitante.equipo.integrantes.filter(pk=jugador.user_id).exists()
            or Inscripcion.objects.filter(jugador=jugador, equipo=partido.equipo_visitante.equipo, torneo=partido.torneo).exists()
        )



        es_del_partido = pertenece_equipo_1 or pertenece_equipo_2

        # Capitanes reales de los equipos (MiembroEquipo)
        capitan_local = getattr(partido.equipo_local.equipo.capitan, 'jugador', None)
        capitan_visitante = getattr(partido.equipo_visitante.equipo.capitan, 'jugador', None)

        # Determinar si el jugador logueado es capitán
        es_capitan_1 = (jugador == capitan_local)
        es_capitan_2 = (jugador == capitan_visitante)

        print("DEBUG → jugador:", jugador)
        print("DEBUG → capitan_local:", capitan_local)
        print("DEBUG → capitan_visitante:", capitan_visitante)
        print("DEBUG → es_capitan_1:", es_capitan_1, "| es_capitan_2:", es_capitan_2)


        mensaje = ""
        estadoBtn = ""

        # Validar que el partido no esté jugado
        if partido.jugado:
            return redirect('detalle_torneo', torneo_id=partido.torneo.id)

        if propuesta.cerrada == True:
            return redirect('detalle_partido', tipo='torneo', partido_id=partido.id)
        
        contador = propuesta.contador or 0
        cerrada = propuesta.cerrada or False

        #######################################################
        if contador == 0 and not cerrada:
            # Solo el capitán del equipo local puede iniciar
            if pertenece_equipo_1:
                if es_capitan_1:
                    mensaje = "Armen el partido"
                    mensaje2 = "Propongan días, horarios y canchas con tu equipo para que el rival elija o modifique."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Esperando a tu capitán..."
                    mensaje2 = "Solo el capitán de tu equipo puede iniciar la propuesta del partido."
                    estadoBtn = "Bloqueado"

            elif pertenece_equipo_2:
                # Visitante siempre espera en el primer turno
                mensaje = "Esperando una propuesta..."
                mensaje2 = "Esperando a que el equipo rival les envíe una propuesta de canchas, días y horarios para el partido. Les llegará una notificación cuando esto ocurra."
                estadoBtn = "Bloqueado"

            else:
                mensaje = "Partido en creación"
                mensaje2 = "Los equipos están decidiendo los detalles del partido..."

        #######################################################
        elif contador == 1 and not cerrada:
            if pertenece_equipo_1:
                if es_capitan_1:
                    mensaje = "Propuesta enviada"
                    mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Propuesta enviada"
                    mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                    estadoBtn = "Habilitado"
            elif pertenece_equipo_2:
                if es_capitan_2:
                    mensaje = "Propuesta recibida"
                    mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Propuesta recibida"
                    mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                    estadoBtn = "Bloqueado"
            else:
                mensaje = "Partido en creación"
                mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
        #######################################################
        elif contador == 2 and not cerrada:
            if pertenece_equipo_1:
                if es_capitan_1:
                    mensaje = "Propuesta recibida"
                    mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Propuesta recibida"
                    mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                    estadoBtn = "Bloqueado"
            elif pertenece_equipo_2:
                if es_capitan_2:
                    mensaje = "Propuesta enviada"
                    mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Propuesta enviada"
                    mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                    estadoBtn = "Habilitado"
            else:
                mensaje = "Partido en creación"
                mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
        #######################################################
        elif contador == 3 and not cerrada:
            if pertenece_equipo_1:
                if es_capitan_1:
                    mensaje = "Propuesta enviada"
                    mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Propuesta enviada"
                    mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                    estadoBtn = "Habilitado"
            elif pertenece_equipo_2:
                if es_capitan_2:
                    mensaje = "Propuesta recibida"
                    mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                    estadoBtn = "Habilitado"
                else:
                    mensaje = "Propuesta recibida"
                    mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                    estadoBtn = "Bloqueado"
            else:
                mensaje = "Partido en creación"
                mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
        #######################################################
        print("pertenece_equipo_1:", pertenece_equipo_1)
        print("pertenece_equipo_2:", pertenece_equipo_2)
        print("jugador.id:", jugador.id, "user.id:", jugador.user.id)
        print("integrantes equipo_local:", list(partido.equipo_local.equipo.integrantes.values_list('id', flat=True)))
        print("integrantes equipo_visitante:", list(partido.equipo_visitante.equipo.integrantes.values_list('id', flat=True)))
        
        contexto = {
            'modo': 'PROPUESTA',
            'partido': partido,
            'propuesta': propuesta,
            'mensaje': mensaje,
            'mensaje2': mensaje2,
            'estadoBtn': estadoBtn,
            'es_capitan_1': es_capitan_1,
            'es_capitan_2': es_capitan_2,
            'url_volver': url_volver,
            'ocultar_navbar': True,  # opcional si tu template usa esta lógica
        }
        
        # ---------- Lógica de DEFECTO (modo organizador) ----------
    else:
        es_encargado = request.user in torneo.encargados_carga.all()

        if request.method == "POST" and es_encargado:
            partido.cancha_id = request.POST.get("cancha")
            partido.dia = request.POST.get("dia")
            partido.hora_inicio = request.POST.get("hora_inicio")
            partido.save()
            return redirect('detalle_partido', tipo='torneo', partido_id=partido.id)

        contexto = {
            'modo': 'POR_DEFECTO',
            'partido': partido,
            'torneo': torneo,
            'es_encargado': es_encargado,
            'url_volver': url_volver,
            'ocultar_navbar': True,
        }

    return render(request, 'partido_torneo/detalle_propuesta.html', contexto)

@login_required
def configurar_partido_torneo(request, partido_id):
    """
    Vista para que los encargados del torneo configuren cancha, ubicación, día y hora del partido.
    Los datos se guardan por API (configurar_partido_api).
    """
    partido = get_object_or_404(
        Partido.objects.select_related('torneo', 'cancha', 'tipo_cancha'),
        id=partido_id
    )
    url_volver = reverse('detalle_propuesta', args=[partido_id])

    # Validar permisos: solo encargados del torneo pueden configurar
    if not partido.torneo.encargados_carga.filter(id=request.user.id).exists():
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)

    contexto = {
        'partido': partido,
        'torneo': partido.torneo,
        'tipo_partido': 'torneo',
        'ocultar_navbar': True,  # opcional si tu template usa esta lógica
        'url_volver': url_volver,
    }

    return render(request, 'configurar_partido_torneo.html', contexto)

@login_required
def propuesta_partido(request, partido_id):
    """
    Vista que muestra el detalle de una propuesta existente (fechas, horas, canchas y precios)
    antes de confirmar o aceptar.
    """
    partido = get_object_or_404(Partido, id=partido_id)

    # 🔹 Intentar obtener la propuesta del partido
    propuesta = getattr(partido, "propuesta", None)
    if not propuesta:
        return render(request, "errores/no_propuesta.html", {"mensaje": "No hay propuesta disponible para este partido."})

    # 🔹 Calcular precios unitarios (si hay precio total)
    def precio_unitario(precio_total, cantidad_jugadores):
        try:
            if not precio_total or not cantidad_jugadores:
                return None
            return round(Decimal(precio_total) / Decimal(cantidad_jugadores), 2)
        except (InvalidOperation, ZeroDivisionError):
            return None

    # Cantidad de jugadores por equipo (si está definida en el partido)
    cant_jugadores = getattr(partido, "jugadores_por_equipo", None)
    if not cant_jugadores:
        # Intentamos obtenerla desde la duración o un valor por defecto (p.ej. fútbol 5)
        cant_jugadores = 5

    precio_unitario1 = precio_unitario(propuesta.precio1, cant_jugadores)
    precio_unitario2 = precio_unitario(propuesta.precio2, cant_jugadores)

    # 🔹 URL para botón de volver
    try:
        url_volver = reverse("detalle_propuesta", args=[partido.id])
    except:
        url_volver = reverse("detalle_torneo", args=[partido.torneo.id])

    context = {
        'ocultar_navbar': True,
        "partido": partido,
        "propuesta": propuesta,
        "precio_unitario1": precio_unitario1,
        "precio_unitario2": precio_unitario2,
        "url_volver": url_volver,
    }

    return render(request, "propuesta_partido_torneo/propuesta_partido.html", context)

""" @login_required
def propuesta_partido(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    jugador = Jugador.objects.get(user=request.user)
    propuesta = getattr(partido, 'propuesta', None)
    torneo = partido.torneo
    modo_seleccion = torneo.modo_seleccion_partido
    

    # --- 🔹 CASO 2: modo PROPUESTA (lógica existente entre capitanes) ---
    # ¿El jugador pertenece a alguno de los equipos del partido?
    pertenece_equipo_1 = (
        Inscripcion.objects.filter(
            jugador=jugador,
            equipo=partido.equipo_local.equipo,  # accedemos al equipo real
            torneo=partido.torneo
        ).exists()

        or IntegranteEquipo.objects.filter(
            usuario=jugador.user,
            equipo=partido.equipo_local.equipo,  # accedemos al Equipo real
            aceptado=True
        ).exists()

        or partido.equipo_local.equipo.integrantes.filter(pk=jugador.user_id).exists()
    )

    pertenece_equipo_2 = (
        Inscripcion.objects.filter(
            jugador=jugador,
            equipo=partido.equipo_visitante.equipo,  # accedemos al equipo real
            torneo=partido.torneo
        ).exists()

        or IntegranteEquipo.objects.filter(
            usuario=jugador.user,
            equipo=partido.equipo_visitante.equipo,  # accedemos al Equipo real
            aceptado=True
        ).exists()

        or partido.equipo_visitante.equipo.integrantes.filter(pk=jugador.user_id).exists()
    )


    es_del_partido = pertenece_equipo_1 or pertenece_equipo_2
    
    es_capitan_1 = (
        jugador == getattr(partido.equipo_local.equipo.capitan, 'jugador', None)
        or jugador == partido.equipo_local.equipo.capitan
    )
    es_capitan_2 = (
        jugador == getattr(partido.equipo_visitante.equipo.capitan, 'jugador', None)
        or jugador == partido.equipo_visitante.equipo.capitan
    )
    
    mensaje = ""
    estadoBtn = ""

    # Validar que el partido no esté jugado
    if partido.jugado:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)

    if propuesta.cerrada == True:
        return redirect('detalle_partido', tipo='torneo', partido_id=partido.id)

    #######################################################
    if propuesta.contador == 0 and not propuesta.cerrada:
        if pertenece_equipo_1:
            if es_capitan_1:
                mensaje = "Armen el partido"
                mensaje2 = "Propongan días, horarios y canchas con tu equipo para que el rival elija o modifique."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Armen el partido"
                mensaje2 = "Propongan días, horarios y canchas con tu equipo para que el rival elija o modifique."
                estadoBtn = "Bloqueado"
        elif pertenece_equipo_2:
            if es_capitan_2:
                mensaje = "Esperando una propuesta..."
                mensaje2 = "Esperando a que el equipo rival les envié una propuesta de canchas, días y horarios para el partido. Les llegara una notificación cuando esto ocurra."
            else:
                mensaje = "Esperando una propuesta..."
                mensaje2 = "Esperando a que el equipo rival les envié una propuesta de canchas, días y horarios para el partido. Les llegara una notificación cuando esto ocurra."
        else:
            mensaje = "Partido en creación"
            mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
    #######################################################
    elif propuesta.contador == 1 and not propuesta.cerrada:
        if pertenece_equipo_1:
            if es_capitan_1:
                mensaje = "Propuesta enviada"
                mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Propuesta enviada"
                mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                estadoBtn = "Habilitado"
        elif pertenece_equipo_2:
            if es_capitan_2:
                mensaje = "Propuesta recibida"
                mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Propuesta recibida"
                mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                estadoBtn = "Bloqueado"
        else:
            mensaje = "Partido en creación"
            mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
    #######################################################
    elif propuesta.contador == 2 and not propuesta.cerrada:
        if pertenece_equipo_1:
            if es_capitan_1:
                mensaje = "Propuesta recibida"
                mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Propuesta recibida"
                mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                estadoBtn = "Bloqueado"
        elif pertenece_equipo_2:
            if es_capitan_2:
                mensaje = "Propuesta enviada"
                mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Propuesta enviada"
                mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                estadoBtn = "Habilitado"
        else:
            mensaje = "Partido en creación"
            mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
    #######################################################
    elif propuesta.contador == 3 and not propuesta.cerrada:
        if pertenece_equipo_1:
            if es_capitan_1:
                mensaje = "Propuesta enviada"
                mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Propuesta enviada"
                mensaje2 = "La propuesta de tu equipo ya fue enviada al equipo rival. Esperando su respuesta."
                estadoBtn = "Habilitado"
        elif pertenece_equipo_2:
            if es_capitan_2:
                mensaje = "Propuesta recibida"
                mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                estadoBtn = "Habilitado"
            else:
                mensaje = "Propuesta recibida"
                mensaje2 = "El rival les hizo una propuesta para el partido, revisen los detalles y decidan si aceptan o si quieren modificarla."
                estadoBtn = "Bloqueado"
        else:
            mensaje = "Partido en creación"
            mensaje2 = "Los equipos estan decidiendo los detalles del partido..."
    #######################################################
    print(es_capitan_1, es_capitan_2)

    contexto = {
        'mensaje': mensaje,
        'mensaje2': mensaje2,
        'estadoBtn': estadoBtn,
        'partido': partido,
        'propuesta': propuesta,
        'jugador': jugador,
        'es_capitan_1': es_capitan_1,
        'es_capitan_2': es_capitan_2,
    }
    return render(request, 'partido_torneo/propuesta_partido.html', contexto)

@login_required
def propuesta_partido_defecto(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    torneo = partido.torneo
    es_encargado = request.user in torneo.encargados_carga.all()

    if not es_encargado:
        return render(request, 'partido_torneo/detalle_propuesta.html', {
            'partido': partido,
            'mensaje': "Esperando confirmación del organizador",
            'mensaje2': "El encargado del torneo definirá la cancha, fecha y hora del partido."
        })

    # Si es encargado, permite definir los datos directamente
    if request.method == "POST":
        partido.cancha_id = request.POST.get("cancha")
        partido.dia = request.POST.get("dia")
        partido.hora_inicio = request.POST.get("hora_inicio")
        partido.save()
        return redirect('detalle_partido', tipo='torneo', partido_id=partido.id)

    return render(request, 'partido_torneo/propuesta_partido_defecto.html', {
        'partido': partido,
        'torneo': torneo,
        'es_encargado': True,
    })

 """

@login_required
def propuesta_partido_1(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    jugador = Jugador.objects.get(user=request.user)
    url_volver = reverse("seleccionar_propuesta", args=[partido.id])

    # Validar que el partido no esté jugado
    if partido.jugado:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)

    # Validar que sea capitán del equipo local o visitante
    capitan_local = getattr(partido.equipo_local.equipo.capitan, 'jugador', None)
    capitan_visitante = getattr(partido.equipo_visitante.equipo.capitan, 'jugador', None)
    
    if jugador not in [capitan_local, capitan_visitante]:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)
    
    
    # Obtener la propuesta si existe
    propuesta = getattr(partido, 'propuesta', None)

    contexto = {
        'ocultar_navbar': True,
        'propuesta': propuesta,
        'partido': partido,
        'url_volver': url_volver,
    }
    return render(request, 'propuesta_partido_torneo/propuesta_1.html', contexto)

@login_required
def propuesta_partido_2(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    jugador = Jugador.objects.get(user=request.user)
    url_volver = reverse("propuesta_partido_1", args=[partido.id])


    # Validar que el partido no esté jugado
    if partido.jugado:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)

    # Validar que sea capitán del equipo local o visitante
    capitan_local = getattr(partido.equipo_local.equipo.capitan, 'jugador', None)
    capitan_visitante = getattr(partido.equipo_visitante.equipo.capitan, 'jugador', None)


    canchas_qs = Cancha.objects.prefetch_related('tipo_cancha').all()
    
    canchas_json = {
        str(cancha.id): {
            "nombre": cancha.nombre,
            "direccion": cancha.direccion or "",
            "tipos": [tc.nombre for tc in cancha.tipo_cancha.all()]
        }
        for cancha in canchas_qs
    }

    return render(request, 'propuesta_partido_torneo/propuesta_2.html', {
        'ocultar_navbar': True,
        'partido': partido,
        'canchas': canchas_qs,
        'canchas_json': json.dumps(canchas_json, cls=DjangoJSONEncoder),
        'url_volver': url_volver,
    })
    
# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from ..models import Propuesta, Partido, Cancha
import json
from decimal import Decimal

@csrf_exempt
def crear_propuesta(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        partido_id = data.get('partido_id')

        partido = Partido.objects.get(id=partido_id)
        jugador = Jugador.objects.get(user=request.user)

        # 🔹 Obtener o crear la propuesta
        propuesta, _ = Propuesta.objects.get_or_create(partido=partido)

        # Función para procesar cancha (crear si no existe)
        def get_or_create_cancha(value, ubicacion=None):
            if not value:
                return None
            try:
                return Cancha.objects.get(id=int(value))
            except (ValueError, Cancha.DoesNotExist):
                cancha, _ = Cancha.objects.get_or_create(nombre=value, defaults={"direccion": ubicacion or ""})
                return cancha


        # Asignar las canchas (crea si no existen)
        propuesta.cancha1 = get_or_create_cancha(data.get('cancha1'), data.get('ubicacion1'))
        propuesta.cancha2 = get_or_create_cancha(data.get('cancha2'), data.get('ubicacion2'))


        # Resto de campos
        propuesta.ubicacion1 = data.get('ubicacion1') or ""
        propuesta.ubicacion2 = data.get('ubicacion2') or ""
        propuesta.precio1 = data.get('precio1') or None
        propuesta.precio2 = data.get('precio2') or None
        propuesta.fecha1 = data.get('fecha1')
        propuesta.hora1  = data.get('hora1')
        propuesta.fecha2 = data.get('fecha2')
        propuesta.hora2  = data.get('hora2')
        propuesta.fecha3 = data.get('fecha3')
        propuesta.hora3  = data.get('hora3')

        propuesta.respondida = True
        propuesta.contador = (propuesta.contador or 0) + 1
        if propuesta.contador >= 4:
            propuesta.cerrada = True

        propuesta.save()

        return JsonResponse({"success": True, "id": propuesta.id})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)



@login_required
def seleccionar_propuesta(request, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)
    jugador = Jugador.objects.get(user=request.user)
    propuesta = getattr(partido, 'propuesta', None)
    url_volver = reverse('detalle_propuesta', args=[partido.id])

    if request.method == 'POST':
        opcion_dia_hora = int(request.POST.get('opcion_dia_hora', 0))
        opcion_cancha   = int(request.POST.get('opcion_cancha', 0))

        if propuesta:
            propuesta.opcion_dia_hora = opcion_dia_hora
            propuesta.opcion_cancha   = opcion_cancha
            propuesta.cerrada = True
            propuesta.contador += 1
            propuesta.save()

        # 🔹 Copiamos fecha/hora, cancha y **precio** al Partido
        if propuesta and partido:
            # Día y hora
            if opcion_dia_hora == 1:
                partido.dia = propuesta.fecha1
                partido.hora_inicio = propuesta.hora1
            elif opcion_dia_hora == 2:
                partido.dia = propuesta.fecha2
                partido.hora_inicio = propuesta.hora2
            elif opcion_dia_hora == 3:
                partido.dia = propuesta.fecha3
                partido.hora_inicio = propuesta.hora3

            # Cancha + PRECIO
            precio_elegido = None
            if opcion_cancha == 1:
                partido.cancha = propuesta.cancha1
                precio_elegido = propuesta.precio1
            elif opcion_cancha == 2:
                partido.cancha = propuesta.cancha2
                precio_elegido = propuesta.precio2
                
            if hasattr(partido, 'precio_total'):
                partido.precio_total = precio_elegido

            print("🧪 opcion_cancha=", opcion_cancha, "precio1/2=", propuesta.precio1, propuesta.precio2)
            print("🧪 precio_total antes:", getattr(partido, 'precio_total', None))

            partido.save()

        return redirect('propuesta_partido', partido_id=partido.id)

    # --- GET ---
    # --- GET ---
    if partido.jugado:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)

    # ⚠️ Ajustar chequeo de capitán correctamente
    capitan_local = getattr(partido.equipo_local.equipo.capitan, 'jugador', None)
    capitan_visitante = getattr(partido.equipo_visitante.equipo.capitan, 'jugador', None)
    es_capitan = (jugador == capitan_local or jugador == capitan_visitante)

    if not es_capitan:
        return redirect('detalle_torneo', torneo_id=partido.torneo.id)


    # Mostrar precios unitarios con cuidado si hay None
    precio_unitario1 = precio_unitario2 = None
    if propuesta:
        def fmt_unitario(total):
            try:
                jugadores_total = getattr(partido, 'max_jugadores', None) or 10
                return "{:,.2f}".format((total or 0) / jugadores_total).replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                return None
        if propuesta.precio1 is not None:
            precio_unitario1 = fmt_unitario(propuesta.precio1)
        if propuesta.precio2 is not None:
            precio_unitario2 = fmt_unitario(propuesta.precio2)

    contexto = {
        'ocultar_navbar': True,
        'url_volver': url_volver,
        'partido': partido,
        'propuesta': propuesta,
        'precio_unitario1': precio_unitario1,
        'precio_unitario2': precio_unitario2,
    }
    return render(request, 'propuesta_partido_torneo/seleccionar_propuesta.html', contexto)


@csrf_exempt
@login_required
def eliminar_jugador(request, partido_id, jugador_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    if request.user != partido.creador:
        return HttpResponseForbidden("No autorizado")

    jugador = get_object_or_404(Jugador, id=jugador_id)

    # Eliminar del partido principal
    partido.jugadores.remove(jugador)

    # Eliminar si está en alguno de los equipos
    partido.equipo_local.remove(jugador)
    partido.equipo_visitante.remove(jugador)

    # Eliminar invitaciones relacionadas a ese jugador en ese partido
    Invitacion.objects.filter(partido=partido, jugador=jugador).delete()

    return JsonResponse({'ok': True})


@login_required
def jugadores_invitados_api(request, partido_id):
    # Invitaciones ENVIADAS por el creador del partido, pero NO aceptadas aún
    invitaciones = Invitacion.objects.filter(
        partido_id=partido_id,
        partido__creador=request.user,
        aceptada=False  # <---- clave
    )

    data = []

    for inv in invitaciones:
        jugador = inv.jugador
        data.append({
            "id": jugador.id,
            "nombre": jugador.nombre,
            "provincia": obtener_codigo_provincia(jugador.provincia),
            "ciudad": jugador.ciudad,
            "img_path": jugador.foto.url if jugador.foto else None,
            "codigo": "0000",
            "aceptada": inv.aceptada
        })

    return JsonResponse(data, safe=False)


@login_required
@require_POST
def cancelar_invitacion(request, partido_id, jugador_id):
    try:
        invitacion = Invitacion.objects.get(partido_id=partido_id, jugador_id=jugador_id, aceptada=False)

        if invitacion.partido.creador != request.user:
            return JsonResponse({"error": "No autorizado"}, status=403)

        invitacion.delete()
        return JsonResponse({"ok": True, "mensaje": "Invitación cancelada"})
    
    except Invitacion.DoesNotExist:
        return JsonResponse({"error": "Invitación no encontrada o ya aceptada"}, status=404)
    


@login_required
def vista_principal(request):
    jugador = Jugador.objects.get(user=request.user)

    # Invitaciones a partidos NO leídas (aunque hayan sido aceptadas o rechazadas)
    cantidad_partido = Invitacion.objects.filter(
        jugador=jugador,
        vista=False,
        partido__cancelado=False,
        partido__jugado=False
    ).count()

    # Invitaciones a equipos NO leídas
    cantidad_equipo = InvitacionEquipo.objects.filter(
        jugador=jugador,
        vista=False
    ).count()

    # Notificaciones del sistema NO leídas
    cantidad_sistema = Notificacion.objects.filter(
        usuario=request.user,
        leida=False
    ).count()

    cantidad_notificaciones = cantidad_partido + cantidad_equipo + cantidad_sistema

    return render(request, 'app_torneo_f5/base.html', {
        'cantidad_notificaciones': cantidad_notificaciones
    })


# app_torneo_f5/views.py
from django.http import Http404
from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth import login, get_backends
from django.core.exceptions import ImproperlyConfigured


def magic_ok(request, token):
    from ..models import MagicLoginToken

    try:
        tok = (MagicLoginToken.objects
               .select_related('user')
               .get(token=token))
    except MagicLoginToken.DoesNotExist:
        raise Http404("Token inválido")

    if not tok.is_valid():
        raise Http404("Enlace vencido o usado")

    # Marcar usado y verificar email
    tok.used = True
    tok.save(update_fields=["used"])
    user = tok.user
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    # Obtener el primer backend cargado realmente
    backend_obj = next(iter(get_backends()), None)
    if not backend_obj:
        raise ImproperlyConfigured("No hay authentication backends cargados.")

    backend_path = f"{backend_obj.__module__}.{backend_obj.__class__.__name__}"
    login(request, user, backend=backend_path)

    return redirect('bienvenido')


def assetlinks_json(request):
    data = [{
        "relation": [
            "delegate_permission/common.handle_all_urls",
            "delegate_permission/common.get_login_creds"
        ],
        "target": {
            "namespace": "android_app",
            "package_name": "ar.com.octopush.ticas.twa",
            "sha256_cert_fingerprints": [
                "1E:AE:AF:23:44:4F:7D:BE:30:92:0D:89:34:0B:AE:0C:0C:07:9E:ED:39:D1:3F:B3:4E:0D:4A:3A:94:70:EB:AE"
            ]
        }
    }]
    return JsonResponse(data, safe=False)



def privacy_policy(request):
    return render(request, 'app_torneo_f5/privacy_policy.html')

from pathlib import Path
from django.http import FileResponse, Http404
from django.conf import settings

def descargar_apk(request):
    apk_path = Path(settings.BASE_DIR) / 'app_torneo_f5' / 'static' / 'apk' / 'Ticas.apk'
    if not apk_path.exists():
        raise Http404("APK no encontrado")

    return FileResponse(
        open(apk_path, 'rb'),
        as_attachment=True,   # 👈 fuerza la descarga
        filename='Ticas.apk',
        content_type='application/vnd.android.package-archive'
    )

@login_required
def crear_partido (request):
    return render(request, 'crear_partido/crear_partido.html')


@login_required
@require_POST
def marcar_notificacion_vista(request, pk):
    n = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    if not n.visto:
        n.visto = True
        # n.fecha_visto = timezone.now()  # si tenés el campo
        n.save(update_fields=['visto'])  # , 'fecha_visto'
    return JsonResponse({'ok': True})


@login_required
def abandonar_partido(request, partido_id):
    if request.method != "POST":
        return HttpResponseForbidden("Método no permitido")

    partido = get_object_or_404(PartidoAmistoso, id=partido_id)
    jugador = get_object_or_404(Jugador, user=request.user)

    # lo sacamos de ambos equipos, por seguridad
    partido.equipo_local.remove(jugador)
    partido.equipo_visitante.remove(jugador)
    partido.jugadores.remove(jugador)

    return JsonResponse({"success": True, "msg": "Te saliste del partido."})


def canchas_futbol(request):
    canchas = Cancha.objects.all()
    jugador = Jugador.objects.get(user=request.user)
    data = []

    for cancha in canchas:
        data.append({
            "id": cancha.id,
            "nombre": cancha.nombre,
            "ubicacion": cancha.direccion,
            "formatos": list(cancha.tipo_cancha.values_list("nombre", flat=True))  # suponiendo campo 'nombre'
            
        })

    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})


def form_delete_account(request):
    return redirect('https://forms.gle/t9qPNtUiPa6VrNeQ9', permanent=True)




from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from app_torneo_f5.models import Partido, EstadisticasJugadorPartido

def carga_estadistica(request, tipo, partido_id):
    partido = get_object_or_404(Partido, id=partido_id)

    # 🚫 Si el partido ya fue jugado o finalizado → redirigir
    if partido.jugado:
        return redirect(f"/partido/{tipo}/{partido.id}/")

    # 🚫 Si ya existen estadísticas cargadas → redirigir
    if EstadisticasJugadorPartido.objects.filter(partido=partido).exists():
        return redirect(f"/partido/{tipo}/{partido.id}/")

    # ✅ OK → renderizar pantalla de carga
    return render(
        request,
        'carga_estadisticas/carga_estadistica_torneo.html',
        {
            'tipo': tipo,
            'partido_id': partido.id,
        }
    )




