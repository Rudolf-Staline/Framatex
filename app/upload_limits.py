import os
from pathlib import Path
import re

from fastapi import HTTPException
from starlette.responses import JSONResponse

MIB = 1024 * 1024
DEFAULTS = {'PDF': 200, 'EXCEL': 100, 'WORD': 100, 'IMAGE': 50, 'OTHER': 20}
GROUPS = {'.pdf': 'PDF', '.xlsx': 'EXCEL', '.docx': 'WORD', '.png': 'IMAGE',
          '.jpg': 'IMAGE', '.jpeg': 'IMAGE', '.txt': 'OTHER', '.eml': 'OTHER', '.csv': 'OTHER'}


def limits_mib():
    limits = {}
    for group, default in DEFAULTS.items():
        key = f'FRAMATEX_UPLOAD_{group}_MIB'
        try:
            limit = int(os.getenv(key, str(default)))
        except ValueError as exc:
            raise RuntimeError(f'{key} doit être un entier de 1 à 200') from exc
        if not 1 <= limit <= 200:
            raise RuntimeError(f'{key} doit être compris entre 1 et 200')
        limits[group] = limit
    return {ext: limits[group] for ext, group in GROUPS.items()}


def upload_limit(filename):
    return limits_mib()[Path(filename).suffix.lower()] * MIB


class InternalUploadBodyLimit:
    """Cap multipart bodies before Starlette spools them, including chunked requests."""

    ROUTES = re.compile(r'/api/(?:launches/[^/]+/(?:documents|document-uploads|intake/preview)|documents/[^/]+/versions)/?')
    MESSAGE = 'Taille maximale du transfert dépassée'

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or not self.ROUTES.fullmatch(scope['path']):
            await self.app(scope, receive, send)
            return
        maximum = (max(limits_mib().values()) + 1) * MIB  # one file plus multipart overhead
        length = dict(scope['headers']).get(b'content-length', b'')
        if length.isdigit() and int(length) > maximum:
            await JSONResponse({'detail': self.MESSAGE}, status_code=413)(scope, receive, send)
            return
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get('body', b''))
            if received > maximum:
                raise HTTPException(413, self.MESSAGE)
            return message

        await self.app(scope, bounded_receive, send)
