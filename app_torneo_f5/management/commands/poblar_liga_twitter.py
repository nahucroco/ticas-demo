from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.text import slugify

from app_torneo_f5.models import *
import random
from datetime import date

User = get_user_model()

EQUIPOS = [
    "Tigre", "River", "Quilmes", "Newells", "Lanus", "Independiente", "Huracán",
    "Godoy Cruz", "Defensa y Justicia", "Chicago", "Boca", "Banfield", "Atlanta",
    "Arsenal", "All Boys", "Argentinos Juniors", "Dock Sud", "Claypole",
    "Rosario Central", "Gimnasia"
]

CLASICOS = [
    ("Boca", "River"),
    ("Newells", "Rosario Central"),
    ("Lanus", "Banfield"),
    ("Atlanta", "All Boys"),
    ("Chicago", "Argentinos Juniors"),
    ("Defensa y Justicia", "Arsenal"),
    ("Godoy Cruz", "Quilmes"),
    ("Tigre", "Gimnasia"),
    ("Huracán", "Independiente"),
    ("Dock Sud", "Claypole"),
]

SEDES_BSAS = [
    "Estadio José Amalfitani - CABA",
    "Estadio Libertadores de América - Avellaneda",
    "Estadio Tomás Ducó - Parque Patricios",
    "Estadio Ciudad de La Plata",
    "Estadio Florencio Sola - Banfield",
    "Estadio José Dellagiovanna - Victoria",
]


class Command(BaseCommand):
    help = "Puebla Liga Argentina de Twitter"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        root = User.objects.get(username="root")

        tipo_cancha, _ = TipoCancha.objects.get_or_create(
            codigo="F8",
            defaults={"nombre": "Futbol 8"}
        )

        torneo = Torneo.objects.create(
            nombre="Liga Argentina de Twitter",
            dia_inicio=date(2026, 3, 2),
            creador=root,
            cantidad_equipos=20,
            tipo_cancha=tipo_cancha
        )

        torneo.encargados_carga.add(root)

        equipos_objs = []

        # =========================
        # CREAR EQUIPOS Y JUGADORES
        # =========================
        for nombre in EQUIPOS:
            equipo = Equipo.objects.create(
                nombre=nombre,
                nombre_corto=slugify(nombre)[:3].upper() if slugify(nombre) else nombre[:3].upper(),
                provincia="Buenos Aires",
                ciudad="Buenos Aires",
                fecha_creacion=date(2026, 1, 1)
            )

            equipos_objs.append(equipo)
            capitan_miembro = None

            # Relación de equipo con torneo activo
            equipo.torneos_en_activo.add(torneo)

            # Crear 16 jugadores
            for j in range(16):
                base_username = slugify(nombre).replace("-", "")
                username = f"{base_username}_{j}"

                user = User.objects.create(
                    username=username,
                    password=make_password("1234"),
                    email_verified=True
                )

                jugador = Jugador.objects.create(
                    user=user,
                    nombre=f"{nombre} Jugador {j + 1}"
                )

                miembro = MiembroEquipo.objects.create(
                    jugador=jugador,
                    equipo=equipo,
                    dorsal=j + 1,
                    fecha_alta=date(2026, 1, 1),
                    estado=MiembroEquipo.HABILITADO
                )

                IntegranteEquipo.objects.create(
                    usuario=user,
                    equipo=equipo,
                    aceptado=True
                )

                # ESTA ERA LA PARTE QUE TE FALTABA
                equipo.integrantes.add(user)

                Inscripcion.objects.create(
                    jugador=jugador,
                    equipo=equipo,
                    torneo=torneo
                )

                if j == 0:
                    capitan_miembro = miembro

            equipo.capitan = capitan_miembro
            equipo.total_integrantes = equipo.integrantes.count()
            equipo.save()

        # =========================
        # PARTICIPACION TORNEO
        # =========================
        zona_a = equipos_objs[:10]
        zona_b = equipos_objs[10:]

        pet_map = {}

        for equipo in zona_a:
            pet = ParticipacionEquipoTorneo.objects.create(
                torneo=torneo,
                equipo=equipo,
                zona="A",
                grupo=1,
                estado=ParticipacionEquipoTorneo.HABILITADO
            )
            pet_map[equipo.nombre] = pet

        for equipo in zona_b:
            pet = ParticipacionEquipoTorneo.objects.create(
                torneo=torneo,
                equipo=equipo,
                zona="B",
                grupo=2,
                estado=ParticipacionEquipoTorneo.HABILITADO
            )
            pet_map[equipo.nombre] = pet

        # =========================
        # FIXTURE ZONAS (round robin simple)
        # =========================
        def generar_fixture(equipos):
            equipos = equipos.copy()
            random.shuffle(equipos)
            n = len(equipos)
            fechas = n - 1

            for fecha in range(1, fechas + 1):
                for i in range(n // 2):
                    local = equipos[i]
                    visitante = equipos[n - 1 - i]

                    Partido.objects.create(
                        torneo=torneo,
                        etapa=Partido.ZONAS,
                        fecha=fecha,
                        equipo_local=pet_map[local.nombre],
                        equipo_visitante=pet_map[visitante.nombre],
                        cancha_text=random.choice(SEDES_BSAS),
                        tipo_cancha=tipo_cancha,
                        ubicacion="Buenos Aires",
                        estado=Partido.PROGRAMADO
                    )

                equipos.insert(1, equipos.pop())

        generar_fixture(zona_a)
        generar_fixture(zona_b)

        # =========================
        # FECHA INTERZONAL CLASICOS
        # =========================
        fecha_interzonal = 10

        for local, visitante in CLASICOS:
            Partido.objects.create(
                torneo=torneo,
                etapa=Partido.ZONAS,
                fecha=fecha_interzonal,
                equipo_local=pet_map[local],
                equipo_visitante=pet_map[visitante],
                cancha_text=random.choice(SEDES_BSAS),
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )

        # =========================
        # PLAYOFFS
        # =========================
        def crear_llave(etapa):
            # CUARTOS
            c1 = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.CUARTOS,
                fecha=11,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )
            c2 = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.CUARTOS,
                fecha=11,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )
            c3 = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.CUARTOS,
                fecha=11,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )
            c4 = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.CUARTOS,
                fecha=11,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )

            # SEMIS
            s1 = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.SEMIFINAL,
                fecha=12,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )
            s2 = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.SEMIFINAL,
                fecha=12,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )

            # FINAL
            f = Partido.objects.create(
                torneo=torneo,
                etapa=etapa,
                ronda=Partido.FINAL,
                fecha=13,
                tipo_cancha=tipo_cancha,
                ubicacion="Buenos Aires",
                estado=Partido.PROGRAMADO
            )

            # Conectar llave
            c1.siguiente_partido = s1
            c1.siguiente_slot = "L"
            c1.save()

            c2.siguiente_partido = s1
            c2.siguiente_slot = "V"
            c2.save()

            c3.siguiente_partido = s2
            c3.siguiente_slot = "L"
            c3.save()

            c4.siguiente_partido = s2
            c4.siguiente_slot = "V"
            c4.save()

            s1.siguiente_partido = f
            s1.siguiente_slot = "L"
            s1.save()

            s2.siguiente_partido = f
            s2.siguiente_slot = "V"
            s2.save()

        crear_llave(Partido.COPAORO)
        crear_llave(Partido.COPAPLATA)

        self.stdout.write(self.style.SUCCESS("Liga Argentina de Twitter creada correctamente"))