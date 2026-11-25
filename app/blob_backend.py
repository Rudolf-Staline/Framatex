"""Private document blob adapter: local disk or authenticated Supabase Storage.

The remote bucket is never made public. Business authorization remains in the
FastAPI routes; this module only receives opaque random blob names. Both backends
return local paths for the existing isolated file-inspection workers.
"""
from __future__ import annotations

import os
import re
import secrets
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests
from fastapi import HTTPException


_NAME = re.compile(r'[a-f0-9]{48}\Z')
_BUCKET = re.compile(r'[a-z][a-z0-9-]{0,62}\Z')


def remote_enabled() -> bool:
    value = os.getenv('FRAMATEX_STORAGE_BACKEND', 'local').lower().strip()
    if value not in {'local', 'supabase'}:
        raise RuntimeError('FRAMATEX_STORAGE_BACKEND invalide')
    if os.getenv('VERCEL') and value != 'supabase':
        raise RuntimeError('FRAMATEX_STORAGE_BACKEND=supabase est obligatoire sur Vercel')
    return value == 'supabase'


def _settings() -> tuple[str, str, dict[str, str]]:
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or
            not re.fullmatch(r'[a-z0-9-]+\.supabase\.co', parsed.hostname) or
            parsed.port is not None or parsed.username is not None or
            parsed.password is not None or parsed.path or parsed.query or parsed.fragment):
        raise RuntimeError('SUPABASE_URL doit être une URL de projet Supabase HTTPS')
    bucket = os.getenv('SUPABASE_STORAGE_BUCKET', 'framat-documents')
    if not _BUCKET.fullmatch(bucket):
        raise RuntimeError('Nom de bucket privé invalide')
    key = os.getenv('SUPABASE_SECRET_KEY', '')
    if not key:
        raise RuntimeError('SUPABASE_SECRET_KEY est obligatoire pour le stockage distant')
    headers = {'apikey': key}
    # New sb_secret_* API keys must NOT be sent as Bearer JWTs.
    if key.count('.') == 2 and not key.startswith('sb_'):
        headers['Authorization'] = 'Bearer ' + key
    return url, bucket, headers


def _endpoint(name: str) -> tuple[str, dict[str, str]]:
    if not _NAME.fullmatch(name):
        raise ValueError('Identifiant de fichier privé invalide')
    url, bucket, headers = _settings()
    prefix = 'bilal-preview-v1' if os.getenv('VERCEL_ENV') == 'preview' else 'bilal-v1'
    return f'{url}/storage/v1/object/{quote(bucket)}/{prefix}/{name}', headers


def upload(local_path: Path, name: str, mime: str) -> None:
    url, headers = _endpoint(name)
    headers = {**headers, 'Content-Type': mime, 'x-upsert': 'false'}
    try:
        with local_path.open('rb') as file:
            result = requests.post(url, headers=headers, data=file, timeout=(5, 40), allow_redirects=False)
    except requests.RequestException as exc:
        raise HTTPException(503, 'Stockage documentaire distant indisponible') from exc
    if result.status_code == 409:
        raise HTTPException(409, 'Objet documentaire déjà présent')
    if result.status_code not in (200, 201):
        raise HTTPException(503, 'Enregistrement du document distant impossible')


def download(cache_dir: Path, name: str, *, maximum_size: int = 100 * 1024 * 1024) -> Path:
    url, headers = _endpoint(name)
    # The downloaded path is a local cache, not the authoritative document.
    cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = cache_dir / name
    if target.is_file() and 0 < target.stat().st_size <= maximum_size:
        return target
    tmp = cache_dir / ('.download-' + secrets.token_hex(16))
    try:
        try:
            with requests.get(url, headers=headers, timeout=(5, 40), stream=True, allow_redirects=False) as response:
                if response.status_code == 404:
                    raise HTTPException(503, 'Fichier distant introuvable')
                if response.status_code != 200:
                    raise HTTPException(503, 'Lecture du document distant impossible')
                size = 0
                descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'wb') as out:
                    for part in response.iter_content(1024 * 1024):
                        size += len(part)
                        if size > maximum_size:
                            raise HTTPException(503, 'Document distant supérieur à la limite admise')
                        out.write(part)
                if size == 0:
                    raise HTTPException(503, 'Document distant vide')
                os.replace(tmp, target)
        except requests.RequestException as exc:
            raise HTTPException(503, 'Lecture du document distant impossible') from exc
        return target
    finally:
        tmp.unlink(missing_ok=True)


def delete(name: str) -> None:
    url, headers = _endpoint(name)
    try:
        response = requests.delete(url, headers=headers, timeout=(5, 20), allow_redirects=False)
    except requests.RequestException as exc:
        raise HTTPException(503, 'Suppression distante impossible') from exc
    # Idempotent cleanup, including a blob already removed from the bucket.
    if response.status_code not in (200, 204, 404):
        raise HTTPException(503, 'Suppression distante impossible')


def publish(path: Path, mime: str) -> None:
    """Persist verified uploads before committing database metadata."""
    if remote_enabled():
        upload(path, path.name, mime)


def resolve(directory: Path, name: str) -> Path:
    if not _NAME.fullmatch(name):
        raise HTTPException(503, 'Identifiant de fichier invalide')
    return download(directory, name) if remote_enabled() else directory / name


def discard(directory: Path, name: str) -> None:
    """Clean uncommitted/expired uploads. Never call on a published version."""
    if not _NAME.fullmatch(name):
        raise ValueError('Identifiant de fichier invalide')
    if remote_enabled():
        delete(name)
    (directory / name).unlink(missing_ok=True)


def validate_configuration() -> None:
    if remote_enabled():
        _settings()
