# serializers.py
from rest_framework import serializers
from django.db.models import Sum
from app_torneo_f5.models import EstadisticasJugadorPartido, EstadisticasEquipoPartido, Partido, ParticipacionEquipoTorneo, Cancha, TipoCancha, Torneo, Jugador, MiembroEquipo

class TipoCanchaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCancha
        fields = ['id', 'nombre']

class TorneoDePartidoSerializer(serializers.ModelSerializer):
    tipo_cancha = TipoCanchaSerializer(read_only=True)
    cantidad_equipos = serializers.SerializerMethodField()
    imagen = serializers.ImageField(source='foto', read_only=True)

    class Meta:
        model = Torneo
        fields = [
            'id',
            'nombre',
            'imagen',   # 👈 ahora sí coincide con el JS
            'tipo_cancha',
            'duracion_partido',
            'cantidad_equipos',
            'modo_seleccion_partido'
        ]
        
    def get_cantidad_equipos(self, obj):
        # Contar cuántas participaciones tiene el torneo
        return obj.participacionequipotorneo_set.count()

class JugadorEnMiembroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jugador
        fields = ['id', 'nombre', 'foto']

class MiembroEquipoSerializer(serializers.ModelSerializer):
    jugador = JugadorEnMiembroSerializer(read_only=True)

    class Meta:
        model = MiembroEquipo
        fields = ['id', 'dorsal', 'estado', 'jugador']

class EquipoEnPartidoSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='equipo.nombre')
    nombre_corto = serializers.CharField(source='equipo.nombre_corto')
    escudo = serializers.ImageField(source='equipo.escudo', read_only=True)
    jugadores = MiembroEquipoSerializer(source='equipo.miembroequipo_set', many=True, read_only=True)
    capitan_id = serializers.SerializerMethodField()

    class Meta:
        model = ParticipacionEquipoTorneo
        fields = ['id', 'nombre', 'nombre_corto', 'escudo', 'jugadores', 'capitan_id']

    def get_capitan_id(self, obj):
        equipo = getattr(obj, 'equipo', None)
        if equipo and equipo.capitan and equipo.capitan.jugador:
            return equipo.capitan.jugador.id
        return None

class MostrarPartidoPorIDSerializer(serializers.ModelSerializer):
    equipo_local = EquipoEnPartidoSerializer(read_only=True)
    equipo_visitante = EquipoEnPartidoSerializer(read_only=True)
    torneo = TorneoDePartidoSerializer(read_only=True)
    tipo_cancha = serializers.StringRelatedField()
    cancha = serializers.StringRelatedField()
    dia_formateado = serializers.SerializerMethodField()

    # helpers
    es_copa = serializers.SerializerMethodField()
    ronda_label = serializers.SerializerMethodField()
    equipos_definidos = serializers.SerializerMethodField()
    copa_label = serializers.SerializerMethodField()

    # ubicacion calculada
    ubicacion = serializers.SerializerMethodField()

    class Meta:
        model = Partido
        fields = [
            'id',
            'dia', 'hora_inicio', 'duracion',
            'ubicacion',
            'cancha', 'tipo_cancha',
            'torneo', 'fecha',
            'etapa', 'ronda',
            'estado',                         # 👈👈 AGREGADO
            'es_copa', 'ronda_label',
            'equipos_definidos', 'copa_label',
            'equipo_local', 'equipo_visitante',
            'dia_formateado',
            'goles_local', 'goles_visitante',
        ]

    def get_ubicacion(self, obj):
        if getattr(obj, 'ubicacion', None):
            return obj.ubicacion

        cancha = getattr(obj, 'cancha', None)
        if cancha:
            return getattr(cancha, 'ubicacion', None) or \
                   getattr(cancha, 'localidad', None) or \
                   getattr(cancha, 'direccion', None)
        return None

    def get_dia_formateado(self, obj):
        return obj.dia.strftime("%d/%b") if obj.dia else None

    def get_es_copa(self, obj):
        return obj.etapa in (Partido.COPAORO, Partido.COPAPLATA)

    def get_copa_label(self, obj):
        if obj.etapa == Partido.COPAORO:
            return "Copa Oro"
        if obj.etapa == Partido.COPAPLATA:
            return "Copa Plata"
        return None

    def get_ronda_label(self, obj):
        mapa = {
            Partido.CUARTOS: 'Cuartos de final',
            Partido.SEMIFINAL: 'Semifinal',
            Partido.FINAL: 'Final',
        }
        if obj.ronda in mapa:
            return mapa[obj.ronda]
        return 'Eliminatoria' if self.get_es_copa(obj) else 'Ronda'

    def get_equipos_definidos(self, obj):
        return bool(obj.equipo_local_id and obj.equipo_visitante_id)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.equipo_local:
            data["equipo_local"] = None
        if not instance.equipo_visitante:
            data["equipo_visitante"] = None
        return data

    def _goles_por_equipo(self, obj, lado: str) -> int | None:
        try:
            eq_part = getattr(obj, f"equipo_{lado}", None)
            if not eq_part:
                return None
            est_eq = EstadisticasEquipoPartido.objects.filter(
                partido=obj, equipo=eq_part
            ).first()
            if est_eq and hasattr(est_eq, "goles"):
                return est_eq.goles or 0
        except Exception:
            pass

        try:
            suma = (EstadisticasJugadorPartido.objects
                    .filter(partido=obj, equipo=getattr(obj, f"equipo_{lado}", None))
                    .aggregate(total=Sum('goles'))['total'])
            return int(suma or 0)
        except Exception:
            return None

    def get_goles_local(self, obj):
        return self._goles_por_equipo(obj, 'local')

    def get_goles_visitante(self, obj):
        return self._goles_por_equipo(obj, 'visitante')



class PartidoConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partido
        fields = ['id', 'cancha', 'ubicacion', 'dia', 'hora_inicio', 'duracion']

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance