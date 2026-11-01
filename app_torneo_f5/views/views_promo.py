
""" Demo stories publicidad """

# views_promo.py (o en el mismo archivo si preferís)

import os, random, glob
from types import SimpleNamespace
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_GET
from django.utils.http import urlencode

# ======= Catálogos / mapping =======
CATEGORIAS = ["goles", "asist", "ataj", "hab", "def"]
NIVELES = ["primera", "segunda", "tercera", "profesional"]  # orden lógico

DISPLAY_TIPO = {
    "goles": "goles",
    "asist": "asistencias",
    "ataj":  "atajadas",
    "hab":   "habilidad",
    "def":   "defensa",
}

CARD_KIND = {
    "goles": "total", "asist": "total", "ataj": "total",
    "hab": "valoracion", "def": "valoracion",
}

PRIORIDAD_TOP = ["hab", "def", "goles", "asist", "ataj"]

def _static_url(*parts):
    base = settings.STATIC_URL.rstrip("/") + "/"
    return base + "/".join(parts)

def _pick_top_key(base_dict):
    """
    base_dict: {'goles': int, 'asist': int, 'ataj': int, 'hab': int, 'def': int}
    Devuelve la clave interna con mayor valor (>0). Empates se resuelven por PRIORIDAD_TOP.
    Si todos son 0, devuelve None.
    """
    # Valor máximo positivo
    max_val = max(base_dict.values()) if base_dict else 0
    if max_val <= 0:
        return None
    candidatos = [k for k, v in base_dict.items() if v == max_val]
    # tie-break por PRIORIDAD_TOP
    for pref in PRIORIDAD_TOP:
        if pref in candidatos:
            return pref
    return candidatos[0] if candidatos else None

def _to_int(v, lo=0, hi=999999):
    try:
        x = int(v)
        return max(lo, min(hi, x))
    except (TypeError, ValueError):
        return 0

# ======= Session helpers =======
PROMO_KEY = "promo_stats"  # todo lo de la promo vive acá

def promo_get(session):
    """
    Devuelve dict con todos los campos usados por las stories:
      goles, asistencias, atajadas, habilidad, defensa (enteros)
    """
    data = session.get(PROMO_KEY, {}) or {}
    return {
        "goles":       _to_int(data.get("goles", 0)),
        "asistencias": _to_int(data.get("asistencias", 0)),
        "atajadas":    _to_int(data.get("atajadas", 0)),
        "habilidad":   _to_int(data.get("habilidad", 0)),
        "defensa":     _to_int(data.get("defensa", 0)),
        # opcional: ultima_frase, etc.
        "ultima_frase": data.get("ultima_frase", ""),
    }

def promo_set(session, **kwargs):
    data = session.get(PROMO_KEY, {}) or {}
    data.update({k: _to_int(v) if k != "ultima_frase" else (v or "") for k, v in kwargs.items()})
    session[PROMO_KEY] = data
    session.modified = True

def promo_clear(session):
    session.pop(PROMO_KEY, None)
    session.modified = True

# ======= Videos =======
def _static_abs(*parts):
    base = getattr(settings, "BASE_DIR", "")
    return os.path.join(base, "static", *parts)

def _abs_to_static_url(abs_path):
    p = abs_path.replace("\\", "/")
    cut = "/static/"
    if cut in p:
        return f"{settings.STATIC_URL}{p.split(cut, 1)[1]}"
    return ""

def _build_catalog():
    catalog = {cat: {lvl: [] for lvl in NIVELES} for cat in CATEGORIAS}
    for cat in CATEGORIAS:
        folder = _static_abs("videos", cat)
        if not os.path.isdir(folder):
            continue
        for fname in os.listdir(folder):
            if not fname.lower().endswith(".mp4"):
                continue
            name = os.path.splitext(fname)[0].lower()
            nivel = next((lvl for lvl in NIVELES if name.startswith(lvl)), "primera")
            url = _abs_to_static_url(os.path.join(folder, fname))
            if url:
                catalog[cat][nivel].append(url)
    return catalog

def _pick_any_video(catalog, categoria, fallback_radar=True):
    pool = []
    for lvl in NIVELES:
        pool.extend(catalog.get(categoria, {}).get(lvl, []))
    if pool:
        return random.choice(pool)

    all_pool = []
    for cat in CATEGORIAS:
        for lvl in NIVELES:
            all_pool.extend(catalog.get(cat, {}).get(lvl, []))
    if all_pool:
        return random.choice(all_pool)

    if fallback_radar:
        return _pick_radar_video()
    return ""

def _pick_radar_video():
    radar_abs = _static_abs("videos", "radar")
    try:
        candidates = glob.glob(os.path.join(radar_abs, "*.mp4"))
    except Exception:
        candidates = []
    if not candidates:
        return ""
    return _abs_to_static_url(random.choice(candidates))

def _fake_partido(_request):
    # ID numérico para que reverse() no falle con el regex [0-9]+
    return SimpleNamespace(id=0, nombre="Partido Promo")

###############################################################################################

@require_http_methods(["GET", "POST"])
def promo_estadisticas_paso1(request):
    partido = _fake_partido(request)
    if request.method == "POST":
        # nada que guardar en este paso; seguimos
        return redirect("promo_estadisticas_paso2")
    return render(request, "stories/carga_estadisticas_1.html", {
        'ocultar_navbar': True,
        "partido": partido,
        "jugadores": [],  # ⚠️ vacío: el template itera sin romper
        "tipo": "promo",
    })

@require_http_methods(["GET", "POST"])
def promo_estadisticas_paso2(request):
    partido = _fake_partido(request)
    if request.method == "POST":
        promo_set(
            request.session,
            defensa=request.POST.get("calificacion_defensivo"),
            habilidad=request.POST.get("calificacion_manejo"),
        )
        return redirect("promo_estadisticas_paso3")
    return render(request, "stories/carga_estadisticas_2.html", {
        'ocultar_navbar': True,
        "partido": partido,
        "jugadores": [],  # si el template lo usa
        "tipo": "promo",
    })

@require_http_methods(["GET", "POST"])
def promo_estadisticas_paso3(request):
    partido = _fake_partido(request)

    if request.method == "POST":
        promo_set(
            request.session,
            ultima_frase=request.POST.get("ultima_frase", ""),
            goles=request.POST.get("goles"),
            asistencias=request.POST.get("asistencias"),
            atajadas=request.POST.get("atajadas"),
        )
        return redirect("promo_estadisticas_stories")

    # GET: opcional limpiar la frase si querés
    return render(request, "stories/carga_estadisticas_3.html", {
        'ocultar_navbar': True,
        "partido": partido,
        "tipo": "promo",
    })

#############################################################################################################


#############################################################################################################

@require_GET
def promo_estadisticas_stories(request):
    """
    Renderiza stories:
      - 2 stats (si hay)
      - 1 radar (3ª) con la Lottie de la stat con mayor aumento (si aplica)
      - 1 violeta final
    """
    s = promo_get(request.session)

    base = {
        "goles": s["goles"],
        "asist": s["asistencias"],
        "ataj":  s["atajadas"],
        "hab":   s["habilidad"],
        "def":   s["defensa"],
    }

    # Top para la Lottie (usando DISPLAY_TIPO)
    top_key = _pick_top_key(base)             # p.ej. "hab" o None
    top_label = DISPLAY_TIPO.get(top_key) if top_key else None   # "habilidad", "defensa", etc.
    top_lottie_url = _static_url("animaciones", f"{top_label}.json") if top_label else None

    elegibles = [k for k, v in base.items() if v > 0]
    catalog = _build_catalog()

    # 1) Hasta 2 slides de stats
    if len(elegibles) >= 2:
        mejoras = random.sample(elegibles, 2)
    elif len(elegibles) == 1:
        mejoras = [elegibles[0], random.choice([c for c in CATEGORIAS if c != elegibles[0]])]
    else:
        mejoras = []

    stories = []
    for idx, cat in enumerate(mejoras[:2]):
        video_url = _pick_any_video(catalog, cat)
        kind = CARD_KIND.get(cat, "total")
        valor = base.get(cat, 0)

        stories.append({
            "kind": "stat",
            "categoria": cat,
            "video_url": video_url,
            "card": {
                "kind": kind,
                "tipo": DISPLAY_TIPO[cat],
                "delta": valor,
                "nuevo": valor,
                "odo_id": f"odometer-{cat}-{idx}",
            }
        })

    # 2) RADAR (3ª) con Lottie superpuesta si hay top
    radar_url = _pick_radar_video() or _pick_any_video(catalog, random.choice(CATEGORIAS), fallback_radar=False)

    radar_story = {
        "kind": "radar",
        "video_url": radar_url,
        "caption": s.get("ultima_frase") or "Radar de jugadas destacadas",
    }

    if top_lottie_url:
        radar_story["lottie"] = {
            "url": top_lottie_url,
            "key": top_key,
            "label": top_label,
        }

    # Insertar como 3ª (índice 2) o al final si aún no hay 2 previas
    insert_idx = 2 if len(stories) >= 2 else len(stories)
    stories.insert(insert_idx, radar_story)

    # 3) Pantalla violeta final
    stories.append({
        "kind": "violet",
        "duration": 20000,
    })

    return render(request, "stories/promo_demo_stories.html", {
        "stories": stories,
        "cta": {
            "logo": "/static/img/ticas_logo.svg",
            "frase": "Donde cada partido cuenta",
            "texto": "Ya disponible en Web y Android",
            "btn_texto": "Probar Ticas",
            "btn_url": "/registro/",
        },
        "ocultar_navbar": True,
    })


@require_GET
def debug_lottie(request):
    """
    /debug/lottie?file=animaciones/defensa.json&renderer=canvas&loop=0
    """
    file_rel = request.GET.get("file", "animaciones/defensa.json").lstrip("/")
    renderer = request.GET.get("renderer", "svg").lower()  # svg | canvas
    loop = request.GET.get("loop", "1")  # "1" o "0"

    lottie_url = f"{settings.STATIC_URL.rstrip('/')}/{file_rel}"
    ctx = {
        "lottie_url": lottie_url,
        "renderer": renderer if renderer in {"svg","canvas"} else "svg",
        "loop": loop == "1",
        "static_url": settings.STATIC_URL.rstrip("/"),
        "file_rel": file_rel,
    }
    return render(request, "stories/debug_lottie.html", ctx)