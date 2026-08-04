import asyncio
import re
import urllib.parse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build


# =====================================
# CONFIGURACION
# =====================================

INICIO = "https://crucemundo.es/"

DOMINIO = "crucemundo.es"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"


MAX_PAGINAS = 300



# =====================================
# GOOGLE DOCS
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











# =====================================
# LIMPIAR HTML
# =====================================

def limpiar(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )


    for x in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):
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



# =====================================
# NORMALIZAR URL
# =====================================

def normalizar_url(url):

    p = urllib.parse.urlparse(url)


    dominio = p.netloc.lower()

    dominio = dominio.replace(
        "www.",
        ""
    )


    ruta = p.path.rstrip("/")


    return dominio + ruta



# =====================================
# COMPROBAR DOMINIO
# =====================================

def es_interna(url):

    try:

        p = urllib.parse.urlparse(url)


        dominio = p.netloc.lower()

        dominio = dominio.replace(
            "www.",
            ""
        )


        return dominio == DOMINIO


    except:

        return False




# =====================================
# SACAR ENLACES
# =====================================

async def sacar_enlaces(page):


    datos = await page.locator(
        "a"
    ).evaluate_all(
        """
        els => els.map(e => ({
            url:e.href,
            texto:e.innerText
        }))
        """
    )


    enlaces=[]

    descubre=[]



    for dato in datos:


        url = dato["url"]

        texto = dato["texto"].strip()



        if texto.lower() == "descubre":

            if url not in descubre:

                descubre.append(
                    url
                )



        if not es_interna(url):

            continue



        excluir=[

            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".zip",
            "/download",
            "olvidoAcceso",
            "logout"

        ]



        if any(
            x.lower() in url.lower()
            for x in excluir
        ):

            continue



        if url not in enlaces:

            enlaces.append(
                url
            )



    return enlaces, descubre







# =====================================
# EXTRAER UNA PAGINA
# =====================================

async def extraer_pagina(page, url):

    try:

        print()
        print("--------------------------------")
        print("Visitando:")
        print(url)


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


        texto = limpiar(
            html
        )



        return f"""

==================================================

URL:
{url}


TITULO:
{titulo}


CONTENIDO:

{texto[:10000]}

==================================================

"""


    except Exception as e:


        print(
            "ERROR:",
            url,
            e
        )


        return ""




# =====================================
# CRAWLER PRINCIPAL
# =====================================

async def crawler():


    visitadas=set()

    pendientes=[
        INICIO
    ]


    salida=[]

    descubre=[]


    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=True
        )


        page = await browser.new_page()



        numero=0



        while pendientes and len(visitadas)<MAX_PAGINAS:


            url = pendientes.pop(0)



            clave = normalizar_url(
                url
            )


            if clave in visitadas:

                continue



            visitadas.add(
                clave
            )


            numero += 1



            print()
            print("================================")
            print("PAGINA:", numero)
            print("Visitadas:", len(visitadas))
            print("Pendientes:", len(pendientes))
            print("URL:", url)
            print("================================")



            # Saltar ficheros

            if re.search(
                r"\.(pdf|doc|docx|xls|xlsx|zip)$",
                url,
                re.I
            ):

                continue



            texto = await extraer_pagina(
                page,
                url
            )



            if texto:

                salida.append(
                    texto
                )



            try:


                nuevos, nuevos_descubre = await sacar_enlaces(
                    page
                )



                for d in nuevos_descubre:

                    if d not in descubre:

                        descubre.append(
                            d
                        )



                for enlace in nuevos:


                    clave_enlace = normalizar_url(
                        enlace
                    )


                    if clave_enlace not in visitadas:


                        if enlace not in pendientes:

                            pendientes.append(
                                enlace
                            )



                print(
                    "Enlaces encontrados:",
                    len(nuevos)
                )



                if nuevos_descubre:

                    print(
                        "DESCUBRE encontrados:",
                        nuevos_descubre
                    )



            except Exception as e:


                print(
                    "ERROR SACANDO ENLACES:",
                    e
                )



        await browser.close()



    return salida, descubre








# =====================================
# EJECUCION
# =====================================

if __name__ == "__main__":


    print("""
====================================
INICIANDO CRAWLER CRUCEMUNDO
====================================
""")


    datos, descubre = asyncio.run(
        crawler()
    )



    documento = "\n".join(
        datos
    )



    documento += """



==================================================
ENLACES CON TEXTO DESCUBRE
==================================================

"""



    for enlace in descubre:

        documento += (
            enlace +
            "\n"
        )



    print()
    print(
        "TOTAL PAGINAS:",
        len(datos)
    )


    print(
        "TOTAL DESCUBRE:",
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
