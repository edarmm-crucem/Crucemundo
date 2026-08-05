#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler mejorado para crucemundo.es
- Concurrency control (multiple workers)
- Cola asincrónica y deduplicación
- Normalización de URLs
- Mejor manejo de errores y reintentos
- Opción de guardar localmente si no hay credenciales de Google
"""

import argparse
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Google API
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ----------------------------------
# Config / Defaults
# ----------------------------------

EXT_RESOURCES_RE = re.compile(
    r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|bmp|css|js|woff|ttf)$", re.I
)
EXT_DOCS_RE = re.compile(r"\.(?:pdf|doc|docx|xls|xlsx|zip)$", re.I)

# ----------------------------------
# Dataclasses
# ----------------------------------

@dataclass
class CrawlerConfig:
    start_url: str
    domain: str
    document_id: str | None = None
    google_key: str | None = None
    max_pages: int = 1000
    concurrency: int = 3
    headless: bool = True
    wait_after_load_ms: int = 800
    user_agent: str = "CrucemundoCrawler/1.0 (+https://crucemundo.es)"


# ----------------------------------
# Crawler
# ----------------------------------

class Crawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited: Set[str] = set()
        self.results: List[str] = []
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.logger = logging.getLogger("crawler")
        self.logger.setLevel(logging.INFO)

    @staticmethod
    def normalize_url(base: str, link: str) -> str | None:
        if not link:
            return None
        # Remove anchors
        link = link.split("#", 1)[0].strip()
        # Resolve relative URLs
        url = urljoin(base, link)
        parsed = urlparse(url)
        if not parsed.scheme.startswith("http"):
            return None
        # Normalize host e.g. www.crucemundo.es -> crucemundo.es
        netloc = parsed.netloc.replace("www.", "")
        normalized = parsed._replace(netloc=netloc).geturl()
        return normalized

    def allowed_url(self, url: str) -> bool:
        # Same domain?
        try:
            netloc = urlparse(url).netloc
            if self.config.domain not in netloc:
                return False
        except Exception:
            return False
        # Skip static resources / documents
        if EXT_RESOURCES_RE.search(url) or EXT_DOCS_RE.search(url):
            return False
        # Skip obvious download paths
        low = url.lower()
        if "pdfcrucerodisp" in low or "/download" in low:
            return False
        return True

    def extract_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            url = self.normalize_url(base_url, href)
            if not url:
                continue
            if self.allowed_url(url):
                links.append(url)
        # preserve order but dedupe
        seen = set()
        out = []
        for u in links:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    @staticmethod
    def extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.extract()
        text = soup.get_text(" ", strip=True)
        # collapse whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    async def fetch_and_process(self, page, url: str):
        self.logger.info("Visitando: %s", url)
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                await page.set_extra_http_headers({"User-Agent": self.config.user_agent})
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(self.config.wait_after_load_ms)
                title = await page.title()
                html = await page.content()
                texto = self.extract_text(html)
                self.results.append(
                    f"\n\n========================================\n\nURL:\n{url}\n\nTITULO:\n{title}\n\n\nCONTENIDO:\n\n{texto}\n\n========================================\n\n"
                )
                # Extract new links
                nuevos = 0
                for destino in self.extract_links(html, url):
                    if destino not in self.visited:
                        await self.enqueue_if_allowed(destino)
                        nuevos += 1
                self.logger.info("Enlaces nuevos encontrados: %d", nuevos)
                return
            except PlaywrightTimeoutError as te:
                self.logger.warning("Timeout en %s (intento %d): %s", url, attempt, te)
            except Exception as e:
                self.logger.exception("Error procesando %s (intento %d): %s", url, attempt, e)
            await asyncio.sleep(1 * attempt)
        self.logger.error("Fallo al obtener %s tras %d intentos", url, attempts)

    async def enqueue_if_allowed(self, url: str):
        if not self.allowed_url(url):
            return
        if url in self.visited:
            return
        # Small safety: avoid queueing beyond max_pages
        total_seen = len(self.visited) + self.queue.qsize()
        if total_seen >= self.config.max_pages:
            return
        await self.queue.put(url)

    async def worker(self, browser, worker_id: int):
        page = await browser.new_page()
        try:
            while True:
                try:
                    url = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    # No items for a while -> check exit condition
                    if self.queue.empty():
                        break
                    else:
                        continue
                if url in self.visited:
                    self.queue.task_done()
                    continue
                # Mark visited early to avoid duplicates
                self.visited.add(url)
                await self.fetch_and_process(page, url)
                self.queue.task_done()
                # Respect max_pages
                if len(self.visited) >= self.config.max_pages:
                    self.logger.info("Alcanzado max_pages (%d).", self.config.max_pages)
                    break
        finally:
            await page.close()

    async def crawl(self):
        await self.queue.put(self.config.start_url)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.headless)
            # Create worker tasks
            workers = [
                asyncio.create_task(self.worker(browser, i))
                for i in range(max(1, self.config.concurrency))
            ]
            # Wait until queue is processed or max_pages reached
            await self.queue.join()
            # Cancel workers
            for w in workers:
                w.cancel()
            await browser.close()

    # ----------------------------------
    # Google Docs writer (synchronous)
    # ----------------------------------

    def write_google_doc(self, text: str):
        if not self.config.document_id or not self.config.google_key:
            # fallback: write local file
            fname = "crawler_output.txt"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(text)
            self.logger.info("Credenciales de Google no proporcionadas: guardado en %s", fname)
            return

        scopes = ["https://www.googleapis.com/auth/documents"]
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.config.google_key, scopes=scopes
            )
            service = build("docs", "v1", credentials=creds)
            doc = service.documents().get(documentId=self.config.document_id).execute()
            self.logger.info("Documento: %s", doc.get("title"))

            contenido = doc.get("body", {}).get("content", [])
            # Delete existing content except the required leading element
            if len(contenido) > 1:
                fin = contenido[-1].get("endIndex", 1)
                service.documents().batchUpdate(
                    documentId=self.config.document_id,
                    body={
                        "requests": [
                            {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": fin - 1}}}
                        ]
                    },
                ).execute()
                self.logger.info("Contenido anterior eliminado")

            BLOQUE = 50000
            posicion = 1
            for i in range(0, len(text), BLOQUE):
                trozo = text[i : i + BLOQUE]
                service.documents().batchUpdate(
                    documentId=self.config.document_id,
                    body={"requests": [{"insertText": {"location": {"index": posicion}, "text": trozo}}]},
                ).execute()
                posicion += len(trozo)
                self.logger.info("Enviados %d caracteres", posicion)
            self.logger.info("Google Doc actualizado correctamente")
        except Exception as e:
            self.logger.exception("Error al escribir en Google Docs: %s", e)
            # fallback local
            fname = "crawler_output_on_error.txt"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(text[:1000000])  # write at most first MB to avoid disk floods
            self.logger.info("Salida guardada localmente en %s", fname)


# ----------------------------------
# CLI / Entrypoint
# ----------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawler mejorado para crucemundo.es")
    p.add_argument("--start", default="https://crucemundo.es/", help="URL inicial")
    p.add_argument("--domain", default="crucemundo.es", help="Dominio permitido")
    p.add_argument("--document-id", default=os.getenv("CRUCEMUNDO_DOC_ID", None), help="Google Document ID")
    p.add_argument("--google-key", default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json"), help="Ruta a credentials.json")
    p.add_argument("--max-pages", type=int, default=500, help="Max páginas a rastrear")
    p.add_argument("--concurrency", type=int, default=3, help="Número de workers concurrentes")
    p.add_argument("--headless", action="store_true", help="Ejecutar navegador en headless")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
    cfg = CrawlerConfig(
        start_url=args.start,
        domain=args.domain,
        document_id=args.document_id,
        google_key=args.google_key if os.path.exists(args.google_key) else None,
        max_pages=args.max_pages,
        concurrency=args.concurrency,
        headless=True,
    )
    crawler = Crawler(cfg)

    async def run():
        await crawler.crawl()

    asyncio.run(run())

    documento = "\n".join(crawler.results)
    crawler.write_google_doc(documento)
    logging.info("Proceso terminado. Páginas visitadas: %d", len(crawler.visited))


if __name__ == "__main__":
    main()
