# app_torneo_f5/models.py
from django.db import models
from django.conf import settings
from datetime import date
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from django import forms
import uuid
import datetime
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from multiselectfield import MultiSelectField
from django.apps import apps

class CustomUser(AbstractUser):
    email_verified = models.BooleanField(default=False)
    picture = models.URLField(blank=True, null=True)
    full_name = models.CharField(max_length=150, blank=True, null=True)  # ⬅️ NUEVO

class Equipo(models.Model):
    nombre = models.CharField(max_length=100)
    nombre_corto = models.CharField(max_length=3, default="NAA")
    provincia = models.CharField(max_length=100, null=True, blank=True)
    ciudad = models.CharField(max_length=100, null=True, blank=True)
    escudo = models.ImageField(upload_to='escudos_equipos/', blank=True, null=True, default='../static/images/escudo-equipo/equipo-a.png')
    integrantes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='equipos', blank=True)
    """ capitan = models.ForeignKey('Jugador', on_delete=models.PROTECT, related_name='capitan_de', null=True, blank=True) """
    capitan = models.ForeignKey('app_torneo_f5.MiembroEquipo', on_delete=models.CASCADE, null=True, blank=True, related_name='capitan_equipo')
    total_integrantes = models.PositiveIntegerField(default=0)
    torneos_en_activo = models.ManyToManyField('app_torneo_f5.Torneo', related_name='equipos_activos', blank=True)
    historial_partidos = models.TextField(blank=True)
    cantidad_partidos_jugados = models.PositiveIntegerField(default=0)
    goles_totales = models.PositiveIntegerField(default=0)
    goles_promedio = models.FloatField(default=0)
    asistencias_totales = models.PositiveIntegerField(default=0)
    asistencias_promedio = models.FloatField(default=0)
    atajadas_totales = models.PositiveIntegerField(default=0)
    atajadas_promedio = models.FloatField(default=0)
    fecha_creacion = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre


class Jugador(models.Model):
    temporal = models.BooleanField(default=False)
    paso_perfil = models.IntegerField(default=0, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    foto = models.ImageField(
        upload_to='static/jugador.png',
        blank=True,
        null=True,
        default='../static/jugador.png'
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    altura = models.PositiveIntegerField(blank=True, null=True)
    pie_preferido = models.CharField(
        max_length=15,
        choices=[('Der', 'Derecho'), ('Izq', 'Izquierdo'), ('Amb', 'Ambidiestro')],
        blank=True, null=True
    )
    posicion_preferida = models.CharField(
        max_length=20,
        choices=[
            ('Arquero', 'Arquero'),
            ('Defensa', 'Defensa'),
            ('Mediocampista', 'Mediocampista'),
            ('Delantero', 'Delantero'),
            ('Versátil', 'Versátil')
        ],
        blank=True, null=True
    )
    genero = models.CharField(
        max_length=10,
        choices=[('masculino', 'Masculino'), ('femenino', 'Femenino'), ('otro', 'Otro')],
        blank=True, null=True
    )
    torneos_activos = models.ManyToManyField('Torneo', blank=True)
    fortalezas = models.TextField(blank=True, null=True)
    debilidades = models.TextField(blank=True, null=True)
    mundiales_ganados = models.PositiveIntegerField(default=0)
    horario_disponible = models.CharField(max_length=100, blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    contacto = models.CharField(max_length=100, blank=True, null=True)

    partidos_jugados = models.PositiveIntegerField(default=0)
    goles_totales = models.PositiveIntegerField(default=0)
    goles_promedio = models.FloatField(default=0)
    asistencias_totales = models.PositiveIntegerField(default=0)
    asistencias_promedio = models.FloatField(default=0)
    atajadas_totales = models.PositiveIntegerField(default=0)
    atajadas_promedio = models.FloatField(default=0)
    participaciones_gol = models.PositiveIntegerField(default=0)

    ultimos_partidos = models.TextField(
        help_text='Ej: 2 goles, 1 asistencia, calificación 4',
        blank=True
    )

    valoracion_ataque = models.FloatField(default=0.0)
    valoracion_defensa = models.FloatField(default=0.0)
    valoracion_creatividad = models.FloatField(default=0.0)
    valoracion_portero = models.FloatField(default=0.0)
    valoracion_habilidad = models.FloatField(default=0.0)

    edad = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre}".strip()

    @property
    def primer_nombre(self):
        return self.nombre.split()[0] if self.nombre else ""

    def actualizar_valoraciones(self):
        from django.db.models import Sum
        from app_torneo_f5.models import EstadisticasJugadorPartido, EstadisticaAmistosa

        qs_torneo = EstadisticasJugadorPartido.objects.filter(
            miembro_equipo__jugador=self,
            jugo=True
        )

        qs_amist = EstadisticaAmistosa.objects.filter(
            jugador=self,
            jugo=True
        )

        agg_torneo = qs_torneo.aggregate(
            goles=Sum('goles'),
            asistencias=Sum('asistencias'),
            atajadas=Sum('atajadas')
        )

        agg_amist = qs_amist.aggregate(
            goles=Sum('goles'),
            asistencias=Sum('asistencias'),
            atajadas=Sum('atajadas')
        )

        total_goles = (agg_torneo['goles'] or 0) + (agg_amist['goles'] or 0)
        total_asists = (agg_torneo['asistencias'] or 0) + (agg_amist['asistencias'] or 0)
        total_atajs = (agg_torneo['atajadas'] or 0) + (agg_amist['atajadas'] or 0)

        partidos_jugados = qs_torneo.count() + qs_amist.count()

        self.goles_totales = total_goles
        self.asistencias_totales = total_asists
        self.atajadas_totales = total_atajs
        self.participaciones_gol = total_goles + total_asists
        self.partidos_jugados = partidos_jugados

        if partidos_jugados > 0:
            self.goles_promedio = round(total_goles / partidos_jugados, 2)
            self.asistencias_promedio = round(total_asists / partidos_jugados, 2)
            self.atajadas_promedio = round(total_atajs / partidos_jugados, 2)

            self.valoracion_ataque = min(round(total_goles / partidos_jugados, 1), 5.0)
            self.valoracion_creatividad = min(round(total_asists / partidos_jugados, 1), 5.0)
            self.valoracion_portero = min(round(total_atajs / partidos_jugados, 1), 5.0)
        else:
            self.goles_promedio = 0.0
            self.asistencias_promedio = 0.0
            self.atajadas_promedio = 0.0

        self.save(update_fields=[
            'goles_totales','asistencias_totales','atajadas_totales',
            'participaciones_gol','partidos_jugados',
            'goles_promedio','asistencias_promedio','atajadas_promedio',
            'valoracion_ataque','valoracion_creatividad','valoracion_portero'
        ])



class TipoCancha(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Cancha(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    tipo_cancha = models.ManyToManyField(TipoCancha)
    imagen = models.ImageField(upload_to='imagenes_cancha/', blank=True, null=True)
    
    def __str__(self):
        return self.nombre

class EstadisticaJugador(models.Model):
    partido = models.ForeignKey('app_torneo_f5.Partido', on_delete=models.CASCADE, related_name='estadisticas')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='estadisticas_torneo')
    goles = models.PositiveIntegerField(default=0)
    asistencias = models.PositiveIntegerField(default=0)
    atajadas = models.PositiveIntegerField(default=0)
    jugo = models.BooleanField(default=True)
    calificacion = models.FloatField(null=True, blank=True)
    calificacion_defensa = models.FloatField(null=True, blank=True)
    calificacion_manejo = models.FloatField(null=True, blank=True)
    dia = models.DateField(null=True, blank=True)
    cantidad_calificaciones = models.PositiveIntegerField(default=1)
    cargada = models.BooleanField(default=False)

    def __str__(self):
        return f'Estadísticas de {self.jugador} en {self.partido}'
    
    @classmethod
    def calcular_promedio_calificacion(cls, jugador, partido):
        calificaciones = cls.objects.filter(
            partido=partido,
            jugador=jugador,
            calificacion__isnull=False
        ).values_list('calificacion', flat=True)

        if not calificaciones:
            return None

        return round(sum(calificaciones) / len(calificaciones), 2)

    def save(self, *args, **kwargs):
        # Asignar día si el partido lo tiene
        if self.partido and self.partido.dia:
            self.dia = self.partido.dia
    
        # Guardar primero la estadística
        super().save(*args, **kwargs)
    
        # Actualizar resultado del partido
        if self.partido and hasattr(self.partido, 'actualizar_resultado'):
            self.partido.actualizar_resultado()
    
        # Actualizar posiciones en torneo
        if self.partido and self.partido.torneo:
            torneo = self.partido.torneo
            participaciones = Participacion.objects.filter(torneo=torneo).order_by('-puntos', '-dif', '-gf')
            for idx, p in enumerate(participaciones, start=1):
                p.posicion = idx
                p.save()
    
    


class PerfilUsuario(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    es_primer_ingreso = models.BooleanField(default=True)


class Participacion(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    torneo = models.ForeignKey('app_torneo_f5.Torneo', on_delete=models.CASCADE)
    puntos = models.PositiveIntegerField(default=0)
    pj = models.PositiveIntegerField(default=0)
    pg = models.PositiveIntegerField(default=0)
    pe = models.PositiveIntegerField(default=0)
    pp = models.PositiveIntegerField(default=0)
    gf = models.PositiveIntegerField(default=0)
    gc = models.PositiveIntegerField(default=0)
    dif = models.IntegerField(default=0)
    sigue_en_competencia = models.BooleanField(default=True)
    posicion = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('equipo', 'torneo')
        
    def __str__(self):
        return f"{self.equipo} en {self.torneo}"


class Inscripcion(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    equipo = models.ForeignKey('Equipo', on_delete=models.CASCADE)
    torneo = models.ForeignKey('Torneo', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('jugador', 'equipo', 'torneo')


import random , string
def generar_codigo():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
class PartidoAmistoso(models.Model):
    cancha = models.CharField(max_length=200, blank=True, null=True)  
    tipo_cancha = models.CharField(max_length=100, blank=True, null=True)  
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='amistosos_creados')
    codigo_invitacion = models.CharField(max_length=15, unique=True, default=generar_codigo, editable=False)
    MODO_JUEGO = [
        ('individual', 'Jugadores individuales')
    ]
    modo_juego = models.CharField(max_length=20, choices=MODO_JUEGO, default='individual')
    duracion = models.PositiveIntegerField(
        help_text="Duración en minutos",
        default=60
    )
    jugadores = models.ManyToManyField(Jugador, blank=True)
    dia = models.DateField(null=True, blank=True)  # ⬅️ antes: fecha = models.DateTimeField()
    hora_inicio = models.TimeField(default=datetime.time(20, 0))
    equipo_local = models.ManyToManyField(Jugador, related_name='amistosos_como_local', blank=True)
    equipo_visitante = models.ManyToManyField(Jugador, related_name='amistosos_como_visitante', blank=True)
    color_equipo_local     = models.CharField(max_length=15, default='bg-d-equipo1', blank=True)
    color_equipo_visitante = models.CharField(max_length=15, default='bg-d-equipo2', blank=True)
    goles_equipo_local = models.PositiveIntegerField(default=0)
    goles_equipo_visitante = models.PositiveIntegerField(default=0)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    max_jugadores = models.PositiveIntegerField(default=10)
    permite_invitaciones = models.BooleanField(default=True)
    jugando = models.BooleanField(default=False)
    jugado = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def clean(self):
        if self.jugando and self.jugado:
            raise ValidationError("No se puede estar 'jugando' y 'jugado' al mismo tiempo.")
        # Si está cancelado, no puede estar jugado ni jugando
        if self.cancelado and (self.jugado or self.jugando):
            raise ValidationError("Un partido cancelado no puede estar 'jugado' ni 'jugando'.")
    
    def actualizar_resultado(self):
        if self.cancelado:
            return
        stats = self.estadisticas.all()
        equipo1 = list(self.equipo_local.all())
        equipo2 = list(self.equipo_visitante.all())
        if not equipo1 and not equipo2:
            return
        goles_local = sum(s.goles for s in stats if s.jugador in equipo1)
        goles_visitante = sum(s.goles for s in stats if s.jugador in equipo2)
        self.goles_equipo_local = goles_local
        self.goles_equipo_visitante = goles_visitante
        self.save()

    def save(self, *args, **kwargs):
        # Fuerza las invariantes también en save (por si no se llamó a clean)
        if self.cancelado:
            self.jugado = False
            self.jugando = False
            # Si querés, también podés nullear resultados:
            # self.goles_equipo_local = 0
            # self.goles_equipo_visitante = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Partido {self.id}"

    def marcar_como_jugado_si_finalizado(self):
        # Si está cancelado, nunca debe pasar a jugado
        if self.cancelado:
            if self.jugado:
                self.jugado = False
                self.save(update_fields=['jugado'])
            return

        if self.finalizado and not self.jugado:
            self.jugado = True
            self.save(update_fields=['jugado'])

    @property
    def finalizado(self):
        if self.cancelado:
            return False
        if self.dia and self.hora_inicio and self.duracion:
            inicio = datetime.datetime.combine(self.dia, self.hora_inicio)
            inicio_aware = timezone.make_aware(inicio, timezone.get_current_timezone())
            fin = inicio_aware + timedelta(minutes=self.duracion)
            return timezone.now() > fin
        return False




class EstadisticaAmistosa(models.Model):
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='estadisticas_amistosas')
    partido = models.ForeignKey(PartidoAmistoso, on_delete=models.CASCADE, related_name='estadisticas')
    goles = models.PositiveIntegerField(default=0)
    asistencias = models.PositiveIntegerField(default=0)
    atajadas = models.PositiveIntegerField(default=0)
    jugo = models.BooleanField(default=True)
    calificacion = models.FloatField(null=True, blank=True)
    calificacion_defensa = models.FloatField(null=True, blank=True)
    calificacion_manejo = models.FloatField(null=True, blank=True)
    dia = models.DateField(null=True, blank=True)
    cantidad_calificaciones = models.PositiveIntegerField(default=1)
    cargada = models.BooleanField(default=False)

    # --- nuevos ---
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    vencida = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('partido', 'jugador')

    def save(self, *args, **kwargs):
        # setear dia antes de guardar
        if self.partido and getattr(self.partido, 'dia', None) and not self.dia:
            self.dia = self.partido.dia

        # calcular fecha_vencimiento solo si no existe y hay día
        if self.dia and self.fecha_vencimiento is None:
            self.fecha_vencimiento = self.dia + timedelta(days=2)

        # actualizar flag vencida en base a la fecha
        if self.fecha_vencimiento:
            self.vencida = timezone.localdate() > self.fecha_vencimiento
        else:
            self.vencida = False

        super().save(*args, **kwargs)




    
    def calcular_goles_por_equipo(partido):
        from app_torneo_f5.models import EstadisticaAmistosa
        stats = EstadisticaAmistosa.objects.filter(partido=partido)
        if partido.modo_juego == 'equipo_vs_equipo':
            jugadores_equipo_local = partido.equipo_local.integrantes.all()
            jugadores_equipo_visitante = partido.equipo_visitante.integrantes.all()
            goles_local = sum(s.goles for s in stats if s.jugador.user in jugadores_equipo_local)
            goles_visitante = sum(s.goles for s in stats if s.jugador.user in jugadores_equipo_visitante)
        elif partido.modo_juego == 'equipo_vs_individual':
            if partido.equipo_local:
                jugadores_equipo_local = partido.equipo_local.integrantes.all()
                goles_local = sum(s.goles for s in stats if s.jugador.user in jugadores_equipo_local)
                goles_visitante = sum(s.goles for s in stats if s.jugador.user not in jugadores_equipo_local)
            else:
                jugadores_equipo_visitante = partido.equipo_visitante.integrantes.all()
                goles_visitante = sum(s.goles for s in stats if s.jugador.user in jugadores_equipo_visitante)
                goles_local = sum(s.goles for s in stats if s.jugador.user not in jugadores_equipo_visitante)
        else:
            jugadores = list(partido.jugadores.all())
            mitad = len(jugadores) // 2
            equipo1 = jugadores[:mitad]
            equipo2 = jugadores[mitad:]
            goles_local = sum(s.goles for s in stats if s.jugador in equipo1)
            goles_visitante = sum(s.goles for s in stats if s.jugador in equipo2)
        return goles_local, goles_visitante
    
class IntegranteEquipo(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='integranteequipos')
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='integranteequipos')
    aceptado = models.BooleanField(default=False)


class Invitacion(models.Model):
    vista = models.BooleanField(default=False)
    partido = models.ForeignKey('PartidoAmistoso', on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invitaciones_enviadas'
    )
    fecha_envio = models.DateTimeField(auto_now_add=True)
    aceptada = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitación a {self.jugador.nombre} para {self.partido}"
class InvitacionEquipo(models.Model):
    vista = models.BooleanField(default=False)
    equipo = models.ForeignKey('Equipo', on_delete=models.CASCADE)
    jugador = models.ForeignKey('Jugador', on_delete=models.CASCADE)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invitaciones_equipo_enviadas'
    )
    fecha_envio = models.DateTimeField(auto_now_add=True)
    aceptada = models.BooleanField(null=True, default=None)  # None = pendiente

    class Meta:
        unique_together = ('equipo', 'jugador')  # para evitar duplicados

    def __str__(self):
        estado = "pendiente" if self.aceptada is None else ("aceptada" if self.aceptada else "rechazada")
        return f"Invitación de {self.equipo.nombre} a {self.jugador.nombre} ({estado})"
class Notificacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)
    tipo = models.CharField(max_length=30, default='sistema')  # 'estadistica', 'sistema', etc.
    extra_id = models.PositiveIntegerField(null=True, blank=True)  # ID del partido, etc.

    def __str__(self):
        return f"Notif a {self.usuario.username}: {self.mensaje[:40]}"

class Propuesta(models.Model):
    contador = models.PositiveIntegerField(default=0)
    respondida = models.BooleanField(default=False) 
    cerrada = models.BooleanField(default=False) 

    partido = models.OneToOneField('Partido', on_delete=models.CASCADE, related_name='propuesta')

    fecha1 = models.DateField(null=True, blank=True)
    hora1 = models.TimeField(null=True, blank=True)
    fecha2 = models.DateField(null=True, blank=True)
    hora2 = models.TimeField(null=True, blank=True)
    fecha3 = models.DateField(null=True, blank=True)
    hora3 = models.TimeField(null=True, blank=True)

    cancha1 = models.ForeignKey('Cancha', on_delete=models.SET_NULL, null=True, blank=True, related_name="propuesta1")
    ubicacion1 = models.CharField(max_length=255, null=True, blank=True)
    precio1 = models.PositiveIntegerField(null=True, blank=True)

    cancha2 = models.ForeignKey('Cancha', on_delete=models.SET_NULL, null=True, blank=True, related_name="propuesta2")
    ubicacion2 = models.CharField(max_length=255, null=True, blank=True)
    precio2 = models.PositiveIntegerField(null=True, blank=True)

    cancha3 = models.ForeignKey('Cancha', on_delete=models.SET_NULL, null=True, blank=True, related_name="propuesta3")
    ubicacion3 = models.CharField(max_length=255, null=True, blank=True)
    precio3 = models.PositiveIntegerField(null=True, blank=True)
    
    opcion_dia_hora = models.PositiveSmallIntegerField(null=True, blank=True)
    opcion_cancha = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Propuesta para partido {self.partido.id}"

class MagicLoginToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="magic_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_valid(self) -> bool:
        # válido 48 horas y no usado
        return (not self.used) and (timezone.now() - self.created_at < timedelta(hours=48))