# Ticas · demo

Ticas es una aplicación web para organizar partidos y torneos de fútbol amateur: armado de
partidos amistosos con invitaciones, torneos con fixture y tabla de posiciones, carga de
estadísticas por jugador y perfiles con valoraciones. Se publicó en Google Play en beta cerrada,
con más de 100 usuarios, y se usó en un torneo real.

Esta es una **versión de demostración** con datos ficticios. Para probarla, entrá con el botón
**"Entrar como invitado"**: no hace falta registrarse. Los datos se reinician en cada despliegue.

## Tecnologías

- Python 3.12, Django 5.2 y Django REST Framework
- Plantillas de Django, JavaScript y CSS (diseño mobile first, instalable como PWA)
- Celery y Redis para tareas programadas (en la demo las tareas corren en el momento)
- Ingreso con Google (social-auth), opcional
- SQLite en la demo; MySQL y Docker en producción

## Diferencias con la versión en producción

- Todas las claves y credenciales salen de variables de entorno; la demo no necesita ninguna.
- No envía emails (se imprimen en el log) ni usa Redis.
- Los datos (equipos, jugadores, torneo y partidos) son inventados y los genera
  `python manage.py cargar_demo`.
- No incluye los videos de las historias promocionales ni datos de usuarios reales.

## Correrla en local

```bash
python -m venv .venv
.venv/Scripts/activate            # en Linux o macOS: source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1                    # en PowerShell: $env:DEBUG=1
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```

Después abrí http://localhost:8000 y tocá "Entrar como invitado".
`python manage.py cargar_demo --reset` borra todo y vuelve a cargar los datos de ejemplo.

## Despliegue

`render.yaml` define el servicio para Render (plan gratuito): instala dependencias, junta los
archivos estáticos y, al arrancar, aplica migraciones y carga los datos de ejemplo.

Desarrollada por el equipo de Octopush.
