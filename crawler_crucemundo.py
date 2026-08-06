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
    "https://www.crucemundo.es/destinos/"
]


# ===============================
# GOOGLE DOCS
# ===============================

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

    end_index = doc["body"]["content"][-1]["endIndex"]

    requests_body = []

    if end_index > 1:

        requests_body.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": 1,
                    "endIndex": end_index - 1
                }
            }
        })

    requests_body.append({
        "insertText": {
            "location": {
                "index": 1
            },
            "text": texto
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

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for x in soup(
        ["script", "style", "noscript"]
    ):
        x.extract()

    texto = soup.get_text(
        " ",
        strip=True
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto


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
                "/crucero/" in u
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
