from django.urls import path
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from app_torneo_f5.views.demo import demo_login

# Vistas principales
from app_torneo_f5.views.views import (
    assetlinks_json,
    privacy_policy,
    atajo_instagram,
    offline,
    form_delete_account,
    vista_bienvenida,
    home,
    torneos_del_usuario,
    detalle_torneo,
    descripcion_torneo,
    equipos_del_usuario,
    detalle_equipo,
    configuracion_equipo,
    invitar_jugadores_equipo,
    buscar_jugadores_equipo,
    busqueda,
    registro_usuario,
    confirmar_registro,
    logout_view,
    auth,
    adelantos,
    mi_perfil,
    perfil,
    configuracion_perfil,
    crear_perfil_1,
    crear_perfil_2,
    crear_perfil_3,
    crear_perfil_4,
    amistosos_disponibles,
    detalle_partido_por_codigo,
    crear_partido_amistoso,
    editar_partido_amistoso,
    confirmar_invitacion,
    mis_invitaciones,
    aceptar_invitacion,
    aceptar_invitacion_uuid,
    partidos,
    crear_partido,
    crear_partido_1,
    crear_partido_2,
    crear_partido_3,
    crear_partido_final,
    configuracion_partido,
    detalle_partido,
    propuesta_partido,
    propuesta_partido_1,
    propuesta_partido_2,
    crear_propuesta,
    detalle_propuesta,
    seleccionar_propuesta,
    invitar_jugadores_vista,
    borrar_partido,
    invitar_jugador,
    marcar_invitacion_vista,
    nuevas_invitaciones,
    armar_equipos,
    confirmar_equipos,
    estadisticas_paso1,
    estadisticas_paso2,
    estadisticas_paso3,
    estadisticas_pasofinal,
    unirse_a_partido,
    cancelar_partido,
    eliminar_jugador,
    jugadores_invitados_api,
    abandonar_partido,
    canchas_futbol,
    
    busqueda_jugadores,
    busqueda_jugadores_invitar,
    busqueda_equipos,
    busqueda_torneos,
    cancelar_invitacion,
    configurar_partido_torneo,
    carga_estadistica,

)

# Vistas API y auxiliares
from app_torneo_f5.views.views import (
    descargar_apk,
    marcar_notificacion_vista,
    magic_ok,

)

from app_torneo_f5.views.api_views import (
    cargar_estadisticas_partido_api,
    obtener_partido_por_id,
    configurar_partido_api,
    listar_canchas_api,
    obtener_cancha_api,
    crear_cancha_api,
    obtener_torneo_por_id,
    api_tabla_torneo,
    api_tabla_posiciones,
    partido_celery_definido,
    cargar_estadisticas_partido_torneo_api,
    carga_estadistica_final,
    obtener_estadisticas_partido,
)


# Vistas de promoción
from app_torneo_f5.views.views_promo import (
    promo_estadisticas_paso1,
    promo_estadisticas_paso2,
    promo_estadisticas_paso3,
    promo_estadisticas_stories,
)

# Healthcheck
def health(_): return HttpResponse("ok")

urlpatterns = [
    path("health", health),
    path('.well-known/assetlinks.json', assetlinks_json, name='assetlinks'),

    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('notificaciones/<int:pk>/visto/', marcar_notificacion_vista, name='noti_visto'),
    
    path('atajo-instagram/', atajo_instagram, name='atajo_instagram'),

    path('offline/', offline, name='offline'),
    
    #Formulario borrar cuenta
    path('form-delete-account/', form_delete_account, name='form_delete_account'),
    
    #Bienvenida
    path('bienvenido', vista_bienvenida, name='bienvenido'),
    path('', home, name='home'),
    path('mis-torneos/', torneos_del_usuario, name='torneos'),
    path('torneo/<int:torneo_id>/', detalle_torneo, name='detalle_torneo'),
    path('descripcion-torneo/<int:torneo_id>/', descripcion_torneo, name='descripcion_torneo'),
    path('mis-equipos/', equipos_del_usuario, name='equipos'),
    path('equipos/<int:pk>/', detalle_equipo, name='detalle_equipo'),
    path('equipos/<int:pk>/configuracion', configuracion_equipo, name='configuracion_equipo'),
    path('equipos/<int:equipo_id>/invitar/', invitar_jugadores_equipo, name='invitar_jugadores_equipo'),
    path('equipos/<int:equipo_id>/buscar-jugadores/', buscar_jugadores_equipo, name='buscar_jugadores_equipo'),
    path('busqueda/', busqueda, name='busqueda'),
    path('registro/', registro_usuario, name='registro_usuario'),
    path('registro/confirmar/<uidb64>/<token>/', confirmar_registro, name='confirmar_registro'),
    path('logout/', logout_view, name='logout'),
    path('login/', auth, name='login'),
    path('demo/', demo_login, name='demo_login'),
    
    
    path('adelantos', adelantos, name='adelantos'),
    
    #Perfil
    path('mi-perfil/', mi_perfil, name='mi_perfil'),
    path('perfil/<int:jugador_id>/', perfil, name='perfil'), 
    path('perfil/<int:pk>/configuracion', configuracion_perfil, name='configuracion_perfil'),
    path('crear-perfil-1/', crear_perfil_1, name='crear_perfil_1'),
    path('crear-perfil-2/', crear_perfil_2, name='crear_perfil_2'),
    path('crear-perfil-3/', crear_perfil_3, name='crear_perfil_3'),
    path('crear-perfil-4/', crear_perfil_4, name='crear_perfil_4'),
    path('partidos-amistosos/', amistosos_disponibles, name='amistosos'),
    path('invitaciones/<str:codigo_invitacion>/', detalle_partido_por_codigo, name='partido_por_codigo'),
    path('partidos-amistosos/crear/', crear_partido_amistoso, name='crear_amistoso'),
    path('partidos-amistosos/editar/<int:pk>/', editar_partido_amistoso, name='editar_amistoso'),
    path('confirmar-invitacion/<uuid:uuid>/', confirmar_invitacion, name='confirmar_invitacion'),
    path('invitaciones/', mis_invitaciones, name='mis_invitaciones'),
    path('invitaciones/aceptar/<int:invitacion_id>/', aceptar_invitacion, name='aceptar_invitacion'),
    path('partidos-amistosos/editar/<int:pk>/', editar_partido_amistoso, name='editar_partido_amistoso'),
    path('api/busqueda/jugadores/invitar/', busqueda_jugadores_invitar, name='jugadores_mock_invitar'),
    path('api/busqueda/jugadores/', busqueda_jugadores, name='jugadores_mock'),
    path('api/busqueda/equipos/', busqueda_equipos, name='busqueda_equipos'),
    path('api/busqueda/torneos/', busqueda_torneos, name='busqueda_torneos'),
    path('partidos/', partidos, name='partidos'),
    path('crear-partido-1/', crear_partido_1, name='crear_partido_1'),
    path('crear-partido' , crear_partido, name='crear_partido'),
    path('crear-partido-2/', crear_partido_2, name='crear_partido_2'),
    path('crear-partido-3/', crear_partido_3, name='crear_partido_3'),
    path('crear-partido-final/', crear_partido_final, name='crear_partido_final'),
    path('partido/<str:tipo>/<int:partido_id>/configuracion', configuracion_partido, name='configuracion_partido'),
    path('partido/<str:tipo>/<int:partido_id>/', detalle_partido, name='detalle_partido'),
    
    # Propuesta de partido de torneo
    path('partido/<int:partido_id>/propuesta-1/', propuesta_partido_1, name='propuesta_partido_1'),
    path('partido/<int:partido_id>/propuesta-2/', propuesta_partido_2, name='propuesta_partido_2'),
    path("crear-propuesta/", crear_propuesta, name="crear_propuesta"),
    path('partido/<int:partido_id>/detalle-propuesta/', detalle_propuesta, name='detalle_propuesta'),
    path('partido/<int:partido_id>/seleccionar-propuesta/', seleccionar_propuesta, name='seleccionar_propuesta'),
    path('partido/<int:partido_id>/propuesta-partido/', propuesta_partido, name='propuesta_partido'),
    path('partidos/<int:partido_id>/configurar/vista/', configurar_partido_torneo, name='configurar_partido_torneo'),

    path('partidos-amistosos/<int:partido_id>/invitar/', invitar_jugadores_vista, name='invitar_jugadores_vista'),
    path('partidos-amistosos/borrar/<int:partido_id>/', borrar_partido, name='borrar_partido'),
    path('invitar/<int:partido_id>/<int:jugador_id>/', invitar_jugador, name='invitar_jugador'),
    path('marcar-invitacion-vista/<str:tipo>/<int:id>/', marcar_invitacion_vista, name='marcar_invitacion_vista'),
    path('aceptar-invitacion/<uuid:uuid>/', confirmar_invitacion, name='aceptar_invitacion_uuid'),
    path('invitaciones/aceptar/uuid/<uuid:uuid>/', aceptar_invitacion_uuid, name='aceptar_invitacion_uuid'),
    path('api/invitaciones/nuevas/', nuevas_invitaciones, name='nuevas_invitaciones'),
    path('partido/<int:partido_id>/armar-equipos/', armar_equipos, name='armar_equipos'),
    path('partido/<int:partido_id>/confirmar-equipos/', confirmar_equipos, name='confirmar_equipos'),
    
    # Carga de estadísticas
    path('partido/<str:tipo>/<int:partido_id>/estadisticas/1/', estadisticas_paso1, name='estadisticas_paso1'),
    path('partido/<str:tipo>/<int:partido_id>/estadisticas/2/', estadisticas_paso2, name='estadisticas_paso2'),
    path('partido/<str:tipo>/<int:partido_id>/estadisticas/3/', estadisticas_paso3, name='estadisticas_paso3'),
    path('partido/<str:tipo>/<int:partido_id>/estadisticas/final/', estadisticas_pasofinal, name='estadisticas_pasofinal'),
    
    path('unirse-a-partido/<int:partido_id>/', unirse_a_partido, name='unirse_a_partido'),
    path('cancelar_partido/<int:partido_id>/', cancelar_partido, name='cancelar_partido'),
    path('partido/<int:partido_id>/eliminar-jugador/<int:jugador_id>/', eliminar_jugador, name='eliminar_jugador'),
    path("api/partido/<int:partido_id>/invitados/", jugadores_invitados_api),
    path('cancelar-invitacion/<int:partido_id>/<int:jugador_id>/', cancelar_invitacion, name="cancelar_invitacion"),

    path('ok/<uuid:token>/', magic_ok, name='magic_ok'),
    
    # Demo stories para promo
    path('promo/estadisticas/1/', promo_estadisticas_paso1, name='promo_estadisticas_paso1'),
    path('promo/estadisticas/2/', promo_estadisticas_paso2, name='promo_estadisticas_paso2'),
    path('promo/estadisticas/3/', promo_estadisticas_paso3, name='promo_estadisticas_paso3'),
    path('promo/estadisticas/stories/', promo_estadisticas_stories, name='promo_estadisticas_stories'),
    path('promo/demo/', promo_estadisticas_stories, name='promo_demo_stories'),
    path('descargar/ticas', descargar_apk, name='descargar_apk'),
    path("partido/<int:partido_id>/abandonar/", abandonar_partido, name="abandonar_partido"),

    path("api/canchas/futbol" , canchas_futbol, name="canchas_futbol"),
    
    #APIs
    path('api/estadisticas/cargar/', cargar_estadisticas_partido_api, name='api_cargar_estadisticas_partido'),
    
    #API partidos
    path('api/partido/<int:partido_id>/', obtener_partido_por_id, name='api_obtener_partido'),
    path('api/partido/<int:partido_id>/estadisticas/', obtener_estadisticas_partido, name='api_obtener_estadisticas_partido'),
    path('api/partidos/<int:partido_id>/configurar/', configurar_partido_api, name='api_configurar_partido'),
    path('api/canchas/', listar_canchas_api, name='api_listar_canchas'),
    path('api/canchas/<int:cancha_id>/', obtener_cancha_api, name='api_obtener_cancha'),
    path('api/canchas/nueva/', crear_cancha_api, name='api_crear_cancha'),
    path('api/torneo/<int:torneo_id>/', obtener_torneo_por_id, name='api_obtener_torneo'),
    path('api/torneo/<int:torneo_id>/tabla/', api_tabla_posiciones, name='api_tabla_posiciones'),

    #api para cargar estadistica
    path('api/partido/torneo/<int:partido_id>/cargar-estadisticas/', cargar_estadisticas_partido_torneo_api, name='api_cargar_estadisticas_partido'),


    #API Celery tasks
    #api para cargar el tiempo que comienza el partido
    path('api/celery/partido-definido/<int:partido_id>/', partido_celery_definido, name='partido_definido'),

    #carga estadisticas torneo

    path ('partido/<str:tipo>/<int:partido_id>/carga-estadisticas/', carga_estadistica, name='carga_estadistica'),
    path ('api/partido/<str:tipo>/<int:partido_id>/cargar-estadisticas/final/', carga_estadistica_final, name='carga_estadistica_final')


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

""" path('partido/<int:partido_id>/propuesta/', propuesta_partido, name='propuesta_partido'), """
""" path('partido/<int:partido_id>/propuesta-defecto/', propuesta_partido_defecto, name='propuesta_partido_defecto'), """
""" propuesta_partido, """
""" propuesta_partido_defecto, """