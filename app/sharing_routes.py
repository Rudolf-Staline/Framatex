"""MVP 0.14 — aperçu client et demandes fournisseurs strictement internes.

Ce module n'ouvre ni API publique, ni compte client/fournisseur, ni transfert externe.
Toutes les actions sont authentifiées et soumises à habilitation serveur.
"""
from __future__ import annotations
import re
import unicodedata
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core import get_db, get_current_user, utcnow
from .models import Document, DocumentVersion, User
from .sharing_models import ClientPublication, SupplierDocumentRequest
from .approval_models import ApprovalRun
from .workflow import latest_review
from .approval_routes import applicable_template
from .main import admin_only, audit, get_launch, must, permitted

router = APIRouter(tags=['0.14 — partage contrôlé simulé'])

# Liste fermée : modifier cette liste uniquement après validation métier par Framatex.
PUBLIC_DOC_TYPES = {'fiche technique','dossier technique client','rapport de controle',
                    'certificat qualite','bon de livraison','fiche qualite'}
SENSITIVE = re.compile(r'\b(prix|couts?|marges?|tarifs?|factures?|budget|interne|confidentiel|orli)\b',re.I)


def norm(value: str) -> str:
    raw = ''.join(c for c in unicodedata.normalize('NFKD', value or '')
                  if not unicodedata.combining(c)).lower()
    return ' '.join(re.sub(r'[_\-.]+', ' ', raw).split())


def source(db: Session, version_id: str, launch_id: str):
    v = db.get(DocumentVersion, version_id)
    doc = db.get(Document, v.document_id) if v else None
    if not doc or doc.folder.launch_id != launch_id:
        raise HTTPException(422, 'Version absente ou étrangère à ce lancement')
    return v, doc


def latest(doc: Document):
    return max(doc.versions, key=lambda v: v.number) if doc.versions else None


def is_approved(db: Session, v: DocumentVersion, doc: Document) -> bool:
    template = applicable_template(db, doc)
    if template:
        return db.scalar(select(ApprovalRun.id).where(
            ApprovalRun.document_version_id == v.id, ApprovalRun.status == 'approved')) is not None
    review = latest_review(db, v.id)
    return bool(review and review.decision == 'approved')


def is_safe(doc: Document) -> bool:
    if doc.folder.slug not in ('jaune','rose'):
        return False
    if norm(doc.doc_type) not in PUBLIC_DOC_TYPES:
        return False
    return not bool(SENSITIVE.search(norm(f"{doc.title} {doc.doc_type} {latest(doc).original_name if latest(doc) else ''}")))


def pub_out(db: Session, p: ClientPublication, launch):
    v = db.get(DocumentVersion, p.document_version_id)
    doc = db.get(Document, v.document_id)
    stale = latest(doc).id != v.id
    wrong_client = norm(p.client_name) != norm(launch.client_name or '')
    approved = is_approved(db, v, doc)
    visible = p.status == 'published' and not stale and not wrong_client and approved and is_safe(doc)
    return {'id':p.id,'document_id':doc.id,'document_title':doc.title,'document_type':doc.doc_type,
        'folder':doc.folder.slug,'version_id':v.id,'version':v.number,'client_name':p.client_name,
        'status':p.status,'stale':stale,'client_changed':wrong_client,'approval_current':approved,
        'effective':visible,'reason':p.reason,'created_at':p.created_at.isoformat(),
        'revoked_at':p.revoked_at.isoformat() if p.revoked_at else None,
        'revoked_reason':p.revoked_reason}


class PublicationInput(BaseModel):
    document_version_id: str
    reason: str = Field(min_length=12, max_length=1200)

class RevokeInput(BaseModel):
    reason: str = Field(min_length=12, max_length=1200)


@router.get('/api/launches/{launch_id}/client-publications')
def list_publications(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user,'launch.read')
    launch = get_launch(db,launch_id)
    rows = db.scalars(select(ClientPublication).where(ClientPublication.launch_id == launch.id)
                      .order_by(ClientPublication.created_at.desc())).all()
    return {'external_access_enabled':False,'client_name':launch.client_name,
            'items':[pub_out(db,p,launch) for p in rows
                     if permitted(user,'document.read',db.get(Document,db.get(DocumentVersion,p.document_version_id).document_id).folder.slug)]}


@router.post('/api/launches/{launch_id}/client-publications',status_code=201)
def publish(launch_id: str, payload: PublicationInput,
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    launch = get_launch(db,launch_id)
    if not (launch.client_name and launch.client_name.strip()):
        raise HTTPException(422,'Renseigner le client du lancement avant une publication')
    v,doc = source(db,payload.document_version_id,launch.id)
    if not is_safe(doc):
        raise HTTPException(422,'Type de document non autorisé à la publication client')
    if latest(doc).id != v.id:
        raise HTTPException(409,'Seule la dernière version peut être publiée')
    if not is_approved(db,v,doc):
        raise HTTPException(409,'Une approbation valide de cette version est nécessaire')
    active = db.scalar(select(ClientPublication).where(
        ClientPublication.document_version_id == v.id, ClientPublication.status == 'published'))
    if active:
        raise HTTPException(409,'Cette version fait déjà l’objet d’une publication active')
    p = ClientPublication(launch_id=launch.id,document_version_id=v.id,
          client_name=launch.client_name.strip(),reason=payload.reason.strip(),created_by=user.id)
    db.add(p);db.flush()
    audit(db,user,'client.publish.simulated','client_publication',p.id,
          {'launch':launch.id,'version':v.id,'client':p.client_name})
    db.commit()
    return pub_out(db,p,launch)


@router.post('/api/client-publications/{publication_id}/revoke')
def revoke(publication_id: str, payload: RevokeInput,
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    p = db.get(ClientPublication,publication_id)
    if not p:
        raise HTTPException(404,'Publication introuvable')
    if p.status != 'published':
        raise HTTPException(409,'Publication déjà retirée')
    p.status='revoked';p.revoked_by=user.id;p.revoked_at=utcnow();p.revoked_reason=payload.reason.strip()
    audit(db,user,'client.publication.revoke','client_publication',p.id,{'reason':p.revoked_reason})
    db.commit()
    return {'id':p.id,'status':p.status}


@router.get('/api/launches/{launch_id}/client-preview')
def client_preview(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Aucun utilisateur externe. Vue de prévisualisation exclusivement réservée à l'admin connecté.
    admin_only(user)
    launch = get_launch(db,launch_id)
    rows = db.scalars(select(ClientPublication).where(ClientPublication.launch_id == launch.id)).all()
    visible = [pub_out(db,p,launch) for p in rows]
    return {'simulation_only':True,'externally_accessible':False,'client':launch.client_name,
            'launch_id':launch.id,'documents':[
                {'title':v['document_title'],'document_type':v['document_type'],
                 'version':v['version'],'published_at':v['created_at']}
                for v in visible if v['effective']]}


class RequestInput(BaseModel):
    folder_slug: Literal['jaune','rose']
    supplier_name: str = Field(min_length=2,max_length=150)
    requested_title: str = Field(min_length=3,max_length=200)
    expected_doc_type: str = Field(min_length=2,max_length=100)
    note: str = Field(default='',max_length=1200)
    due_date: date | None = None

class ResolveInput(BaseModel):
    decision: Literal['received','cancelled']
    document_version_id: str | None = None
    note: str = Field(min_length=12,max_length=1200)


def request_out(db: Session, r: SupplierDocumentRequest):
    v=db.get(DocumentVersion,r.response_version_id) if r.response_version_id else None
    doc=db.get(Document,v.document_id) if v else None
    stale=bool(v and latest(doc).id != v.id)
    return {'id':r.id,'folder_slug':r.folder_slug,'supplier_name':r.supplier_name,
        'requested_title':r.requested_title,'expected_doc_type':r.expected_doc_type,
        'note':r.note,'due_date':r.due_date.isoformat() if r.due_date else None,
        'status':r.status,'created_at':r.created_at.isoformat(),
        'response_version_id':r.response_version_id,'response_document_id':doc.id if doc else None,
        'response_document_title':doc.title if doc else None,'response_stale':stale,
        'resolved_at':r.resolved_at.isoformat() if r.resolved_at else None,
        'resolution_note':r.resolution_note}

@router.get('/api/launches/{launch_id}/supplier-requests')
def requests(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user,'launch.read');get_launch(db,launch_id)
    rows=db.scalars(select(SupplierDocumentRequest).where(SupplierDocumentRequest.launch_id==launch_id)
                    .order_by(SupplierDocumentRequest.created_at.desc())).all()
    return {'external_access_enabled':False,'items':[request_out(db,r) for r in rows
            if permitted(user,'document.read',r.folder_slug)]}

@router.post('/api/launches/{launch_id}/supplier-requests',status_code=201)
def create_request(launch_id: str, payload:RequestInput,
                   user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    must(user,'launch.read');must(user,'document.write',payload.folder_slug)
    launch=get_launch(db,launch_id)
    r=SupplierDocumentRequest(launch_id=launch.id, folder_slug=payload.folder_slug,
        supplier_name=payload.supplier_name.strip(),requested_title=payload.requested_title.strip(),
        expected_doc_type=payload.expected_doc_type.strip(),note=payload.note.strip(),
        due_date=payload.due_date,created_by=user.id)
    db.add(r);db.flush()
    audit(db,user,'supplier.request.create','supplier_request',r.id,
        {'launch':launch.id,'folder':r.folder_slug,'supplier':r.supplier_name})
    db.commit()
    return request_out(db,r)

@router.post('/api/supplier-requests/{request_id}/resolve')
def resolve_request(request_id: str,payload:ResolveInput,
                    user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    r=db.get(SupplierDocumentRequest,request_id)
    if not r:
        raise HTTPException(404,'Demande introuvable')
    must(user,'launch.read');must(user,'document.read',r.folder_slug)
    must(user,'document.write',r.folder_slug)
    if r.status!='requested':
        raise HTTPException(409,'Demande déjà clôturée')
    if payload.decision=='received':
        if not payload.document_version_id:
            raise HTTPException(422,'Associez une version documentaire reçue')
        v,doc=source(db,payload.document_version_id,r.launch_id)
        if doc.folder.slug != r.folder_slug:
            raise HTTPException(422,'Justificatif dans un autre sous-dossier')
        if latest(doc).id != v.id:
            raise HTTPException(409,'Justificatif obsolète : utilisez sa version courante')
        if norm(doc.doc_type) != norm(r.expected_doc_type):
            raise HTTPException(422,'Le type documentaire ne correspond pas à la demande')
        r.response_version_id=v.id
    elif payload.document_version_id:
        raise HTTPException(422,'Une annulation ne doit pas porter de version justificative')
    r.status=payload.decision;r.resolved_at=utcnow();r.resolved_by=user.id
    r.resolution_note=payload.note.strip()
    audit(db,user,'supplier.request.resolve','supplier_request',r.id,
        {'decision':r.status,'version':r.response_version_id,'note':r.resolution_note})
    db.commit()
    return request_out(db,r)
