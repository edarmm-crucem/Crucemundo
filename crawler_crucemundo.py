import asyncio
import re
import requests
import os

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ==================================
# CONFIGURACION
# ==================================

INICIO = "https://crucemundo.es/"

DOMINIO = "crucemundo.es"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"


visitadas = set()
pendientes = set()

resultado = []


# ==================================
# GOOGLE DOC
# ==================================

def escribir_google_doc(texto):

    print("Entrando en escribir_google_doc")
    print("Caracteres:", len(texto))

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

    print("Documento:", doc["title"])

    contenido = doc.get(
        "body",
        {}
    ).get(
        "content",
        []
    )

    # borrar contenido actual

    if len(contenido) > 1:

        fin = contenido[-1].get(
            "endIndex",
            1
        )

        service.documents().batchUpdate(
            documentId=DOCUMENT_ID,
            body={
                "requests": [
                    {
                        "deleteContentRange": {
                            "range": {
                                "startIndex": 1,
                                "endIndex": fin - 1
                            }
                        }
                    }
                ]
            }
        ).execute()

        print("Contenido anterior eliminado")

    BLOQUE = 50000

    posicion = 1

    for i in range(0, len(texto), BLOQUE):

        trozo = texto[i:i + BLOQUE]

        service.documents().batchUpdate(
            documentId=DOCUMENT_ID,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {
                                "index": posicion
                            },
                            "text": trozo
                        }
                    }
                ]
            }
        ).execute()

        posicion += len(trozo)

        print(
            f"Enviados {posicion} caracteres"
        )

    print("Google Doc actualizado correctamente")




# ==================================
# EXTRAER ENLACES
# ==================================

async def obtener_enlaces(page):


    enlaces = await page.locator(
        "a"
    ).evaluate_all(
        """
        elementos => elementos.map(a => ({
            texto: a.innerText || "",
            url: a.href || ""
        }))
        """
    )


    nuevos=[]


    for enlace in enlaces:


        url = enlace["url"].strip()


        if not url:
            continue


        # quitar anclas
        url = url.split("#")[0]


        # normalizar
        url = url.replace(
            "www.crucemundo.es",
            "crucemundo.es"
        )


        # solo dominio principal
        if DOMINIO not in url:
            continue



        # ignorar recursos

        if re.search(
            r"\.(jpg|jpeg|png|gif|webp|svg|ico|bmp|css|js|woff|ttf)$",
            url,
            re.I
        ):
            continue



        # ignorar documentos

        if re.search(
            r"\.(pdf|doc|docx|xls|xlsx|zip)$",
            url,
            re.I
        ):
            continue



        # ignorar descargas conocidas

        if any(
            x in url.lower()
            for x in [
                "pdfcrucerodisp",
                "/download"
            ]
        ):
            continue



        nuevos.append(
            {
                "url":url,
                "texto":enlace["texto"].strip()
            }
        )



    # quitar duplicados

    salida=[]

    vistos=set()


    for x in nuevos:


        if x["url"] not in vistos:

            vistos.add(
                x["url"]
            )

            salida.append(
                x
            )


    return salida













# ==================================
# LEER PAGINA Y AÑADIR CONTENIDO
# ==================================

async def leer_pagina(page, url):

    try:


        print("")
        print("--------------------------------")
        print("VISITANDO:")
        print(url)
        print("--------------------------------")


        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )


        await page.wait_for_timeout(
            1000
        )


        titulo = await page.title()


        html = await page.content()


        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        # quitar código innecesario

        for x in soup(
            [
                "script",
                "style",
                "noscript",
                "svg"
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



        # guardar información

        resultado.append(
            f"""

========================================

URL:
{url}

TITULO:
{titulo}


CONTENIDO:

{texto}

========================================

"""
        )



        enlaces = await obtener_enlaces(
            page
        )


        print(
            "Enlaces encontrados:",
            len(enlaces)
        )


        nuevos = 0


        for enlace in enlaces:


            destino = enlace["url"]


            if destino not in visitadas and destino not in pendientes:

                pendientes.add(
                    destino
                )

                nuevos += 1


        print(
            "Nuevos enlaces:",
            nuevos
        )



    except Exception as e:


        print(
            "ERROR:",
            url,
            e
        )



# ==================================
# PROCESO PRINCIPAL
# ==================================

async def crawler():


    print(
        "===================================="
    )

    print(
        "INICIANDO CRAWLER CRUCEMUNDO"
    )

    print(
        "SIN SITEMAP"
    )

    print(
        "===================================="
    )



    pendientes.add(
        INICIO
    )



    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=True
        )


        page = await browser.new_page()



        contador = 0



        while pendientes:


            url = pendientes.pop()


            if url in visitadas:
                continue



            visitadas.add(
                url
            )


            contador += 1


            print("")
            print(
                "PAGINA",
                contador
            )

            print(
                "Visitadas:",
                len(visitadas)
            )

            print(
                "Pendientes:",
                len(pendientes)
            )



            await leer_pagina(
                page,
                url
            )



        await browser.close()



    print("")
    print(
        "===================================="
    )

    print(
        "FIN CRAWLER"
    )

    print(
        "TOTAL PAGINAS:",
        len(visitadas)
    )

    print(
        "===================================="
    )













# ==================================
# FINAL
# ==================================

if __name__ == "__main__":


    asyncio.run(
        crawler()
    )


    print(
        ""
    )

    print(
        "Creando documento..."
    )


    documento = "\n".join(
        resultado
    )


    escribir_google_doc(
        documento
    )


    print(
        ""
    )

    print(
        "===================================="
    )

    print(
        "PROCESO TERMINADO"
    )

    print(
        "===================================="
    )
