from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db
from .main import store_upload,STORAGE,audit
from .partner_routes import staff,partner,req_get,event
from .partner_permissions import require
from .partner_models import PartnerEvent
from .partner_phase2_models import PartnerAttachment,PartnerMessage
from .partner_client_routes import thread_get,order_get
from .partner_uploads import lock_budget,verify_budget

router=APIRouter(tags=['Pièces jointes partenaires'])

def out(row):
    return {'id':row.id,'name':row.original_name,'size':row.size,'sha256':row.sha256,'classification':row.classification,'created_at':row.created_at}

async def upload_attachment(db,file,org_id,actor,event_id=None,message_id=None):
    lock_budget(db,org_id)
    name,disk,size,sha,mime=await store_upload(file)
    try:
        verify_budget(db,org_id,size)
        row=PartnerAttachment(partner_id=org_id,event_id=event_id,message_id=message_id,owner=actor,original_name=name,disk_name=disk,size=size,sha256=sha)
        db.add(row);db.flush();audit(db,None,'partner.attachment','partner_attachment',row.id,{'author':actor,'sha256':sha});db.commit();return out(row)
    except Exception:
        db.rollback();(STORAGE/disk).unlink(missing_ok=True);raise

@router.post('/api/partner/requests/{rid}/attachments',status_code=201)
async def supplier_attach(rid:str,file:UploadFile=File(...),message:str=Form(...,min_length=1,max_length=4000),account=Depends(partner),db:Session=Depends(get_db)):
    require(db,account,'message.write');row=req_get(db,rid,account)
    e=PartnerEvent(request_id=rid,actor='partner:'+account.id,kind='attachment',message=message);db.add(e);db.flush()
    return await upload_attachment(db,file,row.partner_id,e.actor,event_id=e.id)

@router.post('/api/partners/requests/{rid}/attachments',status_code=201)
async def staff_attach(rid:str,file:UploadFile=File(...),message:str=Form(...,min_length=1,max_length=4000),user=Depends(staff),db:Session=Depends(get_db)):
    row=req_get(db,rid);e=PartnerEvent(request_id=rid,actor='staff:'+user.id,kind='attachment',message=message);db.add(e);db.flush()
    return await upload_attachment(db,file,row.partner_id,e.actor,event_id=e.id)

@router.post('/api/partner/threads/{tid}/attachments',status_code=201)
async def client_attach(tid:str,file:UploadFile=File(...),message:str=Form(...,min_length=1,max_length=4000),account=Depends(partner),db:Session=Depends(get_db)):
    require(db,account,'message.write');thread=thread_get(db,tid,account)
    if thread.status=='closed':raise HTTPException(409,'Échange clôturé')
    m=PartnerMessage(thread_id=tid,author='partner:'+account.id,text=message);db.add(m);db.flush()
    return await upload_attachment(db,file,account.partner_id,m.author,message_id=m.id)

@router.post('/api/partners/threads/{tid}/attachments',status_code=201)
async def employee_attach(tid:str,file:UploadFile=File(...),message:str=Form(...,min_length=1,max_length=4000),user=Depends(staff),db:Session=Depends(get_db)):
    thread=thread_get(db,tid);order=order_get(db,thread.order_id)
    if thread.status=='closed':raise HTTPException(409,'Échange clôturé')
    m=PartnerMessage(thread_id=tid,author='staff:'+user.id,text=message);db.add(m);db.flush()
    return await upload_attachment(db,file,order.partner_id,m.author,message_id=m.id)

def attachment_get(db,aid,account=None):
    row=db.get(PartnerAttachment,aid)
    if not row or (account and row.partner_id!=account.partner_id):raise HTTPException(404,'Pièce introuvable')
    if row.event_id:req_get(db,db.get(PartnerEvent,row.event_id).request_id,account)
    else:thread_get(db,db.get(PartnerMessage,row.message_id).thread_id,account)
    if not (STORAGE/row.disk_name).is_file():raise HTTPException(503,'Fichier indisponible')
    return row

@router.get('/api/partner/attachments/{aid}/download')
def download(aid:str,account=Depends(partner),db:Session=Depends(get_db)):
    row=attachment_get(db,aid,account)
    return FileResponse(STORAGE/row.disk_name,filename=row.original_name,media_type='application/octet-stream')

@router.get('/api/partners/attachments/{aid}/download')
def employee_download(aid:str,user=Depends(staff),db:Session=Depends(get_db)):
    row=attachment_get(db,aid)
    return FileResponse(STORAGE/row.disk_name,filename=row.original_name,media_type='application/octet-stream')
