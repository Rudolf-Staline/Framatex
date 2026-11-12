"""Shared, authenticated help APIs; no endpoint writes a business object."""
from collections import Counter
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from .core import get_db,ROOT,utcnow
from .guide_core import (principal,PROCEDURES,NAV,TOURS,CATALOG,GuideContext,procedure,tour,visible,permitted,
                         resolve,check_context,retrieve,answer,related,reserve,setting,Principal)
from .guide_models import GuideProgress,GuidePreference,GuideFeedback,GuideVisit,GuideEvent

router=APIRouter(tags=['Framatex Guide'])

def identity(request:Request,db:Session=Depends(get_db)):
    who=principal(request,db)
    if not reserve('http:'+who.owner,setting('FRAMATEX_GUIDE_HTTP_REQUESTS_PER_MINUTE',300),60):raise HTTPException(429,'Guide temporairement limité : réessayez dans une minute')
    return who

def decorate(p):return {**p,'help_url':'/help?surface='+('internal' if any(a in p['audience'] for a in ('employee','admin')) else 'partner')+'#procedure/'+p['id']}

def event(db,who,kind,target=''):
    db.add(GuideEvent(owner=who.owner,kind=kind,target=target))

@router.get('/help')
def help_page():
    return FileResponse(ROOT/'static/guide.html',headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"})

@router.get('/api/guide/public')
def public_help():
    who=Principal('public',None,set())
    return {'version':CATALOG['version'],'audience':'public','procedures':[decorate(p) for p in PROCEDURES.values() if visible(p,who)],'navigation':{k:v for k,v in NAV.items() if k in ('activate_account','login_partner')},'actions':[],'tours':[],'recent':[],'popular':[p['id'] for p in PROCEDURES.values() if visible(p,who)],'automatic':'never'}

@router.get('/api/guide/catalog')
def catalog(request:Request,who=Depends(identity),db:Session=Depends(get_db)):
    allowed=[p for p in PROCEDURES.values() if visible(p,who)];ids={p['id'] for p in allowed}
    recent=list(db.scalars(select(GuideVisit).where(GuideVisit.owner==who.owner).order_by(GuideVisit.updated_at.desc()).limit(20)))
    popular=[pid for pid,_count in db.execute(select(GuideVisit.procedure_id,func.sum(GuideVisit.views)).group_by(GuideVisit.procedure_id).order_by(func.sum(GuideVisit.views).desc())) if pid in ids][:6]
    preference=db.get(GuidePreference,who.owner)
    import hashlib
    return {'session_key':hashlib.sha256(request.cookies.get('framat_partner' if who.kind in ('supplier','client') else 'framat_session','').encode()).hexdigest()[:20],'profile_key':hashlib.sha256(who.owner.encode()).hexdigest()[:20],'version':CATALOG['version'],'locale':'fr','available_locales':['fr'],'audience':who.audience,
        'procedures':[decorate(p) for p in allowed],'navigation':{k:v for k,v in NAV.items() if permitted(who,v['requires']) and (v['surface']=='internal')==(who.kind=='employee')},
        'recent':[r.procedure_id for r in recent if r.procedure_id in ids],'popular':popular or [p['id'] for p in allowed[:6]],'automatic':preference.automatic if preference else 'new',
        'welcome_available':any(permitted(who,NAV[s['destination']]['requires']) for s in TOURS['welcome_'+who.audience]['steps']),
        'ai_configured':__import__('os').getenv('FRAMATEX_GUIDE_AI_ENABLED','0')=='1' and bool(__import__('os').getenv('GEMINI_API_KEY'))}

@router.get('/api/guide/categories')
def categories(who=Depends(identity)):
    counts=Counter(p['category'] for p in PROCEDURES.values() if visible(p,who))
    return [{'id':k,'count':v} for k,v in sorted(counts.items())]

@router.get('/api/guide/procedures/{pid}')
def detail(pid:str,who=Depends(identity),db:Session=Depends(get_db)):
    return decorate(procedure(pid,who))

@router.post('/api/guide/procedures/{pid}/visit')
def visit(pid:str,who=Depends(identity),db:Session=Depends(get_db)):
    procedure(pid,who)
    from sqlalchemy.dialects.sqlite import insert
    stmt=insert(GuideVisit).values(owner=who.owner,procedure_id=pid,views=1,updated_at=utcnow())
    db.execute(stmt.on_conflict_do_update(index_elements=['owner','procedure_id'],set_={'views':GuideVisit.views+1,'updated_at':utcnow()}));db.commit()
    return {'recorded':True}

@router.get('/api/guide/search')
def search(q:str=Query('',max_length=500),page:str=Query('home',max_length=40),who=Depends(identity)):
    context=GuideContext(page=page)
    if page not in set(NAV)|{'detail','assistant','help','supplier','client','partners','documents','unknown'}:raise HTTPException(422,'Page inconnue')
    if not q.strip():hits=[p for p in PROCEDURES.values() if visible(p,who) and (related(p,page) or page=='help')][:8];denied=False
    else:hits,denied=retrieve(q,who,context,8)
    return {'items':[decorate(p) for p in hits],'total':len(hits),'restricted':denied}

class Ask(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=2,max_length=500)
    context:GuideContext=Field(default_factory=GuideContext)
    use_ai:bool=True

@router.post('/api/guide/ask')
def ask(payload:Ask,who=Depends(identity),db:Session=Depends(get_db)):
    if len(payload.question.strip())<2:raise HTTPException(422,'Question vide')
    check_context(payload.context,who,db)
    if not reserve('ask:'+who.owner,setting('FRAMATEX_GUIDE_REQUESTS_PER_MINUTE',40),60):raise HTTPException(429,'Trop de questions : réessayez dans une minute')
    hits,denied=retrieve(payload.question,who,payload.context)
    mode='local';fallback='restricted' if denied else None;clarification=len(hits)>1 and len(payload.question.split())<=2
    if hits and payload.use_ai and not denied:
        from .guide_gemini import choose
        selection,fallback=choose(payload.question,who,payload.context,hits)
        if selection:
            allowed={p['id']:p for p in hits};hits=[allowed[pid] for pid in selection.procedure_ids]
            mode='gemini';clarification=selection.requires_clarification
    event(db,who,'unresolved' if not hits else 'clarification' if clarification else 'answered');db.commit()
    return answer(hits,who,payload.context,db,clarification=clarification,source=mode,fallback=fallback)

@router.post('/api/guide/actions/{action_id}/resolve')
def action(action_id:str,context:GuideContext,who=Depends(identity),db:Session=Depends(get_db)):
    return resolve(action_id,who,context,db)

@router.get('/api/guide/tours')
def tours(who=Depends(identity)):
    result=[]
    for t in TOURS.values():
        if visible(t,who):
            try:result.append(tour(t['id'],who))
            except HTTPException as exc:
                if exc.status_code!=404:raise
    return result

@router.get('/api/guide/tours/{tid}')
def get_tour(tid:str,who=Depends(identity)):return tour(tid,who)

@router.get('/api/guide/progress')
def progress(who=Depends(identity),db:Session=Depends(get_db)):
    return [{k:getattr(r,k) for k in ('tour_id','version','step','status','updated_at')} for r in db.scalars(select(GuideProgress).where(GuideProgress.owner==who.owner)) if r.tour_id in TOURS and visible(TOURS[r.tour_id],who)]

class ProgressInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tour_id:str=Field(max_length=100)
    version:int=Field(ge=1,le=10000)
    step:int=Field(ge=0,le=100)
    status:Literal['started','paused','finished','skipped','missing']

@router.put('/api/guide/progress')
def save_progress(payload:ProgressInput,who=Depends(identity),db:Session=Depends(get_db)):
    t=tour(payload.tour_id,who)
    if payload.version!=t['version'] or payload.step>=len(t['steps']):raise HTTPException(409,'La visite a changé : rechargez ses étapes')
    if payload.status=='finished' and payload.step!=len(t['steps'])-1:raise HTTPException(422,'La visite doit atteindre sa dernière étape')
    from sqlalchemy.dialects.sqlite import insert
    values={'owner':who.owner,**payload.model_dump(),'updated_at':utcnow()}
    stmt=insert(GuideProgress).values(**values)
    db.execute(stmt.on_conflict_do_update(index_elements=['owner','tour_id','version'],set_={k:v for k,v in values.items() if k not in ('owner','tour_id','version')}))
    event(db,who,'tour_'+payload.status,payload.tour_id);db.commit();return {'saved':True}

class PreferenceInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    automatic:Literal['later','never','accepted']

@router.put('/api/guide/preferences')
def preferences(payload:PreferenceInput,who=Depends(identity),db:Session=Depends(get_db)):
    from sqlalchemy.dialects.sqlite import insert
    stmt=insert(GuidePreference).values(owner=who.owner,automatic=payload.automatic,updated_at=utcnow())
    db.execute(stmt.on_conflict_do_update(index_elements=['owner'],set_={'automatic':payload.automatic,'updated_at':utcnow()}));db.commit();return {'saved':True}

class FeedbackInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    procedure_id:str|None=Field(None,max_length=100)
    helpful:bool
    reason:Literal['none','unclear','outdated','missing','navigation','other']='none'

@router.post('/api/guide/feedback',status_code=201)
def feedback(payload:FeedbackInput,who=Depends(identity),db:Session=Depends(get_db)):
    if payload.procedure_id:procedure(payload.procedure_id,who)
    if not reserve('feedback:'+who.owner,20,60):raise HTTPException(429,'Retours trop fréquents')
    db.add(GuideFeedback(owner=who.owner,**payload.model_dump()));db.commit();return {'recorded':True,'alternatives':'/help'}

@router.get('/api/guide/stats')
def stats(who=Depends(identity),db:Session=Depends(get_db)):
    if not who.admin:raise HTTPException(403,'Statistiques réservées aux administrateurs')
    return {'procedure_views':[{'procedure_id':p,'views':n} for p,n in db.execute(select(GuideVisit.procedure_id,func.sum(GuideVisit.views)).group_by(GuideVisit.procedure_id))],
        'events':dict(db.execute(select(GuideEvent.kind,func.count()).group_by(GuideEvent.kind)).all()),
        'insufficient':[{'procedure_id':p,'count':n} for p,n in db.execute(select(GuideFeedback.procedure_id,func.count()).where(GuideFeedback.helpful.is_(False)).group_by(GuideFeedback.procedure_id))],
        'abandonment':[{'tour_id':t,'step':s,'count':n} for t,s,n in db.execute(select(GuideProgress.tour_id,GuideProgress.step,func.count()).where(GuideProgress.status.in_(['paused','missing'])).group_by(GuideProgress.tour_id,GuideProgress.step))],
        'question_text_stored':False}

@router.get('/api/guide/contexts/{kind}')
def contexts(kind:Literal['order','launch','supplier_request','client_order'],order_id:str|None=Query(None,min_length=36,max_length=36),who=Depends(identity),db:Session=Depends(get_db)):
    if who.kind=='employee' and not permitted(who,[{'action':'launch.read'}]):raise HTTPException(404,'Contexte inaccessible')
    if kind=='order' and who.kind=='employee':
        from .partner_phase2_models import BusinessOrder
        from .order_documents import order_accessible
        return [{'id':r.id,'label':r.reference} for r in db.scalars(select(BusinessOrder).order_by(BusinessOrder.created_at.desc())) if order_accessible(db,who.subject,r.id)]
    if kind=='launch' and who.kind=='employee':
        from .models import Launch
        from .access import accessible
        query=select(Launch).order_by(Launch.created_at.desc())
        if order_id:
            from .order_documents import must_order
            from .partner_phase2_models import BusinessOrderLaunch
            must_order(db,who.subject,order_id)
            query=query.join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id==order_id)
        return [{'id':r.id,'label':r.name} for r in db.scalars(query) if accessible(db,who.subject,r)]
    if kind=='supplier_request' and who.kind=='supplier':
        from .partner_models import PartnerRequest
        return [{'id':r.id,'label':r.title} for r in db.scalars(select(PartnerRequest).where(PartnerRequest.partner_id==who.subject.partner_id).order_by(PartnerRequest.created_at.desc()))]
    if kind=='client_order' and who.kind=='client':
        from .partner_phase2_models import PartnerClientOrder
        from .partner_client_routes import order_get
        rows=[]
        for r in db.scalars(select(PartnerClientOrder).where(PartnerClientOrder.partner_id==who.subject.partner_id,PartnerClientOrder.active.is_(True))):
            try:order_get(db,r.id,who.subject)
            except HTTPException:continue
            rows.append({'id':r.id,'label':r.reference})
        return rows
    raise HTTPException(404,'Type de contexte inaccessible')
