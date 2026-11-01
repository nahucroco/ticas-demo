from django.db import models
from django.core.exceptions import ValidationError
from types import SimpleNamespace

class DatosAdicionalesTorneo(models.Model):
    torneo = models.OneToOneField('Torneo', on_delete=models.CASCADE, related_name='datos_adicionales', null=True, blank=True)
    usa_tarjetas_amarillas = models.BooleanField(default=False)
    usa_tarjetas_rojas = models.BooleanField(default=False)
    usa_pases = models.BooleanField(default=False)
    usa_faltas_cometidas = models.BooleanField(default=False)
    usa_faltas_recibidas = models.BooleanField(default=False)
    usa_posesion = models.BooleanField(default=False)
    usa_atajadas = models.BooleanField(default=False)
    usa_tiros_arco = models.BooleanField(default=False)

class Torneo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    descripcion_corta = models.TextField(blank=True)
    dia_creacion = models.DateField(auto_now_add=True, null=True, blank=True)
    dia_inicio = models.DateField(null=True, blank=True)
    dia_fin = models.DateField(null=True, blank=True)

    encargados_carga = models.ManyToManyField('app_torneo_f5.CustomUser', related_name='torneos_carga')
    creador = models.ForeignKey('app_torneo_f5.CustomUser', on_delete=models.CASCADE, related_name='torneos_creados')

    cantidad_equipos = models.PositiveIntegerField(default=0)

    tipo_cancha = models.ForeignKey('app_torneo_f5.TipoCancha', on_delete=models.SET_NULL, null=True)
    duracion_partido = models.PositiveIntegerField(default=60, help_text="Duración en minutos")

    foto = models.ImageField(upload_to='torneos/', null=True, blank=True)

    # Registro de estadísticas
    POR_EQUIPO = 'POR_EQUIPO'
    POR_PARTIDO = 'POR_PARTIDO'
    modo_registro_estadisticas = models.CharField(max_length=20, choices=[
        (POR_EQUIPO, 'Por Equipo'),
        (POR_PARTIDO, 'Por Partido')
    ],
    default=POR_PARTIDO
    )

    # Selección de partido
    POR_DEFECTO = 'POR_DEFECTO'
    PROPUESTA = 'PROPUESTA'
    modo_seleccion_partido = models.CharField(max_length=20, choices=[
        (POR_DEFECTO, 'Por Defecto'),
        (PROPUESTA, 'Propuesta')
    ],
    default=POR_DEFECTO
    )

    # Creación de partidos
    MANUAL = 'MANUAL'
    AUTOMATICA = 'AUTOMATICA'
    modo_creacion_partidos = models.CharField(max_length=20, choices=[
        (MANUAL, 'Manual'),
        (AUTOMATICA, 'Automática')
    ],
    default=MANUAL
    )

    # Estado del torneo
    ACTIVO = 'ACTIVO'
    TERMINADO = 'TERMINADO'
    PENDIENTE = 'PENDIENTE'
    estado = models.CharField(max_length=20, choices=[
            (ACTIVO, 'Activo'),
            (TERMINADO, 'Terminado'),
            (PENDIENTE, 'Pendiente')
        ],
        default='ACTIVO'
    )
    
    # Plantillas de torneo
    LIGATW = 'LIGATW'
    plantilla = models.CharField(max_length=20, choices=[
            (LIGATW, 'LIGATW')
        ],
        default='LIGATW'
    )
    PUBLICO = 'PUBLICO'
    PRIVADO = 'PRIVADO'
    visibilidad = models.CharField(
        max_length=10,
        choices=[
            (PUBLICO, 'Público'),
            (PRIVADO, 'Privado'),
        ],
        default=PRIVADO
    )
    def __str__(self):
        return self.nombre
 
class MiembroEquipo(models.Model):
    jugador = models.ForeignKey('app_torneo_f5.Jugador', on_delete=models.CASCADE)
    equipo = models.ForeignKey('app_torneo_f5.Equipo', on_delete=models.CASCADE)
    dorsal = models.IntegerField()
    fecha_alta = models.DateField()
    fecha_baja = models.DateField(null=True, blank=True)

    HABILITADO = 'HABILITADO'
    BAJA = 'BAJA'
    estado = models.CharField(max_length=20, choices=[
        (HABILITADO, 'Habilitado'),
        (BAJA, 'Baja')
    ])
    def __str__(self):
        return f"{self.jugador} ({self.equipo})"

class ParticipacionEquipoTorneo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    equipo = models.ForeignKey('app_torneo_f5.Equipo', on_delete=models.CASCADE)
    puntos = models.IntegerField(default=0)
    grupo = models.PositiveSmallIntegerField(default=1, db_index=True)
    encargado_carga = models.ForeignKey('app_torneo_f5.CustomUser', on_delete=models.SET_NULL, null=True)
    pj = models.IntegerField(default=0)
    pg = models.IntegerField(default=0)
    pe = models.IntegerField(default=0)
    pp = models.IntegerField(default=0)
    gf = models.IntegerField(default=0)
    gc = models.IntegerField(default=0)
    dif = models.IntegerField(default=0)
    sigue_en_competencia = models.BooleanField(default=True)
    posicion = models.IntegerField(null=True, blank=True)
    jugadores_suspendidos = models.ManyToManyField(MiembroEquipo, blank=True)

    INCOMPLETO = 'INCOMPLETO'
    HABILITADO = 'HABILITADO'
    estado = models.CharField(max_length=20, choices=[
        (INCOMPLETO, 'Incompleto'),
        (HABILITADO, 'Habilitado')
    ])
    
    #Zonas
    A = 'A'
    B = 'B'
    zona = models.CharField(
        max_length=1,
        choices=[(A, 'A'), (B, 'B')],
        default=A,          # ⬅️ default temporal para poder migrar
        db_index=True,
    )
    
    #Etiquetas identificadoras de 
    C1 = 'C1'
    C2 = 'C2'
    C3 = 'C3'
    C4 = 'C4'
    C5 = 'C5'
    C6 = 'C6'
    C7 = 'C7'
    C8 = 'C8'
    S1 = 'S1'
    S2 = 'S2'
    S3 = 'S3'
    S4 = 'S4'
    F1 = 'F1'
    F2 = 'F2'
    etiqueta = models.CharField(max_length=20, null=True, blank=True, choices=[
        (C1, 'C1'),
        (C2, 'C2'),
        (C3, 'C3'),
        (C4, 'C4'),
        (C5, 'C5'),
        (C6, 'C6'),
        (C7, 'C7'),
        (C8, 'C8'),
        (S1, 'S1'),
        (S2, 'S2'),
        (S3, 'S3'),
        (S4, 'S4'),
        (F1, 'F1'),
        (F2, 'F2'),
    ])
    def __str__(self):
        return f"{self.equipo} - {self.torneo}"

    @staticmethod
    def grupos_choices_para_torneo(torneo):
        """Devuelve [(1,'Grupo 1'), (2,'Grupo 2'), ...] según cantidad_grupos del torneo."""
        n = int(getattr(torneo, 'cantidad_grupos', 1) or 1)
        return [(i, f"Grupo {i}") for i in range(1, n+1)]
    
    @classmethod
    def recalcular_torneo(cls, torneo):
        from app_torneo_f5.models import Partido

        # Resetear todo
        cls.objects.filter(torneo=torneo).update(
            puntos=0, pj=0, pg=0, pe=0, pp=0,
            gf=0, gc=0, dif=0
        )

        partidos = Partido.objects.filter(
            torneo=torneo,
            jugado=True
        )

        for partido in partidos:
            local = partido.equipo_local
            visitante = partido.equipo_visitante

            gl = partido.goles_local or 0
            gv = partido.goles_visitante or 0

            # PJ
            local.pj += 1
            visitante.pj += 1

            # GF / GC
            local.gf += gl
            local.gc += gv

            visitante.gf += gv
            visitante.gc += gl

            # Resultado
            if gl > gv:
                local.pg += 1
                visitante.pp += 1
                local.puntos += 3
            elif gv > gl:
                visitante.pg += 1
                local.pp += 1
                visitante.puntos += 3
            else:
                local.pe += 1
                visitante.pe += 1
                local.puntos += 1
                visitante.puntos += 1

            local.dif = local.gf - local.gc
            visitante.dif = visitante.gf - visitante.gc

            local.save()
            visitante.save()
    

# =========================
# PARTIDO – añade FK a FaseTorneo
# =========================

class Partido(models.Model):
    torneo = models.ForeignKey(
        'app_torneo_f5.Torneo',
        on_delete=models.CASCADE,
        related_name="partidos"
    )

    # ================= ETAPA =================
    ZONAS = 'ZONAS'
    COPAORO = 'COPAORO'
    COPAPLATA = 'COPAPLATA'

    etapa = models.CharField(
        max_length=9,
        choices=[
            (ZONAS, 'ZONAS'),
            (COPAORO, 'COPAORO'),
            (COPAPLATA, 'COPAPLATA')
        ],
        default=ZONAS,
        db_index=True,
    )

    # ================= RONDA =================
    NONE = 'NONE'
    CUARTOS = 'CUARTOS'
    SEMIFINAL = 'SEMIFINAL'
    FINAL = 'FINAL'

    ronda = models.CharField(
        max_length=10,
        choices=[
            (NONE,'NONE'),
            (CUARTOS,'CUARTOS'),
            (SEMIFINAL,'SEMIFINAL'),
            (FINAL,'FINAL')
        ],
        default=NONE,
        db_index=True,
    )

    # ================= EQUIPOS =================
    equipo_local = models.ForeignKey(
        'app_torneo_f5.ParticipacionEquipoTorneo',
        on_delete=models.CASCADE,
        related_name='partidos_locales',
        null=True, blank=True
    )

    equipo_visitante = models.ForeignKey(
        'app_torneo_f5.ParticipacionEquipoTorneo',
        on_delete=models.CASCADE,
        related_name='partidos_visitantes',
        null=True, blank=True
    )

    equipo_ganador = models.ForeignKey(
        'app_torneo_f5.ParticipacionEquipoTorneo',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='partidos_ganados'
    )

    goles_local = models.PositiveIntegerField(default=0)
    goles_visitante = models.PositiveIntegerField(default=0)

    # ================= FECHA =================
    fecha = models.PositiveIntegerField()
    dia = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    inicio_datetime = models.DateTimeField(null=True, blank=True)

    # ================= CANCHA =================
    cancha = models.ForeignKey(
        'app_torneo_f5.Cancha',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    tipo_cancha = models.ForeignKey(
        'app_torneo_f5.TipoCancha',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    cancha_text = models.CharField(max_length=120, blank=True, null=True)
    tipo_cancha_text = models.CharField(max_length=120, blank=True, null=True)
    ubicacion = models.CharField(max_length=200, blank=True, null=True)

    duracion = models.PositiveIntegerField(default=90)
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    # ================= ESTADO =================
    jugado = models.BooleanField(default=False)
    jugando = models.BooleanField(default=False)
    cancelado = models.BooleanField(default=False)
    VACIO = 'VACIO'
    INDEFINIDO = 'INDEFINIDO'
    PROGRAMADO = 'PROGRAMADO'
    EN_CURSO = 'EN_CURSO'
    CANCELADO = 'CANCELADO'
    SUSPENDIDO = 'SUSPENDIDO'
    FINALIZADO = 'FINALIZADO'
    EN_PENALES = 'EN_PENALES'
    TIEMPO_EXTRA = 'TIEMPO_EXTRA'
    ESTADO_CHOICES = [
        (VACIO, 'Vacío'),
        (INDEFINIDO, 'Indefinido'),
        (PROGRAMADO, 'Programado'),
        (EN_CURSO, 'En curso'),
        (CANCELADO, 'Cancelado'),
        (SUSPENDIDO, 'Suspendido'),
        (FINALIZADO, 'Finalizado'),
        (EN_PENALES, 'En penales'),
        (TIEMPO_EXTRA, 'Tiempo extra'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=VACIO)
    # en Partido(models.Model)

    # Partido(models.Model)

    siguiente_partido = models.ForeignKey(
        "self",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="partidos_previos"
    )

    SLOT_LOCAL = "L"
    SLOT_VISITA = "V"
    siguiente_slot = models.CharField(
        max_length=1,
        choices=[(SLOT_LOCAL, "LOCAL"), (SLOT_VISITA, "VISITANTE")],
        null=True, blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['torneo', 'fecha']),
        ]

    def __str__(self):
        local = self.equipo_local.equipo if self.equipo_local_id else "TBD"
        visita = self.equipo_visitante.equipo if self.equipo_visitante_id else "TBD"
        return f"{local} vs {visita} (Fecha {self.fecha})"

    def actualizar_resultado(self):
        from django.db.models import Sum
        from app_torneo_f5.models import EstadisticasJugadorPartido

        goles_local = EstadisticasJugadorPartido.objects.filter(
            partido=self,
            miembro_equipo__equipo=self.equipo_local.equipo,
            jugo=True
        ).aggregate(total=Sum("goles"))["total"] or 0

        goles_visitante = EstadisticasJugadorPartido.objects.filter(
            partido=self,
            miembro_equipo__equipo=self.equipo_visitante.equipo,
            jugo=True
        ).aggregate(total=Sum("goles"))["total"] or 0

        self.goles_local = goles_local
        self.goles_visitante = goles_visitante

        if goles_local > goles_visitante:
            self.equipo_ganador = self.equipo_local
        elif goles_visitante > goles_local:
            self.equipo_ganador = self.equipo_visitante
        else:
            self.equipo_ganador = None

        self.jugado = True
        self.estado = self.FINALIZADO

        self.save()
        

""" class Propuesta(models.Model):
    partido = models.OneToOneField(Partido, on_delete=models.CASCADE)
    contador = models.IntegerField(default=0)
    respondida = models.BooleanField(default=False)
    cerrada = models.BooleanField(default=False)
    fecha1 = models.DateField()
    hora1 = models.TimeField()
    fecha2 = models.DateField()
    hora2 = models.TimeField()
    fecha3 = models.DateField()
    hora3 = models.TimeField()
    cancha1 = models.ForeignKey('app_torneo_f5.Cancha', on_delete=models.SET_NULL, null=True, related_name='propuestas_cancha1')
    ubicacion1 = models.CharField(max_length=255)
    precio1 = models.FloatField()
    cancha2 = models.ForeignKey('app_torneo_f5.Cancha', on_delete=models.SET_NULL, null=True, related_name='propuestas_cancha2')
    ubicacion2 = models.CharField(max_length=255)
    precio2 = models.FloatField() """

class ParticipacionJugadorTorneo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE, related_name='participaciones_jugadores')
    jugador = models.ForeignKey('app_torneo_f5.Jugador', on_delete=models.CASCADE, related_name='participaciones_torneo')
    miembro_equipo = models.ForeignKey(MiembroEquipo, on_delete=models.SET_NULL, null=True, blank=True)
    equipo_torneo = models.ForeignKey(
        ParticipacionEquipoTorneo, on_delete=models.SET_NULL, null=True, blank=True, related_name='jugadores_torneo'
    )
    grupo = models.PositiveSmallIntegerField(default=1, db_index=True)

    pj = models.PositiveIntegerField(default=0)           
    goles = models.PositiveIntegerField(default=0)
    asistencias = models.PositiveIntegerField(default=0)
    atajadas = models.PositiveIntegerField(default=0)
    tiros_arco = models.PositiveIntegerField(default=0)
    tarjetas_amarillas = models.PositiveIntegerField(default=0)
    tarjetas_rojas = models.PositiveIntegerField(default=0)
    faltas_recibidas = models.PositiveIntegerField(default=0)
    faltas_cometidas = models.PositiveIntegerField(default=0)

    prom_goles = models.FloatField(default=0.0)
    prom_asistencias = models.FloatField(default=0.0)
    prom_atajadas = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Un jugador solo debe tener una “ficha” por torneo
        unique_together = (('torneo', 'jugador'),)
        indexes = [
            models.Index(fields=['torneo', 'grupo']),
            models.Index(fields=['torneo', '-goles']),
            models.Index(fields=['torneo', '-asistencias']),
            models.Index(fields=['torneo', '-atajadas']),
        ]

    def __str__(self):
        return f"{self.jugador} en {self.torneo} (G:{self.goles} A:{self.asistencias} PJ:{self.pj})"

    def clean(self):
        super().clean()
        # validar grupo dentro del rango del torneo
        if self.torneo_id and not (1 <= int(self.grupo) <= int(self.torneo.cantidad_grupos or 1)):
            raise ValidationError({'grupo': f"El grupo debe estar entre 1 y {self.torneo.cantidad_grupos}."})
        # coherencia torneo/equipo_torneo
        if self.equipo_torneo and self.equipo_torneo.torneo_id != self.torneo_id:
            raise ValidationError({'equipo_torneo': "El equipo_torneo no pertenece a este torneo."})
        # si tenemos miembro_equipo, y también equipo_torneo, que el Equipo coincida
        if self.miembro_equipo and self.equipo_torneo:
            if self.miembro_equipo.equipo_id != self.equipo_torneo.equipo_id:
                raise ValidationError({'miembro_equipo': "El miembro_equipo no coincide con equipo_torneo."})

    # ---- Recalcular totales desde EstadisticasJugadorPartido ----
    def recompute_from_partidos(self):
        from django.db.models import Sum, Count, Q
        qs = EstadisticasJugadorPartido.objects.filter(
            miembro_equipo__jugador=self.jugador,
            partido__torneo=self.torneo,
        )

        agg = qs.aggregate(
            goles=Sum('goles') or 0,
            asistencias=Sum('asistencias') or 0,
            atajadas=Sum('atajadas') or 0,
            tiros_arco=Sum('tiros_arco') or 0,
            tarjetas_amarillas=Sum('tarjetas_amarillas') or 0,
            tarjetas_rojas=Sum('tarjeta_roja') or 0,  # bool cuenta como 0/1
            faltas=Sum('faltas') or 0,
            pj=Count('id', filter=Q(jugo=True)),
        )

        # set totales
        self.goles = int(agg.get('goles') or 0)
        self.asistencias = int(agg.get('asistencias') or 0)
        self.atajadas = int(agg.get('atajadas') or 0)
        self.tiros_arco = int(agg.get('tiros_arco') or 0)
        self.tarjetas_amarillas = int(agg.get('tarjetas_amarillas') or 0)
        self.tarjetas_rojas = int(agg.get('tarjetas_rojas') or 0)
        self.faltas = int(agg.get('faltas') or 0)
        self.pj = int(agg.get('pj') or 0)

        # promedios
        denom = self.pj if self.pj > 0 else 1
        self.prom_goles = self.goles / denom
        self.prom_asistencias = self.asistencias / denom
        self.prom_atajadas = self.atajadas / denom

        # sincronizar equipo_torneo y grupo si se puede inferir
        if not self.equipo_torneo_id:
            # intentamos inferir del último partido jugado en este torneo
            last_stat = qs.select_related('miembro_equipo__equipo').order_by('-id').first()
            if last_stat:
                pet = ParticipacionEquipoTorneo.objects.filter(
                    torneo=self.torneo,
                    equipo=last_stat.miembro_equipo.equipo
                ).first()
                if pet:
                    self.equipo_torneo = pet
                    self.grupo = pet.grupo
        else:
            # si existe equipo_torneo y cambió su grupo, lo reflejamos
            self.grupo = self.equipo_torneo.grupo or self.grupo

        return self

class EstadisticasJugadorPartido(models.Model):
    miembro_equipo = models.ForeignKey(MiembroEquipo, on_delete=models.CASCADE)
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    tarjetas_amarillas = models.IntegerField(default=0)
    tarjeta_roja = models.BooleanField(default=False)
    faltas = models.IntegerField(default=0)
    atajadas = models.IntegerField(default=0)
    goles = models.IntegerField(default=0)
    autogoles = models.IntegerField(default=0)
    asistencias = models.IntegerField(default=0)
    tiros_arco = models.IntegerField(default=0)
    jugo = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.miembro_equipo} | {self.partido}"

class EstadisticasEquipoPartido(models.Model):
    equipo = models.ForeignKey(ParticipacionEquipoTorneo, on_delete=models.CASCADE)
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    pases = models.IntegerField(default=0)
    posesion = models.FloatField(default=0.0)

class InvitacionEquipoTorneo(models.Model):
    torneo = models.ForeignKey(Torneo, on_delete=models.CASCADE)
    equipo = models.ForeignKey('app_torneo_f5.Equipo', on_delete=models.CASCADE)
    fecha_envio = models.DateField()
    fecha_respuesta = models.DateField(null=True, blank=True)

    PENDIENTE = 'PENDIENTE'
    ACEPTADA = 'ACEPTADA'
    RECHAZADA = 'RECHAZADA'
    EXPIRADA = 'EXPIRADA'
    estado = models.CharField(max_length=20, choices=[
        (PENDIENTE, 'Pendiente'),
        (ACEPTADA, 'Aceptada'),
        (RECHAZADA, 'Rechazada'),
        (EXPIRADA, 'Expirada')
    ])
    def __str__(self):
        return f"Invitación {self.equipo} → {self.torneo} ({self.estado})"
