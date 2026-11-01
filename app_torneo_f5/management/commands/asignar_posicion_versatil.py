from django.core.management.base import BaseCommand
from django.db.models import Q
from app_torneo_f5.models import Jugador


class Command(BaseCommand):
    help = "Asigna la posición 'Versátil' a los jugadores que no tienen posición favorita"

    def handle(self, *args, **kwargs):
        jugadores = Jugador.objects.filter(
            Q(posicion_preferida__isnull=True) | Q(posicion_preferida="")
        )

        cantidad = jugadores.count()

        jugadores.update(posicion_preferida="Versátil")

        self.stdout.write(
            self.style.SUCCESS(f"{cantidad} jugadores actualizados con posición 'Versátil'")
        )