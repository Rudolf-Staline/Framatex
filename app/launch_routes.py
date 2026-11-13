"""Launch and dashboard HTTP endpoints."""
from __future__ import annotations
from fastapi import APIRouter
from .access import is_admin, permitted, must
from .audit import audit
from .launches import get_launch, launch_out, FOLDERS, STATUSES
from .order_documents import doc_out
import os
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import Document, Folder, Launch, User
from .completeness import evaluate
from .orli_models import OrliLink

router = APIRouter()

class LaunchPayload(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    client_name: str | None = Field(default=None, max_length=150)
    order_ref: str | None = Field(default=None, max_length=100)
    orli_ref: str | None = Field(default=None, max_length=100)
    order_id: str | None = Field(default=None,min_length=36,max_length=36)


class LaunchPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    client_name: str | None = Field(default=None, max_length=150)
    order_ref: str | None = Field(default=None, max_length=100)
    orli_ref: str | None = Field(default=None, max_length=100)
    status: str | None = None


@router.get("/api/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    from .access import visible
    launches = visible(db, user, db.scalars(select(Launch)).all())
    from .order_documents import document_accessible
    documents = db.scalars(select(Document).join(Folder)).all()
    visible_documents = [d for d in documents if document_accessible(db,user,d) and permitted(user, "document.read", d.folder.slug)]
    completion = [evaluate(db, l, user, permitted) for l in launches]
    return {"launches": len(launches), "incomplete": sum(l.status == "À compléter" for l in launches),
            "documents": len(visible_documents), "versions": sum(len(d.versions) for d in visible_documents),
            "completeness_actions": sum(c["counts"]["missing"] + c["counts"]["pending_validation"] for c in completion),
            "completeness_unconfigured": sum(not c["configured"] for c in completion),
            "recent": [launch_out(l) for l in sorted(launches, key=lambda l: l.created_at, reverse=True)[:5]]}


@router.get("/api/launches")
def launches(q: str = Query("",max_length=200), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    from .access import visible
    rows = visible(db, user, db.scalars(select(Launch).order_by(Launch.created_at.desc())).all())
    term = q.strip().lower()
    if term:
        rows = [l for l in rows if term in " ".join((l.name, l.client_name or "", l.order_ref or "", l.orli_ref or "")).lower()]
    return [launch_out(l) for l in rows]


@router.post("/api/launches", status_code=201)
def create_launch(payload: LaunchPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.create")
    order=None
    if payload.order_id:
        from .order_documents import must_order
        from .partner_models import Partner
        order=must_order(db,user,payload.order_id)
        if (payload.order_ref and payload.order_ref!=order.reference) or (payload.client_name and payload.client_name!=db.get(Partner,order.client_id).name):
            raise HTTPException(422,'Client ou référence incompatible avec la commande')
        payload.order_ref=order.reference;payload.client_name=db.get(Partner,order.client_id).name
    l = Launch(name=payload.name.strip(), client_name=payload.client_name or None, order_ref=payload.order_ref or None, orli_ref=payload.orli_ref or None, restricted=os.getenv("FRAMATEX_RESTRICT_NEW_LAUNCHES", "0") == "1", created_by=user.id)
    db.add(l)
    db.flush()
    if order:
        from .partner_phase2_models import BusinessOrderLaunch
        from .order_documents import dossier
        db.add(BusinessOrderLaunch(launch_id=l.id,order_id=order.id,linked_by=user.id));dossier(db,order.id)
    else:
        for slug, label in FOLDERS:
            db.add(Folder(launch_id=l.id, slug=slug, label=label))
    audit(db, user, "launch.create", "launch", l.id, {"name": l.name, "orli": l.orli_ref})
    db.commit()
    return launch_out(l)


@router.get("/api/launches/{launch_id}")
def launch_detail(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    l = get_launch(db, launch_id)
    folders = []
    for slug, label in FOLDERS:
        folder = next((f for f in l.folders if f.slug == slug), None)
        docs = [] if not folder or not permitted(user, "document.read", slug) else [doc_out(d) for d in folder.documents]
        folders.append({"slug": slug, "label": label, "can_read": permitted(user, "document.read", slug), "can_write": permitted(user, "document.write", slug), "documents": docs})
    return {**launch_out(l), "folders": folders, "can_update": permitted(user, "launch.update"), "can_manage_access": is_admin(user)}


@router.patch("/api/launches/{launch_id}")
def update_launch(launch_id: str, payload: LaunchPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.update")
    l = get_launch(db, launch_id)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in STATUSES:
        raise HTTPException(422, "Statut inconnu")
    from .partner_phase2_models import BusinessOrderLaunch, BusinessOrder
    from .partner_models import Partner
    from .sharing_routes import norm
    relation = db.get(BusinessOrderLaunch, l.id)
    if relation:
        order = db.get(BusinessOrder, relation.order_id)
        if ('order_ref' in changes and (changes['order_ref'] or '').strip() != order.reference
            or 'client_name' in changes and norm(changes['client_name']) != norm(db.get(Partner, order.client_id).name)):
            raise HTTPException(409, "Commande rattachée : détacher le lancement avec justification avant de modifier son client ou sa référence")
    if "orli_ref" in changes and db.scalar(select(OrliLink).where(OrliLink.launch_id == l.id)):
        current_ref = l.orli_ref or ''
        requested_ref = changes['orli_ref'] or ''
        from .orli_import import normalize_reference
        if normalize_reference(current_ref) != normalize_reference(requested_ref):
            raise HTTPException(409, "Référence rapprochée à ORLI : modification interdite sans procédure de déliaison")
    for field, value in changes.items():
        setattr(l, field, value.strip() if isinstance(value, str) else value)
    audit(db, user, "launch.update", "launch", l.id, {"fields": list(changes.keys())})
    db.commit()
    return launch_out(l)
