from rest_framework import serializers
from app_torneo_f5.models import EstadisticasJugadorPartido, EstadisticasEquipoPartido

class EstadisticaJugadorSerializer(serializers.Serializer):
    jugador_id = serializers.IntegerField()
    goles = serializers.IntegerField(default=0)
    asistencias = serializers.IntegerField(default=0)
    atajadas = serializers.IntegerField(default=0)
    faltas_cometidas = serializers.IntegerField(default=0)
    faltas_recibidas = serializers.IntegerField(default=0)
    tarjeta_amarilla = serializers.BooleanField(default=False)
    tarjeta_roja = serializers.BooleanField(default=False)
    jugo = serializers.BooleanField(default=False)

class CargaEstadisticasPartidoSerializer(serializers.Serializer):
    partido_id = serializers.IntegerField()
    posesion_local = serializers.IntegerField()
    posesion_visitante = serializers.IntegerField()
    goles_local = serializers.IntegerField()
    goles_visitante = serializers.IntegerField()
    jugadores_stats = EstadisticaJugadorSerializer(many=True)
    
class MostrarPartidoPorIDSerializer(serializers.Serializer):
    partido_id = serializers.IntegerField()
    posesion_local = serializers.IntegerField()
    posesion_visitante = serializers.IntegerField()
    goles_local = serializers.IntegerField()
    goles_visitante = serializers.IntegerField()
    jugadores_stats = EstadisticaJugadorSerializer(many=True)