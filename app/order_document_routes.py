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
    sections.sort(key=lambda item:['jaune','rose','bleu','vert'].index(item['slug']))
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


@router.get('/api/orders/{oid}/approval-overview')
def approvals(oid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .approval_models import ApprovalRun
    from .approval_routes import latest_version,applicable_template,run_out
    must(user,'launch.read');must_order(db,user,oid)
    root=db.scalar(select(OrderDossier).where(OrderDossier.order_id==oid))
    if not root:raise HTTPException(409,'Migration documentaire requise')
    result=[]
    for doc in db.scalars(select(Document).join(Folder).where(Folder.dossier_id==root.id)):
        if not permitted(user,'document.read',doc.folder.slug) or not doc.versions:continue
        version=latest_version(doc);template=applicable_template(db,doc)
        runs=list(db.scalars(select(ApprovalRun).join(DocumentVersion).where(DocumentVersion.document_id==doc.id).order_by(ApprovalRun.started_at.desc(),ApprovalRun.cycle.desc())))
        run=next((r for r in runs if r.document_version_id==version.id),None)
        result.append({'document_id':doc.id,'can_start':bool(template and not run and (permitted(user,'document.write',doc.folder.slug) or permitted(user,'document.review',doc.folder.slug))),
            'run':run_out(db,run,user,doc) if run else None,'previous':[run_out(db,r,user,doc) for r in runs if not run or r.id!=run.id]})
    return {'order_id':oid,'items':result}


from pydantic import BaseModel,Field,ConfigDict
class MemberInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    user_id:str=Field(min_length=36,max_length=36)
    reason:str=Field(min_length=12,max_length=1500)

@router.post('/api/orders/{oid}/members',status_code=201)
def add_member(oid:str,payload:MemberInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .main import admin_only
    from .models import User
    from .order_documents import OrderMember
    admin_only(user);must_order(db,user,oid)
    target=db.get(User,payload.user_id)
    if not target or not target.active:raise HTTPException(422,'Collaborateur actif nécessaire')
    if not permitted(target,'launch.read'):raise HTTPException(422,'Le collaborateur doit disposer du droit de lecture')
    if not db.get(OrderMember,(oid,target.id)):db.add(OrderMember(order_id=oid,user_id=target.id))
    audit(db,user,'order.member.grant','order',oid,payload.model_dump());db.commit()
    return {'order_id':oid,'user_id':target.id}

@router.delete('/api/orders/{oid}/members/{user_id}')
def revoke_member(oid:str,user_id:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .main import admin_only
    from .order_documents import OrderMember
    admin_only(user);must_order(db,user,oid)
    row=db.get(OrderMember,(oid,user_id))
    if not row:raise HTTPException(404,'Habilitation absente')
    db.delete(row);audit(db,user,'order.member.revoke','order',oid,{'user_id':user_id});db.commit()
    return {'revoked':True}


@router.get('/api/orders/{oid}/paper-link')
def paper_link(oid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .paper_routes import _public_base_url
    must(user,'launch.read');order=must_order(db,user,oid)
    return {'order_id':oid,'order_reference':order.reference,'url':f'{_public_base_url()}/#/order/{oid}',
            'requires_authentication':True,'is_access_token':False}

@router.get('/api/orders/{oid}/paper-qr.png')
def paper_qr(oid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .paper_routes import _qr_png
    from fastapi.responses import Response
    data=paper_link(oid,user,db)
    return Response(_qr_png(data['url']),media_type='image/png',headers={'Cache-Control':'private, no-store'})


class CompletenessInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    profile_id:str|None=Field(None,min_length=36,max_length=36)
    phase:Literal['preparation','approvisionnement','fabrication','expedition','cloture']='preparation'
    order_type:str=Field('',max_length=100)

@router.get('/api/orders/{oid}/completeness')
def completeness(oid:str,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .order_completeness import evaluate
    must(user,'launch.read');order=must_order(db,user,oid)
    return evaluate(db,order,user,permitted)

@router.put('/api/orders/{oid}/completeness/context')
def context(oid:str,payload:CompletenessInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from .main import admin_only
    from .order_documents import OrderCompleteness
    from .completeness_models import CompletenessProfile
    admin_only(user);must_order(db,user,oid)
    if payload.profile_id and not db.get(CompletenessProfile,payload.profile_id):raise HTTPException(422,'Profil de complétude absent')
    row=db.get(OrderCompleteness,oid)
    if not row:row=OrderCompleteness(order_id=oid);db.add(row)
    for key,value in payload.model_dump().items():setattr(row,key,value)
    audit(db,user,'order.completeness.context','order',oid,payload.model_dump());db.commit()
    return completeness(oid,user,db)
