#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawler_crucemundo.py - Crawler mejorado para crucemundo.es
- Extrae el contenido principal y limpia ruido antes de guardar
- Concurrency control (multiple workers)
- Cola asincrónica y deduplicación
- Normalización de URLs
- Manejo de errores y reintentos
- Escritura local atómica periódica (flush intermedio)
- Subida a Google Docs/Drive vía Service Account o OAuth usuario
- Fallback: si Drive falla por cuota, sube a Google Cloud Storage (bucket configurado)
- Guarda last_doc_id.txt si crea uno nuevo
- NUEVO: guarda visited_urls.txt (orden de visita) y opcionalmente lo sube a GCS o Drive
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
import tempfile
import time
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

# Drive resumable upload
from googleapiclient.http import MediaFileUpload

# Google Cloud Storage client for fallback
from google.cloud import storage

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
DEFAULT_URLS_OUT = "visited_urls.txt"


@dataclass
class CrawlerConfig:
    start_url: str
    domain: str
    document_id: Optional[str] = None
    google_key: Optional[str] = None  # service account json path
    client_secrets: Optional[str] = None  # oauth client secrets for user flow
    use_user_oauth: bool = False
    drive_folder_id: Optional[str] = None
    gcs_bucket: Optional[str] = None
    out_path: str = DEFAULT_OUT
    urls_out: str = DEFAULT_URLS_OUT
    max_pages: int = 1000
    concurrency: int = 3
    headless: bool = True
    wait_after_load_ms: int = 800
    user_agent: str = "CrucemundoCrawler/1.0 (+https://crucemundo.es)"
    flush_every: int = 50  # guardar intermedio cada N páginas


# ----------------------------------
# Utilities: Google credentials
# ----------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
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
        self.visited: Set[str] = set()        # for fast membership checks
        self.visited_list: List[str] = []     # preserve order of visits
        self.results: List[str] = []
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.logger = logging.getLogger("crawler")
        self.logger.setLevel(logging.INFO)

        # flush control (guarda intermedio cada N páginas)
        self._pages_since_flush = 0
        self._flush_every = getattr(config, "flush_every", 50)

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
        # fallback: extrae todo el texto sin limpieza heurística
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            tag.extract()
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text

    # --- Limpieza inteligente del contenido principal ---
    def clean_text(self, text: str) -> str:
        """
        Limpia ruido del texto:
        - Colapsa espacios
        - Filtra frases cortas repetidas
        - Quita líneas tipo lista extensas (muchas comas)
        - Quita bloques con demasiadas palabras capitalizadas (menús)
        - Elimina párrafos que contienen muchas palabras/keywords de navegación/reserva
        Devuelve texto con párrafos separados por salto de línea simple.
        """
        if not text:
            return ""

        text = re.sub(r"\s+", " ", text).strip()
        # fragmentar por oraciones/segmentos para filtrar
        segments = re.split(r"(?<=[\.\!\?])\s+", text)

        cleaned = []
        short_seen = {}
        junk_keywords = [
            "resérvalo", "reservar", "home", "inicio", "contacto", "hable",
            "buscar", "reservas", "login", "usuario", "password", "cookies",
            "aceptar", "política", "condiciones", "mensaje enviado", "teléfono",
            "whatsapp", "reservas", "ofertas", "últimas", "síguenos", "suscríbete"
        ]

        for seg in segments:
            s = seg.strip()
            if not s:
                continue

            low = s.lower()

            # 1) Filtrar repeticiones de frases muy cortas (evitar menús repetidos)
            if len(s) < 30:
                key = re.sub(r"\s+", " ", low)
                short_seen[key] = short_seen.get(key, 0) + 1
                if short_seen[key] > 2:
                    continue

            # 2) Filtrar listas muy largas separadas por comas (p. ej. listado de países)
            if s.count(",") > 6 and len(s.split()) > 20:
                continue

            # 3) Filtrar bloques con demasiadas palabras Capitalizadas (menus / cabeceras)
            words = s.split()
            cap_words = sum(1 for w in words if w and w[0].isupper())
            if len(words) and cap_words > max(10, len(words) * 0.6):
                continue

            # 4) Filtrar si contiene muchas de las palabras junk
            if sum(1 for kw in junk_keywords if kw in low) >= 2:
                continue

            # 5) Filtrar líneas que son muy cortas y no aportan contenido (p. ej. "Home", "Reservar")
            if len(s) < 8 and s.isalpha():
                continue

            cleaned.append(s)

        # Unir en párrafos (doble salto para legibilidad)
        out = "\n\n".join(cleaned)

        # Eliminar duplicados consecutivos
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        dedup = []
        for ln in lines:
            if not dedup or ln != dedup[-1]:
                dedup.append(ln)

        return "\n".join(dedup)

    def extract_main_text(self, html: str) -> str:
        """
        Intenta localizar el contenido principal de la página:
        - Prioriza <article> y <main>
        - Busca div/section con id/class que contengan 'content', 'main', 'article', 'post', 'entry', 'page', 'body'
        - Si no hay candidatos, usa el body limpiado
        Luego pasa el texto por clean_text().
        """
        soup = BeautifulSoup(html, "html.parser")

        # Eliminar bloques obvios
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
            tag.decompose()

        candidates = []

        # 1) article / main
        for sel in ("article", "main"):
            for node in soup.find_all(sel):
                txt = node.get_text(" ", strip=True)
                if len(txt) > 120:
                    candidates.append(txt)

        # 2) div/section con ids/classes que sugieran contenido principal
        pattern = re.compile(r"(content|main|article|post|entry|page|body|texto|contenido|detalle)", re.I)
        for node in soup.find_all(["div", "section"]):
            node_id = node.get("id") or ""
            classes = " ".join(node.get("class") or [])
            if pattern.search(node_id) or pattern.search(classes):
                txt = node.get_text(" ", strip=True)
                if len(txt) > 120:
                    candidates.append(txt)

        # 3) fallback: tomar el elemento con mayor cantidad de texto (heurística)
        if not candidates:
            max_text = ""
            for node in soup.find_all(["div", "section", "body"]):
                txt = node.get_text(" ", strip=True)
                if len(txt) > len(max_text):
                    max_text = txt
            if max_text:
                candidates.append(max_text)

        # seleccionar el candidato más largo
        if candidates:
            best = max(candidates, key=lambda s: len(s))
        else:
            best = soup.get_text(" ", strip=True)

        return self.clean_text(best)

    def _maybe_flush_results(self):
        """Guarda resultados parciales en el fichero local cada _flush_every páginas."""
        self._pages_since_flush += 1
        if self._pages_since_flush >= self._flush_every:
            try:
                out = "\n".join(self.results)
                out_path = pathlib.Path(self.config.out_path)
                tmp = out_path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(out)
                    f.flush()
                    os.fsync(f.fileno())
                tmp.replace(out_path)
                self.logger.info("Flush intermedio guardado en %s (%d bytes)", out_path, out_path.stat().st_size)
            except Exception:
                self.logger.exception("Error guardando flush intermedio")
            finally:
                self._pages_since_flush = 0

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

                # Usar el extractor "principal" y limpieza antes de guardar
                texto = self.extract_main_text(html)

                self.results.append(
                    "\n\n========================================\n\n"
                    f"URL:\n{url}\n\nTITULO:\n{title}\n\n\nCONTENIDO:\n\n{texto}\n\n"
                    "========================================\n\n"
                )

                # flush intermedio
                self._maybe_flush_results()

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
                # mark visited (set + ordered list)
                self.visited.add(url)
                self.visited_list.append(url)
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

    def _upload_to_gcs(self, local_path: pathlib.Path, bucket_name: str, dest_name: Optional[str] = None):
        """Sube local_path a gs://{bucket_name}/{dest_name} usando las credenciales del runner."""
        try:
            if not bucket_name:
                self.logger.error("GCS bucket no proporcionado.")
                return False
            dest_name = dest_name or local_path.name
            # If credentials.json exists and GOOGLE_APPLICATION_CREDENTIALS not set, set it
            if os.path.exists("credentials.json") and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath("credentials.json")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(dest_name)
            blob.upload_from_filename(str(local_path))
            self.logger.info("Subido a GCS: gs://%s/%s", bucket_name, dest_name)
            return True
        except Exception as e:
            self.logger.exception("Fallo subiendo a GCS: %s", e)
            return False

    def _upload_text_via_drive_media(self, drive_service, text: str, name_prefix: str = "IA_BRUTO"):
        """Sube el texto como archivo .txt y solicita conversión a Google Docs en una sola llamada."""
        try:
            tmp = pathlib.Path(tempfile.gettempdir()) / f"crawler_upload_{int(time.time())}.txt"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            file_metadata = {
                "name": f"{name_prefix} - backup {datetime.datetime.utcnow().strftime('%Y-%m-%d_%H%M%S')}",
                "mimeType": "application/vnd.google-apps.document",  # pide conversión a Google Doc
            }
            media = MediaFileUpload(str(tmp), mimetype="text/plain", resumable=True)
            created = drive_service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
            return created.get("id"), created.get("webViewLink")
        except Exception as e:
            self.logger.exception("Fallo subiendo via MediaFileUpload: %s", e)
            raise

    def write_google_doc(self, text: str):
        """Escribe en Google Doc usando oAuth de usuario o service account según configuración.
        Siempre escribe copia local atómica (self.config.out_path).
        Si doc objetivo existe y hay permisos, lo sobrescribe. Si no y hay cuota, crea uno nuevo y guarda last_doc_id.txt.
        Si Drive falla por cuota, intenta fallback a GCS si se configuró bucket.
        Para archivos grandes usa MediaFileUpload para convertir a Google Doc en una sola petición.
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
            if not self.config.google_key:
                self.logger.info("No se proporcionó google_key ni uso de OAuth usuario; no se intentará subir.")
                return
            try:
                creds = load_service_account_creds(self.config.google_key)
            except Exception as e:
                self.logger.exception("No se pudieron cargar credenciales de service account: %s", e)
                return

        try:
            docs_service = build("docs", "v1", credentials=creds)
            drive_service = build("drive", "v3", credentials=creds)
        except Exception as e:
            self.logger.exception("No se pudieron construir servicios de Google APIs: %s", e)
            return

        quota_info = self._get_drive_quota(drive_service)
        if quota_info:
            self.logger.info("Drive quota: limit=%s usage=%s remaining=%s", quota_info["limit"], quota_info["usage"], quota_info["remaining"])
        else:
            self.logger.info("Drive quota info no disponible (remaining=None)")

        target_id = self.config.document_id

        # If there is a target_id, try to overwrite it (by deleting contents then inserting),
        # otherwise, use a single MediaFileUpload conversion to create new doc.
        if target_id:
            try:
                doc = docs_service.documents().get(documentId=target_id).execute()
                self.logger.info("Acceso a Google Doc objetivo OK. Título: %s", doc.get("title"))
                body = doc.get("body", {}).get("content", [])
                if len(body) > 1:
                    end_index = body[-1].get("endIndex", 1)
                    if end_index > 1:
                        docs_service.documents().batchUpdate(
                            documentId=target_id,
                            body={"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}]},
                        ).execute()
                        self.logger.info("Contenido previo eliminado en doc ID=%s", target_id)
                # Insert in reasonable-size chunks to avoid enormous requests
                BLOQUE = 100000  # aumentar a 100k para reducir llamadas
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
                if "storageQuotaExceeded" in err:
                    self.logger.error("Quota de Drive excedida; no se intentará crear otro documento.")
                    # Try fallback to GCS
                    gcs_bucket = self.config.gcs_bucket or os.getenv("GCS_BUCKET")
                    if gcs_bucket and out_fname.exists():
                        dest = f"crawler_output_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
                        ok = self._upload_to_gcs(out_fname, gcs_bucket, dest_name=dest)
                        if ok:
                            self.logger.info("Fallback: archivo subido a GCS: gs://%s/%s", gcs_bucket, dest)
                        else:
                            self.logger.error("Fallback a GCS falló.")
                    else:
                        self.logger.info("No se configuró GCS_BUCKET; no se intentó subir a GCS.")
                    return
                # otherwise continue to try creating a new doc
            except Exception as e:
                self.logger.exception("Error al acceder/actualizar doc objetivo: %s", e)
                # continue to try to create new doc

        # Create new doc using MediaFileUpload to convert .txt -> Google Doc in single request
        try:
            new_id, new_link = self._upload_text_via_drive_media(drive_service, text)
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
                # Try fallback to GCS
                gcs_bucket = self.config.gcs_bucket or os.getenv("GCS_BUCKET")
                if gcs_bucket and out_fname.exists():
                    dest = f"crawler_output_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
                    ok = self._upload_to_gcs(out_fname, gcs_bucket, dest_name=dest)
                    if ok:
                        self.logger.info("Fallback: archivo subido a GCS: gs://%s/%s", gcs_bucket, dest)
                    else:
                        self.logger.error("Fallback a GCS falló.")
                else:
                    self.logger.info("No se configuró GCS_BUCKET; no se intentó subir a GCS.")
            return
        except Exception as e:
            self.logger.exception("Fallo creando nuevo doc: %s", traceback.format_exc())
            # As last resort, save partial large output
            try:
                err_fname = pathlib.Path(DEFAULT_ON_ERROR_OUT)
                with open(err_fname, "w", encoding="utf-8") as f:
                    f.write(text[:1_000_000])
                self.logger.info("Salida parcial guardada en %s", err_fname)
            except Exception as e3:
                self.logger.exception("No se pudo escribir %s: %s", DEFAULT_ON_ERROR_OUT, e3)
            return

    # -----------------------
    # New: write visited URLs
    # -----------------------
    def write_visited_urls(self, urls_out: Optional[str] = None, upload_gcs: bool = False, upload_drive: bool = False, drive_key: Optional[str] = None):
        """
        Escribe self.visited_list en urls_out (una URL por línea con timestamp).
        Si upload_gcs=True y config.gcs_bucket presente, intenta subir el fichero a GCS.
        Si upload_drive=True and drive_key provided, intenta crear un Google Doc con el contenido (conversion).
        """
        urls_out = urls_out or self.config.urls_out
        p = pathlib.Path(urls_out)
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"# Visited URLs - start={self.config.start_url} domain={self.config.domain} generated_at={ts}\n")
                for u in self.visited_list:
                    f.write(u + "\n")
            self.logger.info("Visited URLs written to %s (%d urls)", p, len(self.visited_list))
        except Exception as e:
            self.logger.exception("Error writing visited URLs file %s: %s", p, e)
            return

        # Try upload to GCS if requested
        if upload_gcs:
            bucket = self.config.gcs_bucket or os.getenv("GCS_BUCKET")
            if bucket:
                try:
                    ok = self._upload_to_gcs(p, bucket, dest_name=f"visited_urls_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt")
                    if ok:
                        self.logger.info("Visited URLs uploaded to GCS: gs://%s/%s", bucket, p.name)
                except Exception as e:
                    self.logger.exception("Failed uploading visited URLs to GCS: %s", e)
            else:
                self.logger.warning("upload_gcs requested but no GCS bucket configured (config.gcs_bucket or env GCS_BUCKET)")

        # Try create Google Doc if requested
        if upload_drive:
            key = drive_key or self.config.google_key or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not key:
                self.logger.warning("upload_drive requested but no google_key provided")
            else:
                try:
                    creds = load_service_account_creds(key)
                    drive_service = build("drive", "v3", credentials=creds)
                    # read file content
                    with open(p, "r", encoding="utf-8") as f:
                        txt = f.read()
                    new_id, link = self._upload_text_via_drive_media(drive_service, txt, name_prefix="Visited_URLs")
                    self.logger.info("Visited URLs Google Doc created: ID=%s link=%s", new_id, link)
                except Exception as e:
                    self.logger.exception("Failed creating Google Doc for visited URLs: %s", e)


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
    p.add_argument("--gcs-bucket", default=os.getenv("GCS_BUCKET", None), help="Nombre del bucket GCS para fallback (opcional)")
    p.add_argument("--out", default=DEFAULT_OUT, help="Ruta local de salida (crawler_output.txt por defecto)")
    p.add_argument("--urls-out", default=DEFAULT_URLS_OUT, help="Ruta local para guardar visited URLs (visited_urls.txt por defecto)")
    p.add_argument("--upload-urls-gcs", action="store_true", help="Subir visited_urls.txt a GCS (requiere --gcs-bucket o env GCS_BUCKET)")
    p.add_argument("--upload-urls-drive", action="store_true", help="Crear Google Doc con visited_urls.txt (requiere --google-key o GOOGLE_APPLICATION_CREDENTIALS)")
    p.add_argument("--max-pages", type=int, default=500, help="Max páginas a rastrear")
    p.add_argument("--concurrency", type=int, default=3, help="Número de workers concurrentes")
    p.add_argument("--headless", action="store_true", help="Forzar headless (útil en CI). Si no hay DISPLAY se activará automáticamente.")
    p.add_argument("--no-headless", action="store_true", help="Forzar modo con interfaz (requiere DISPLAY/X server)")
    p.add_argument("--flush-every", type=int, default=None, help="Guardar intermedio cada N páginas (opcional)")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)

    # Determine headless behavior:
    if args.headless:
        headless_flag = True
    elif args.no_headless:
        headless_flag = False
    else:
        headless_flag = os.environ.get("DISPLAY") is None

    cfg = CrawlerConfig(
        start_url=args.start,
        domain=args.domain,
        document_id=args.document_id,
        google_key=args.google_key if args.google_key and os.path.exists(args.google_key) else None,
        client_secrets=args.client_secrets if args.client_secrets and os.path.exists(args.client_secrets) else None,
        use_user_oauth=args.use_user_oauth,
        drive_folder_id=args.drive_folder_id,
        gcs_bucket=args.gcs_bucket,
        out_path=args.out,
        urls_out=args.urls_out,
        max_pages=args.max_pages,
        concurrency=args.concurrency,
        headless=headless_flag,
    )
    if args.flush_every:
        cfg.flush_every = args.flush_every

    crawler = Crawler(cfg)

    logging.getLogger("crawler").info(
        "Iniciando crawler - start=%s domain=%s concurrency=%d max_pages=%d out=%s urls_out=%s use_user_oauth=%s headless=%s gcs_bucket=%s flush_every=%s",
        cfg.start_url, cfg.domain, cfg.concurrency, cfg.max_pages, cfg.out_path, cfg.urls_out, cfg.use_user_oauth, cfg.headless, cfg.gcs_bucket, cfg.flush_every
    )

    async def run():
        await crawler.crawl()

    asyncio.run(run())

    documento = "\n".join(crawler.results)
    crawler.write_google_doc(documento)

    # write visited URLs and optionally upload
    crawler.write_visited_urls(urls_out=cfg.urls_out, upload_gcs=args.upload_urls_gcs, upload_drive=args.upload_urls_drive, drive_key=cfg.google_key)

    logging.info("Proceso terminado. Páginas visitadas: %d", len(crawler.visited_list))


if __name__ == "__main__":
    main()
