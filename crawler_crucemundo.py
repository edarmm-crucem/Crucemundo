from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import time

URL_INICIAL = "https://tudominio.com"
ARCHIVO_SALIDA = "contenido_completo.txt"

visitadas = set()
pendientes = deque([URL_INICIAL])

dominio = urlparse(URL_INICIAL).netloc

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as salida:

        while pendientes:

            url = pendientes.popleft()

            if url in visitadas:
                continue

            try:
                print(f"Procesando: {url}")

                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=60000
                )

                time.sleep(1)

                html = page.content()

                soup = BeautifulSoup(html, "html.parser")

                visitadas.add(url)

                for tag in soup([
                    "script",
                    "style",
                    "noscript",
                    "svg"
                ]):
                    tag.decompose()

                titulo = ""

                if soup.title:
                    titulo = soup.title.get_text(strip=True)

                texto = soup.get_text(
                    separator="\n",
                    strip=True
                )

                salida.write("\n")
                salida.write("=" * 120 + "\n")
                salida.write(f"URL: {url}\n")
                salida.write(f"TITULO: {titulo}\n")
                salida.write("=" * 120 + "\n\n")
                salida.write(texto)
                salida.write("\n\n")

                enlaces = soup.find_all("a", href=True)

                for enlace in enlaces:

                    href = enlace["href"]

                    if href.startswith("#"):
                        continue

                    if href.startswith("mailto:"):
                        continue

                    if href.startswith("tel:"):
                        continue

                    url_absoluta = urljoin(url, href)

                    parsed = urlparse(url_absoluta)

                    url_limpia = (
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    )

                    if (
                        parsed.netloc == dominio
                        and url_limpia not in visitadas
                        and url_limpia not in pendientes
                    ):
                        pendientes.append(url_limpia)

            except Exception as e:
                print(f"Error en {url}: {e}")

    browser.close()

print(f"\nTotal URLs visitadas: {len(visitadas)}")
print(f"TXT generado: {ARCHIVO_SALIDA}")
