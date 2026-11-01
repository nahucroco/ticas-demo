import matplotlib
matplotlib.use('Agg')  # Usar backend sin GUI
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import matplotlib.font_manager as fm
from collections import defaultdict
from django.db.models import Avg
from django.utils.timezone import localtime, make_aware, get_default_timezone
from .models import EstadisticaJugador
import os
from django.conf import settings
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager as fm, rcParams
from pathlib import Path

""" fuente_path = "static/fonts/Outfit-Regular.ttf"  # por ejemplo: "static/fonts/Montserrat-Regular.ttf"
fuente_prop = fm.FontProperties(fname=fuente_path, size=12) """

# Ruta absoluta a un .ttf real incluido en tu repo (no woff/woff2)
FONT_PATH = Path(settings.BASE_DIR) / "static" / "fonts" / "Outfit-Regular.ttf"

def _fp(size):
    # si Outfit se registró, bastan family+size;
    # si querés 100% explícito, podés intentar fname con try/except.
    return fm.FontProperties(family="Outfit", size=size)

def _setup_font():
    try:
        if FONT_PATH.exists() and FONT_PATH.suffix.lower() in {".ttf", ".otf"}:
            fm.fontManager.addfont(str(FONT_PATH))
            rcParams["font.family"] = "Outfit"
        else:
            rcParams["font.family"] = "DejaVu Sans"
    except Exception:
        rcParams["font.family"] = "DejaVu Sans"

_setup_font()

def generar_radar_valoraciones(jugador):
    labels = ['Ata', 'Cre', 'Hab', 'Por', 'Def']
    valores = [
        jugador.valoracion_ataque,
        jugador.valoracion_creatividad,
        jugador.valoracion_habilidad,
        jugador.valoracion_portero,
        jugador.valoracion_defensa,
    ]
    valores += valores[:1]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(2.5, 2.5), subplot_kw=dict(polar=True))

    # Dirección y orientación
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Eliminar grilla circular
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color='grey', linestyle='-', linewidth=0.2)
    ax.tick_params(pad=12)  # Aumenta la separación del texto con el centro



    # Dibujar líneas radiales manuales (grilla poligonal)
    for i in range(1, 6):  # Niveles 2, 4, 6, 8, 10
        r = [i] * len(angles)
        ax.plot(angles, r, color='gray', linewidth=0.2, linestyle='-', zorder=1)
        if i == 5:
            ax.plot(angles, r, color='gray', linewidth=1.2, linestyle='-', zorder=1)

    # Dibujar los datos del jugador
    ax.plot(angles, valores, color='#733BDE80', linewidth=2, zorder=2)
    ax.fill(angles, valores, color='#733BDE80', alpha=0.4, zorder=2)

    # Etiquetas
    """ etiquetas_completas = [
        f"{label}\n{valor:.1f}"
        for label, valor in zip(labels, valores[:-1])
    ]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(etiquetas_completas, fontproperties=fuente_prop, color='#FFF')  """
    etiquetas_completas = [f"{label}\n{valor:.1f}" for label, valor in zip(labels, valores[:-1])]
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(etiquetas_completas, fontproperties=_fp(12), color='#FFF')



    ax.set_yticklabels([])  # Ocultar etiquetas circulares
    ax.set_ylim(0, 5)
    ax.spines['polar'].set_linewidth(0)

    plt.tight_layout()

    # Guardar imagen con fondo transparente
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', transparent=True, dpi=300)
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    return imagen_base64


""" def generar_radar_valoraciones(jugador):
    labels = ['Ata', 'Cre', 'Hab', 'Por', 'Def']
    valores = [
        jugador.valoracion_ataque,
        jugador.valoracion_creatividad,
        jugador.valoracion_habilidad,
        jugador.valoracion_portero,
        jugador.valoracion_defensa,
    ]
    valores += valores[:1]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(1, 1), dpi=300)  # altura aumentada
    ax = fig.add_axes([0.0, -0.08, 1.0, 1.1], polar=True)  # bajamos el gráfico un 15% hacia abajo


    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color='grey', linestyle='-', linewidth=0.9)
    ax.tick_params(pad=20)

    # Líneas radiales
    for i in range(1, 6):
        r = [i] * len(angles)
        ax.plot(angles, r, color='grey', linewidth=0.1, linestyle='-', zorder=1)
        if i == 5:
            ax.plot(angles, r, color='grey', linewidth=0.5, linestyle='-', zorder=1)
    for angle in angles[:-1]:
        ax.plot([angle, angle], [0, 5], color='grey', linewidth=0.1)


    ax.plot(angles, valores, color='#733BDE80', linewidth=2, zorder=2)
    ax.fill(angles, valores, color='#733BDE80', alpha=0.4, zorder=2)

    ax.set_xticks([])
    ax.set_yticklabels([])
    ax.set_ylim(0, 5)
    ax.spines['polar'].set_linewidth(0)

    # 🎨 Coordenadas manuales para cada label y su valor
    ata, cre, hab, por, defn = valores[:-1]

    # ATAQUE (arriba)
    ax.text(0, 7.1, 'Ata', ha='center', va='bottom', fontproperties=fuente_prop, color='white')
    ax.text(0, 6.1, f"{ata:.1f}".replace('.', ','), ha='center', va='center',
            fontproperties=fuente_prop,
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#733BDE', edgecolor='none'),
            color='white')

    # CREATIVIDAD (arriba derecha)
    ax.text(4.2, 3.2, 'Cre', ha='left', va='bottom', fontproperties=fuente_prop, color='white')
    ax.text(4.2, 2.3, f"{cre:.1f}".replace('.', ','), ha='left', va='center',
            fontproperties=fuente_prop,
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#733BDE', edgecolor='none'),
            color='white')

    # HABILIDAD (abajo derecha)
    ax.text(3.7, -3.8, 'Hab', ha='left', va='top', fontproperties=fuente_prop, color='white')
    ax.text(3.7, -4.6, f"{hab:.1f}".replace('.', ','), ha='left', va='center',
            fontproperties=fuente_prop,
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#733BDE', edgecolor='none'),
            color='white')

    # PORTERO (abajo izquierda)
    ax.text(-2.8, 6.7, 'Por', ha='right', va='top', fontproperties=fuente_prop, color='white')
    ax.text(-2.2, 4.9, f"{por:.1f}".replace('.', ','), ha='right', va='bottom',
            fontproperties=fuente_prop,
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#733BDE', edgecolor='none'),
            color='white')

    # DEFENSA (arriba izquierda)
    ax.text(4.9, 5.2, 'Def', ha='right', va='bottom', fontproperties=fuente_prop, color='white')
    ax.text(-4.2, 2.3, f"{defn:.1f}".replace('.', ','), ha='right', va='center',
            fontproperties=fuente_prop,
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#733BDE', edgecolor='none'),
            color='white')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', transparent=True, pad_inches=0)
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    print("Tamaño de imagen (px):", fig.get_size_inches() * fig.dpi)

    plt.close(fig)

    return imagen_base64 """


def generar_grafico_resultados(ganados, empatados, perdidos):
    # Datos y colores
    valores = [ganados, empatados, perdidos]
    colores = ['#27BA37', '#C9C9C9', '#E32C2C']  # verde, gris, rojo
    etiquetas = ['Ganados', 'Empatados', 'Perdidos']
    
    if sum(valores) == 0:
        return None  # o devolver una imagen base64 vacía

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(2, 2), facecolor='#383650')
    wedges, texts = ax.pie(
        valores,
        labels=None,
        startangle=90,
        colors=colores,
        wedgeprops=dict(width=0.4)  # Anillo
    )

    ax.axis('equal')  # Hacerlo perfectamente circular

    # Guardar en base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', transparent=True, bbox_inches='tight', pad_inches=0, dpi=120)
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    return imagen_base64


def obtener_promedios_mensuales_torneo(jugador):
    from calendar import month_name
    from app_torneo_f5.models import EstadisticaJugador 
    
    MESES_ES = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    primera_estad = EstadisticaJugador.objects.filter(
        jugador=jugador,
        calificacion__isnull=False,
        dia__isnull=False
    ).order_by('dia').first()
    
    promedios = {}
    
    if primera_estad:
        anio_objetivo = primera_estad.dia.year

        # Paso 2: Obtener todas las estadísticas del mismo año
        estadisticas = EstadisticaJugador.objects.filter(
            jugador=jugador,
            calificacion__isnull=False,
            dia__year=anio_objetivo
        )

        # Paso 3: Agrupar calificaciones por mes
        calificaciones_por_mes = defaultdict(list)
        for estad in estadisticas:
            mes = estad.dia.month
            calificaciones_por_mes[mes].append(estad.calificacion)

        # Paso 4: Calcular promedios y formatear
        for mes in sorted(calificaciones_por_mes):
            califs = calificaciones_por_mes[mes]
            promedio = sum(califs) / len(califs)
            mes_str = MESES_ES[mes]
            promedios[mes_str] = round(promedio, 1)

        # Mostrar resultados
        for p in promedios.items():
            print(p)
    else:
        print("No hay estadísticas con calificación para este jugador.")
    """ promedios = {
        'Ene': 9.8,
        'Feb': 7.2,
        'Mar': 8.5,
        'Abr': 8.0,
        'May': 7.5,
        'Jun': 8.1,
        'Jul': 9.9,
        'Ago': 7.3,
        'Sep': 7.0,
        'Oct': 8.7,
        'Nov': 7.4,
        'Dic': 9.6
    } """
    return promedios    


def obtener_promedios_mensuales_amistoso(jugador):
    from calendar import month_name
    from app_torneo_f5.models import EstadisticaAmistosa 
    
    MESES_ES = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }
    
    primera_estad = EstadisticaAmistosa.objects.filter(
        jugador=jugador,
        calificacion__isnull=False,
        dia__isnull=False
    ).order_by('dia').first()
    
    promedios = {}
    
    if primera_estad:
        anio_objetivo = primera_estad.dia.year

        # Paso 2: Obtener todas las estadísticas del mismo año
        estadisticas = EstadisticaAmistosa.objects.filter(
            jugador=jugador,
            calificacion__isnull=False,
            dia__year=anio_objetivo
        )

        # Paso 3: Agrupar calificaciones por mes
        calificaciones_por_mes = defaultdict(list)
        for estad in estadisticas:
            mes = estad.dia.month
            calificaciones_por_mes[mes].append(estad.calificacion)

        # Paso 4: Calcular promedios y formatear
        for mes in sorted(calificaciones_por_mes):
            califs = calificaciones_por_mes[mes]
            promedio = sum(califs) / len(califs)
            mes_str = MESES_ES[mes]
            promedios[mes_str] = round(promedio, 1)

        # Mostrar resultados
        for p in promedios.items():
            print(p)
    else:
        print("No hay estadísticas con calificación para este jugador.")
    """ promedios = {
        'Ene': 2.8,
        'Feb': 1.2,
        'Mar': 4.5,
        'Abr': 2.0,
        'May': 3.5,
        'Jun': 6.1,
        'Jul': 2.9,
        'Ago': 4.3,
        'Sep': 3.0,
        'Oct': 9.7,
        'Nov': 1.4,
        'Dic': 1.6
    } """
    return promedios    
    
def generar_grafico_calificaciones(promedios):
    if not promedios:
        return None 

    """ fuente_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Outfit-Regular.ttf')
    fuente_prop = fm.FontProperties(fname=fuente_path, size=12) """
    fuente_prop = _fp(12)


    meses_ordenados = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    meses = [m for m in meses_ordenados if m in promedios]
    valores = [promedios[m] for m in meses]

    colores = []
    for val in valores:
        if val < 5:
            colores.append('#EA7236')
        elif val < 7:
            colores.append('#F1C40F')
        elif val < 9:
            colores.append('#81AC4B')
        else:
            colores.append('#0CA678')

    
    cantidad_barras = len(meses)
    bar_width = 0.28
    espacio_entre_barras = 0.065
    
    """ fig_width = max(2.0, cantidad_barras * bar_width)
    fig, ax = plt.subplots(figsize=(fig_width, 1), dpi=150) """
    fig_width = len(meses) * (bar_width + espacio_entre_barras)
    fig, ax = plt.subplots(figsize=(fig_width, 1.5), dpi=150)
    
    ax.set_position([0.01, 0.2, 0.9, 0.7])  # [left, bottom, width, height]

    """ x = [i * 0.45 for i in range(len(meses))] """  # Más juntos
    x = [i * (bar_width + espacio_entre_barras) for i in range(len(meses))]

    
    bars = ax.bar(x, valores, width=bar_width, color=colores, align='edge')
    
    ax.set_xticks([i + bar_width / 2 for i in x])  # Centra los nombres debajo de cada barra

    ax.set_xticklabels(meses, fontproperties=fuente_prop, fontsize=7, color="#FFFFFF84")
    
    """ ax.set_xlim(0, x[-1] + 0.45) """
    ax.set_xlim(0, x[-1] + bar_width + espacio_entre_barras)

    for bar, valor in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, f"{valor:.1f}",
                ha='center', va='bottom', fontsize=8, color='white', fontweight='normal', fontproperties=fuente_prop)

    fig.patch.set_facecolor('#3F374E')
    ax.set_facecolor('#3F374E')
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params()
    ax.tick_params(axis='x', length=0)
    ax.set_ylim(0, 10)
    ax.yaxis.set_ticks([])

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', transparent=False)
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)

    return img_base64
    
""" def generar_grafico_calificaciones(promedios):
    import os
    import io
    import base64
    from django.conf import settings
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from PIL import Image

    fuente_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Outfit-Regular.woff2')
    fuente_prop = fm.FontProperties(fname=fuente_path, size=12)

    meses_ordenados = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    meses = [m for m in meses_ordenados if m in promedios]
    valores = [promedios[m] for m in meses]

    colores = []
    for val in valores:
        if val < 5:
            colores.append('#EA7236')
        elif val < 7:
            colores.append('#F1C40F')
        elif val < 9:
            colores.append('#81AC4B')
        else:
            colores.append('#0CA678')

    fig, ax = plt.subplots(figsize=(3, 1.5), dpi=600)
    ax.set_position([0.01, 0.2, 0.9, 0.7])

    bar_width = 0.27
    x = [i * 0.33 for i in range(len(meses))]

    bars = ax.bar(x, valores, width=bar_width, color=colores, align='edge')

    ax.set_xticks([i + bar_width / 2 for i in x])
    ax.set_xticklabels(meses, fontproperties=fuente_prop, fontsize=7, color="#FFFFFF84")
    ax.set_xlim(0, len(meses))

    for bar, valor in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2, str(int(valor)),
                ha='center', va='bottom', fontsize=8, color='white', fontweight='normal', fontproperties=fuente_prop)

    fig.patch.set_facecolor('#3F374E')
    ax.set_facecolor('#3F374E')
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params()
    ax.tick_params(axis='x', length=0)
    ax.set_ylim(0, 10)
    ax.yaxis.set_ticks([])

    # Guardar en buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=600, bbox_inches=None, transparent=False)
    plt.close(fig)
    buffer.seek(0)

    # 🔁 Redimensionar imagen a alto fijo
    img = Image.open(buffer)
    new_height = 70  # altura deseada en píxeles
    width_original, height_original = img.size
    new_width = int(width_original * (new_height / height_original))
    resized_img = img.resize((new_width, new_height), Image.LANCZOS)

    # Convertir a base64
    final_buffer = io.BytesIO()
    resized_img.save(final_buffer, format='PNG')
    img_base64 = base64.b64encode(final_buffer.getvalue()).decode('utf-8')

    return img_base64 """

 