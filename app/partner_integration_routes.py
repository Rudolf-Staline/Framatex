from .order_documents import document_in_launch
"""Controlled integration without copying blobs or losing supplier provenance."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .core import get_db, get_current_user
from .main import must, audit, STORAGE, doc_out
from .access import must_access
from .order_documents import document_accessible
from .models import Document, DocumentVersion, Folder
from .workflow_models import DocumentReview
from .workflow import emit_document_impacts
from .partner_models import PartnerSubmission, PartnerRequest
from .partner_phase2_models import PartnerIntegration
from .partner_routes import req_get, claim, event, staff

router=APIRouter(tags=['Intégration documentaire fournisseur'])

class IntegrationInput(BaseModel):
    submission_id: str
    folder: Literal['jaune','rose','bleu','vert']
    document_id: str | None=None

class ReasonInput(BaseModel):
    reason: str=Field(min_length=3,max_length=2000)

def business_available(db,version_id):
    link=db.scalar(select(PartnerIntegration).where(PartnerIntegration.version_id==version_id))
    return not link or link.active

@router.post('/api/partners/requests/{rid}/integrate',status_code=201)
def integrate(rid:str,payload:IntegrationInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    request=req_get(db,rid)
    launch=must_access(db,user,request.launch_id)
    must(user,'launch.read');must(user,'document.read',payload.folder);must(user,'document.write',payload.folder);must(user,'document.review',payload.folder)
    source=db.get(PartnerSubmission,payload.submission_id)
    latest=db.scalar(select(PartnerSubmission).where(PartnerSubmission.request_id==rid).order_by(PartnerSubmission.number.desc()).limit(1))
    if not source or source.request_id!=rid or source.status!='approved' or latest.id!=source.id:
        raise HTTPException(409,'Seule la dernière transmission approuvée peut être intégrée')
    if launch.order_ref and launch.order_ref!=request.order_ref:
        raise HTTPException(409,'Référence commande incompatible avec le lancement')
    if db.get(PartnerIntegration,source.id):raise HTTPException(409,'Cette version a déjà été intégrée')
    if not (STORAGE/source.disk_name).is_file():raise HTTPException(503,'Fichier source absent')
    claim(db,request)
    if payload.document_id:
        document=db.get(Document,payload.document_id)
        previous=db.scalar(select(PartnerIntegration).join(DocumentVersion,PartnerIntegration.version_id==DocumentVersion.id).join(PartnerSubmission,PartnerIntegration.submission_id==PartnerSubmission.id).where(DocumentVersion.document_id==payload.document_id,PartnerSubmission.request_id==rid))
        if not document or not document_in_launch(db, document, request.launch_id) or document.folder.slug!=payload.folder or not previous:
            raise HTTPException(409,'Document cible étranger à la demande ou au dossier')
    else:
        existing=db.scalar(select(PartnerIntegration).join(PartnerSubmission).where(PartnerSubmission.request_id==rid))
        if existing:raise HTTPException(409,'Choisir le document déjà intégré pour ajouter une version')
        folder=next((f for f in launch.folders if f.slug==payload.folder),None)
        if not folder:raise HTTPException(422,'Rubrique absente')
        document=Document(launch_id=request.launch_id,folder_id=folder.id,title=request.title,doc_type=request.doc_type,created_by=user.id)
        db.add(document);db.flush()
    version=DocumentVersion(document_id=document.id,number=max((v.number for v in document.versions),default=0)+1,
        original_name=source.original_name,disk_name=source.disk_name,size=source.size,sha256=source.sha256,
        content_type=source.content_type,uploaded_by=user.id,created_at=source.created_at)
    document.versions.append(version)
    try:
        db.flush()
        db.add(PartnerIntegration(submission_id=source.id,version_id=version.id,integrated_by=user.id))
        db.add(DocumentReview(document_version_id=version.id,decision='approved',comment=f'Intégration contrôlée de la transmission {source.id}',reviewed_by=user.id))
        emit_document_impacts(db,document,version)
        from .quality_routes import auto_inspect_excel
        auto_inspect_excel(db,version,user.id)
        audit(db,user,'partner.integrate','document_version',version.id,{'submission_id':source.id,'account_id':source.account_id,'sha256':source.sha256})
        event(db,request,'staff:'+user.id,'integrated',f'Version fournisseur {source.number} intégrée au dossier interne')
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Intégration concurrente ou version déjà intégrée')
    return {'document':doc_out(document),'version_id':version.id,'source':provenance(db,version.id)}

def provenance(db,version_id):
    link=db.scalar(select(PartnerIntegration).where(PartnerIntegration.version_id==version_id))
    if not link:return None
    source=db.get(PartnerSubmission,link.submission_id);request=db.get(PartnerRequest,source.request_id)
    return {'submission_id':source.id,'request_id':request.id,'partner_id':request.partner_id,'account_id':source.account_id,
            'source_version':source.number,'submitted_at':source.created_at,'sha256':source.sha256,'reviewed_by':source.reviewed_by,
            'decision':source.status,'decision_reason':source.reason,'integrated_by':link.integrated_by,'active':link.active,'withdrawal_reason':link.withdrawal_reason}

@router.get('/api/document-versions/{version_id}/supplier-origin')
def origin(version_id:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    version=db.get(DocumentVersion,version_id)
    if not version:raise HTTPException(404,'Version introuvable')
    assert_document_access(db,user,version.document);must(user,'document.read',version.document.folder.slug)
    return provenance(db,version_id)

@router.post('/api/document-versions/{version_id}/supplier-withdrawal')
def withdraw(version_id:str,payload:ReasonInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    version=db.get(DocumentVersion,version_id)
    if not version:raise HTTPException(404,'Version introuvable')
    assert_document_access(db,user,version.document);must(user,'document.review',version.document.folder.slug)
    link=db.scalar(select(PartnerIntegration).where(PartnerIntegration.version_id==version_id))
    if not link or not link.active:raise HTTPException(409,'Intégration absente ou déjà retirée')
    link.active=False;link.withdrawal_reason=payload.reason
    db.add(DocumentReview(document_version_id=version.id,decision='rejected',comment=payload.reason,reviewed_by=user.id))
    audit(db,user,'partner.integration.withdraw','document_version',version.id,{'reason':payload.reason})
    db.commit();return {'active':False}

@router.post('/api/partners/requests/{rid}/reopen')
def reopen(rid:str,payload:ReasonInput,user=Depends(staff),db:Session=Depends(get_db)):
    row=req_get(db,rid)
    if row.status not in ('approved','closed'):raise HTTPException(409,'Demande non clôturée ou approuvée')
    claim(db,row);row.status='requested';event(db,row,'staff:'+user.id,'reopened',payload.reason)
    audit(db,user,'partner.reopen','partner_request',rid,payload.model_dump());db.commit();return {'status':row.status}

class ConfirmedDatumInput(BaseModel):
    confirmed_id: str
    field_key: Literal['quantite_lancement','besoin_matiere_total','quantite_livree','quantite_recue','reference_matiere','reference_lancement','montant_total']

@router.post('/api/document-versions/{version_id}/data-from-confirmed',status_code=201)
def use_confirmed(version_id:str,payload:ConfirmedDatumInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .intake_models import ConfirmedField
    from .quality_models import DocumentDatum
    from .quality_routes import normalized_datum
    from .partner_phase2_models import ConfirmedDatumSource
    version=db.get(DocumentVersion,version_id)
    if not version:raise HTTPException(404,'Version introuvable')
    assert_document_access(db,user,version.document)
    must(user,'document.read',version.document.folder.slug);must(user,'document.write',version.document.folder.slug)
    if not business_available(db,version_id) or version.number!=max(v.number for v in version.document.versions):raise HTTPException(409,'Version retirée ou obsolète')
    source=db.get(ConfirmedField,payload.confirmed_id)
    mapping={'quantite_lancement':('quantite',{'pièce'}),'besoin_matiere_total':('quantite',{'m'}),
        'quantite_livree':('quantite',{'m','pièce','kg'}),'quantite_recue':('quantite',{'m','pièce','kg'}),
        'reference_matiere':('reference_matiere',{'','référence'}),'reference_lancement':('numero_lancement',{'','référence'}),
        'montant_total':('montant',{'MAD','EUR'})}
    source_key,units=mapping[payload.field_key]
    if not source or source.document_version_id!=version_id or source.field_key!=source_key or source.unit not in units:
        raise HTTPException(422,'Champ confirmé de cette version avec unité compatible requis')
    unit='référence' if payload.field_key.startswith('reference_') else source.unit
    if db.scalar(select(DocumentDatum).where(DocumentDatum.document_version_id==version_id,DocumentDatum.field_key==payload.field_key)):
        raise HTTPException(409,'Donnée déjà renseignée ; aucune valeur écrasée')
    row=DocumentDatum(document_version_id=version_id,field_key=payload.field_key,value_text=normalized_datum(payload.field_key,source.value,unit),unit=unit,recorded_by=source.confirmed_by,recorded_at=source.confirmed_at)
    db.add(row);db.flush();db.add(ConfirmedDatumSource(datum_id=row.id,confirmed_id=source.id))
    audit(db,user,'quality.confirmed.use','document_version',version_id,{'datum_id':row.id,'confirmed_id':source.id})
    db.commit();return {'id':row.id,'confirmed_id':source.id,'value':row.value_text,'unit':row.unit}

@router.get('/api/documents/{doc_id}/supplier-detail')
def supplier_document(doc_id:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    doc=db.get(Document,doc_id)
    if not doc:raise HTTPException(404,'Document introuvable')
    assert_document_access(db,user,doc);must(user,'document.read',doc.folder.slug)
    return doc_out(doc)


def assert_document_access(db,user,doc):
    if not document_accessible(db,user,doc):raise HTTPException(404,'Document introuvable')
