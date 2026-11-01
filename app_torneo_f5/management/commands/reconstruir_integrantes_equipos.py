from django.core.management.base import BaseCommand
from app_torneo_f5.models import Equipo, MiembroEquipo


class Command(BaseCommand):
    help = "Reconstruye el campo integrantes de Equipo a partir de MiembroEquipo"

    def handle(self, *args, **kwargs):

        equipos = Equipo.objects.all()

        total_agregados = 0

        for equipo in equipos:

            # limpiar integrantes actuales
            equipo.integrantes.clear()

            miembros = MiembroEquipo.objects.filter(
                equipo=equipo,
                estado="HABILITADO"
            ).select_related("jugador__user")

            count = 0

            for miembro in miembros:
                if miembro.jugador and miembro.jugador.user:
                    equipo.integrantes.add(miembro.jugador.user)
                    count += 1

            equipo.total_integrantes = count
            equipo.save(update_fields=["total_integrantes"])

            total_agregados += count

            self.stdout.write(
                self.style.SUCCESS(
                    f"{equipo.nombre}: {count} integrantes"
                )
            )

        self.stdout.write("")
        self.stdout.write("------ RESUMEN ------")
        self.stdout.write(f"Total integrantes agregados: {total_agregados}")