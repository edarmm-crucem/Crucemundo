import argparse
import asyncio
import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI


# ===============================
# CONFIGURACIÓN
# ===============================

DOMAIN = "https://crucemundo.es"

SITEMAP = DOMAIN + "/sitemap.xml"

FLOTA = DOMAIN + "/flota-cruceros-fluviales"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"

# Se usan para DESCUBRIR enlaces. Lo que se guarda en el documento lo decide
# url_valida() más abajo.
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

# Páginas que se visitan para descubrir enlaces pero NO se guardan:
# - reservarcrucero: casi todo cookies, con precios "desde" que mezclan barcos
# - noticiascrucemundo: blog de 2020 (covid, recetas)
# - contacto: horarios que contradicen el bloque manual (el contacto va en el manual)
RUTAS_EXCLUIDAS = ["/reservarcrucero/", "/noticiascrucemundo/", "/contacto/"]

# Etiquetas HTML que casi siempre son ruido (menús, footer, cookies, formularios...)
# y no aportan información útil sobre cruceros/destinos.
ETIQUETAS_A_DESCARTAR = [
    "script", "style", "noscript",
    "nav", "header", "footer",
    "form", "button", "iframe", "svg",
    "aside",
]

# Bloques del banner de cookies: se eliminan por id/clase. El límite de tamaño
# evita borrar por error un contenedor grande que solo "mencione" cookies.
PATRON_COOKIES = re.compile(r"cookie|consent|cmp|iabv2|onetrust|cybot|gdpr|rgpd", re.I)
MAX_TEXTO_BLOQUE_COOKIES = 8000

# Red de seguridad: desde estas marcas hasta el final de la página es banner de
# cookies (así venía en el documento actual: siempre al final).
MARCAS_FIN_CONTENIDO = ["Powered by CookiePage"]

# Longitud mínima de una línea para conservarla. Filtra restos sueltos tipo
# "Inicio", "Menú", "Aceptar", "×", etc. que quedan tras limpiar el HTML.
LONGITUD_MINIMA_LINEA = 3

# Tope de seguridad por página (antes se cortaba a 6000 y se perdían itinerarios,
# barcos y alojamiento). Una ficha completa ronda los 10.000-15.000 caracteres.
MAX_CARACTERES_PAGINA = 60000

# Fecha de hoy, para descartar salidas pasadas.
HOY = datetime.now(ZoneInfo("Europe/Madrid")).date()

# Datos para subir el contenido a un Vector Store de OpenAI (búsqueda semántica).
# El Vector Store se crea UNA sola vez a mano; aquí solo se actualiza su contenido.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "")

# Avisos de calidad de datos detectados durante la ejecución (se imprimen al final).
AVISOS = []


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
    """
    Escribe el contenido del crawler después del marcador y devuelve la parte
    manual (todo lo que hay hasta el marcador incluido), para poder subirla
    también al Vector Store. Si no hay marcador, devuelve "".
    """

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

    parte_manual = ""

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

        parte_manual = full_text[:marcador_fin_offset]

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

    return parte_manual


# ===============================
# OPENAI VECTOR STORE (búsqueda semántica)
# ===============================

def actualizar_vector_store(texto):
    """
    Sube el contenido actual al Vector Store de OpenAI, para que el bot pueda
    hacer búsqueda semántica (file_search).

    Orden seguro: primero SUBE el fichero nuevo y solo si queda procesado
    correctamente BORRA los antiguos. Así, si la subida falla, el bot sigue
    teniendo la versión anterior en vez de quedarse sin información.
    """

    if not OPENAI_API_KEY or not OPENAI_VECTOR_STORE_ID:
        print(
            "Aviso: falta OPENAI_API_KEY o OPENAI_VECTOR_STORE_ID; "
            "se omite la actualización del Vector Store."
        )
        return

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Ficheros que ya hay (se recorren todas las páginas del listado).
    antiguos = []

    try:
        for f in client.vector_stores.files.list(
            vector_store_id=OPENAI_VECTOR_STORE_ID
        ):
            antiguos.append(f.id)
    except Exception as e:
        print("Aviso: no se pudo listar los ficheros del Vector Store:", e)

    # Guarda el contenido en un fichero local temporal y lo sube
    ruta_temporal = "ia_bruto_actual.txt"

    with open(ruta_temporal, "w", encoding="utf-8") as fh:
        fh.write(texto)

    with open(ruta_temporal, "rb") as fh:
        nuevo = client.vector_stores.files.upload_and_poll(
            vector_store_id=OPENAI_VECTOR_STORE_ID,
            file=fh
        )

    if getattr(nuevo, "status", None) != "completed":
        print(
            "ATENCIÓN: el fichero nuevo no quedó 'completed' "
            f"(estado: {getattr(nuevo, 'status', None)}). "
            "No se borra la versión anterior."
        )
        return

    # Borra los antiguos, cada uno con su propio try para que un fallo
    # puntual no impida borrar el resto.
    borrados = 0
    fallidos = 0

    for fid in antiguos:

        if fid == nuevo.id:
            continue

        try:
            client.vector_stores.files.delete(
                vector_store_id=OPENAI_VECTOR_STORE_ID,
                file_id=fid
            )
            client.files.delete(fid)
            borrados += 1
        except Exception as e_individual:
            fallidos += 1
            print(f"Aviso: no se pudo borrar el fichero {fid}:", e_individual)

    print(f"Vector Store: {borrados} ficheros antiguos borrados, {fallidos} fallidos.")

    if fallidos > 0:
        print(
            "ATENCIÓN: quedaron ficheros antiguos sin borrar. "
            "Revisa manualmente en platform.openai.com/storage/files"
        )

    print("Vector Store actualizado con el contenido nuevo.")


# ===============================
# LIMPIEZA TEXTO
# ===============================

def limpiar(html):
    """
    Extrae el texto útil de una página, descartando menús, cabecera, pie de
    página, formularios, el banner de cookies y otros bloques que no aportan
    información real sobre cruceros/destinos.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for etiqueta in ETIQUETAS_A_DESCARTAR:
        for x in soup.find_all(etiqueta):
            x.extract()

    # Banner de cookies (por id/clase)
    candidatos = []

    for x in soup.find_all(True):

        if x.name in ("html", "body", "main"):
            continue

        ident = " ".join([x.get("id") or ""] + list(x.get("class") or []))

        if PATRON_COOKIES.search(ident) and len(x.get_text()) < MAX_TEXTO_BLOQUE_COOKIES:
            candidatos.append(x)

    for x in candidatos:
        if not x.decomposed:
            x.decompose()

    # Texto línea a línea para poder filtrar líneas basura.
    # IMPORTANTE: solo se eliminan repeticiones CONSECUTIVAS (menús duplicados).
    # Antes se eliminaba cualquier línea ya vista en la página, y eso borraba
    # fechas y precios repetidos de las tablas de salidas (por ejemplo la fecha
    # de llegada de una salida que es a la vez la fecha de salida de la
    # siguiente), que es lo que provocaba errores como confundir el día de
    # llegada con el de salida.
    lineas_limpias = []
    previa = None

    for linea in soup.get_text("\n").split("\n"):

        linea = re.sub(r"\s+", " ", linea).strip()

        if len(linea) < LONGITUD_MINIMA_LINEA:
            continue

        if linea == previa:
            continue

        previa = linea
        lineas_limpias.append(linea)

    texto = " ".join(lineas_limpias)

    # Red de seguridad: si el banner de cookies se coló, se corta desde su marca.
    for marca in MARCAS_FIN_CONTENIDO:
        i = texto.find(marca)
        if i != -1:
            texto = texto[:i].rstrip()

    return texto


# ===============================
# SALIDAS Y PRECIOS (tabla clara)
# ===============================

RE_TABLA_SALIDAS = re.compile(
    r"Salida Desde Llegada Precio Desde Reservar(.*?)(?=Duración|INCLUIDO)",
    re.S
)

RE_LISTA_FECHAS = re.compile(
    r"(?:Duración\s+)?Fechas de salida\s*(.*?)\s*(?=Ciudades)",
    re.S
)

RE_TOKEN = re.compile(
    r"\d{2}-\d{2}-\d{4}"          # fecha dd-mm-aaaa
    r"|\d+(?:[.,]\d+)?\s?€"       # precio
    r"|[^\W\d_][^\d€]*"           # palabras (puertos, RESERVAR, títulos...)
)


def _a_fecha(s):
    try:
        d, m, y = (int(p) for p in s.split("-"))
        return date(y, m, d)
    except Exception:
        return None


def _fmt(d):
    return d.strftime("%d-%m-%Y")


def _dias_del_crucero(texto):
    """Duración en días, tal como aparece en la cabecera ('Río Danubio 5 días 470€')."""
    m = re.search(r"(\d+)\s*días\s+\d", texto)
    return int(m.group(1)) if m else None


def _filas_de_la_tabla(bloque):
    """
    Convierte el texto plano de la tabla en filas {salida, llegada, precios, puertos}.
    Orden de las celdas en la web: salida, [puerto], llegada, [puerto], precio(s).
    Con dos precios, el primero es el normal y el segundo el de oferta.
    """

    filas = []
    fila = None

    for m in RE_TOKEN.finditer(bloque):

        tok = m.group(0).strip()

        if not tok:
            continue

        if re.fullmatch(r"\d{2}-\d{2}-\d{4}", tok):

            d = _a_fecha(tok)

            if d is None:
                continue

            if fila is None or fila["llegada"] is not None:
                fila = {
                    "salida": d, "llegada": None, "precios": [],
                    "p_salida": "", "p_llegada": ""
                }
                filas.append(fila)
            else:
                fila["llegada"] = d

        elif tok.endswith("€"):

            if fila is not None and fila["llegada"] is not None:
                fila["precios"].append(re.sub(r"\s+", "", tok))

        else:

            if fila is None or "RESERVAR" in tok.upper():
                continue

            if fila["llegada"] is None:
                if not fila["p_salida"]:
                    fila["p_salida"] = tok
            elif not fila["precios"] and not fila["p_llegada"]:
                fila["p_llegada"] = tok

    return filas


def normalizar_salidas(texto, url=""):
    """
    Sustituye la tabla de salidas aplanada por una línea clara por salida:
      • Salida 08-12-2026 → llegada 12-12-2026: precio 940.00€, oferta 470.00€
    y quita las salidas ya pasadas. Valida cada fila con la duración del
    crucero (llegada = salida + días - 1); si no cuadra, la marca para verificar
    en vez de darla por buena.
    """

    m = RE_TABLA_SALIDAS.search(texto)

    if not m:
        return filtrar_lista_fechas(texto)

    filas = _filas_de_la_tabla(m.group(1))

    if not filas:
        return filtrar_lista_fechas(texto)

    dias = _dias_del_crucero(texto)

    lineas = []

    for f in filas:

        if f["llegada"] is None:
            AVISOS.append(f"{url}: fila sin fecha de llegada ({_fmt(f['salida'])})")
            continue

        if f["salida"] < HOY:
            continue

        cuadra = dias is None or (f["llegada"] - f["salida"]).days == dias - 1

        if not cuadra:
            AVISOS.append(
                f"{url}: salida {_fmt(f['salida'])} → llegada {_fmt(f['llegada'])} "
                f"no cuadra con {dias} días"
            )

        origen = f" ({f['p_salida']})" if f["p_salida"] else ""
        destino = f" ({f['p_llegada']})" if f["p_llegada"] else ""

        if len(f["precios"]) == 0:
            precio = "precio: consultar"
        elif len(f["precios"]) == 1:
            precio = f"precio {f['precios'][0]}"
        elif len(f["precios"]) == 2:
            precio = f"precio {f['precios'][0]}, oferta {f['precios'][1]}"
        else:
            precio = "precios " + ", ".join(f["precios"])

        aviso = "" if cuadra else " [VERIFICAR: las fechas no cuadran con la duración; consultar con atención al cliente]"

        lineas.append(
            f"• Salida {_fmt(f['salida'])}{origen} → llegada {_fmt(f['llegada'])}{destino}: {precio}{aviso}"
        )

    if lineas:
        bloque_nuevo = (
            "SALIDAS Y PRECIOS (por persona; la salida es el día de embarque y la llegada el de desembarque): "
            + " ".join(lineas) + " "
        )
    else:
        bloque_nuevo = (
            "SALIDAS Y PRECIOS: no hay salidas futuras publicadas en la web. "
            "Consultar con atención al cliente. "
        )

    texto = texto[:m.start()] + bloque_nuevo + texto[m.end():]

    # La lista "Fechas de salida" queda redundante (y a veces incompleta):
    # la información buena está ya en SALIDAS Y PRECIOS.
    texto = RE_LISTA_FECHAS.sub("", texto)

    return texto


def filtrar_lista_fechas(texto):
    """Si no se pudo reconstruir la tabla, al menos quita las fechas ya pasadas de la lista."""

    def _filtrar(m):

        fechas = re.findall(r"\d{2}-\d{2}-\d{4}", m.group(1))
        futuras = [f for f in fechas if (_a_fecha(f) or HOY) >= HOY]

        if futuras:
            return "Fechas de salida: " + " | ".join(futuras) + " "

        return "Fechas de salida: no hay fechas futuras publicadas. "

    return RE_LISTA_FECHAS.sub(_filtrar, texto)


# ===============================
# URLS
# ===============================

def url_valida(u):
    """Decide si una URL se guarda en el documento."""

    if any(r in u for r in RUTAS_EXCLUIDAS):
        return False

    # Índice /crucero/ vacío: la web responde "este crucero ha zarpado" (404)
    if re.search(r"/crucero/?$", u.split("?")[0].split("#")[0]):
        return False

    return (
        u in SEED_URLS
        or "/crucero/" in u
        or "/barcoscrucemundo/" in u
        or "/flota-cruceros-fluviales/" in u
        or "/destinos/" in u
    )


def _clave_url(u):
    """Clave para detectar la misma página con distinto aspecto (www, barra final, slug)."""

    m = re.search(r"/barcoscrucemundo/(\d+)/", u)
    if m:
        return "barco:" + m.group(1)

    m = re.search(r"/crucero/.+?/(\d+)/?$", u)
    if m:
        return "crucero:" + m.group(1)

    k = u.split("?")[0].split("#")[0].lower()
    k = re.sub(r"^https?://(www\.)?", "", k)

    return k.rstrip("/")


def deduplicar_urls(urls):
    """Una sola URL por página. Entre variantes, prefiere la del slug sin 'quot'/'antilde'."""

    elegidas = {}

    for u in urls:

        k = _clave_url(u)

        actual = elegidas.get(k)

        if actual is None:
            elegidas[k] = u
            continue

        peso_u = (("quot" in u) or ("antilde" in u), len(u))
        peso_a = (("quot" in actual) or ("antilde" in actual), len(actual))

        if peso_u < peso_a:
            elegidas[k] = u

    return list(elegidas.values())


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

        texto = normalizar_salidas(texto, url)

        if len(texto) > MAX_CARACTERES_PAGINA:
            AVISOS.append(f"{url}: página cortada a {MAX_CARACTERES_PAGINA} caracteres")

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

{texto[:MAX_CARACTERES_PAGINA]}

"""

    except Exception as e:

        print(
            "ERROR",
            url,
            e
        )

        return ""


# ===============================
# ARGUMENTOS (compatibles con el workflow de GitHub Actions)
# ===============================

def leer_argumentos():
    """
    El workflow pasa varias opciones (--out, --urls-out, --document-id,
    --google-key, --headless, ...). Se aceptan todas; las que este script no
    usa se ignoran sin error.
    """

    global DOCUMENT_ID, GOOGLE_KEY

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    parser.add_argument("--urls-out", default="")
    parser.add_argument("--document-id", default="")
    parser.add_argument("--google-key", default="")

    args, _ = parser.parse_known_args()

    if args.document_id:
        DOCUMENT_ID = args.document_id

    if args.google_key:
        GOOGLE_KEY = args.google_key

    return args


# ===============================
# PROCESO PRINCIPAL
# ===============================

async def crawler(args):

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

        urls = [u for u in urls if url_valida(u)]

        urls = deduplicar_urls(urls)

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

    print(
        "Tamaño del contenido del crawler:",
        len(documento),
        "caracteres en",
        len(urls),
        "páginas"
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(documento)

    if args.urls_out:
        with open(args.urls_out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(urls))

    parte_manual = escribir_google_doc(
        documento
    )

    # Al Vector Store van el bloque manual (reglas, cancelación, documentación...)
    # y el contenido del crawler, para que el bot pueda buscar en los dos.
    if parte_manual:
        contenido_vector = parte_manual + "\n\n" + documento
    else:
        print(
            "Aviso: no se obtuvo el bloque manual; el Vector Store llevará solo "
            "el contenido del crawler."
        )
        contenido_vector = documento

    actualizar_vector_store(
        contenido_vector
    )

    if AVISOS:
        print("\n===== AVISOS DE CALIDAD DE DATOS =====")
        for a in AVISOS:
            print("-", a)

    print(
        "FINALIZADO"
    )


if __name__ == "__main__":

    asyncio.run(
        crawler(leer_argumentos())
    )
