"""Persistent in-app notices. No external delivery and no implied email receipt."""
from datetime import date,timedelta
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session
from .core import get_db,utcnow
from .models import uid,User,Role
from .partner_routes import partner,staff,req_get,visible_publication
from .partner_models import PartnerRequest,PartnerPublication
from .partner_phase2_models import PartnerNotice,PartnerNoticeRead,PartnerClientOrder
from .partner_client_routes import order_get

router=APIRouter(tags=['Notifications partenaires'])

def emit(db,org,scope,target,kind,key,message):
    db.execute(insert(PartnerNotice).values(id=uid(),partner_id=org,scope=scope,target_id=target,
        kind=kind,event_key=key,message=message,created_at=utcnow()).on_conflict_do_nothing(index_elements=['partner_id','event_key']))

def visible(db,row,account):
    if not row or row.partner_id!=account.partner_id:return False
    try:
        if row.scope=='order':
            order=order_get(db,row.target_id,account)
            return row.kind!='deadline' or (order.status!='Terminée' and row.event_key.endswith(str(order.confirmed_due)))
        if row.scope=='publication':return bool(visible_publication(db,db.get(PartnerPublication,row.target_id),account))
        if row.scope=='request':
            request=req_get(db,row.target_id,account)
            return row.kind!='deadline' or (request.status in ('requested','rejected','pending') and row.event_key.endswith(str(request.due_date)))
    except HTTPException:return False
    return False

def out(db,row,account):
    return {'id':row.id,'scope':row.scope,'target_id':row.target_id,'kind':row.kind,'message':row.message,
        'created_at':row.created_at,'read':db.get(PartnerNoticeRead,(account.id,row.id)) is not None}

@router.get('/api/partner/notice-center')
def notices(account=Depends(partner),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    result=[];skipped=0
    # Iterate in bounded batches, apply current scope before visible pagination.
    rows=db.scalars(select(PartnerNotice).where(PartnerNotice.partner_id==account.partner_id).order_by(PartnerNotice.created_at.desc(),PartnerNotice.id).execution_options(yield_per=100))
    for row in rows:
        if not visible(db,row,account):continue
        if skipped<offset:skipped+=1;continue
        result.append(out(db,row,account))
        if len(result)==limit:break
    return result

@router.post('/api/partner/notice-center/{nid}/read')
def read(nid:str,account=Depends(partner),db:Session=Depends(get_db)):
    row=db.get(PartnerNotice,nid)
    if not visible(db,row,account):raise HTTPException(404,'Notification introuvable')
    db.execute(insert(PartnerNoticeRead).values(account_id=account.id,notice_id=nid,read_at=utcnow()).on_conflict_do_nothing())
    db.commit();return {'read':True}

def incoming_client(db,order,message):
    from .internal_notifications import emit_to_user
    for user in db.scalars(select(User).join(User.roles).where(User.active.is_(True),Role.name=='Administrateur')).unique():
        emit_to_user(db,user_id=user.id,launch_id=order.launch_id,folder='jaune',event_key='client-message:'+message.id,
            kind='client_message',title='Message client reçu',message=f'{order.reference} : {message.text[:300]}')

def generate_due(db,today=None):
    today=today or date.today();end=today+timedelta(days=3)
    for row in db.scalars(select(PartnerRequest).where(PartnerRequest.due_date<=end,PartnerRequest.status.in_(['requested','rejected','pending']))):
        emit(db,row.partner_id,'request',row.id,'deadline',f'due:request:{row.id}:{row.due_date}',f'{row.title} · Échéance documentaire : {row.due_date}')
    for row in db.scalars(select(PartnerClientOrder).where(PartnerClientOrder.active.is_(True),PartnerClientOrder.confirmed_due<=end,PartnerClientOrder.status!='Terminée')):
        emit(db,row.partner_id,'order',row.id,'deadline',f'due:order:{row.id}:{row.confirmed_due}',f'{row.reference} · Échéance confirmée : {row.confirmed_due}')

@router.post('/api/partners/notifications/refresh-deadlines')
def refresh_due(user=Depends(staff),db:Session=Depends(get_db)):
    generate_due(db);db.commit();return {'generated':True,'external_email_sent':False}

if __name__=='__main__':
    from .core import SessionLocal
    from .migrate import migrate
    migrate()
    with SessionLocal() as db:generate_due(db);db.commit()
    print('Échéances internes actualisées ; aucun email envoyé.')
