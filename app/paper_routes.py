"""0.6 — Liaison papier par QR et passeport numérique de chaque version.

Le QR est un simple pointeur vers un lancement. Il ne transporte aucun secret ni
aucun droit d'accès. Le passeport expose le hash archivé ET une vérification
indépendante des octets actuellement stockés.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlsplit

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core import get_current_user, get_db
from .models import DocumentVersion, User
from .workflow_models import DocumentReview

router = APIRouter(tags=["0.6 — Papier et passeport"])


def _context():
    # Avoid a circular import when main.py includes this router.
    from .main import STORAGE, audit, get_launch, is_admin, must, permitted
    return STORAGE, audit, get_launch, is_admin, must, permitted


def _public_base_url() -> str:
    """Never trust Host or X-Forwarded-* when creating scannable labels."""
    value = os.getenv("FRAMATEX_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise HTTPException(503, "FRAMATEX_PUBLIC_BASE_URL doit être une origine HTTP(S) sans chemin")
    return value


def _qr_png(value: str) -> bytes:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(value)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


@router.get("/api/launches/{launch_id}/paper-link")
def paper_link(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, _, get_launch, _, must, _ = _context()
    must(user, "launch.read")
    launch = get_launch(db, launch_id)
    return {
        "launch_id": launch.id,
        "launch_name": launch.name,
        "url": f"{_public_base_url()}/#/launch/{launch.id}",
        "requires_authentication": True,
        "is_access_token": False,
        "notice": "Le QR ne donne aucun droit. Connexion et habilitations restent obligatoires.",
    }


@router.get("/api/launches/{launch_id}/paper-qr.png")
def paper_qr(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = paper_link(launch_id, user, db)
    return Response(content=_qr_png(data["url"]), media_type="image/png",
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/api/launches/{launch_id}/paper-label", response_class=HTMLResponse)
def paper_label(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = paper_link(launch_id, user, db)
    b64 = base64.b64encode(_qr_png(data["url"])).decode("ascii")
    name = escape(data["launch_name"])
    identifier = escape(data["launch_id"])
    url = escape(data["url"], quote=True)
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Étiquette de dossier jaune</title>
<style>body{{font:16px Arial,sans-serif;color:#202d27;max-width:550px;margin:60px auto}}
.label{{border:2px solid #26392c;border-radius:14px;padding:32px;text-align:center}}
h1{{font-size:25px}}h2{{font-size:17px;font-weight:normal}}img{{width:260px;height:260px}}
code{{word-break:break-all;font-size:12px}}p.note{{font-size:13px;color:#52625a}}
@media print{{body{{margin:0}}.controls{{display:none}}}}</style></head><body>
<div class="controls"><button onclick="window.print()">Imprimer l'étiquette</button></div>
<div class="label"><h1>FRAMATEX · DOSSIER JAUNE</h1><h2>{name}</h2><img alt="QR code du lancement" src="data:image/png;base64,{b64}">
<p><strong>Identifiant interne</strong></p><code>{identifier}</code><p class="note">Scanner puis se connecter pour déposer ou consulter une pièce.</p>
<p class="note">Le QR code n'est pas un droit d'accès.</p><small>{url}</small></div></body></html>'''
    return HTMLResponse(html, headers={"Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'", "X-Content-Type-Options": "nosniff"})


def _verify_file(version: DocumentVersion):
    from .main import STORAGE
    from .cloud_storage import ensure_local
    path = ensure_local(version.disk_name, STORAGE)
    if not path.is_file():
        return {"status": "missing", "actual_sha256": None, "actual_size": None}
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
                size += len(block)
    except OSError:
        return {"status": "unavailable", "actual_sha256": None, "actual_size": None}
    actual = digest.hexdigest()
    intact = actual == version.sha256 and size == version.size
    return {"status": "intact" if intact else "mismatch", "actual_sha256": actual, "actual_size": size}


@router.get("/api/document-versions/{version_id}/passport")
def document_passport(version_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, _, _, _, must, _ = _context()
    version = db.get(DocumentVersion, version_id)
    if not version:
        raise HTTPException(404, "Version introuvable")
    document = version.document
    must(user, "launch.read")
    must(user, "document.read", document.folder.slug)
    reviews = db.scalars(select(DocumentReview).where(DocumentReview.document_version_id == version.id)
                         .order_by(DocumentReview.reviewed_at, DocumentReview.id)).all()
    history = sorted(document.versions, key=lambda v: v.number)
    previous = next((v for v in history if v.number == version.number - 1), None)
    uploader = db.get(User, version.uploaded_by)
    return {
        "version_id": version.id,
        "document_id": document.id,
        "title": document.title,
        "document_type": document.doc_type,
        "folder": document.folder.slug,
        "launch_id": document.folder.launch_id,
        "version": version.number,
        "is_current": version.number == history[-1].number,
        "original_filename": version.original_name,
        "size": version.size,
        "mime_type": version.content_type,
        "sha256_registered": version.sha256,
        "previous_version": ({"id": previous.id, "number": previous.number, "sha256_registered": previous.sha256} if previous else None),
        "uploader": {"id": version.uploaded_by, "name": uploader.name if uploader else "Compte indisponible"},
        "uploaded_at": version.created_at.isoformat(),
        "reviews": [{"decision": r.decision, "comment": r.comment,
                     "reviewed_at": r.reviewed_at.isoformat(),
                     "reviewer_name": (db.get(User, r.reviewed_by).name if db.get(User, r.reviewed_by) else "Compte indisponible")}
                    for r in reviews],
        "integrity": {**_verify_file(version), "checked_at": datetime.now(timezone.utc).isoformat()},
        "notice": "L'empreinte vérifie les octets stockés face au hash enregistré en base ; ce n'est ni une signature électronique ni une preuve d'inaltérabilité de la base.",
    }
