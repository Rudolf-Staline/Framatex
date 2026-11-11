"""Order-owned dossier API; launch routes remain compatibility entrypoints."""
from typing import Literal
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db, get_current_user
from .models import Folder, Document, DocumentVersion
from .main import must, permitted, doc_out, store_upload, STORAGE, audit
from .order_documents import dossier, must_order, launch_order, OrderDossier

router=APIRouter(tags=['Dossiers Jaunes par commande'])

@router.get('/api/orders/{oid}/dossier')
def detail(oid:str, launch_id:str|None=None, q:str=Query('',max_length=200),
           user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');order=must_order(db,user,oid)
    root=db.scalar(select(OrderDossier).where(OrderDossier.order_id==oid))
    if not root:raise HTTPException(409,'Dossier absent : migration requise')
    if launch_id:
        link=launch_order(db,launch_id)
        if not link or link.order_id!=oid:raise HTTPException(422,'Lancement étranger à la commande')
    sections=[]
    for f in db.scalars(select(Folder).where(Folder.dossier_id==root.id).order_by(Folder.slug)):
        can_read=permitted(user,'document.read',f.slug)
        docs=[doc_out(d) for d in f.documents if (not launch_id or d.launch_id==launch_id) and (not q or q.casefold() in (d.title+' '+d.doc_type).casefold())] if can_read else []
        sections.append({'id':f.id,'slug':f.slug,'label':f.label,'can_read':can_read,'can_write':permitted(user,'document.write',f.slug),'documents':docs})
    return {'id':root.id,'order_id':oid,'reference':order.reference,'client_id':order.client_id,'sections':sections}

@router.post('/api/orders/{oid}/documents',status_code=201)
async def upload(oid:str,folder:Literal['jaune','rose','bleu','vert']=Form(...),
                 title:str=Form(...,min_length=1,max_length=220),doc_type:str=Form('Autre',min_length=1,max_length=100),
                 launch_id:str|None=Form(None),file:UploadFile=File(...),
                 user=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');must(user,'document.write',folder);must_order(db,user,oid)
    if not title.strip() or not doc_type.strip():raise HTTPException(422,'Titre et type nécessaires')
    if launch_id:
        link=launch_order(db,launch_id)
        if not link or link.order_id!=oid:raise HTTPException(422,'Lancement étranger à la commande')
    root=dossier(db,oid)
    section=db.scalar(select(Folder).where(Folder.dossier_id==root.id,Folder.slug==folder))
    original,disk_name,size,sha,mime=await store_upload(file)
    try:
        doc=Document(folder_id=section.id,launch_id=launch_id,title=title.strip(),doc_type=doc_type.strip(),created_by=user.id)
        db.add(doc);db.flush()
        version=DocumentVersion(document_id=doc.id,number=1,original_name=original,disk_name=disk_name,size=size,sha256=sha,content_type=mime,uploaded_by=user.id)
        db.add(version);db.flush()
        from .quality_routes import auto_inspect_excel
        auto_inspect_excel(db,version,user.id)
        audit(db,user,'document.upload','document',doc.id,{'order_id':oid,'launch_id':launch_id,'sha256':sha})
        db.commit();return doc_out(doc)
    except Exception:
        db.rollback();(STORAGE/disk_name).unlink(missing_ok=True);raise
