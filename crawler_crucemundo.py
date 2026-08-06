import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ===============================
# CONFIGURACIÓN
# ===============================

DOMAIN = "https://crucemundo.es"

SITEMAP = DOMAIN + "/sitemap.xml"

FLOTA = DOMAIN + "/flota-cruceros-fluviales"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"

SEED_URLS = [
    "https://www.crucemundo.es/flota-cruceros-fluviales/",
    "https://www.crucemundo.es/crucero/",
    "https://www.crucemundo.es/reservarcrucero/",
    "https://www.crucemundo.es/destinos/",
    "https://crucemundo.es/tuviaje/",
    "https://crucemundo.es/downloads/",
    "https://crucemundo.es/noticiascrucemundo/",
    "https://crucemundo.es/contacto/"
]

# Todo lo que haya ANTES de este texto en el Google Doc se conserva tal cual
# (escríbelo tú a mano una vez). Todo lo que haya DESPUÉS lo sobrescribe el crawler.
MARCADOR = "FIN INFORMACION MANUAL"

# Etiquetas HTML que casi siempre son ruido (menús, footer, cookies, formularios...)
# y no aportan información útil sobre cruceros/destinos.
ETIQUETAS_A_DESCARTAR = [
    "script", "style", "noscript",
    "nav", "header", "footer",
    "form", "button", "iframe", "svg",
    "aside",
]

# Longitud mínima de una línea para conservarla. Filtra restos sueltos tipo
# "Inicio", "Menú", "Aceptar", "×", etc. que quedan tras limpiar el HTML.
LONGITUD_MINIMA_LINEA = 3


# ===============================
# GOOGLE DOCS
# ===============================

def _extraer_texto_y_runs(doc):
    """
    Recorre la estructura del documento y devuelve:
    - full_text: todo el texto concatenado, tal y como lo vería un humano
    - runs: lista de (offset_en_full_text, indice_real_en_el_doc, texto_del_run)
      necesaria para poder traducir una posición dentro de full_text a un
      índice válido para la API de Google Docs (que no trabaja con strings,
      sino con índices dentro de la estructura del documento).
    """

    full_text = ""
    runs = []

    for element in doc["body"]["content"]:

        paragraph = element.get("paragraph")

        if not paragraph:
            continue

        for el in paragraph.get("elements", []):

            text_run = el.get("textRun")

            if not text_run:
                continue

            contenido = text_run.get("content", "")

            runs.append((len(full_text), el["startIndex"], contenido))

            full_text += contenido

    return full_text, runs


def _indice_doc_desde_offset(runs, offset):
    """Traduce un offset dentro de full_text al índice real del documento."""

    for run_offset, doc_start, contenido in runs:

        run_len = len(contenido)

        if run_offset <= offset <= run_offset + run_len:
            return doc_start + (offset - run_offset)

    # Si no se encuentra (no debería pasar), usamos el final del último run.
    if runs:
        run_offset, doc_start, contenido = runs[-1]
        return doc_start + len(contenido)

    return 1


def escribir_google_doc(texto):

    scopes = [
        "https://www.googleapis.com/auth/documents"
    ]

    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_KEY,
        scopes=scopes
    )

    service = build(
        "docs",
        "v1",
        credentials=creds
    )

    doc = service.documents().get(
        documentId=DOCUMENT_ID
    ).execute()

    full_text, runs = _extraer_texto_y_runs(doc)

    end_index = doc["body"]["content"][-1]["endIndex"]

    marcador_pos = full_text.find(MARCADOR)

    requests_body = []

    if marcador_pos == -1:

        # El marcador no está en el documento todavía: no tocamos nada de lo
        # que ya hay (por seguridad, para no borrar info manual sin querer)
        # y añadimos el marcador + el contenido nuevo al final.
        print(
            f"Aviso: no se encontró '{MARCADOR}' en el documento. "
            "Se añade el marcador y el contenido nuevo al final, sin borrar nada existente."
        )

        insert_index = end_index - 1

        requests_body.append({
            "insertText": {
                "location": {
                    "index": insert_index
                },
                "text": f"\n\n{MARCADOR}\n\n{texto}"
            }
        })

    else:

        marcador_fin_offset = marcador_pos + len(MARCADOR)

        marcador_fin_doc_index = _indice_doc_desde_offset(runs, marcador_fin_offset)

        # Borra todo lo que hay después del marcador (si hay algo que borrar)
        if end_index - 1 > marcador_fin_doc_index:

            requests_body.append({
                "deleteContentRange": {
                    "range": {
                        "startIndex": marcador_fin_doc_index,
                        "endIndex": end_index - 1
                    }
                }
            })

        # Inserta el contenido nuevo justo después del marcador
        requests_body.append({
            "insertText": {
                "location": {
                    "index": marcador_fin_doc_index
                },
                "text": f"\n\n{texto}"
            }
        })

    service.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={
            "requests": requests_body
        }
    ).execute()


# ===============================
# LIMPIEZA TEXTO
# ===============================

def limpiar(html):
    """
    Extrae el texto útil de una página, descartando menús, cabecera, pie de
    página, formularios y otros bloques que se repiten en todas las páginas
    del sitio y no aportan información real sobre cruceros/destinos.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for etiqueta in ETIQUETAS_A_DESCARTAR:
        for x in soup.find_all(etiqueta):
            x.extract()

    # Obtenemos el texto línea a línea (en vez de todo pegado con espacios)
    # para poder filtrar líneas basura y quitar duplicados fácilmente.
    lineas_crudas = soup.get_text("\n").split("\n")

    lineas_limpias = []
    vistas = set()

    for linea in lineas_crudas:

        linea = re.sub(r"\s+", " ", linea).strip()

        if len(linea) < LONGITUD_MINIMA_LINEA:
            continue

        # Evita repetir la misma línea varias veces seguidas en la misma
        # página (típico de menús desplegables duplicados en HTML).
        if linea in vistas:
            continue

        vistas.add(linea)
        lineas_limpias.append(linea)

    return " ".join(lineas_limpias)


# ===============================
# SITEMAP
# ===============================

def leer_sitemap():

    urls = []

    r = requests.get(
        SITEMAP,
        timeout=30
    )

    locs = re.findall(
        r"<loc>(.*?)</loc>",
        r.text
    )

    for u in locs:

        # evitar PDF que rompe Playwright
        if "pdfcrucerodisp.php" in u:
            continue

        urls.append(u)

    return urls


# ===============================
# EXTRAER BARCOS
# ===============================

async def sacar_barcos(page):

    await page.goto(
        FLOTA,
        wait_until="networkidle"
    )

    links = await page.eval_on_selector_all(
        "a",
        "els => els.map(e => e.href)"
    )

    barcos = []

    for l in links:

        if "/barcoscrucemundo/" in l:

            if l not in barcos:
                barcos.append(l)

    return barcos


# ===============================
# EXTRAER LINKS DE SEMILLAS
# ===============================

async def extraer_links(page, url):

    encontrados = []

    try:

        await page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        links = await page.eval_on_selector_all(
            "a",
            "els => els.map(e => e.href)"
        )

        for l in links:

            if not l:
                continue

            if "crucemundo.es" not in l:
                continue

            encontrados.append(l)

    except Exception as e:

        print(
            "ERROR LINKS",
            url,
            e
        )

    return encontrados


# ===============================
# EXTRAER PAGINA
# ===============================

async def extraer_pagina(page, url):

    try:

        try:

            await page.goto(
                url,
                wait_until="networkidle",
                timeout=60000
            )

        except Exception:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

        html = await page.content()

        titulo = await page.title()

        texto = limpiar(html)

        return f"""

==============================
URL
==============================

{url}

==============================
TITULO
==============================

{titulo}

==============================
CONTENIDO
==============================

{texto[:6000]}

"""

    except Exception as e:

        print(
            "ERROR",
            url,
            e
        )

        return ""


# ===============================
# PROCESO PRINCIPAL
# ===============================

async def crawler():

    salida = []

    urls = leer_sitemap()

    urls.extend(SEED_URLS)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        print(
            "Extrayendo flota..."
        )

        barcos = await sacar_barcos(page)

        print(
            "Barcos encontrados:",
            len(barcos)
        )

        urls.extend(barcos)

        for seed in SEED_URLS:

            print(
                "Explorando:",
                seed
            )

            nuevos = await extraer_links(
                page,
                seed
            )

            urls.extend(nuevos)

        urls = list(
            dict.fromkeys(urls)
        )

        urls = [
            u for u in urls
            if (
                u in SEED_URLS
                or "/crucero/" in u
                or "/reservarcrucero/" in u
                or "/barcoscrucemundo/" in u
                or "/flota-cruceros-fluviales/" in u
                or "/destinos/" in u
            )
        ]

        print(
            "URLs finales:",
            len(urls)
        )

        for i, url in enumerate(urls):

            print(
                i + 1,
                "/",
                len(urls),
                url
            )

            texto = await extraer_pagina(
                page,
                url
            )

            salida.append(texto)

        await browser.close()

    documento = "\n".join(
        salida
    )

    escribir_google_doc(
        documento
    )

    print(
        "FINALIZADO"
    )


if __name__ == "__main__":

    asyncio.run(
        crawler()
    )
