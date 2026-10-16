#!/usr/bin/env python3
"""
Busca empresas parecidas a Pilou (fintech de inversión, cercana y educativa,
enfocada en mujeres o principiantes, en Latinoamérica) y las guarda en CSV y Excel.

Cómo funciona:
  1. Lanza varias búsquedas en DuckDuckGo (no necesita clave de API).
  2. Se queda con un resultado por dominio y descarta medios, redes sociales y directorios.
  3. Visita la web de cada empresa y lee título, descripción, Instagram, LinkedIn y email.
  4. Puntúa cada empresa según cuánto se parece a Pilou y ordena de mayor a menor.

Uso:
  pip install requests beautifulsoup4 openpyxl ddgs
  python buscar_empresas_como_pilou.py
  python buscar_empresas_como_pilou.py --resultados 20 --salida mis_empresas
  python buscar_empresas_como_pilou.py --busqueda "app de ahorro para jóvenes Chile"
"""

import argparse
import csv
import re
import sys
import time
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Búsquedas por defecto. Añade o quita las que quieras.
BUSQUEDAS = [
    "plataforma de inversión para mujeres México",
    "fintech inversión mujeres Latinoamérica",
    "app para invertir para principiantes México",
    "asesor de inversiones independiente CNBV plataforma digital",
    "roboadvisor México carteras diversificadas",
    "plataforma de inversión educación financiera Colombia",
    "plataforma de inversión para principiantes Chile",
    "plataforma de inversión para principiantes Perú",
    "fintech inversión Argentina principiantes",
    "inversión como prestación para empleados México fintech",
    "educación financiera para mujeres invertir startup",
    "fintech ahorro e inversión mujeres emprendedoras",
]

# Empresas parecidas que ya aparecen en prensa; se buscan por nombre para encontrar su web.
SEMILLAS = [
    "Fintual", "Flink app inversión", "Kuspit", "GBM+ inversión", "Cetesdirecto",
    "Mujer Financiera Argentina", "Morado fintech Colombia", "Tappoyo Perú",
    "Monet Yo soy M Colombia", "Microwd",
]

# Dominios que no son empresas candidatas (medios, redes, directorios, la propia Pilou).
EXCLUIR = {
    "pilou.io", "piloufin.com", "wikipedia.org", "linkedin.com", "facebook.com",
    "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com",
    "forbes.com.mx", "forbes.com", "rankia.mx", "rankia.co", "rankia.cl", "rankia.com",
    "expansion.mx", "elfinanciero.com.mx", "eleconomista.com.mx", "eleconomista.es",
    "medium.com", "crunchbase.com", "vc4a.com", "finnosummit.com", "emprendedor.com",
    "google.com", "apple.com", "play.google.com", "reddit.com", "quora.com",
    "mercadopago.com.mx", "financera.mx", "gob.mx", "condusef.gob.mx", "glassdoor.com",
    "indeed.com", "amazon.com", "bloomberglinea.com", "contxto.com", "techcrunch.com",
    "investing.com", "brokerchooser.com", "finect.com", "fastercapital.com", "grokipedia.com",
    "guiadefondos.com", "musamagazine.us", "editorialge.com", "hotbook.mx", "mamaejecutiva.net",
    "segundoenfoque.com", "fintechfuturo.com", "terra2us.com", "empremexico.com",
    "latamfintech.co", "colombiafintech.co", "fintechmexico.org", "wefintech.org",
    "mujeresfintech.co", "descubre.vc", "aden.org", "nafin.com", "colsubsidio.com",
}

# Partes del dominio que indican medio, universidad, gobierno o comparador.
EXCLUIR_PATRON = re.compile(
    r"(^|\.)(rankia|wikipedia|investing|forbes|expansion|elpais|infobae|eleconomista)\.|"
    r"\.(edu|gob|gov)(\.|$)|\.edu\.[a-z]{2}$|(^|\.)(blog|news|noticias|revista|magazine)")

# Rasgos de Pilou y su peso en la puntuación. Cada grupo suma una vez.
RASGOS = {
    "inversion":   (3, ["invertir", "inversión", "inversion", "portafolio", "cartera",
                        "fondos", "etf", "rendimiento", "patrimonio", "acciones"]),
    "ahorro":      (1, ["ahorro", "ahorrar", "metas", "objetivos financieros"]),
    "mujeres":     (3, ["mujeres", "para ellas", "femenin", "women", "mujer"]),
    "principiantes": (2, ["principiante", "primera vez", "desde cero", "sin experiencia",
                          "nunca has invertido", "empieza a invertir"]),
    "educacion":   (2, ["educación financiera", "educacion financiera", "aprende",
                        "talleres", "cursos", "blog", "comunidad"]),
    "asesoria":    (2, ["asesor", "asesoría", "asesoria", "experto", "acompañamiento"]),
    "empresas_b2b": (1, ["prestación", "prestacion", "empleados", "colaboradores",
                         "beneficio para empleados", "para empresas"]),
    "regulada":    (1, ["cnbv", "regulad", "supervisad", "superintendencia", "cmf", "cnv", "smv"]),
    "latam":       (1, ["méxico", "mexico", "colombia", "chile", "perú", "peru",
                        "argentina", "latinoamérica", "latam", "ecuador", "uruguay"]),
    "digital":     (1, ["app", "plataforma", "100% digital", "en línea", "online", "fintech"]),
}
PUNTOS_MAX = sum(p for p, _ in RASGOS.values())

PAISES = ["México", "Colombia", "Chile", "Perú", "Argentina", "Ecuador", "Uruguay",
          "España", "Estados Unidos", "Brasil"]


def dominio(url):
    host = urlparse(url).netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def excluido(dom):
    return bool(EXCLUIR_PATRON.search(dom)) or any(dom == d or dom.endswith("." + d) for d in EXCLUIR)


# --------------------------------------------------------------------------- búsqueda

def buscar_ddgs(consulta, n):
    from ddgs import DDGS  # pip install ddgs
    with DDGS() as d:
        for r in d.text(consulta, region="mx-es", max_results=n):
            yield {"url": r.get("href", ""), "titulo": r.get("title", ""),
                   "fragmento": r.get("body", "")}


def buscar_html(consulta, n):
    """Alternativa sin librería: la versión HTML de DuckDuckGo."""
    r = requests.post("https://html.duckduckgo.com/html/", data={"q": consulta},
                      headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for res in soup.select(".result")[:n]:
        a = res.select_one("a.result__a")
        if not a:
            continue
        href = a.get("href", "")
        if "uddg=" in href:  # enlace de redirección de DuckDuckGo
            href = unquote(parse_qs(urlparse(href).query).get("uddg", [href])[0])
        frag = res.select_one(".result__snippet")
        yield {"url": href, "titulo": a.get_text(" ", strip=True),
               "fragmento": frag.get_text(" ", strip=True) if frag else ""}


def buscar(consulta, n):
    try:
        return list(buscar_ddgs(consulta, n))
    except ImportError:
        pass
    except Exception as e:
        print(f"  ddgs falló ({e}); pruebo la versión HTML", file=sys.stderr)
    try:
        return list(buscar_html(consulta, n))
    except Exception as e:
        print(f"  búsqueda fallida: {e}", file=sys.stderr)
        return []


# --------------------------------------------------------------------------- análisis

def leer_web(url):
    """Descarga la portada de la empresa y extrae los datos útiles."""
    raiz = f"{urlparse(url).scheme or 'https'}://{urlparse(url).netloc}/"
    try:
        r = requests.get(raiz, headers={"User-Agent": UA}, timeout=15)
        r.raise_for_status()
        if "charset" not in r.headers.get("content-type", "").lower():
            r.encoding = r.apparent_encoding  # evita textos tipo "AsesorÃ­a"
    except Exception as e:
        return {"web": raiz, "error": str(e)[:120]}
    return analizar_html(r.text, raiz)


def analizar_html(html, raiz):
    soup = BeautifulSoup(html, "html.parser")
    titulo = soup.title.get_text(strip=True) if soup.title else ""
    desc = ""
    for attrs in ({"name": "description"}, {"property": "og:description"}):
        m = soup.find("meta", attrs=attrs)
        if m and m.get("content"):
            desc = m["content"].strip()
            break
    enlaces = [urljoin(raiz, a["href"]) for a in soup.find_all("a", href=True)]

    def primero(patron):
        return next((u for u in enlaces if re.search(patron, u, re.I)), "")

    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    texto = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    emails = sorted({e.rstrip(".") for e in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html)})
    emails = [e for e in emails if not e.lower().endswith((".png", ".jpg", ".webp", ".svg"))]
    return {
        "web": raiz,
        "titulo_web": titulo[:150],
        "descripcion": desc[:300],
        "instagram": primero(r"instagram\.com/[^/?#]+"),
        "linkedin": primero(r"linkedin\.com/company/"),
        "email": ", ".join(emails[:3]),
        "texto": texto[:20000],
        "error": "",
    }


def puntuar(texto):
    t = texto.lower()
    puntos, rasgos = 0, []
    for nombre, (peso, palabras) in RASGOS.items():
        if any(p in t for p in palabras):
            puntos += peso
            rasgos.append(nombre)
    return round(100 * puntos / PUNTOS_MAX), rasgos


def detectar_pais(texto):
    t = texto.lower()
    cuenta = {p: t.count(p.lower()) + t.count(p.lower().replace("é", "e").replace("ú", "u"))
              for p in PAISES}
    mejor = max(cuenta, key=cuenta.get)
    return mejor if cuenta[mejor] else ""


# --------------------------------------------------------------------------- salida

COLUMNAS = ["parecido_pilou", "empresa", "web", "pais_probable", "rasgos",
            "descripcion", "instagram", "linkedin", "email", "encontrada_con", "error"]


def guardar(filas, base):
    import os
    os.makedirs(os.path.dirname(base) or ".", exist_ok=True)
    with open(base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        print("openpyxl no está instalado; solo se guarda el CSV", file=sys.stderr)
        return [base + ".csv"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Empresas como Pilou"
    ws.append(COLUMNAS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for fila in filas:
        ws.append([fila.get(c, "") for c in COLUMNAS])
    anchos = {"A": 14, "B": 32, "C": 34, "D": 14, "E": 40, "F": 60,
              "G": 34, "H": 34, "I": 30, "J": 40, "K": 20}
    for col, ancho in anchos.items():
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(base + ".xlsx")
    return [base + ".csv", base + ".xlsx"]


# --------------------------------------------------------------------------- principal

def main():
    ap = argparse.ArgumentParser(description="Encuentra empresas parecidas a Pilou")
    ap.add_argument("--resultados", type=int, default=10,
                    help="resultados por búsqueda (por defecto 10)")
    ap.add_argument("--busqueda", action="append",
                    help="búsqueda propia; se puede repetir. Sustituye a las de por defecto")
    ap.add_argument("--sin-semillas", action="store_true",
                    help="no buscar las empresas parecidas ya conocidas")
    ap.add_argument("--minimo", type=int, default=40,
                    help="parecido mínimo (0-100) para entrar en la lista")
    ap.add_argument("--salida", default="resultados/empresas_como_pilou",
                    help="nombre base de los ficheros de salida")
    args = ap.parse_args()

    consultas = args.busqueda or BUSQUEDAS
    if not args.sin_semillas and not args.busqueda:
        consultas = consultas + SEMILLAS

    candidatos = {}
    for i, q in enumerate(consultas, 1):
        print(f"[{i}/{len(consultas)}] {q}")
        for r in buscar(q, args.resultados):
            dom = dominio(r["url"])
            if not dom or excluido(dom):
                continue
            c = candidatos.setdefault(dom, {**r, "encontrada_con": []})
            c["encontrada_con"].append(q)
        time.sleep(1.5)  # para no saturar el buscador

    print(f"\n{len(candidatos)} webs candidatas. Visitándolas...")
    filas = []
    for i, (dom, c) in enumerate(candidatos.items(), 1):
        print(f"  ({i}/{len(candidatos)}) {dom}")
        info = leer_web(c["url"])
        texto = " ".join([c["titulo"], c["fragmento"], info.get("titulo_web", ""),
                          info.get("descripcion", ""), info.get("texto", "")])
        nota, rasgos = puntuar(texto)
        if nota < args.minimo:
            continue
        filas.append({
            "parecido_pilou": nota,
            "empresa": info.get("titulo_web") or c["titulo"],
            "web": info.get("web", ""),
            "pais_probable": detectar_pais(texto),
            "rasgos": ", ".join(rasgos),
            "descripcion": info.get("descripcion") or c["fragmento"],
            "instagram": info.get("instagram", ""),
            "linkedin": info.get("linkedin", ""),
            "email": info.get("email", ""),
            "encontrada_con": " | ".join(c["encontrada_con"][:3]),
            "error": info.get("error", ""),
        })

    filas.sort(key=lambda f: f["parecido_pilou"], reverse=True)
    ficheros = guardar(filas, args.salida)
    print(f"\n{len(filas)} empresas guardadas en: {', '.join(ficheros)}")


if __name__ == "__main__":
    main()
