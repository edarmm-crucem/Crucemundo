import asyncio
import re

from bs4 import BeautifulSoup
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ==================================================
# CONFIGURACION
# ==================================================

DOMAIN = "https://crucemundo.es"

START_URL = DOMAIN + "/"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"



# ==================================================
# VARIABLES GLOBALES
# ==================================================

visitadas = set()

pendientes = set()

descubre = []

contenido = []



# ==================================================
# FILTROS
# ==================================================

EXTENSIONES_IGNORAR = [

    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",

    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",

    ".zip",
    ".rar",

    ".mp3",
    ".mp4"
]



# ==================================================
# GOOGLE DOC
# ==================================================

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


    requests = []


    cuerpo = doc.get(
        "body",
        {}
    ).get(
        "content",
        []
    )


    if len(cuerpo) > 1:


        fin = cuerpo[-1].get(
            "endIndex",
            1
        )


        requests.append(
            {
                "deleteContentRange":
                {
                    "range":
                    {
                        "startIndex":1,
                        "endIndex":fin-1
                    }
                }
            }
        )


    requests.append(
        {
            "insertText":
            {
                "location":
                {
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









# ==================================================
# FUNCIONES AUXILIARES
# ==================================================

def limpiar(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    for tag in soup(
        [
            "script",
            "style",
            "noscript"
        ]
    ):

        tag.extract()


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





def normalizar_url(url):

    if not url:
        return None


    url = url.split("#")[0]


    if url.endswith("/"):
        url = url[:-1]


    return url






def url_permitida(url):


    if not url:
        return False



    url = url.lower()



    # Solo dominio crucemundo

    if not url.startswith(
        DOMAIN
    ):

        return False



    # Ignorar extensiones

    for ext in EXTENSIONES_IGNORAR:

        if url.endswith(ext):

            return False



    return True






# ==================================================
# EXTRAER ENLACES DE UNA PAGINA
# ==================================================

async def extraer_enlaces(page):


    enlaces = await page.locator(
        "a"
    ).evaluate_all(
        """
        elementos => elementos.map(
            e => ({
                texto:e.innerText.trim(),
                url:e.href
            })
        )
        """
    )


    resultado=[]


    for e in enlaces:


        url = normalizar_url(
            e["url"]
        )


        if not url_permitida(url):
            continue



        resultado.append(
            {
                "texto":e["texto"],
                "url":url
            }
        )



    return resultado





# ==================================================
# BUSCAR DESCUBRE
# ==================================================

async def detectar_descubre(page,pagina):


    enlaces = await extraer_enlaces(
        page
    )



    for e in enlaces:


        texto = e["texto"].upper()



        if "DESCUBRE" in texto:


            encontrado = False


            for d in descubre:

                if d["url"] == e["url"]:

                    encontrado=True
                    break



            if not encontrado:


                print(
                    "DESCUBRE:",
                    e["texto"],
                    "->",
                    e["url"]
                )


                descubre.append(
                    {
                        "pagina":pagina,
                        "texto":e["texto"],
                        "url":e["url"]
                    }
                )



    return enlaces













# ==================================================
# PROCESAR PAGINA
# ==================================================

async def procesar_pagina(page, url):


    try:


        print("")
        print("------------------------------------")
        print("VISITANDO:")
        print(url)
        print("------------------------------------")



        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )



        await page.wait_for_timeout(
            1000
        )



        html = await page.content()



        # Guardar contenido

        texto = limpiar(
            html
        )



        contenido.append(

            """

====================================
URL:
%s

CONTENIDO:
%s

====================================

"""
            %
            (
                url,
                texto[:8000]
            )

        )



        # Buscar DESCUBRE

        enlaces = await detectar_descubre(
            page,
            url
        )



        print(
            "Enlaces encontrados:",
            len(enlaces)
        )



        # Añadir nuevas páginas


        nuevos = 0


        for e in enlaces:


            destino = e["url"]



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



            await procesar_pagina(
                page,
                url
            )



        await browser.close()



    print("")
    print("====================================")
    print("FIN CRAWLER")
    print("TOTAL PAGINAS:",
          len(visitadas))

    print(
        "TOTAL DESCUBRE:",
        len(descubre)
    )

    print("====================================")








# ==================================================
# GENERAR INFORME FINAL
# ==================================================

def generar_informe():


    salida = []



    salida.append(
        "CRAWLER CRUCEMUNDO\n"
    )

    salida.append(
        "====================================\n\n"
    )



    salida.append(
        "TOTAL PAGINAS VISITADAS: "
        + str(len(visitadas))
        + "\n"
    )


    salida.append(
        "TOTAL ENLACES DESCUBRE: "
        + str(len(descubre))
        + "\n\n"
    )



    salida.append(
        "====================================\n"
    )

    salida.append(
        "ENLACES DESCUBRE ENCONTRADOS\n"
    )

    salida.append(
        "====================================\n\n"
    )



    for d in descubre:


        salida.append(
            "PAGINA DONDE APARECE:\n"
            + d["pagina"]
            + "\n\n"
            "TEXTO DEL ENLACE:\n"
            + d["texto"]
            + "\n\n"
            "DESTINO:\n"
            + d["url"]
            + "\n"
            "------------------------------------\n\n"
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
# EJECUCION FINAL
# ==================================================

if __name__ == "__main__":


    asyncio.run(
        crawler()
    )



    print(
        "Creando documento..."
    )



    informe = generar_informe()



    escribir_google_doc(
        informe
    )



    print("")
    print("====================================")
    print("PROCESO TERMINADO")
    print("====================================")
