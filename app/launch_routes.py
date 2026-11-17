"""Launch and dashboard HTTP endpoints."""
from __future__ import annotations
from fastapi import APIRouter
from .access import is_admin, permitted, must
from .audit import audit
from .launches import get_launch, launch_out, FOLDERS, STATUSES
from .order_documents import doc_out
import os
from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select,func,or_
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
    from .access import launch_access_clause
    launches = list(db.scalars(select(Launch).where(launch_access_clause(user,Launch.id))))
    from .order_documents import document_access_clause
    from .models import DocumentVersion
    folders=[slug for slug,_label in FOLDERS if permitted(user,'document.read',slug)]
    visible_docs=select(Document.id).join(Folder).where(Folder.slug.in_(folders),document_access_clause(user))
    document_count=db.scalar(select(func.count()).select_from(visible_docs.subquery()))
    version_count=db.scalar(select(func.count()).select_from(DocumentVersion).where(DocumentVersion.document_id.in_(visible_docs)))
    from .partner_phase2_models import BusinessOrder, BusinessOrderLaunch
    from .order_documents import order_access_clause
    from .order_completeness import evaluate as evaluate_order
    orders = list(db.scalars(select(BusinessOrder).where(order_access_clause(user))))
    completion = [evaluate_order(db, order, user, permitted) for order in orders]
    completion.extend(evaluate(db, launch, user, permitted) for launch in launches
                      if not db.get(BusinessOrderLaunch, launch.id))
    obligations = {r['obligation_key']: r for report in completion for r in report['rows']}
    open_ids = {l.id for l in launches if l.status != 'Clôturé'}
    closed_orders = {order.id for order in orders if (linked := list(db.scalars(select(Launch).join(
        BusinessOrderLaunch).where(BusinessOrderLaunch.order_id == order.id)))) and all(l.status == 'Clôturé' for l in linked)}
    return {"launches": len(launches), "incomplete": sum(l.status == "À compléter" for l in launches),
            "documents": document_count, "versions": version_count,
            "completeness_actions": sum(r['due'] and r['status'] in ('missing','pending_validation','pending_publication')
                and (not r.get('launch_id') or r['launch_id'] in open_ids) and r.get('order_id') not in closed_orders for r in obligations.values()),
            "completeness_unconfigured": sum(not c["configured"] for c in completion),
            "recent": [launch_out(l) for l in sorted(launches, key=lambda l: l.created_at, reverse=True)[:5]]}


@router.get("/api/launches")
def launches(response:Response,q:str=Query("",max_length=200),offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=100),page:bool=False,
             user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    from .access import launch_access_clause
    from .partner_phase2_models import BusinessOrderLaunch
    must(user,"launch.read")
    query=select(Launch,BusinessOrderLaunch.order_id).outerjoin(BusinessOrderLaunch).where(launch_access_clause(user,Launch.id))
    if q.strip():
        term='%'+q.strip()+'%'
        query=query.where(or_(*(column.ilike(term) for column in (Launch.name,Launch.client_name,Launch.order_ref,Launch.orli_ref))))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.execute(query.order_by(Launch.created_at.desc(),Launch.id).offset(offset).limit(limit))
    items=[launch_out(launch,order_id) for launch,order_id in rows]
    response.headers['X-Total-Count']=str(total)
    return {'items':items,'total':total,'offset':offset,'limit':limit} if page else items


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
    from .order_documents import document_accessible
    l = get_launch(db, launch_id)
    folders = []
    for slug, label in FOLDERS:
        folder = next((f for f in l.folders if f.slug == slug), None)
        docs = [] if not folder or not permitted(user, "document.read", slug) else [doc_out(d) for d in folder.documents if document_accessible(db,user,d)]
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
