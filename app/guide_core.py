"""One source of procedures, permissions, local retrieval and safe action resolution."""
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
import json,re,unicodedata
from fastapi import HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,update
from .core import get_current_user,COOKIE,SessionLocal

DATA=Path(__file__).parent/'guide_data'
CATALOG=json.loads((DATA/'catalog.fr.json').read_text())
NAV=json.loads((DATA/'navigation.json').read_text())
PROCEDURES={p['id']:p for p in CATALOG['procedures']}
TOURS={t['id']:t for t in CATALOG['tours']}
ACTIONS=CATALOG['actions']

@dataclass
class Principal:
    kind:str
    subject:object
    rights:set
    admin:bool=False
    @property
    def owner(self):return ('partner:' if self.kind in ('supplier','client') else 'employee:')+self.subject.id
    @property
    def audience(self):return 'admin' if self.admin else self.kind


def principal(request,db):
    surface=request.headers.get('X-Framatex-Guide-Surface','internal')
    if surface not in ('internal','partner'):raise HTTPException(422,'Espace de guide inconnu')
    if surface=='partner':
        from .partner_routes import partner
        from .partner_models import Partner
        from .partner_permissions import permissions
        user=partner(request,db);return Principal(db.get(Partner,user.partner_id).kind,user,permissions(db,user))
    from .main import is_admin
    user=get_current_user(request,db)
    return Principal('employee',user,set(),is_admin(user))


def permitted(principal,requirements):
    from .main import permitted as employee_permitted
    for req in requirements:
        if req.get('admin') and not principal.admin:return False
        if 'audience' in req and principal.audience not in req['audience']:return False
        if 'partner_permission' in req and req['partner_permission'] not in principal.rights:return False
        if 'action' in req:
            if principal.kind!='employee':return False
            f=req.get('folder')
            if f=='any':
                if not any(employee_permitted(principal.subject,req['action'],slug) for slug in ('jaune','rose','bleu','vert')):return False
            elif not employee_permitted(principal.subject,req['action'],f):return False
    return True


def visible(p,principal):return principal.audience in p['audience'] and permitted(principal,p['requires'])

def related(p,page):
    """Map rendered screens to catalogue destinations, independently of UI labels."""
    destination=NAV[p['destination']]
    if p['destination']==page:return True
    if page=='dossiers':return destination['handler'] in ('order','order_upload')
    if page=='detail':return destination['handler']=='launch'
    if page in ('supplier','client'):return page in p['audience'] and destination['surface']=='partner'
    if page=='partner_admin':return destination['handler']=='partner_admin'
    if page=='documents':return p['destination']=='search'
    return False


def procedure(pid,principal):
    p=PROCEDURES.get(pid)
    if not p or not visible(p,principal):raise HTTPException(404,'Procédure introuvable pour vos habilitations')
    return p


def tour(tid,principal):
    t=TOURS.get(tid)
    if not t or not visible(t,principal):raise HTTPException(404,'Visite introuvable pour vos habilitations')
    if t['procedure_id']:procedure(t['procedure_id'],principal)
    result={**t,'steps':[s for s in t['steps'] if permitted(principal,NAV[s['destination']]['requires'])]}
    if not result['steps']:raise HTTPException(404,'Aucune étape autorisée dans cette visite')
    return result


class GuideContext(BaseModel):
    model_config=ConfigDict(extra='forbid')
    page:str=Field('home',max_length=40)
    procedure_id:str|None=Field(None,max_length=100,pattern=r'^[a-z][a-z0-9_]+$')
    order_id:str|None=Field(None,pattern=r'^[0-9a-fA-F-]{36}$')
    launch_id:str|None=Field(None,pattern=r'^[0-9a-fA-F-]{36}$')
    client_order_id:str|None=Field(None,pattern=r'^[0-9a-fA-F-]{36}$')
    supplier_request_id:str|None=Field(None,pattern=r'^[0-9a-fA-F-]{36}$')


def check_context(context,who,db):
    if context.page not in set(NAV)|{'detail','assistant','help','supplier','client','partners','documents','unknown'}:
        raise HTTPException(422,'Page de contexte inconnue')
    if context.procedure_id:procedure(context.procedure_id,who)
    if (context.order_id or context.launch_id) and (who.kind!='employee' or not permitted(who,[{'action':'launch.read'}])):raise HTTPException(404,'Contexte inaccessible')
    if context.order_id:
        if who.kind!='employee':raise HTTPException(404,'Commande introuvable')
        from .order_documents import must_order
        must_order(db,who.subject,context.order_id)
    if context.launch_id:
        if who.kind!='employee':raise HTTPException(404,'Lancement introuvable')
        from .access import must_access
        must_access(db,who.subject,context.launch_id)
        if context.order_id:
            from .order_documents import launch_order
            relation=launch_order(db,context.launch_id)
            if not relation or relation.order_id!=context.order_id:raise HTTPException(422,'Contexte commande/lancement incompatible')
    if context.client_order_id:
        from .partner_client_routes import order_get
        if who.kind!='client':raise HTTPException(404,'Commande client introuvable')
        order_get(db,context.client_order_id,who.subject)
    if context.supplier_request_id:
        from .partner_routes import req_get
        if who.kind!='supplier':raise HTTPException(404,'Demande introuvable')
        req_get(db,context.supplier_request_id,who.subject)
    return context


def resolve(action_id,who,context,db):
    a=ACTIONS.get(action_id)
    if not a:raise HTTPException(404,'Action de guide inconnue')
    p=procedure(a['procedure_id'],who)
    if a['type']=='start_tour':tour(a['destination'],who)
    if a['type']=='open_procedure':return {**a,'navigation':None,'context':{},'folder':None,'requires_selection':None}
    d=NAV[p['destination']]
    if not permitted(who,d['requires']):raise HTTPException(404,'Destination inaccessible')
    check_context(context,who,db)
    resource=d['context'];key={'order':'order_id','launch':'launch_id','supplier_request':'supplier_request_id','client_order':'client_order_id'}.get(resource)
    missing=bool(key and not getattr(context,key))
    folder=p['destination'].removeprefix('order_') if p['destination'] in ('order_jaune','order_rose','order_bleu','order_vert') else 'jaune' if p['id']=='upload_technical_document' else None
    return {**a,'navigation':d,'context':context.model_dump(),'folder':folder,'requires_selection':resource if missing else None}

STOP=set('comment ou je peux puis une un le la les des de du dans pour mon ma mes est et au aux a quel quelle il faut faire vous moi me cette ce ça'.split())
def normalize(text):return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
def words(text):return [w.rstrip('s') for w in re.findall(r'[a-z0-9]+',normalize(text)) if w not in STOP and len(w)>1]
VOCAB={w for p in PROCEDURES.values() for text in [p['title'],*p['keywords']] for w in words(text)}
def terms(text):
    result=[]
    for w in words(text):result.append(w if w in VOCAB else next(iter(get_close_matches(w,sorted(VOCAB),n=1,cutoff=.82)),w))
    return result


def rank(question):
    tokens=terms(question);ws=set(tokens);result=[]
    for p in PROCEDURES.values():
        title=set(words(p['title']));score=2*len(ws&title)
        for key in p['keywords']:
            kw=set(words(key))
            score=max(score,6*len(kw)+len(ws&title) if kw and kw<=ws else len(ws&kw))
        verbs={'creer','ajouter','deposer','inviter','approuver','corriger','reouvrir','rechercher','retrouver','transmettre','consulter','configurer','poser','joindre','declarer','repondre'}
        score+=5*len(ws&title&verbs)
        if title and title<=ws:score+=10
        if score>=2:result.append((score,p))
    return sorted(result,key=lambda item:(-item[0],item[1]['id']))


def retrieve(question,who,context,limit=5):
    normalized=normalize(question)
    if any(x in normalized for x in ('prix de vente','montant exact','quantite exacte','contenu du document','contenu de la facture')):return [],True
    if any(x in normalized for x in ('ignore les','ignore previous','system prompt','reveal secret','instructions precedentes','tous les mots de passe','donne le mot de passe')):
        return [],True
    if 'cette page' in normalized:
        candidates=[p for p in PROCEDURES.values() if visible(p,who) and related(p,context.page)]
        return candidates[:limit],False
    if context.procedure_id and any(phrase in normalized for phrase in ('et ensuite','et apres','la suite','cette procedure','cette etape')):
        p=PROCEDURES.get(context.procedure_id)
        if p and visible(p,who):return [p],False
    all_hits=rank(question)
    if all_hits and who.audience in all_hits[0][1]['audience'] and not visible(all_hits[0][1],who) and all_hits[0][0]>=6:return [],True
    hits=[(score,p) for score,p in all_hits if visible(p,who)]
    if not hits:return [],False
    best=hits[0][0]
    hits=[(s,p) for s,p in hits if s>=max(2,best*.45)]
    return [p for _,p in hits[:limit]],False


def answer(procs,who,context,db,*,clarification=False,source='local',fallback=None):
    chosen=procs[:3]
    return {'title':chosen[0]['title'] if chosen else 'Question à préciser',
        'answer':'\n'.join(f'{i+1}. {s["description"]}' for i,s in enumerate(chosen[0]['steps'])) if chosen else 'Je ne dispose pas de procédure vérifiée et autorisée pour cette demande. Précisez la fonctionnalité ou consultez le centre d’aide.',
        'procedure_ids':[p['id'] for p in chosen],'procedures':chosen,
        'actions':[resolve(a,who,context,db) for p in chosen for a in p['actions']],
        'requires_clarification':clarification or not chosen,'source':source,'fallback_reason':fallback,
        'requires_human_action':True,'business_operations_performed':False}


def reserve(key,limit,window):
    """Atomic counters persist across workers and restarts; no question text stored."""
    import time
    from sqlalchemy.dialects.sqlite import insert
    from .guide_models import GuideBudget
    key=f'{key}:{int(time.time())//window}'
    with SessionLocal() as db:
        db.execute(insert(GuideBudget).values(key=key,used=0).on_conflict_do_nothing(index_elements=['key']))
        n=db.execute(update(GuideBudget).where(GuideBudget.key==key,GuideBudget.used<limit).values(used=GuideBudget.used+1)).rowcount
        db.commit();return n==1


def setting(name,default,minimum=1,maximum=100000):
    import os
    try:value=int(os.getenv(name,str(default)))
    except ValueError:return default
    return value if minimum<=value<=maximum else default
