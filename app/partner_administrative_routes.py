"""Versioned administrative documents, private to an organization and Framatex."""
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Form
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db
from .main import store_upload, STORAGE
from .audit import audit
from .partner_routes import partner,staff,org_get
from .partner_permissions import require
from .partner_uploads import lock_budget,verify_budget
from .partner_phase2_models import PartnerAdministrativeDocument

router=APIRouter(tags=['Pièces administratives partenaires'])

def out(row):
    return {k:getattr(row,k) for k in ('id','title','number','original_name','size','sha256','status','reason','created_at')}

def list_files(db,oid):
    return [out(r) for r in db.scalars(select(PartnerAdministrativeDocument).where(PartnerAdministrativeDocument.partner_id==oid).order_by(PartnerAdministrativeDocument.title,PartnerAdministrativeDocument.number))]

@router.get('/api/partner/administrative-documents')
def own_files(account=Depends(partner),db:Session=Depends(get_db)):
    return list_files(db,account.partner_id)

@router.get('/api/partners/organizations/{oid}/administrative-documents')
def staff_files(oid:str,user=Depends(staff),db:Session=Depends(get_db)):
    org_get(db,oid);return list_files(db,oid)

async def save(db,oid,actor,title,file):
    title=title.strip()
    if not title:raise HTTPException(422,'Titre requis')
    lock_budget(db,oid)
    name,disk,size,sha,mime=await store_upload(file)
    try:
        verify_budget(db,oid,size)
        previous=db.scalar(select(PartnerAdministrativeDocument).where(PartnerAdministrativeDocument.partner_id==oid,PartnerAdministrativeDocument.title==title).order_by(PartnerAdministrativeDocument.number.desc()).limit(1))
        row=PartnerAdministrativeDocument(partner_id=oid,title=title,number=previous.number+1 if previous else 1,owner=actor,original_name=name,disk_name=disk,size=size,sha256=sha)
        db.add(row);db.flush();audit(db,None,'partner.admin_document.upload','partner',oid,{'version_id':row.id,'owner':actor,'sha256':sha})
        db.commit();return out(row)
    except Exception:
        db.rollback();(STORAGE/disk).unlink(missing_ok=True);raise

@router.post('/api/partner/administrative-documents',status_code=201)
async def own_upload(title:str=Form(...,min_length=1,max_length=150),file:UploadFile=File(...),account=Depends(partner),db:Session=Depends(get_db)):
    require(db,account,'document.write');return await save(db,account.partner_id,'partner:'+account.id,title,file)

@router.post('/api/partners/organizations/{oid}/administrative-documents',status_code=201)
async def staff_upload(oid:str,title:str=Form(...,min_length=1,max_length=150),file:UploadFile=File(...),user=Depends(staff),db:Session=Depends(get_db)):
    org_get(db,oid);return await save(db,oid,'staff:'+user.id,title,file)

class ReviewInput(BaseModel):
    status:Literal['approved','rejected']
    reason:str=Field(min_length=3,max_length=2000)

@router.post('/api/partners/administrative-documents/{vid}/review')
def review(vid:str,payload:ReviewInput,user=Depends(staff),db:Session=Depends(get_db)):
    row=db.get(PartnerAdministrativeDocument,vid)
    if not row:raise HTTPException(404,'Pièce absente')
    lock_budget(db,row.partner_id);db.refresh(row)
    current=db.scalar(select(PartnerAdministrativeDocument.id).where(PartnerAdministrativeDocument.partner_id==row.partner_id,PartnerAdministrativeDocument.title==row.title).order_by(PartnerAdministrativeDocument.number.desc()).limit(1))
    if row.status!='pending' or current!=vid:raise HTTPException(409,'Seule la dernière version en attente peut être examinée')
    row.status=payload.status;row.reason=payload.reason;row.reviewed_by=user.id
    audit(db,user,'partner.admin_document.review','partner',row.partner_id,{'version_id':vid,**payload.model_dump()});db.commit();return out(row)

def file_response(db,vid,account=None):
    row=db.get(PartnerAdministrativeDocument,vid)
    if not row or (account and row.partner_id!=account.partner_id):raise HTTPException(404,'Pièce absente')
    if not (STORAGE/row.disk_name).is_file():raise HTTPException(503,'Fichier indisponible')
    return FileResponse(STORAGE/row.disk_name,filename=row.original_name,media_type='application/octet-stream')

@router.get('/api/partner/administrative-documents/{vid}/download')
def own_download(vid:str,account=Depends(partner),db:Session=Depends(get_db)):
    return file_response(db,vid,account)

@router.get('/api/partners/administrative-documents/{vid}/download')
def staff_download(vid:str,user=Depends(staff),db:Session=Depends(get_db)):
    return file_response(db,vid)
