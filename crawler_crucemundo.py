#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawler.py - Crawler mejorado para crucemundo.es
- Concurrency control (multiple workers)
- Cola asincrónica y deduplicación
- Normalización de URLs
- Manejo de errores y reintentos
- Escritura local atómica
- Subida a Google Docs/Drive vía Service Account o OAuth usuario
- Si el doc objetivo no es accesible, puede crear uno nuevo (si hay cuota)
- Guarda last_doc_id.txt si crea uno nuevo

Requisitos:
pip install playwright beautifulsoup4 google-api-python-client google-auth google-auth-oauthlib unidecode
python -m playwright install chromium
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
import json
from dataclasses import dataclass
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Google APIs
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.exceptions

# ----------------------------------
# Config / Defaults
# ----------------------------------

EXT_RESOURCES_RE = re.compile(
    r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|bmp|css|js|woff|ttf)$", re.I
)
EXT_DOCS_RE = re.compile(r"\.(?:pdf|doc|docx|xls|xlsx|zip)$", re.I)

DEFAULT_OUT = "crawler_output.txt"
DEFAULT_ON_ERROR_OUT = "crawler_output_on_error.txt"
LAST_DOC_ID = "last_doc_id.txt"
TOKEN_CACHE = "token_user.json"


@dataclass
class CrawlerConfig:
    start_url: str
    domain: str
    document_id: Optional[str] = None
    google_key: Optional[str] = None  # service account json path
    client_secrets: Optional[str] = None  # oauth client secrets for user flow
    use_user_oauth: bool = False
    drive_folder_id: Optional[str] = None
    out_path: str = DEFAULT_OUT
    max_pages: int = 1000
    concurrency: int = 3
    headless: bool = True
    wait_after_load_ms: int = 800
    user_agent: str = "CrucemundoCrawler/1.0 (+https://crucemundo.es)"


# ----------------------------------
# Utilities: Google credentials
# ----------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    # if you only need readonly support, change scopes accordingly
]


def load_service_account_creds(key_path: str):
    if not key_path or not os.path.exists(key_path):
        raise FileNotFoundError(f"Service account key not found: {key_path}")
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return creds


def load_user_oauth_creds(client_secrets_path: str):
    """
    Runs an installed app flow (interactive) and caches token in TOKEN_CACHE.
    Useful for local runs where you want the user's Drive quota to be used.
    """
    if not client_secrets_path or not os.path.exists(client_secrets_path):
        raise FileNotFoundError(f"Client secrets file not found: {client_secrets_path}")

    creds = None
    if os.path.exists(TOKEN_CACHE):
        try:
            with open(TOKEN_CACHE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Build credentials from saved token - use google.oauth2.credentials if needed
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_info(data, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save for next time
        try:
            with open(TOKEN_CACHE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            pass
    return creds


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
    # Google Docs writer + helpers (usuario o service account)
    # ----------------------------------

    def _create_new_doc_and_return(self, docs_service, drive_service, name_prefix: str = "IA_BRUTO"):
        """Crea un nuevo Google Doc y devuelve (doc_id, webViewLink)."""
        new_name = f"{name_prefix} - backup {datetime.datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')}"
        file_metadata = {"name": new_name, "mimeType": "application/vnd.google-apps.document"}
        # Si el usuario proporcionó folder id, colócalo allí
        if self.config.drive_folder_id:
            file_metadata["parents"] = [self.config.drive_folder_id]
        created = drive_service.files().create(body=file_metadata, fields="id,webViewLink").execute()
        new_id = created.get("id")
        link = created.get("webViewLink")
        self.logger.info("Nuevo Google Doc creado: %s (ID=%s)", new_name, new_id)
        return new_id, link

    def _get_drive_quota(self, drive_service):
        try:
            about = drive_service.about().get(fields="storageQuota").execute()
            quota = about.get("storageQuota", {})
            limit = int(quota.get("limit") or 0)
            usage = int(quota.get("usage") or 0)
            remaining = (limit - usage) if limit > 0 else None
            return {"limit": limit, "usage": usage, "remaining": remaining}
        except Exception as e:
            self.logger.debug("No se pudo obtener cuota de Drive: %s", repr(e))
            return None

    def write_google_doc(self, text: str):
        """Escribe en Google Doc usando oAuth de usuario o service account según configuración.
        Siempre escribe copia local atómica (self.config.out_path).
        Si doc objetivo existe y hay permisos, lo sobrescribe. Si no y hay cuota, crea uno nuevo y guarda last_doc_id.txt.
        """
        out_fname = pathlib.Path(self.config.out_path)
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

        # Decide qué credenciales usar
        creds = None
        docs_service = None
        drive_service = None

        if self.config.use_user_oauth:
            try:
                creds = load_user_oauth_creds(self.config.client_secrets)
            except Exception as e:
                self.logger.exception("No se pudieron obtener credenciales de usuario OAuth: %s", e)
                self.logger.info("Se mantiene copia local y se aborta intento de subida.")
                return
        else:
            # service account mode (if provided)
            if not self.config.google_key:
                self.logger.info("No se proporcionó google_key ni uso de OAuth usuario; no se intentará subir.")
                return
            try:
                creds = load_service_account_creds(self.config.google_key)
            except Exception as e:
                self.logger.exception("No se pudieron cargar credenciales de service account: %s", e)
                return

        # Build services
        try:
            docs_service = build("docs", "v1", credentials=creds)
            drive_service = build("drive", "v3", credentials=creds)
        except Exception as e:
            self.logger.exception("No se pudieron construir servicios de Google APIs: %s", e)
            return

        # Check drive quota (informativo)
        quota_info = self._get_drive_quota(drive_service)
        if quota_info:
            self.logger.info("Drive quota: limit=%s usage=%s remaining=%s", quota_info["limit"], quota_info["usage"], quota_info["remaining"])

        target_id = self.config.document_id

        # If there's a target id, try to write into it
        if target_id:
            try:
                doc = docs_service.documents().get(documentId=target_id).execute()
                self.logger.info("Acceso a Google Doc objetivo OK. Título: %s", doc.get("title"))
                # remove previous content (between 1 and endIndex-1)
                body = doc.get("body", {}).get("content", [])
                if len(body) > 1:
                    end_index = body[-1].get("endIndex", 1)
                    if end_index > 1:
                        docs_service.documents().batchUpdate(
                            documentId=target_id,
                            body={"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}]},
                        ).execute()
                        self.logger.info("Contenido previo eliminado en doc ID=%s", target_id)
                # Insert text in blocks
                BLOQUE = 50000
                position = 1
                for i in range(0, len(text), BLOQUE):
                    chunk = text[i : i + BLOQUE]
                    docs_service.documents().batchUpdate(
                        documentId=target_id,
                        body={"requests": [{"insertText": {"location": {"index": position}, "text": chunk}}]},
                    ).execute()
                    position += len(chunk)
                self.logger.info("Google Doc (ID=%s) actualizado correctamente.", target_id)
                return
            except HttpError as he:
                err = repr(he)
                self.logger.warning("No se pudo escribir en doc objetivo (ID=%s): %s", target_id, err)
                # if quota exceeded, bail out early
                if "storageQuotaExceeded" in err:
                    self.logger.error("Quota de Drive excedida; no se intentará crear otro documento.")
                    return
                # else continue and maybe try create new doc

            except Exception as e:
                self.logger.exception("Error al acceder/actualizar doc objetivo: %s", e)
                # continue to try to create new doc if possible

        # If we reach here, either no target_id or failed to use it; try to create new doc if quota allows
        if quota_info and quota_info.get("remaining") is not None:
            # Simple heuristic: if remaining is zero or negative, avoid creating
            if quota_info["remaining"] <= 0:
                self.logger.error("Drive sin espacio disponible (remaining=%s). No se creará nuevo documento.", quota_info["remaining"])
                return

        # Create new doc
        try:
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
            with open(LAST_DOC_ID, "w", encoding="utf-8") as f:
                f.write(new_id)
            self.logger.info("Nuevo Google Doc creado y escrito (ID=%s). Guardado en %s", new_id, LAST_DOC_ID)
            return
        except HttpError as he:
            err = repr(he)
            self.logger.exception("HttpError al intentar crear nuevo doc: %s", err)
            if "storageQuotaExceeded" in err:
                self.logger.error("Drive quota exceeded al crear doc; manteniendo copia local.")
            return
        except Exception as e:
            self.logger.exception("Fallo creando nuevo doc: %s", traceback.format_exc())
            return


# ----------------------------------
# CLI / Entrypoint
# ----------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawler mejorado para crucemundo.es")
    p.add_argument("--start", default="https://crucemundo.es/", help="URL inicial")
    p.add_argument("--domain", default="crucemundo.es", help="Dominio permitido")
    p.add_argument("--document-id", default=os.getenv("CRUCEMUNDO_DOC_ID", None), help="Google Document ID (opcional)")
    p.add_argument("--google-key", default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json"), help="Ruta a service account JSON")
    p.add_argument("--client-secrets", default=os.getenv("CLIENT_SECRETS", "client_secrets.json"), help="Ruta a client_secrets.json (OAuth user flow)")
    p.add_argument("--use-user-oauth", action="store_true", help="Usar OAuth de usuario (interactive) en vez de service account")
    p.add_argument("--drive-folder-id", default=None, help="ID de carpeta en Drive donde crear nuevos docs (opcional)")
    p.add_argument("--out", default=DEFAULT_OUT, help="Ruta local de salida (crawler_output.txt por defecto)")
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
        client_secrets=args.client_secrets if args.client_secrets and os.path.exists(args.client_secrets) else None,
        use_user_oauth=args.use_user_oauth,
        drive_folder_id=args.drive_folder_id,
        out_path=args.out,
        max_pages=args.max_pages,
        concurrency=args.concurrency,
        headless=args.headless,
    )
    crawler = Crawler(cfg)

    # Log startup info
    logging.getLogger("crawler").info("Iniciando crawler - start=%s domain=%s concurrency=%d max_pages=%d out=%s use_user_oauth=%s",
                                      cfg.start_url, cfg.domain, cfg.concurrency, cfg.max_pages, cfg.out_path, cfg.use_user_oauth)

    async def run():
        await crawler.crawl()

    asyncio.run(run())

    documento = "\n".join(crawler.results)
    # Save/write
    crawler.write_google_doc(documento)
    logging.info("Proceso terminado. Páginas visitadas: %d", len(crawler.visited))


if __name__ == "__main__":
    main()
