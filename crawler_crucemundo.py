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

# ===============================
# EXTRAER BARCOS
# ===============================

async def sacar_barcos(page):

    print("Entrando en flota...")

    await page.goto(
        FLOTA,
        wait_until="networkidle",
        timeout=60000
    )

    await page.wait_for_timeout(5000)

    html = await page.content()

    print("HTML FLOTA:", len(html))


    # Guardar HTML para inspección si falla
    with open("flota_debug.html", "w", encoding="utf-8") as f:
        f.write(html)


    if "DESCUBRE" in html.upper():
        print("Encontrado texto DESCUBRE")
    else:
        print("NO aparece DESCUBRE")


    resultado=[]


    # Buscar enlaces visibles con DESCUBRE
    enlaces = await page.locator("a").evaluate_all(
        """
        els => els.map(e => ({
            texto: e.innerText,
            href: e.href,
            html: e.outerHTML
        }))
        """
    )


    for e in enlaces:

        texto = (e["texto"] or "").strip().upper()


        if "DESCUBRE" in texto:

            url = e["href"]


            if url and url not in resultado:

                resultado.append(url)


    print(
        "Enlaces DESCUBRE encontrados:",
        len(resultado)
    )


    # Si no encuentra nada, buscamos cualquier enlace
    # cercano a texto MS
    if len(resultado)==0:


        print("Buscando bloques con MS...")


        bloques = await page.locator(
            "body"
        ).inner_text()


        encontrados = re.findall(
            r"https?://[^\s]+",
            html
        )


        for u in encontrados:

            if (
                "barco" in u.lower()
                or "crucemundo" in u.lower()
            ):

                if u not in resultado:
                    resultado.append(u)



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
