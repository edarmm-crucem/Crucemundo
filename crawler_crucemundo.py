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

    try:
        # 1. Leer el documento para saber cuántos caracteres tiene realmente
        doc = service.documents().get(documentId=DOCUMENT_ID).execute()
        end_index = doc["body"]["content"][-1]["endIndex"] - 1
        print(f"[GDOC] Documento leido OK. Longitud actual: {end_index}")

        requests_batch = []

        # Solo borrar si hay algo que borrar (si end_index es 1, el doc esta vacio)
        if end_index > 1:
            requests_batch.append({
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": end_index}
                }
            })

        # Google Docs tiene un limite de ~1.000.000 caracteres por doc
        texto_final = texto[:999000]

        requests_batch.append({
            "insertText": {
                "location": {"index": 1},
                "text": texto_final
            }
        })

        result = service.documents().batchUpdate(
            documentId=DOCUMENT_ID,
            body={"requests": requests_batch}
        ).execute()

        print("[GDOC] batchUpdate ejecutado correctamente.")
        print("[GDOC] replies:", len(result.get("replies", [])))

    except Exception as e:
        print("[GDOC] ERROR AL ESCRIBIR EN GOOGLE DOCS:")
        print(repr(e))
        raise  # relanzar para que el fallo sea visible y no pase desapercibido


# ===============================
# LIMPIEZA TEXTO
# ===============================

def limpiar(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for x in soup(
        ["script","style","noscript"]
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

    urls=[]

    r=requests.get(
        SITEMAP,
        timeout=30
    )

    locs=re.findall(
        r"<loc>(.*?)</loc>",
        r.text
    )


    for u in locs:

        if "reservarcrucero" not in u:
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


    html = await page.content()


    barcos=re.findall(
        r'href="([^"]*barcoscrucemundo[^"]*)"',
        html
    )


    resultado=[]


    for b in barcos:

        if not b.startswith("http"):
            b=DOMAIN+b


        if b not in resultado:
            resultado.append(b)


    return resultado



# ===============================
# EXTRAER PAGINA
# ===============================

async def extraer_pagina(page,url):

    try:

        await page.goto(
            url,
            wait_until="networkidle",
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


    salida=[]


    urls=leer_sitemap()


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


        urls=list(
            dict.fromkeys(urls)
        )


        for i,url in enumerate(urls):

            print(
                i+1,
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



    documento="\n".join(
        salida
    )


    escribir_google_doc(
        documento
    )


    print(
        "FINALIZADO"
    )



if __name__=="__main__":

    asyncio.run(
        crawler()
    )
