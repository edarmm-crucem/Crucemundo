import asyncio
import re
import urllib.parse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build



# ===============================
# CONFIGURACION
# ===============================

DOMAIN = "https://crucemundo.es"

INICIO = DOMAIN + "/"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"


MAX_PAGINAS = 300

ESPERA = 1500



# ===============================
# GOOGLE DOCS
# ===============================

def escribir_google_doc(texto):

    scopes=[
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


    contenido=doc.get(
        "body",
        {}
    ).get(
        "content",
        []
    )


    if len(contenido)>1:

        fin=contenido[-1].get(
            "endIndex",
            1
        )


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
# LIMPIAR HTML
# ===============================

def limpiar(html):

    soup=BeautifulSoup(
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


    texto=soup.get_text(
        " ",
        strip=True
    )


    texto=re.sub(
        r"\s+",
        " ",
        texto
    )


    return texto





# ===============================
# ENLACES INTERNOS
# ===============================

async def sacar_enlaces(page,url_actual):


    enlaces=await page.locator(
        "a"
    ).evaluate_all(
        """
        els=>els.map(e=>e.href)
        """
    )


    resultado=[]


    for enlace in enlaces:


        if not enlace:
            continue


        enlace=urllib.parse.urljoin(
            url_actual,
            enlace
        )


        enlace=enlace.split("#")[0]


        # quitar www
        enlace=enlace.replace(
            "https://www.crucemundo.es",
            "https://crucemundo.es"
        )


        if not enlace.startswith(DOMAIN):
            continue



        basura=[
            ".pdf",
            ".doc",
            ".xls",
            ".zip",
            "logout",
            "olvidoAcceso",
            "altaagencias"
        ]


        if any(
            x in enlace.lower()
            for x in basura
        ):
            continue



        if enlace not in resultado:
            resultado.append(enlace)



    return resultado











# ===============================
# CAPTURAR AJAX / XHR
# ===============================

async def capturar_ajax(page):

    ajax=[]


    async def respuesta(response):

        url=response.url


        if url not in ajax:

            tipo=response.request.resource_type


            if tipo in [
                "xhr",
                "fetch"
            ]:

                ajax.append(url)



    page.on(
        "response",
        respuesta
    )


    return ajax





# ===============================
# EXTRAER UNA PAGINA
# ===============================

async def visitar_pagina(page,url):


    print()
    print("--------------------------------")
    print("Visitando:")
    print(url)



    ajax=[]


    async def guardar_ajax(response):

        if response.request.resource_type in [
            "xhr",
            "fetch"
        ]:

            if response.url not in ajax:
                ajax.append(
                    response.url
                )



    page.on(
        "response",
        guardar_ajax
    )



    try:


        await page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )


        await page.wait_for_timeout(
            ESPERA
        )



        html=await page.content()



        titulo=await page.title()



        texto=limpiar(
            html
        )



        # Mostrar AJAX encontrados

        if ajax:

            print(
                "AJAX encontrados:",
                len(ajax)
            )


            for a in ajax:

                if (
                    "init" in a.lower()
                    or "php" in a.lower()
                    or "json" in a.lower()
                    or "ajax" in a.lower()
                ):

                    print(
                        "POSIBLE DATOS:",
                        a
                    )



        enlaces=await sacar_enlaces(
            page,
            url
        )



        print(
            "Enlaces encontrados:",
            len(enlaces)
        )



        resultado=f"""

==================================================

URL:
{url}


TITULO:
{titulo}


AJAX:

{chr(10).join(ajax)}


CONTENIDO:

{texto[:8000]}

==================================================

"""


        return resultado,enlaces



    except Exception as e:


        print(
            "ERROR:",
            url,
            e
        )


        return "",[]








# =====================================
# MAIN
# =====================================

if __name__=="__main__":


    print("""
====================================
INICIANDO CRAWLER CRUCEMUNDO
====================================
""")


    datos, descubre = asyncio.run(
        crawler()
    )



    documento="\n".join(
        datos
    )



    documento += """




==================================================
ENLACES CON TEXTO DESCUBRE
==================================================

"""



    for x in descubre:

        documento += (
            x+"\n"
        )



    print(
        "TOTAL PAGINAS:",
        len(datos)
    )


    print(
        "DESCUBRE encontrados:",
        len(descubre)
    )



    print(
        "Escribiendo Google Doc..."
    )



    escribir_google_doc(
        documento
    )



    print("""
====================================
CRAWLER FINALIZADO
====================================
""")


