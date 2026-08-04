import asyncio
import re
import requests
import os

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

    doc = service.documents().get(
        documentId=DOCUMENT_ID
    ).execute()


    requests=[]

    contenido = doc.get("body", {}).get("content", [])

    if len(contenido) > 1:

        ultimo = contenido[-1]

        fin = ultimo.get("endIndex",1)

        requests.append(
            {
                "deleteContentRange":{
                    "range":{
                        "startIndex":1,
                        "endIndex":fin-1
                    }
                }
            }
        )


    requests.append(
        {
            "insertText":{
                "location":{
                    "index":1
                },
                "text":texto
            }
        }
    )


    service.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={
            "requests":requests
        }
    ).execute()


    print("Google Doc actualizado")



# ===============================
# LIMPIAR HTML
# ===============================

def limpiar(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    for x in soup(
        [
            "script",
            "style",
            "noscript"
        ]
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


    print("Entrando en flota...")


    await page.goto(
        FLOTA,
        wait_until="domcontentloaded",
        timeout=60000
    )


    # Esperar carga JS

    await page.wait_for_timeout(5000)


    html = await page.content()



    barcos = re.findall(
        r'https?://[^"\']*barcoscrucemundo[^"\']*',
        html,
        re.I
    )


    resultado=[]


    for b in barcos:


        b=b.replace(
            "&amp;",
            "&"
        )


        if b not in resultado:
            resultado.append(b)



    print(
        "Barcos detectados:",
        resultado
    )


    return resultado





# ===============================
# EXTRAER PAGINA
# ===============================

async def extraer_pagina(page,url):

    try:


        # Saltar descargas

        if url.endswith(".pdf") or "pdfcrucerodisp" in url:
            print(
                "SALTO PDF:",
                url
            )
            return ""



        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )


        await page.wait_for_timeout(
            1500
        )


        html = await page.content()


        titulo = await page.title()


        texto = limpiar(html)



        return f"""

==================================================

URL:
{url}


==================================================

TITULO:
{titulo}


==================================================

CONTENIDO:

{texto[:8000]}

"""



    except Exception as e:


        print(
            "ERROR",
            url,
            e
        )


        return ""





# ===============================
# PROCESO
# ===============================

async def crawler():


    salida=[]


    urls=leer_sitemap()



    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=True
        )


        page = await browser.new_page()



        barcos = await sacar_barcos(
            page
        )


        print(
            "Barcos encontrados:",
            len(barcos)
        )



        urls.extend(
            barcos
        )


        urls=list(
            dict.fromkeys(urls)
        )



        print(
            "TOTAL URL:",
            len(urls)
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


            if texto:
                salida.append(texto)



        await browser.close()




    documento="\n".join(
        salida
    )


    print(
        "Escribiendo Google Doc..."
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
