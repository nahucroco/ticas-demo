"""
Carga los datos de ejemplo de la demo: un usuario invitado, ocho equipos con jugadores
inventados, un torneo a mitad de camino y algunos partidos amistosos.

Es idempotente: si el usuario de la demo ya existe, no hace nada (usar --reset para empezar
de cero). Todos los nombres son ficticios.
"""

import random
from datetime import date, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app_torneo_f5.models import (
    Cancha,
    EstadisticaAmistosa,
    EstadisticasJugadorPartido,
    Equipo,
    Inscripcion,
    IntegranteEquipo,
    Jugador,
    MiembroEquipo,
    Participacion,
    Partido,
    ParticipacionEquipoTorneo,
    PartidoAmistoso,
    TipoCancha,
    Torneo,
)

User = get_user_model()

EQUIPOS = [
    ("Los Halcones", "HAL"),
    ("Deportivo Norte", "DNO"),
    ("Atlético Ribera", "ARI"),
    ("La Banda del Pasaje", "BDP"),
    ("Sportivo Parque", "SPA"),
    ("Real Cortada", "RCO"),
    ("Juventud Unida", "JUV"),
    ("Club Los Tilos", "TIL"),
]

NOMBRES = [
    "Tomás", "Lucas", "Mateo", "Bruno", "Joaquín", "Franco", "Santiago", "Thiago", "Ramiro", "Ignacio",
    "Facundo", "Agustín", "Lautaro", "Valentín", "Gonzalo", "Ezequiel", "Nicolás", "Martín", "Julián", "Matías",
    "Federico", "Emiliano", "Leandro", "Maximiliano", "Benjamín", "Gastón", "Hernán", "Kevin", "Marcos", "Pablo",
]
APELLIDOS = [
    "Ferreyra", "Godoy", "Ledesma", "Quiroga", "Benítez", "Ojeda", "Acosta", "Villalba", "Medina", "Sosa",
    "Ríos", "Paz", "Vera", "Molina", "Castro", "Ponce", "Rojas", "Herrera", "Aguirre", "Luna",
]
POSICIONES = ["Arquero", "Defensa", "Defensa", "Mediocampista", "Mediocampista", "Delantero", "Delantero", "Versátil"]
CANCHAS = [
    ("Complejo El Potrero", "Av. Siempreviva 742"),
    ("La Canchita del Sur", "Calle Falsa 123"),
    ("Fútbol 5 Los Álamos", "Bv. de los Álamos 1500"),
]


class Command(BaseCommand):
    help = "Carga los datos ficticios de la demo de Ticas"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Borra la base y vuelve a cargar todo")

    def handle(self, *args, reset=False, **kwargs):
        if reset:
            call_command("flush", interactive=False, verbosity=0)
        elif User.objects.filter(username=settings.DEMO_USERNAME).exists():
            self.stdout.write("La demo ya tiene datos; no se carga nada.")
            return
        random.seed(5)
        with transaction.atomic():
            self.cargar()
        self.stdout.write(self.style.SUCCESS("Datos de la demo cargados."))

    # ------------------------------------------------------------------ helpers

    def nombre_unico(self, usados):
        while True:
            nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
            if nombre not in usados:
                usados.add(nombre)
                return nombre

    def crear_jugador(self, username, nombre, posicion):
        user = User.objects.create_user(username=username, password=None, email_verified=True, full_name=nombre)
        user.first_name, _, user.last_name = nombre.partition(" ")
        user.save()
        perfil = user.perfilusuario
        perfil.es_primer_ingreso = False
        perfil.save()
        nacimiento = date(random.randint(1992, 2005), random.randint(1, 12), random.randint(1, 28))
        return Jugador.objects.create(
            user=user,
            nombre=nombre,
            posicion_preferida=posicion,
            pie_preferido=random.choice(["Der", "Der", "Izq", "Amb"]),
            genero="masculino",
            altura=random.randint(165, 192),
            fecha_nacimiento=nacimiento,
            edad=(date.today() - nacimiento).days // 365,
            provincia="Santa Fe",
            ciudad="Rosario",
            paso_perfil=4,
        )

    # ------------------------------------------------------------------ carga

    def cargar(self):
        hoy = timezone.localdate()
        f5, _ = TipoCancha.objects.get_or_create(codigo="F5", defaults={"nombre": "Fútbol 5"})
        TipoCancha.objects.get_or_create(codigo="F7", defaults={"nombre": "Fútbol 7"})
        canchas = []
        for nombre, direccion in CANCHAS:
            cancha = Cancha.objects.create(nombre=nombre, direccion=direccion, ubicacion="Rosario, Santa Fe")
            cancha.tipo_cancha.add(f5)
            canchas.append(cancha)

        # Usuario invitado: es el que usa el botón "Entrar como invitado".
        demo = self.crear_jugador(settings.DEMO_USERNAME, "Invitado Demo", "Mediocampista")
        demo.fortalezas = "Visión de juego, pase largo"
        demo.horario_disponible = "Martes y jueves a la noche"
        demo.save()

        usados = {"Invitado Demo"}
        alta = hoy - timedelta(days=120)
        torneo = Torneo.objects.create(
            nombre="Copa Primavera Ticas",
            descripcion="Torneo de fútbol 5 con datos ficticios para probar la demo.",
            descripcion_corta="Fútbol 5 · 8 equipos · todos contra todos",
            dia_inicio=hoy - timedelta(weeks=4),
            creador=demo.user,
            cantidad_equipos=len(EQUIPOS),
            tipo_cancha=f5,
            duracion_partido=50,
            estado=Torneo.ACTIVO,
            visibilidad=Torneo.PUBLICO,
        )
        torneo.encargados_carga.add(demo.user)

        participaciones = []
        miembros_por_equipo = {}
        for i, (nombre, corto) in enumerate(EQUIPOS):
            equipo = Equipo.objects.create(
                nombre=nombre, nombre_corto=corto, provincia="Santa Fe", ciudad="Rosario", fecha_creacion=alta
            )
            equipo.torneos_en_activo.add(torneo)
            miembros = []
            for j in range(7):
                if i == 0 and j == 0:
                    jugador = demo
                else:
                    jugador = self.crear_jugador(
                        f"{corto.lower()}{j + 1}", self.nombre_unico(usados), POSICIONES[j % len(POSICIONES)]
                    )
                miembro = MiembroEquipo.objects.create(
                    jugador=jugador, equipo=equipo, dorsal=j + 1, fecha_alta=alta, estado=MiembroEquipo.HABILITADO
                )
                IntegranteEquipo.objects.create(usuario=jugador.user, equipo=equipo, aceptado=True)
                equipo.integrantes.add(jugador.user)
                Inscripcion.objects.create(jugador=jugador, equipo=equipo, torneo=torneo)
                miembros.append(miembro)
            equipo.capitan = miembros[0]
            equipo.total_integrantes = len(miembros)
            equipo.save()
            pet = ParticipacionEquipoTorneo.objects.create(
                torneo=torneo, equipo=equipo, zona="A", grupo=1, estado=ParticipacionEquipoTorneo.HABILITADO
            )
            participaciones.append(pet)
            miembros_por_equipo[pet.id] = miembros

        # Todos contra todos: las primeras 4 fechas ya se jugaron, las otras 3 están programadas.
        orden = participaciones[:]
        n = len(orden)
        for fecha in range(1, n):
            dia = torneo.dia_inicio + timedelta(weeks=fecha - 1)
            for k in range(n // 2):
                local, visita = orden[k], orden[n - 1 - k]
                partido = Partido.objects.create(
                    torneo=torneo,
                    etapa=Partido.ZONAS,
                    fecha=fecha,
                    equipo_local=local,
                    equipo_visitante=visita,
                    dia=dia,
                    hora_inicio=time(20 + k % 3, 0),
                    cancha=canchas[k % len(canchas)],
                    tipo_cancha=f5,
                    ubicacion="Rosario, Santa Fe",
                    duracion=50,
                    estado=Partido.PROGRAMADO,
                )
                if dia < hoy:
                    self.jugar(partido, miembros_por_equipo)
            orden.insert(1, orden.pop())
        ParticipacionEquipoTorneo.recalcular_torneo(torneo)
        # El inicio todavía lee la tabla del modelo anterior (Participacion): se copia la posición.
        tabla = sorted(
            ParticipacionEquipoTorneo.objects.filter(torneo=torneo), key=lambda p: (-p.puntos, -p.dif, -p.gf)
        )
        for posicion, pet in enumerate(tabla, start=1):
            pet.posicion = posicion
            pet.save(update_fields=["posicion"])
            Participacion.objects.create(
                equipo=pet.equipo, torneo=torneo, puntos=pet.puntos, pj=pet.pj, pg=pet.pg, pe=pet.pe,
                pp=pet.pp, gf=pet.gf, gc=pet.gc, dif=pet.dif, posicion=posicion,
            )

        # Amistosos: uno jugado con estadísticas y dos por jugar.
        companeros = list(Jugador.objects.exclude(pk=demo.pk)[:9])
        jugadores = [demo, *companeros]
        jugado = PartidoAmistoso.objects.create(
            creador=demo.user, cancha=canchas[0].nombre, tipo_cancha="Fútbol 5", ubicacion="Rosario, Santa Fe",
            dia=hoy - timedelta(days=3), hora_inicio=time(21, 0), goles_equipo_local=6, goles_equipo_visitante=4,
            precio_total=40000, jugado=True,
        )
        jugado.jugadores.set(jugadores)
        jugado.equipo_local.set(jugadores[:5])
        jugado.equipo_visitante.set(jugadores[5:])
        for jugador in jugadores:
            EstadisticaAmistosa.objects.create(
                jugador=jugador, partido=jugado, goles=random.randint(0, 2), asistencias=random.randint(0, 2),
                calificacion=round(random.uniform(6, 9), 1), dia=jugado.dia, cargada=jugador != demo,
            )
        for dias, hora, cancha in ((2, time(20, 0), canchas[1]), (6, time(22, 0), canchas[2])):
            proximo = PartidoAmistoso.objects.create(
                creador=demo.user, cancha=cancha.nombre, tipo_cancha="Fútbol 5", ubicacion="Rosario, Santa Fe",
                dia=hoy + timedelta(days=dias), hora_inicio=hora, precio_total=40000,
            )
            proximo.jugadores.set(random.sample(jugadores, 7) if demo in jugadores else jugadores[:7])
            proximo.jugadores.add(demo)

        for jugador in Jugador.objects.all():
            jugador.actualizar_valoraciones()

    def jugar(self, partido, miembros_por_equipo):
        """Resultado y estadísticas individuales coherentes con el marcador."""
        goles = {}
        for pet in (partido.equipo_local, partido.equipo_visitante):
            miembros = miembros_por_equipo[pet.id]
            arquero = next((m for m in miembros if m.jugador.posicion_preferida == "Arquero"), miembros[-1])
            total = random.choice([0, 1, 2, 2, 3, 3, 4, 5])
            goles[pet.id] = total
            autores = [random.choice([m for m in miembros if m != arquero]) for _ in range(total)]
            for miembro in miembros:
                EstadisticasJugadorPartido.objects.create(
                    miembro_equipo=miembro,
                    partido=partido,
                    jugo=True,
                    goles=autores.count(miembro),
                    asistencias=random.choice([0, 0, 0, 1]),
                    atajadas=random.randint(2, 7) if miembro == arquero else 0,
                    tiros_arco=random.randint(0, 3),
                )
        partido.goles_local = goles[partido.equipo_local_id]
        partido.goles_visitante = goles[partido.equipo_visitante_id]
        partido.jugado = True
        partido.estado = Partido.FINALIZADO
        partido.save()
