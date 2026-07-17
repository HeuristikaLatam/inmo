"""
indices.py — inmo.heuristika.pro
Descarga los datos que necesita el tablero inmobiliario:
  - mindicador.cl (sin API key): UF, dólar, TPM
  - api.cmfchile.cl (requiere CMF_API_KEY): tasas hipotecarias (TIP, tipo
    Hipotecario UF) para calcular un promedio de mercado
  - Titulares de economía/inmobiliario vía RSS (Diario Financiero,
    Cooperativa, BioBioChile), filtrados por palabras clave relevantes

Además mantiene un historial diario liviano (un punto por día, sin
duplicar si se corre más de una vez el mismo día) para poder calcular el
"dato remarcable" del día — el indicador que más se alejó de su propio
comportamiento reciente, no necesariamente el que más subió o bajó.

Escribe todo a datos.json, que luego consume build_site.py.

Uso local:
    export CMF_API_KEY="tu_api_key"
    python3 indices.py
"""

import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

CMF_API_KEY = os.environ.get("CMF_API_KEY", "")
HOY = datetime.now().strftime("%Y-%m-%d")
ARCHIVO_DATOS = "datos.json"

# Tipos de operación TIP relevantes para crédito hipotecario.
# Ver documentación: https://api.cmfchile.cl/documentacion/TIP.html
TIPOS_HIPOTECARIO = {
    14: "Hipotecario UF (>1 año, sobre 2.000 UF)",
    24: "Hipotecario UF (>1 año, hasta 2.000 UF)",
}

RSS_FEEDS = [
    ("Diario Financiero", "https://www.df.cl/noticias/site/list/port/rss.xml"),
    ("Cooperativa", "https://www.cooperativa.cl/noticias/site/tax/port/all/rss_6___1.xml"),
    ("BioBioChile", "https://www.biobiochile.cl/static/feed-rss"),
]

PALABRAS_CLAVE = [
    "uf", "tasa", "dividendo", "hipotecari", "inmobiliari", "crédito",
    "credito", "vivienda", "arriendo", "construcción", "construccion",
    "banco central", "tpm", "dólar", "dolar", "propiedad", "subsidio",
]

MIN_TITULARES = 6
MAX_TITULARES = 12


def http_get(url, timeout=25, reintentos=4):
    """GET con reintentos: las APIs públicas a veces se cuelgan, y este
    script corre solo, sin nadie mirando."""
    ultimo_error = None
    for intento in range(1, reintentos + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            ultimo_error = e
            if intento < reintentos:
                print(f"  aviso: intento {intento} falló ({e}), reintentando...")
                time.sleep(2 * intento)
    raise ultimo_error


def http_get_json(url, timeout=25, reintentos=4):
    return json.loads(http_get(url, timeout=timeout, reintentos=reintentos).decode("utf-8"))


# ---------------------------------------------------------------------------
# mindicador.cl
# ---------------------------------------------------------------------------

def get_mindicador_actual():
    print("Descargando UF, dólar y TPM de mindicador.cl ...")
    data = http_get_json("https://mindicador.cl/api")
    out = {}
    for campo in ("uf", "dolar", "tpm"):
        if campo in data:
            out[campo] = {
                "nombre": data[campo]["nombre"],
                "unidad": data[campo]["unidad_medida"],
                "valor": data[campo]["valor"],
                "fecha": data[campo]["fecha"],
            }
    return out


# ---------------------------------------------------------------------------
# api.cmfchile.cl (TIP hipotecario)
# ---------------------------------------------------------------------------

def _extraer_items(data, clave, recurso):
    bloque = data.get(clave, [])
    if isinstance(bloque, list):
        return bloque
    if isinstance(bloque, dict):
        sub = bloque.get(recurso.upper(), [])
        return sub if isinstance(sub, list) else ([sub] if sub else [])
    return []


def get_tasa_hipotecaria_promedio():
    """Trae el TIP del año actual, filtra a los tipos hipotecarios y
    devuelve el promedio del dato más reciente de cada tipo."""
    if not CMF_API_KEY:
        print("AVISO: no hay CMF_API_KEY definida, se omite tasa hipotecaria.")
        return None

    print("Descargando tasas hipotecarias (TIP) de la CMF ...")
    anio = datetime.now().year
    url = (
        f"https://api.cmfchile.cl/api-sbifv3/recursos_api/tip/{anio}"
        f"?apikey={CMF_API_KEY}&formato=json"
    )
    try:
        data = http_get_json(url)
    except Exception as e:
        print(f"  error al traer TIP: {e}")
        return None

    items = _extraer_items(data, "TIPs", "tip")
    ultimo_por_tipo = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            tipo = int(item.get("Tipo"))
        except (TypeError, ValueError):
            continue
        if tipo not in TIPOS_HIPOTECARIO:
            continue
        try:
            valor = float(item.get("Valor"))
        except (TypeError, ValueError):
            continue
        fecha = item.get("Fecha")
        if not fecha:
            continue
        actual = ultimo_por_tipo.get(tipo)
        if not actual or fecha > actual["fecha"]:
            ultimo_por_tipo[tipo] = {"fecha": fecha, "valor": valor}

    if not ultimo_por_tipo:
        print("  aviso: no se encontraron datos de TIP hipotecario para este año.")
        return None

    valores = [v["valor"] for v in ultimo_por_tipo.values()]
    fecha_mas_reciente = max(v["fecha"] for v in ultimo_por_tipo.values())
    promedio = round(sum(valores) / len(valores), 2)
    detalle = {
        TIPOS_HIPOTECARIO[t]: v["valor"] for t, v in ultimo_por_tipo.items()
    }
    return {
        "nombre": "Tasa hipotecaria promedio (TIP)",
        "unidad": "Porcentaje",
        "valor": promedio,
        "fecha": fecha_mas_reciente,
        "detalle": detalle,
    }


# ---------------------------------------------------------------------------
# Titulares RSS
# ---------------------------------------------------------------------------

def _texto_relevante(titulo):
    t = titulo.lower()
    return any(palabra in t for palabra in PALABRAS_CLAVE)


def _parsear_rss(xml_bytes, fuente):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"  aviso: no se pudo parsear RSS de {fuente}: {e}")
        return items

    for item in root.iter("item"):
        titulo_el = item.find("title")
        link_el = item.find("link")
        fecha_el = item.find("pubDate")
        titulo = (titulo_el.text or "").strip() if titulo_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        fecha = (fecha_el.text or "").strip() if fecha_el is not None else ""
        if not titulo or not link:
            continue
        items.append({"titulo": titulo, "link": link, "fecha": fecha, "fuente": fuente})
    return items


def get_titulares():
    print("Descargando titulares RSS (Diario Financiero, Cooperativa, BioBioChile) ...")
    todos = []
    for fuente, url in RSS_FEEDS:
        try:
            crudo = http_get(url)
        except Exception as e:
            print(f"  aviso: no se pudo descargar RSS de {fuente}: {e}")
            continue
        todos.extend(_parsear_rss(crudo, fuente))
        time.sleep(0.2)

    relevantes = [it for it in todos if _texto_relevante(it["titulo"])]

    # Si el filtro por palabras clave dejó pocos titulares (o ninguno),
    # completamos con los más recientes de todas las fuentes, sin repetir,
    # hasta llegar a un mínimo razonable en vez de mostrar una sección casi vacía.
    if len(relevantes) < MIN_TITULARES:
        links_ya_incluidos = {it["link"] for it in relevantes}
        extra = [it for it in todos if it["link"] not in links_ya_incluidos]
        faltan = MIN_TITULARES - len(relevantes)
        relevantes = relevantes + extra[:faltan]

    return relevantes[:MAX_TITULARES]


# ---------------------------------------------------------------------------
# Historial diario + "dato remarcable" (z-score simplificado)
# ---------------------------------------------------------------------------

def _cambio_pct(actual, anterior):
    if anterior in (None, 0):
        return None
    return (actual - anterior) / abs(anterior) * 100


def actualizar_historial(historial, macro, tasa_hipotecaria):
    """Agrega/reemplaza el punto de hoy para cada indicador. `historial`
    es un dict indicador -> lista de {"fecha": ..., "valor": ...}."""
    valores_hoy = {}
    if macro.get("uf"):
        valores_hoy["uf"] = macro["uf"]["valor"]
    if macro.get("dolar"):
        valores_hoy["dolar"] = macro["dolar"]["valor"]
    if macro.get("tpm"):
        valores_hoy["tpm"] = macro["tpm"]["valor"]
    if tasa_hipotecaria:
        valores_hoy["tasa_hipotecaria"] = tasa_hipotecaria["valor"]

    for indicador, valor in valores_hoy.items():
        serie = historial.setdefault(indicador, [])
        if serie and serie[-1]["fecha"] == HOY:
            serie[-1]["valor"] = valor
        else:
            serie.append({"fecha": HOY, "valor": valor})
        # nos quedamos con los últimos 90 puntos, no necesitamos más para
        # calcular volatilidad reciente
        historial[indicador] = serie[-90:]

    return historial


NOMBRES_INDICADOR = {
    "uf": "la UF",
    "dolar": "el dólar",
    "tpm": "la TPM",
    "tasa_hipotecaria": "la tasa hipotecaria promedio",
}


def calcular_dato_remarcable(historial):
    """Para cada indicador con al menos 2 puntos, calcula el cambio % del
    último punto. Si hay historial suficiente (>=5 cambios previos),
    compara ese cambio contra la volatilidad típica del indicador
    (z-score). Si no, usa directamente el cambio % absoluto como score.
    Devuelve el indicador con el score más alto, o None si no hay datos
    suficientes todavía."""
    candidatos = []
    for indicador, serie in historial.items():
        if len(serie) < 2:
            continue
        cambios = []
        for i in range(1, len(serie)):
            c = _cambio_pct(serie[i]["valor"], serie[i - 1]["valor"])
            if c is not None:
                cambios.append(c)
        if not cambios:
            continue
        ultimo_cambio = cambios[-1]

        if len(cambios) >= 6:
            previos = cambios[:-1]
            media = statistics.mean(previos)
            desv = statistics.pstdev(previos)
            score = abs(ultimo_cambio - media) / desv if desv > 1e-9 else abs(ultimo_cambio)
            modo = "zscore"
        else:
            score = abs(ultimo_cambio)
            modo = "cambio_pct"

        candidatos.append({
            "indicador": indicador,
            "nombre": NOMBRES_INDICADOR.get(indicador, indicador),
            "cambio_pct": round(ultimo_cambio, 2),
            "score": round(score, 3),
            "modo": modo,
            "valor_actual": serie[-1]["valor"],
            "fecha": serie[-1]["fecha"],
        })

    if not candidatos:
        return None

    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos[0]


def main():
    datos_previos = {}
    if os.path.exists(ARCHIVO_DATOS):
        try:
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
                datos_previos = json.load(f)
        except Exception as e:
            print(f"aviso: no se pudo leer {ARCHIVO_DATOS} previo ({e}), se parte de cero.")

    historial = datos_previos.get("historial", {})

    macro = get_mindicador_actual()
    tasa_hipotecaria = get_tasa_hipotecaria_promedio()
    titulares = get_titulares()

    historial = actualizar_historial(historial, macro, tasa_hipotecaria)
    dato_remarcable = calcular_dato_remarcable(historial)

    salida = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "macro": macro,
        "tasa_hipotecaria": tasa_hipotecaria,
        "titulares": titulares,
        "historial": historial,
        "dato_remarcable": dato_remarcable,
    }

    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"OK -> {ARCHIVO_DATOS}")


if __name__ == "__main__":
    main()
