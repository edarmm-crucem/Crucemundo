#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler mejorado para crucemundo.es
- Concurrency control (multiple workers)
- Cola asincrónica y deduplicación
- Normalización de URLs
- Manejo de errores y reintentos
- Opción de escribir en Google Docs; si falla, crea uno nuevo y guarda el nuevo ID
- Siempre deja copia local crawler_output.txt y last_doc_id.txt (si crea uno nuevo)

Requisitos:
pip install playwright beautifulsoup4 google-api-python-client google-auth unidecode
y ejecutar: playwright install chromium
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import pathlib
import traceback
import datetime
from dataclasses import dataclass
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ----------------------------------
# Config / Defaults
# ----------------------------------

EXT_RESOURCES_RE = re.compile(
    r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|bmp|css|js|woff|ttf)$", re.I
)
EXT_DOCS_RE = re.compile(r"\.(?:pdf|doc|docx|xls|xlsx|zip)$", re.I)


@dataclass
class CrawlerConfig:
    start_url: str
    domain: str
    document_id: Optional[str] = None
    google_key: Optional[str] = None
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
    def normalize_url(base: str, link: str) -> Optional[str]:
        if not link:
            return None
        link = link.split("#", 1)[0].strip()
        url = urljoin(base, link)
        parsed = urlparse(url)
        if not parsed.scheme.startswith("http"):
            return None
        netloc = parsed.netloc.replace("www.", "")
        normalized = parsed._replace(netloc=netloc).geturl()
        return normalized

    def allowed_url(self, url: str) -> bool:
        try:
            netloc = urlparse(url).netloc
            if self.config.domain not in netloc:
                return False
        except Exception:
            return False
        if EXT_RESOURCES_RE.search(url) or EXT_DOCS_RE.search(url):
            return False
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
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            tag.extract()
        text = soup.get_text(" ", strip=True)
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
                    "\n\n========================================\n\n"
                    f"URL:\n{url}\n\nTITULO:\n{title}\n\n\nCONTENIDO:\n\n{texto}\n\n"
                    "========================================\n\n"
                )
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
                    if self.queue.empty():
                        break
                    else:
                        continue
                if url in self.visited:
                    self.queue.task_done()
                    continue
                self.visited.add(url)
                await self.fetch_and_process(page, url)
                self.queue.task_done()
                if len(self.visited) >= self.config.max_pages:
                    self.logger.info("Alcanzado max_pages (%d).", self.config.max_pages)
                    break
        finally:
            try:
                await page.close()
            except Exception:
                pass

    async def crawl(self):
        await self.queue.put(self.config.start_url)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.headless)
            workers = [
                asyncio.create_task(self.worker(browser, i))
                for i in range(max(1, self.config.concurrency))
            ]
            await self.queue.join()
            for w in workers:
                w.cancel()
            try:
                await asyncio.gather(*workers, return_exceptions=True)
            except Exception:
                pass
            await browser.close()

    # ----------------------------------
    # Google Docs writer + helpers
    # ----------------------------------

    def _create_new_doc_and_return(self, docs_service, drive_service, name_prefix: str = "IA_BRUTO"):
        """Crea un nuevo Google Doc y devuelve (doc_id, webViewLink)."""
        new_name = f"{name_prefix} - backup {datetime.datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')}"
        file_metadata = {"name": new_name, "mimeType": "application/vnd.google-apps.document"}
        created = drive_service.files().create(body=file_metadata, fields="id,webViewLink").execute()
        new_id = created.get("id")
        link = created.get("webViewLink")
        self.logger.info("Nuevo Google Doc creado: %s (ID=%s)", new_name, new_id)
        return new_id, link

    def write_google_doc(self, text: str):
        """Intentar escribir en Google Doc; si falla, crear uno nuevo y escribir ahí.
        Siempre escribe copia local de seguridad y guarda nuevo doc id en last_doc_id.txt cuando crea uno nuevo.
        """
        out_fname = pathlib.Path.cwd() / "crawler_output.txt"
        try:
            tmp = out_fname.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(out_fname)
            self.logger.info("Copia local escrita en %s (%d bytes)", out_fname, out_fname.stat().st_size)
        except Exception as e:
            self.logger.exception("Fallo al escribir copia local %s: %s", out_fname, e)

        # If no google key provided, stop here (we have local copy)
        if not self.config.google_key:
            self.logger.info("No se proporcionó google_key; no se intentará subir a Google Docs.")
            return

        try:
            scopes = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]
            creds = service_account.Credentials.from_service_account_file(self.config.google_key, scopes=scopes)
            docs_service = build("docs", "v1", credentials=creds)
            drive_service = build("drive", "v3", credentials=creds)

            target_id = self.config.document_id
            if target_id:
                try:
                    doc = docs_service.documents().get(documentId=target_id).execute()
                    self.logger.info("Acceso a Google Doc objetivo OK. Título: %s", doc.get("title"))
                except HttpError as he:
                    self.logger.warning(
                        "No se puede acceder al doc configurado (ID=%s): %s", target_id, repr(he)
                    )
                    new_id, new_link = self._create_new_doc_and_return(docs_service, drive_service)
                    target_id = new_id
                    self.config.document_id = new_id
                    with open("last_doc_id.txt", "w", encoding="utf-8") as f:
                        f.write(new_id)
                    self.logger.info("Nuevo ID guardado en last_doc_id.txt (ID=%s)", new_id)
            else:
                new_id, new_link = self._create_new_doc_and_return(docs_service, drive_service)
                target_id = new_id
                self.config.document_id = new_id
                with open("last_doc_id.txt", "w", encoding="utf-8") as f:
                    f.write(new_id)
                self.logger.info("Nuevo ID guardado en last_doc_id.txt (ID=%s)", new_id)

            try:
                doc = docs_service.documents().get(documentId=target_id).execute()
                body = doc.get("body", {}).get("content", [])
                if len(body) > 1:
                    end_index = body[-1].get("endIndex", 1)
                    if end_index > 1:
                        docs_service.documents().batchUpdate(
                            documentId=target_id,
                            body={"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}]},
                        ).execute()
                        self.logger.info("Contenido previo eliminado en doc ID=%s", target_id)
            except HttpError as he:
                self.logger.warning("No se pudo limpiar contenido previo del doc ID=%s: %s", target_id, repr(he))

            BLOQUE = 50000
            position = 1
            for i in range(0, len(text), BLOQUE):
                chunk = text[i : i + BLOQUE]
                docs_service.documents().batchUpdate(
                    documentId=target_id,
                    body={"requests": [{"insertText": {"location": {"index": position}, "text": chunk}}]},
                ).execute()
                position += len(chunk)
                self.logger.info("Subido bloque hasta %d caracteres al doc ID=%s", position, target_id)

            self.logger.info("Google Doc (ID=%s) actualizado correctamente.", target_id)

        except HttpError as he:
            self.logger.exception("HttpError al intentar escribir en Google Docs: %s", repr(he))
            try:
                creds = service_account.Credentials.from_service_account_file(self.config.google_key, scopes=scopes)
                docs_service = build("docs", "v1", credentials=creds)
                drive_service = build("drive", "v3", credentials=creds)
                new_id, new_link = self._create_new_doc_and_return(docs_service, drive_service)
                BLOQUE = 50000
                position = 1
                for i in range(0, len(text), BLOQUE):
                    chunk = text[i : i + BLOQUE]
                    docs_service.documents().batchUpdate(
                        documentId=new_id,
                        body={"requests": [{"insertText": {"location": {"index": position}, "text": chunk}}]},
                    ).execute()
                    position += len(chunk)
                self.config.document_id = new_id
                with open("last_doc_id.txt", "w", encoding="utf-8") as f:
                    f.write(new_id)
                self.logger.info("Fallback: nuevo Google Doc creado y escrito (ID=%s). Guardado en last_doc_id.txt", new_id)
            except Exception as e2:
                self.logger.exception("Fallo también al crear/escribir nuevo doc: %s\n%s", e2, traceback.format_exc())
                try:
                    err_fname = pathlib.Path.cwd() / "crawler_output_on_error.txt"
                    with open(err_fname, "w", encoding="utf-8") as f:
                        f.write(text[:1_000_000])
                    self.logger.info("Salida parcial guardada en %s", err_fname)
                except Exception as e3:
                    self.logger.exception("No se pudo escribir %s: %s", "crawler_output_on_error.txt", e3)

        except Exception as e:
            self.logger.exception("Error inesperado al subir a Google Docs: %s\n%s", e, traceback.format_exc())
            try:
                err_fname = pathlib.Path.cwd() / "crawler_output_on_error.txt"
                with open(err_fname, "w", encoding="utf-8") as f:
                    f.write(text[:1_000_000])
                self.logger.info("Salida parcial guardada en %s", err_fname)
            except Exception as e3:
                self.logger.exception("No se pudo escribir %s: %s", "crawler_output_on_error.txt", e3)


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
        google_key=args.google_key if args.google_key and os.path.exists(args.google_key) else None,
        max_pages=args.max_pages,
        concurrency=args.concurrency,
        headless=True,  # keep headless True by default; change here if desired
    )
    crawler = Crawler(cfg)

    async def run():
        await crawler.crawl()

    asyncio.run(run())

    documento = "\n".join(crawler.results)
    # Save/write
    crawler.write_google_doc(documento)
    logging.info("Proceso terminado. Páginas visitadas: %d", len(crawler.visited))


if __name__ == "__main__":
    main()
