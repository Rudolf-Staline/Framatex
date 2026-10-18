"""Private Supabase Storage adapter for the future Framatex online demo.

Only the FastAPI server possesses the service credential.  No public bucket,
signed URL, or browser-side key is used.  Application ACLs are checked before
these functions are called.  Temporary copies live in the ephemeral data dir.
"""
from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import HTTPException

MAX_FILE_BYTES = 20 * 1024 * 1024
_KEY_RE = re.compile(r"[0-9a-f]{48}\Z")


def enabled() -> bool:
    return os.getenv("FRAMATEX_STORAGE_BACKEND", "local") == "supabase"


def _config():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SECRET_KEY", "")
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "framat-documents")
    if not url.startswith("https://") or not key or not re.fullmatch(r"[a-z0-9-]{3,60}", bucket):
        raise RuntimeError("Supabase Storage: SUPABASE_URL, SUPABASE_SECRET_KEY et bucket prive requis")
    return url, key, bucket


def _endpoint(key: str, authenticated: bool = False) -> tuple[str, dict]:
    if not _KEY_RE.fullmatch(key):
        raise ValueError("Identifiant de document non conforme")
    base, secret, bucket = _config()
    section = "authenticated/" if authenticated else ""
    return (f"{base}/storage/v1/object/{section}{quote(bucket)}/{key}",
            {"Authorization": f"Bearer {secret}", "apikey": secret})


def upload_local(key: str, path: Path):
    if not enabled():
        return
    uri, headers = _endpoint(key)
    headers = {**headers, "Content-Type": "application/octet-stream", "x-upsert": "false"}
    try:
        with httpx.Client(timeout=45) as client, path.open("rb") as f:
            response = client.post(uri, headers=headers, content=f)
        if response.status_code not in (200, 201):
            raise HTTPException(503, "Le stockage documentaire est indisponible")
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Stockage documentaire inaccessible") from exc


def ensure_local(key: str, root: Path) -> Path:
    """Return an ephemeral copy when cloud mode is enabled; never expose its URL."""
    path = root / key
    if not enabled() or path.is_file():
        return path
    uri, headers = _endpoint(key, authenticated=True)
    temp = root / ("download-" + secrets.token_hex(12))
    root.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.Client(timeout=45) as client, client.stream("GET", uri, headers=headers) as response:
            if response.status_code == 404:
                return path
            if response.status_code != 200:
                raise HTTPException(503, "Le document distant est temporairement indisponible")
            length = 0
            with temp.open("xb") as f:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    length += len(chunk)
                    if length > MAX_FILE_BYTES:
                        raise HTTPException(503, "Fichier distant au-dela de la taille autorisee")
                    f.write(chunk)
        temp.replace(path)
        return path
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Impossible de lire le document distant") from exc
    finally:
        temp.unlink(missing_ok=True)


def remove(key: str, root: Path):
    local = root / key
    if enabled():
        uri, headers = _endpoint(key)
        try:
            with httpx.Client(timeout=20) as client:
                response = client.delete(uri, headers=headers)
            if response.status_code not in (200, 204, 404):
                raise HTTPException(503, "La suppression du fichier distant a echoue")
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Impossible de joindre le stockage distant") from exc
    local.unlink(missing_ok=True)


def assert_ready():
    if not enabled():
        return
    _config()
