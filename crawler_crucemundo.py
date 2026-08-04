import asyncio
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ======================================================
# CONFIGURACIÓN
# ======================================================

DOMAIN = "https://crucemundo.es"

START_URL = DOMAIN + "/"

DOCUMENT_ID = "1-MklRtqm3n31WxMduWlyV1Lj_lwws7wkEIIBqgToycs"

GOOGLE_KEY = "credentials.json"

MAX_TEXTO = 8000

TIMEOUT = 60000

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

    contenido = doc.get(
        "body",
        {}
    ).get(
        "content",
        []
    )

    if len(contenido) > 1:

        fin = contenido[-1]["endIndex"]

        requests.append(
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": fin - 1
                    }
                }
            }
        )

    requests.append(
        {
            "insertText": {
                "location": {
                    "index": 1
                },
                "text": texto
            }
        }
    )

    service.documents().batchUpdate(
        documentId=DOCUMENT_ID,
        body={
            "requests": requests
        }
    ).execute()

    print("Google Doc actualizado")




def limpiar_html(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe"
        ]
    ):
        tag.decompose()

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









def normalizar(url):

    url = url.split("#")[0]

    url = url.rstrip("/")

    return url



def es_interna(url):

    return urlparse(url).netloc.endswith(
        "crucemundo.es"
    )



def ignorar(url):

    url = url.lower()

    extensiones = (

        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".webp",
        ".css",
        ".js",
        ".ico",
        ".zip",
        ".xml",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp4",
        ".mp3",
        ".avi"

    )

    if url.endswith(extensiones):
        return True

    if "mailto:" in url:
        return True

    if "tel:" in url:
        return True

    if "javascript:" in url:
        return True

    return False



# ======================================================
# EXTRAER UNA PÁGINA
# ======================================================

async def procesar_pagina(page, url):

    try:

        print("\nVisitando:", url)

        await page.goto(
            url,
            wait_until="networkidle",
            timeout=TIMEOUT
        )

        await page.wait_for_timeout(1000)

        titulo = await page.title()

        html = await page.content()

        texto = limpiar_html(html)

        enlaces = await page.locator("a[href]").evaluate_all(
            """
            els => els.map(e => e.href)
            """
        )

        nuevos = []

        for enlace in enlaces:

            if not enlace:
                continue

            enlace = urljoin(url, enlace)

            enlace = normalizar(enlace)

            if not es_interna(enlace):
                continue

            if ignorar(enlace):
                continue

            nuevos.append(enlace)

        nuevos = list(dict.fromkeys(nuevos))

        print("Enlaces encontrados:", len(nuevos))

        bloque = f"""

==================================================

URL:
{url}

==================================================

TITULO:
{titulo}

==================================================

CONTENIDO:

{texto[:MAX_TEXTO]}

"""

        return bloque, nuevos

    except Exception as e:

        print("ERROR:", url)
        print(e)

        return "", []








# ======================================================
# COLA
# ======================================================

class Cola:

    def __init__(self):

        self.pendientes = []

        self.visitadas = set()

    def agregar(self, url):

        url = normalizar(url)

        if url in self.visitadas:
            return

        if url in self.pendientes:
            return

        self.pendientes.append(url)

    def siguiente(self):

        if not self.pendientes:
            return None

        return self.pendientes.pop(0)

    def visitar(self, url):

        self.visitadas.add(
            normalizar(url)
        )




# ======================================================
# MOTOR DEL CRAWLER
# ======================================================

async def ejecutar_crawler():

    salida = []

    cola = Cola()

    cola.agregar(
        START_URL
    )


    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=True
        )


        page = await browser.new_page()


        contador = 0


        while True:


            url = cola.siguiente()


            if not url:
                break


            if url in cola.visitadas:
                continue


            cola.visitar(url)


            contador += 1


            print(
                "\n===================================="
            )

            print(
                "PÁGINA",
                contador
            )

            print(
                "Visitadas:",
                len(cola.visitadas)
            )

            print(
                "Pendientes:",
                len(cola.pendientes)
            )


            texto, enlaces = await procesar_pagina(
                page,
                url
            )


            if texto:

                salida.append(
                    texto
                )


            for enlace in enlaces:

                cola.agregar(
                    enlace
                )


        await browser.close()


    print(
        "\nTOTAL PÁGINAS:",
        len(cola.visitadas)
    )


    return "\n".join(
        salida
    )







# ======================================================
# GUARDAR RESULTADO
# ======================================================

def preparar_documento(texto):

    if not texto:

        return (
            "No se ha encontrado contenido."
        )


    cabecera = """

CRAWLER CRUCEMUNDO
==================

Fecha de rastreo automática.

"""

    return cabecera + texto



# ======================================================
# MAIN
# ======================================================

async def main():

    print(
        "===================================="
    )

    print(
        "INICIANDO CRAWLER CRUCEMUNDO"
    )

    print(
        "URL inicial:",
        START_URL
    )

    print(
        "===================================="
    )


    documento = await ejecutar_crawler()


    documento = preparar_documento(
        documento
    )


    print(
        "\nEscribiendo Google Doc..."
    )


    try:

        escribir_google_doc(
            documento
        )


    except Exception as e:

        print(
            "ERROR GOOGLE DOC:"
        )

        print(e)

        # Guardar copia local si falla Google

        with open(
            "resultado_crawler.txt",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                documento
            )


        print(
            "Guardado resultado_crawler.txt"
        )



    print(
        "\n===================================="
    )

    print(
        "CRAWLER FINALIZADO"
    )

    print(
        "===================================="
    )



# ======================================================
# EJECUCIÓN
# ======================================================

if __name__ == "__main__":


    asyncio.run(
        main()
    )








