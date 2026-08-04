import asyncio
import re
import os
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build


# =====================================
# CONFIGURACION
# =====================================

DOMAIN = "https://crucemundo.es"

START_URL = DOMAIN + "/"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"


# =====================================
# FILTROS
# =====================================

EXTENSIONES_IGNORAR = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".mp4",
    ".mp3"
]


# =====================================
# GOOGLE DOC
# =====================================

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


    peticiones=[]


    contenido = doc.get(
        "body",
        {}
    ).get(
        "content",
        []
    )


    if len(contenido)>1:

        fin = contenido[-1].get(
            "endIndex",
            1
        )


        if fin>2:

            peticiones.append(
                {
                    "deleteContentRange":{
                        "range":{
                            "startIndex":1,
                            "endIndex":fin-1
                        }
                    }
                }
            )


    peticiones.append(
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
            "requests":peticiones
        }
    ).execute()


    print("Google Doc actualizado")


# ===============================
# FUNCIONES AUXILIARES
# ===============================

def es_url_valida(url):

    if not url:
        return False

    url = url.lower()


    # Ignorar imágenes
    extensiones_no_validas = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".bmp",
        ".tif",
        ".tiff"
    ]


    for ext in extensiones_no_validas:
        if url.endswith(ext):
            return False


    # Ignorar documentos
    documentos = [
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".zip"
    ]


    for ext in documentos:
        if url.endswith(ext):
            return False


    return True





def normalizar_url(url):

    if not url:
        return None


    url = url.split("#")[0]


    if url.startswith("//"):
        url="https:"+url


    if url.startswith("/"):
        url = DOMAIN + url


    return url.rstrip("/")






# ===============================
# EXTRAER ENLACES
# ===============================

async def extraer_enlaces(page):

    enlaces = await page.locator("a").evaluate_all(
        """
        elementos => elementos.map(a => ({
            texto:a.innerText.trim(),
            href:a.href
        }))
        """
    )


    resultado=[]


    for e in enlaces:


        url = normalizar_url(
            e["href"]
        )


        if not es_url_valida(url):
            continue


        if not url.startswith(DOMAIN):
            continue


        texto = e["texto"]


        resultado.append(
            {
                "url":url,
                "texto":texto
            }
        )


    return resultado







# ===============================
# BUSCAR DESCUBRE
# ===============================

async def buscar_descubre(page,url):

    encontrados=[]


    enlaces = await extraer_enlaces(page)


    for e in enlaces:


        texto = e["texto"].upper()


        if "DESCUBRE" in texto:


            encontrados.append(
                {
                    "texto":e["texto"],
                    "url":e["url"]
                }
            )



    return encontrados










# ==================================================
# PROCESAR UNA PAGINA
# ==================================================

async def procesar_pagina(page, url):

    try:

        print("")
        print("====================================")
        print("VISITANDO:")
        print(url)
        print("====================================")


        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )


        await page.wait_for_timeout(
            1000
        )


        html = await page.content()


        # Guardar texto de la página

        texto = limpiar(
            html
        )


        contenido.append(
            f"""

====================================
URL:
{url}

CONTENIDO:
{texto[:8000]}

"""
        )


        # Buscar enlaces DESCUBRE

        encontrados = await buscar_descubre(
            page,
            url
        )


        for d in encontrados:


            existe = False


            for x in descubre:

                if x["url"] == d["url"]:
                    existe=True
                    break


            if not existe:

                print(
                    "DESCUBRE ENCONTRADO:",
                    d["texto"],
                    "->",
                    d["url"]
                )


                descubre.append(
                    {
                        "pagina":url,
                        "texto":d["texto"],
                        "url":d["url"]
                    }
                )



        # Sacar nuevos enlaces

        enlaces = await extraer_enlaces(
            page
        )


        nuevos = 0


        for e in enlaces:


            enlace = e["url"]


            if enlace not in visitadas and enlace not in pendientes:

                pendientes.add(
                    enlace
                )

                nuevos += 1



        print(
            "Nuevos enlaces:",
            nuevos
        )


        print(
            "Pendientes:",
            len(pendientes)
        )



    except Exception as e:


        print(
            "ERROR EN:",
            url
        )

        print(
            e
        )






# ==================================================
# CRAWLER PRINCIPAL
# ==================================================

async def crawler():


    print("")
    print("====================================")
    print("INICIANDO CRAWLER CRUCEMUNDO")
    print("SIN SITEMAP")
    print("====================================")


    pendientes.add(
        START_URL
    )


    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=True
        )


        page = await browser.new_page()



        contador=0



        while pendientes:


            url = pendientes.pop()


            url = normalizar_url(
                url
            )


            if not url:
                continue



            if url in visitadas:
                continue



            visitadas.add(
                url
            )


            contador += 1


            print("")
            print(
                "PAGINA:",
                contador
            )

            print(
                "Visitadas:",
                len(visitadas)
            )


            await procesar_pagina(
                page,
                url
            )



        await browser.close()



    print("")
    print("====================================")
    print("CRAWLER TERMINADO")
    print("TOTAL PAGINAS:",
          len(visitadas))
    print("TOTAL DESCUBRE:",
          len(descubre))
    print("====================================")







# ==================================================
# GENERAR INFORME FINAL
# ==================================================

def generar_documento():

    salida = []


    salida.append(
        "CRAWLER CRUCEMUNDO\n"
    )


    salida.append(
        "====================================\n"
    )


    salida.append(
        f"TOTAL PAGINAS VISITADAS: {len(visitadas)}\n"
    )


    salida.append(
        f"TOTAL ENLACES DESCUBRE: {len(descubre)}\n"
    )


    salida.append(
        "\n\n"
    )



    salida.append(
        "LISTADO DESCUBRE\n"
    )


    salida.append(
        "====================================\n"
    )


    for d in descubre:


        salida.append(
            "\n"
            "PAGINA DONDE APARECE:\n"
            + d["pagina"]
            + "\n\n"
            "TEXTO DEL ENLACE:\n"
            + d["texto"]
            + "\n\n"
            "DESTINO:\n"
            + d["url"]
            + "\n"
            "------------------------------------\n"
        )



    salida.append(
        "\n\n"
        "CONTENIDO DE PAGINAS\n"
    )


    salida.append(
        "====================================\n"
    )


    for c in contenido:

        salida.append(
            c
        )



    return "".join(
        salida
    )





# ==================================================
# EJECUCION
# ==================================================

if __name__ == "__main__":


    asyncio.run(
        crawler()
    )


    print(
        "Generando documento..."
    )


    documento = generar_documento()



    escribir_google_doc(
        documento
    )


    print("")
    print("====================================")
    print("FINALIZADO CORRECTAMENTE")
    print("====================================")














