from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django import forms  # ⬅️ necesario para fallbacks

# ===== Fallbacks de forms si no existen en forms.py =====
try:
    from .forms import EstadisticaAmistosaForm, EstadisticasJugadorPartidoForm
except Exception:
    from .models import EstadisticaAmistosa, EstadisticasJugadorPartido
    class EstadisticaAmistosaForm(forms.ModelForm):
        class Meta:
            model = EstadisticaAmistosa
            fields = "__all__"
    class EstadisticasJugadorPartidoForm(forms.ModelForm):
        class Meta:
            model = EstadisticasJugadorPartido
            fields = "__all__"

from .models import (
    # Core
    Torneo, Equipo, Jugador, TipoCancha, Cancha,
    Participacion, Inscripcion, PerfilUsuario, IntegranteEquipo,
    Notificacion, Invitacion, InvitacionEquipo,
    # Torneo/Liga TW
    ParticipacionEquipoTorneo, Partido, Propuesta,
    # Amistosos / Stats
    PartidoAmistoso, EstadisticaJugador, EstadisticaAmistosa,
    EstadisticasJugadorPartido, MiembroEquipo,  # ⬅️ aseguramos import
)

CustomUser = get_user_model()


# =========================
#  Usuarios
# =========================
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'groups')
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datos extra', {'fields': ('email_verified', 'picture', 'full_name')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active')}),
    )
    search_fields = ('username', 'email', 'full_name')
    ordering = ('username',)


# =========================
#  Equipo / Integrantes
# =========================
class IntegranteEquipoInline(admin.TabularInline):
    model = IntegranteEquipo
    extra = 1
    autocomplete_fields = ['usuario']
    fields = ['usuario', 'aceptado']
    verbose_name = 'Integrante'
    verbose_name_plural = 'Integrantes'


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "nombre_corto", "provincia", "ciudad")
    search_fields = ("nombre", "nombre_corto", "provincia", "ciudad")
    inlines = [IntegranteEquipoInline]


@admin.register(IntegranteEquipo)
class IntegranteEquipoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'equipo', 'aceptado']
    list_filter = ['aceptado', 'equipo']
    search_fields = ['usuario__username', 'equipo__nombre']


# ===== ✅ REGISTRO REQUERIDO PARA AUTOCOMPLETE EN EstadisticasJugadorPartidoAdmin =====
@admin.register(MiembroEquipo)
class MiembroEquipoAdmin(admin.ModelAdmin):
    list_display = ("id", "jugador", "equipo", "dorsal", "estado", "fecha_alta", "fecha_baja")
    list_filter = ("estado", "equipo")
    search_fields = ("jugador__nombre", "jugador__user__username", "equipo__nombre")  # ⬅️ necesario para autocomplete


# =========================
#  Canchas / Tipos
# =========================
@admin.register(Cancha)
class CanchaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "direccion", "lista_tipos", "thumb")
    list_filter = ("tipo_cancha",)
    search_fields = ("nombre", "direccion", "tipo_cancha__nombre")
    filter_horizontal = ("tipo_cancha",)
    readonly_fields = ("preview",)
    fields = ("nombre", "direccion", "tipo_cancha", "imagen", "preview")

    @admin.display(description="Tipos")
    def lista_tipos(self, obj):
        return ", ".join(obj.tipo_cancha.values_list("nombre", flat=True)) or "—"

    @admin.display(description="Imagen")
    def thumb(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height:40px;width:auto;border-radius:4px;" />', obj.imagen.url)
        return "—"

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj and obj.imagen:
            return format_html('<img src="{}" style="max-height:200px;width:auto;border-radius:6px;" />', obj.imagen.url)
        return "Sin imagen"


@admin.register(TipoCancha)
class TipoCanchaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


# =========================
#  Torneo / Participaciones (modelo nuevo)
# =========================
@admin.register(Torneo)
class TorneoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "estado", "dia_inicio", "dia_fin", "tipo_cancha", "duracion_partido")
    list_filter = ("estado", "tipo_cancha")
    search_fields = ("nombre",)
    autocomplete_fields = ("encargados_carga", "creador")


@admin.register(ParticipacionEquipoTorneo)
class ParticipacionEquipoTorneoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "torneo", "equipo", "zona", "grupo", "etiqueta",
        "puntos", "pj", "pg", "pe", "pp", "gf", "gc", "dif",
        "estado", "sigue_en_competencia", "posicion",
    )
    list_filter = ("torneo", "zona", "grupo", "estado", "sigue_en_competencia", "etiqueta")
    search_fields = ("equipo__nombre", "equipo__nombre_corto", "torneo__nombre")
    autocomplete_fields = ("torneo", "equipo", "encargado_carga")
    list_select_related = ("torneo", "equipo")


# =========================
#  Partido (Zonas/Copa Oro/Plata)
# =========================
@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "torneo", "etapa", "ronda", "fecha", "estado", "jugado",
        "equipo_local", "equipo_visitante",
        "goles_local", "goles_visitante",
        "dia", "hora_inicio",
    )
    list_filter = ("torneo", "etapa", "ronda", "estado", "jugado", "fecha", "dia")
    search_fields = (
        "torneo__nombre",
        "equipo_local__equipo__nombre",
        "equipo_visitante__equipo__nombre",
    )
    autocomplete_fields = (
        "torneo", "equipo_local", "equipo_visitante",
        "equipo_ganador", "cancha", "tipo_cancha",
    )
    date_hierarchy = "dia"
    list_select_related = ("torneo", "equipo_local", "equipo_visitante", "equipo_ganador")


# =========================
#  Propuesta (one-to-one con Partido)
# =========================
@admin.register(Propuesta)
class PropuestaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'partido', 'respondida', 'cerrada',
        'opcion_dia_hora', 'opcion_cancha',
        'contador', 'op1_fecha_hora', 'op1_cancha', 'op1_precio',
    )
    list_filter = ('respondida', 'cerrada', 'opcion_dia_hora', 'opcion_cancha')
    search_fields = (
        'partido__id',
        'ubicacion1', 'ubicacion2', 'ubicacion3',
        'cancha1__nombre', 'cancha2__nombre', 'cancha3__nombre',
    )
    autocomplete_fields = ('partido', 'cancha1', 'cancha2', 'cancha3')
    readonly_fields = ('contador',)
    ordering = ('-id',)
    date_hierarchy = 'fecha1'

    actions = ['marcar_respondida', 'marcar_cerrada', 'reabrir']

    def marcar_respondida(self, request, queryset):
        updated = queryset.update(respondida=True)
        self.message_user(request, f'{updated} propuestas marcadas como respondidas.')
    marcar_respondida.short_description = 'Marcar como respondida'

    def marcar_cerrada(self, request, queryset):
        updated = queryset.update(cerrada=True)
        self.message_user(request, f'{updated} propuestas marcadas como cerradas.')
    marcar_cerrada.short_description = 'Marcar como cerrada'

    def reabrir(self, request, queryset):
        updated = queryset.update(cerrada=False, respondida=False)
        self.message_user(request, f'{updated} propuestas reabiertas.')
    reabrir.short_description = 'Reabrir (quitar respondida/cerrada)'

    # Helpers
    def op1_fecha_hora(self, obj):
        f = obj.fecha1.strftime('%Y-%m-%d') if obj.fecha1 else '—'
        h = obj.hora1.strftime('%H:%M') if obj.hora1 else '—'
        return f'{f} {h}'
    op1_fecha_hora.short_description = 'Opción 1 (fecha/hora)'

    def op1_cancha(self, obj):
        return obj.cancha1 or obj.ubicacion1 or '—'
    op1_cancha.short_description = 'Opción 1 (cancha/ubicación)'

    def op1_precio(self, obj):
        return obj.precio1 if obj.precio1 is not None else '—'
    op1_precio.short_description = 'Opción 1 ($)'


# =========================
#  Estadísticas (torneo / amistosos)
# =========================
@admin.register(EstadisticasJugadorPartido)
class EstadisticasJugadorPartidoAdmin(admin.ModelAdmin):
    form = EstadisticasJugadorPartidoForm
    list_display = (
        "get_jugador", "get_equipo", "get_partido_info",
        "goles", "asistencias", "atajadas",
        "tarjetas_amarillas", "tarjeta_roja", "jugo",
    )
    list_filter = ("jugo", "tarjeta_roja", "partido__torneo", "miembro_equipo__equipo")
    search_fields = (
        "miembro_equipo__jugador__nombre",
        "miembro_equipo__jugador__user__username",
        "partido__id",
    )
    autocomplete_fields = ("miembro_equipo", "partido")  # ✅ ahora sí, MiembroEquipo tiene admin con search_fields
    list_select_related = ("miembro_equipo__jugador", "miembro_equipo__equipo", "partido")
    ordering = ("-partido__id",)

    def get_partido_info(self, obj):
        return str(obj.partido) if obj.partido_id else "-"
    get_partido_info.short_description = "Partido"

    def get_jugador(self, obj):
        return obj.miembro_equipo.jugador if obj.miembro_equipo_id else "-"
    get_jugador.short_description = "Jugador"

    def get_equipo(self, obj):
        return obj.miembro_equipo.equipo if obj.miembro_equipo_id else "-"
    get_equipo.short_description = "Equipo"


@admin.register(EstadisticaAmistosa)
class EstadisticaAmistosaAdmin(admin.ModelAdmin):
    form = EstadisticaAmistosaForm
    list_display = ('jugador', 'get_partido_info', 'goles', 'asistencias', 'atajadas', 'jugo', 'vencida')
    list_filter = ('jugador', 'partido', 'vencida')
    search_fields = ('jugador__nombre', 'partido__id')
    autocomplete_fields = ('jugador', 'partido')
    date_hierarchy = 'dia'

    def get_partido_info(self, obj):
        return str(obj.partido) if obj.partido else "-"
    get_partido_info.short_description = 'Partido'


# =========================
#  Amistosos
# =========================
@admin.register(PartidoAmistoso)
class PartidoAmistosoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "dia", "hora_inicio", "duracion",
        "modo_juego", "jugado", "jugando", "cancelado",
        "goles_equipo_local", "goles_equipo_visitante",
    )
    list_filter = ("modo_juego", "jugado", "jugando", "cancelado")
    search_fields = ("codigo_invitacion",)
    date_hierarchy = "dia"


# =========================
#  Otros básicos
# =========================
@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "ciudad", "provincia", "partidos_jugados", "goles_totales", "asistencias_totales")
    search_fields = ("nombre", "user__username")
    list_filter = ("provincia", "ciudad")


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje', 'tipo', 'fecha', 'leida')
    list_filter = ('tipo', 'leida')
    search_fields = ('usuario__username', 'mensaje')


@admin.register(Invitacion)
class InvitacionAdmin(admin.ModelAdmin):
    list_display = ('jugador', 'partido', 'fecha_envio', 'vista', 'aceptada')
    list_filter = ('vista', 'aceptada')
    search_fields = ('jugador__nombre', 'partido__id')
    autocomplete_fields = ('jugador', 'partido')


@admin.register(InvitacionEquipo)
class InvitacionEquipoAdmin(admin.ModelAdmin):
    list_display = ('jugador', 'equipo', 'fecha_envio', 'vista', 'aceptada')
    list_filter = ('vista', 'aceptada', 'equipo')
    search_fields = ('jugador__nombre', 'equipo__nombre')
    autocomplete_fields = ('jugador', 'equipo')


@admin.register(Participacion)
class ParticipacionAdmin(admin.ModelAdmin):
    list_display = ("id", "equipo", "torneo", "puntos", "pj", "pg", "pe", "pp", "gf", "gc", "dif", "posicion", "sigue_en_competencia")
    list_filter = ("torneo", "sigue_en_competencia")
    search_fields = ("equipo__nombre", "torneo__nombre")
    autocomplete_fields = ("equipo", "torneo")


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ("id", "jugador", "equipo", "torneo")
    list_filter = ("torneo", "equipo")
    search_fields = ("jugador__nombre", "equipo__nombre", "torneo__nombre")
    autocomplete_fields = ("jugador", "equipo", "torneo")


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("user", "es_primer_ingreso")
    search_fields = ("user__username",)
    autocomplete_fields = ("user",)
