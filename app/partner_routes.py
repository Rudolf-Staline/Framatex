"""Partner portal. All internal operations require an administrator initially.
No implicit access to internal launches, documents, users or search is granted.
"""
from datetime import timedelta, date
import hashlib
import os
import secrets
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .core import (get_db, get_current_user, utcnow, hash_password, check_password,
                   login_limit_key, login_attempt_allowed, record_login_failure, clear_login_failures, ROOT)
from .models import User, Launch, DocumentVersion
from .partner_models import (Partner, PartnerAccount, PartnerToken, PartnerRequest,
                             PartnerSubmission, PartnerEvent, PartnerPublication)
from .main import admin_only, audit, store_upload, STORAGE

router = APIRouter(tags=['Partenaires'])
COOKIE = 'framat_partner'

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def staff(user: User = Depends(get_current_user)):
    admin_only(user)
    return user

def partner(request: Request, db: Session = Depends(get_db)):
    token = db.get(PartnerToken, digest(request.cookies.get(COOKIE, '')))
    if not token or token.kind != 'session' or token.consumed or token.expires_at.replace(tzinfo=None) <= utcnow().replace(tzinfo=None):
        raise HTTPException(401, 'Session partenaire nécessaire')
    account = db.get(PartnerAccount, token.account_id)
    org = db.get(Partner, account.partner_id) if account else None
    if not account or not account.active or not account.password_hash or not org or not org.active:
        raise HTTPException(401, 'Accès partenaire révoqué')
    from .partner_permissions import require, email_allowed
    if not email_allowed(db, account.partner_id, account.email):
        raise HTTPException(403, "Domaine email non autorisé")
    require(db, account, "read")
    return account

def org_get(db, org_id, kind=None):
    org = db.get(Partner, org_id)
    if not org or (kind and org.kind != kind):
        raise HTTPException(404, 'Organisation introuvable')
    return org

def req_get(db, request_id, account=None):
    row = db.get(PartnerRequest, request_id)
    if not row or (account and row.partner_id != account.partner_id):
        raise HTTPException(404, 'Demande introuvable')
    return row

def event(db, row, actor, kind, message=''):
    entry = PartnerEvent(request_id=row.id, actor=actor, kind=kind, message=message)
    db.add(entry); db.flush()
    if actor.startswith('partner:') and kind=='message':
        from .internal_notifications import emit_to_user
        emit_to_user(db,user_id=row.created_by,launch_id=row.launch_id,folder='jaune',event_key='supplier-message:'+entry.id,kind='supplier_message',title='Message fournisseur reçu',message=f'{row.title} : {message[:300]}')
    if actor.startswith('staff:'):
        from .partner_mail import enqueue
        enqueue(db, entry)

def claim(db, row):
    # Compare-and-swap serializes decisions and uploads, including concurrent requests.
    changed = db.execute(update(PartnerRequest).where(PartnerRequest.id == row.id,
        PartnerRequest.revision == row.revision).values(revision=row.revision + 1),
        execution_options={'synchronize_session': False})
    if changed.rowcount != 1:
        raise HTTPException(409, 'Demande modifiée : actualiser puis réessayer')

def request_out(row):
    return {k: getattr(row, k) for k in ('id','partner_id','order_ref','title','doc_type','due_date','status','created_at')}

def submission_out(row):
    return {k: getattr(row, k) for k in ('id','number','original_name','sha256','size','status','reason','created_at')}

def detail(db, row):
    versions = db.scalars(select(PartnerSubmission).where(PartnerSubmission.request_id == row.id).order_by(PartnerSubmission.number)).all()
    events = db.scalars(select(PartnerEvent).where(PartnerEvent.request_id == row.id).order_by(PartnerEvent.created_at, PartnerEvent.id)).all()
    from .partner_phase2_models import PartnerIntegration
    from .models import DocumentVersion
    links = list(db.scalars(select(PartnerIntegration).where(PartnerIntegration.submission_id.in_([v.id for v in versions]))))
    return {**request_out(row), 'integrated_document_id': db.get(DocumentVersion,links[0].version_id).document_id if links else None, 'versions': [submission_out(v) for v in versions],
            'attachments': attachments_for_request(db,row.id),
            'history': [{'id': e.id, 'author': 'Framatex' if e.actor.startswith('staff:') else 'Fournisseur',
                         'kind': e.kind, 'message': e.message, 'created_at': e.created_at} for e in events]}

class OrgInput(BaseModel):
    kind: Literal['supplier', 'client']
    name: str = Field(min_length=1, max_length=150)
    contact: str = Field(default='', max_length=2000)

class ActiveInput(BaseModel):
    active: bool

class InviteInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        if value.count('@') != 1 or any(c.isspace() for c in value) or '.' not in value.split('@')[1]:
            raise ValueError('Adresse email invalide')
        return value

class InvitationInput(InviteInput):
    role_id: str | None = None

class ActivationInput(BaseModel):
    token: str = Field(min_length=30, max_length=200)
    password: str = Field(min_length=12, max_length=256)

class LoginInput(InviteInput):
    password: str = Field(max_length=256)

class RequestInput(BaseModel):
    partner_id: str
    launch_id: str
    order_ref: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    doc_type: str = Field(min_length=1, max_length=100)
    due_date: date | None = None

class MessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

class DecisionInput(BaseModel):
    version_id: str
    decision: Literal['approved', 'rejected']
    reason: str = Field(min_length=3, max_length=2000)

@router.get('/partners')
def page():
    return FileResponse(ROOT / 'static' / 'partners.html', headers={'Cache-Control':'no-store',
        'Content-Security-Policy': "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'"})

@router.get('/api/partners/organizations')
def organizations(user=Depends(staff), db: Session = Depends(get_db)):
    return [{'id': p.id, 'kind': p.kind, 'name': p.name, 'contact': p.contact, 'active': p.active}
            for p in db.scalars(select(Partner).order_by(Partner.name))]

@router.post('/api/partners/organizations', status_code=201)
def create_org(payload: OrgInput, user=Depends(staff), db: Session = Depends(get_db)):
    row = Partner(**payload.model_dump())
    db.add(row); db.flush()
    audit(db, user, 'partner.create', 'partner', row.id)
    db.commit()
    return {'id': row.id, **payload.model_dump(), 'active': row.active}

@router.patch('/api/partners/organizations/{org_id}')
def active_org(org_id: str, payload: ActiveInput, user=Depends(staff), db: Session = Depends(get_db)):
    row = org_get(db, org_id)
    row.active = payload.active
    if not payload.active:
        ids = select(PartnerAccount.id).where(PartnerAccount.partner_id == org_id)
        db.execute(update(PartnerToken).where(PartnerToken.account_id.in_(ids)).values(consumed=True))
    audit(db, user, 'partner.active', 'partner', row.id, payload.model_dump())
    db.commit()
    return {'active': row.active}

@router.get('/api/partners/organizations/{org_id}/accounts')
def accounts(org_id: str, user=Depends(staff), db: Session = Depends(get_db)):
    org_get(db, org_id)
    return [{'id': a.id, 'email': a.email, 'active': a.active, 'activated': bool(a.password_hash)}
            for a in db.scalars(select(PartnerAccount).where(PartnerAccount.partner_id == org_id))]

@router.post('/api/partners/organizations/{org_id}/invitations', status_code=201)
def invite(org_id: str, payload: InvitationInput, user=Depends(staff), db: Session = Depends(get_db)):
    org = org_get(db, org_id)
    from .partner_phase2_models import PartnerRole,PartnerRoleAssignment
    role = db.get(PartnerRole,payload.role_id) if payload.role_id else None
    if payload.role_id and (not role or role.partner_id != org_id):
        raise HTTPException(422,'Rôle étranger à cette organisation')
    if not org.active:
        raise HTTPException(409, 'Organisation suspendue')
    from .partner_permissions import email_allowed
    if not email_allowed(db, org_id, payload.email):
        raise HTTPException(422, 'Domaine email non autorisé')
    account = db.scalar(select(PartnerAccount).where(PartnerAccount.email == payload.email))
    if account and account.partner_id != org_id:
        raise HTTPException(409, 'Adresse déjà enregistrée')
    if account and not account.active:
        raise HTTPException(409, 'Réactiver le compte avant de renouveler son accès')
    if not account:
        account = PartnerAccount(partner_id=org_id, email=payload.email)
        db.add(account)
        try:
            db.flush()
        except IntegrityError:
            db.rollback(); raise HTTPException(409, 'Adresse déjà enregistrée')
    if role:
        assignment=db.get(PartnerRoleAssignment,account.id)
        if assignment:assignment.role_id=role.id
        else:db.add(PartnerRoleAssignment(account_id=account.id,role_id=role.id))
    db.execute(update(PartnerToken).where(PartnerToken.account_id == account.id,
        PartnerToken.kind == 'invite').values(consumed=True))
    token = secrets.token_urlsafe(48)
    db.add(PartnerToken(digest=digest(token), account_id=account.id, kind='invite', expires_at=utcnow()+timedelta(hours=24)))
    audit(db, user, 'partner.invite', 'partner_account', account.id)
    db.commit()
    return {'account_id': account.id, 'activation_token': token, 'expires_in_hours':24,
            'email_status':'not_sent', 'instruction':'Transmettre ce code par un canal autorisé. Aucun email envoyé.'}

@router.patch('/api/partners/accounts/{account_id}')
def active_account(account_id: str, payload: ActiveInput, user=Depends(staff), db: Session = Depends(get_db)):
    row = db.get(PartnerAccount, account_id)
    if not row:
        raise HTTPException(404, 'Compte introuvable')
    row.active = payload.active
    db.execute(update(PartnerToken).where(PartnerToken.account_id == row.id).values(consumed=True))
    audit(db, user, 'partner.account.active', 'partner_account', row.id, payload.model_dump())
    db.commit()
    return {'active': row.active}

@router.post('/api/partner-auth/activate')
def activate(payload: ActivationInput, db: Session = Depends(get_db)):
    token = db.get(PartnerToken, digest(payload.token))
    if not token or token.kind != 'invite' or token.consumed or token.expires_at.replace(tzinfo=None) <= utcnow().replace(tzinfo=None):
        raise HTTPException(400, 'Invitation invalide ou expirée')
    account = db.get(PartnerAccount, token.account_id)
    if not account.active or not org_get(db, account.partner_id).active:
        raise HTTPException(400, 'Invitation invalide ou expirée')
    password_hash = hash_password(payload.password)
    changed = db.execute(update(PartnerToken).where(PartnerToken.digest == token.digest,
        PartnerToken.consumed.is_(False)).values(consumed=True))
    if changed.rowcount != 1:
        raise HTTPException(409, 'Invitation déjà utilisée')
    account.password_hash = password_hash
    db.execute(update(PartnerToken).where(PartnerToken.account_id == account.id).values(consumed=True))
    audit(db, None, 'partner.activate', 'partner_account', account.id)
    db.commit()
    return {'activated': True}

@router.post('/api/partner-auth/login')
def login(payload: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    key = login_limit_key(request.client.host if request.client else 'unknown', 'partner:'+payload.email)
    if not login_attempt_allowed(key):
        raise HTTPException(429, 'Trop de tentatives, réessayer plus tard')
    account = db.scalar(select(PartnerAccount).where(PartnerAccount.email == payload.email))
    if not account or not account.active or not account.password_hash or not check_password(account.password_hash, payload.password) or not org_get(db, account.partner_id).active:
        record_login_failure(key)
        raise HTTPException(401, 'Identifiants invalides')
    clear_login_failures(key)
    token = secrets.token_urlsafe(48)
    db.add(PartnerToken(digest=digest(token), account_id=account.id, kind='session', expires_at=utcnow()+timedelta(hours=8)))
    db.commit()
    from .core import cookie_secure
    response.set_cookie(COOKIE, token, httponly=True, samesite='strict', secure=cookie_secure(), max_age=28800)
    return {'id': account.id, 'organization': org_get(db, account.partner_id).name}

@router.post('/api/partner-auth/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    db.execute(update(PartnerToken).where(PartnerToken.digest == digest(request.cookies.get(COOKIE,''))).values(consumed=True))
    db.commit(); response.delete_cookie(COOKIE)
    return {'logged_out': True}

@router.get('/api/partner/home')
def home(account=Depends(partner), db: Session = Depends(get_db)):
    org = org_get(db, account.partner_id)
    from .partner_permissions import permissions
    return {'organization': org.name, 'kind': org.kind, 'email': account.email, 'permissions': sorted(permissions(db, account))}

@router.post('/api/partners/requests', status_code=201)
def create_request(payload: RequestInput, user=Depends(staff), db: Session = Depends(get_db)):
    org = org_get(db, payload.partner_id, 'supplier')
    if not org.active or not db.get(Launch, payload.launch_id):
        raise HTTPException(422, 'Organisation inactive ou lancement inexistant')
    from .order_registry_routes import check_order_scope
    check_order_scope(db,payload.launch_id,reference=payload.order_ref)
    row = PartnerRequest(**payload.model_dump(), created_by=user.id)
    db.add(row); db.flush()
    event(db, row, 'staff:'+user.id, 'requested', payload.title)
    audit(db, user, 'partner.request', 'partner_request', row.id)
    db.commit()
    return request_out(row)

@router.get('/api/partners/requests')
def staff_requests(user=Depends(staff), db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), q: str = Query('',max_length=200), status: str | None = None, sort: Literal['newest','oldest','due']='newest'):
    return request_search(db,None,q,status,sort,offset,limit)

@router.get('/api/partner/requests')
def supplier_requests(account=Depends(partner), db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), q: str = Query('',max_length=200), status: str | None = None, sort: Literal['newest','oldest','due']='newest'):
    return request_search(db,account.partner_id,q,status,sort,offset,limit)

@router.get('/api/partners/requests/{rid}')
def staff_detail(rid: str, user=Depends(staff), db: Session = Depends(get_db)):
    return detail(db, req_get(db, rid))

@router.get('/api/partner/requests/{rid}')
def supplier_detail(rid: str, account=Depends(partner), db: Session = Depends(get_db)):
    result = detail(db, req_get(db, rid, account))
    result.pop('integrated_document_id',None)
    return result

@router.post('/api/partner/requests/{rid}/versions', status_code=201)
async def upload(rid: str, file: UploadFile = File(...), account=Depends(partner), db: Session = Depends(get_db)):
    from .partner_permissions import require
    require(db, account, 'document.write')
    row = req_get(db, rid, account)
    if row.status not in ('requested','rejected'):
        raise HTTPException(409, 'Dépôt autorisé pour une demande ouverte ou refusée uniquement')
    claim(db, row)
    from .partner_uploads import lock_budget,verify_budget
    lock_budget(db,row.partner_id)
    original, disk, size, sha, mime = await store_upload(file)
    try:
        verify_budget(db,row.partner_id,size)
        latest = db.scalar(select(PartnerSubmission).where(PartnerSubmission.request_id == rid).order_by(PartnerSubmission.number.desc()).limit(1))
        version = PartnerSubmission(request_id=rid, number=latest.number+1 if latest else 1,
            account_id=account.id, original_name=original, disk_name=disk, size=size, sha256=sha, content_type=mime)
        db.add(version); db.flush()
        row.status = 'pending'
        event(db, row, 'partner:'+account.id, 'submitted', f'Version {version.number} · SHA256 {sha}')
        from .internal_notifications import emit_to_user
        emit_to_user(db, user_id=row.created_by, launch_id=row.launch_id, folder='jaune',
            event_key='partner-submission:'+version.id, kind='supplier_submission', title='Document fournisseur reçu', message=row.title)
        db.commit()
        return submission_out(version)
    except Exception:
        db.rollback(); (STORAGE / disk).unlink(missing_ok=True); raise

@router.post('/api/partners/requests/{rid}/decision')
def decision(rid: str, payload: DecisionInput, user=Depends(staff), db: Session = Depends(get_db)):
    row = req_get(db, rid)
    latest = db.scalar(select(PartnerSubmission).where(PartnerSubmission.request_id == rid).order_by(PartnerSubmission.number.desc()).limit(1))
    if row.status != 'pending' or not latest or latest.id != payload.version_id:
        raise HTTPException(409, 'Seule la version courante en attente peut être examinée')
    claim(db, row)
    latest.status = row.status = payload.decision
    latest.reason = payload.reason; latest.reviewed_by = user.id
    event(db, row, 'staff:'+user.id, payload.decision, f'Version {latest.number} : {payload.reason}')
    audit(db, user, 'partner.review', 'partner_submission', latest.id, payload.model_dump())
    db.commit()
    return detail(db, row)

@router.post('/api/partners/requests/{rid}/close')
def close(rid: str, user=Depends(staff), db: Session = Depends(get_db)):
    row = req_get(db, rid)
    if row.status != 'approved':
        raise HTTPException(409, 'Approbation requise avant clôture')
    claim(db, row); row.status = 'closed'
    event(db, row, 'staff:'+user.id, 'closed')
    audit(db, user, 'partner.close', 'partner_request', row.id)
    db.commit(); return request_out(row)

@router.post('/api/partner/requests/{rid}/messages', status_code=201)
def supplier_message(rid: str, payload: MessageInput, account=Depends(partner), db: Session = Depends(get_db)):
    from .partner_permissions import require
    require(db, account, 'message.write')
    row = req_get(db, rid, account)
    event(db, row, 'partner:'+account.id, 'message', payload.message)
    db.commit(); return {'recorded':True, 'email_status':'not_sent'}

@router.post('/api/partners/requests/{rid}/messages', status_code=201)
def staff_message(rid: str, payload: MessageInput, user=Depends(staff), db: Session = Depends(get_db)):
    event(db, req_get(db, rid), 'staff:'+user.id, 'message', payload.message)
    db.commit(); return {'recorded':True, 'email_status':'not_sent'}

def download(db, rid, vid, account=None):
    req_get(db, rid, account)
    version = db.get(PartnerSubmission, vid)
    if not version or version.request_id != rid or not (STORAGE / version.disk_name).is_file():
        raise HTTPException(404, 'Pièce introuvable')
    return FileResponse(STORAGE / version.disk_name, filename=version.original_name, media_type=version.content_type)

@router.get('/api/partner/requests/{rid}/versions/{vid}/download')
def supplier_download(rid: str, vid: str, account=Depends(partner), db: Session = Depends(get_db)):
    return download(db, rid, vid, account)

@router.get('/api/partners/requests/{rid}/versions/{vid}/download')
def staff_download(rid: str, vid: str, user=Depends(staff), db: Session = Depends(get_db)):
    return download(db, rid, vid)

class PublicationInput(BaseModel):
    partner_id: str
    publication_id: str

@router.post('/api/partners/publications', status_code=201)
def publish(payload: PublicationInput, user=Depends(staff), db: Session = Depends(get_db)):
    from .sharing_models import ClientPublication
    from .sharing_routes import pub_out, norm
    org = org_get(db, payload.partner_id, 'client')
    publication = db.get(ClientPublication, payload.publication_id)
    launch = db.get(Launch, publication.launch_id) if publication else None
    if not org.active or not publication or not pub_out(db, publication, launch)['effective'] or norm(org.name) != norm(publication.client_name):
        raise HTTPException(409, 'Publication approuvée effective et destinataire correspondant requis')
    from .partner_phase2_models import PartnerClientOrder
    grant=db.scalar(select(PartnerClientOrder).where(PartnerClientOrder.partner_id==org.id,PartnerClientOrder.launch_id==publication.launch_id))
    if grant and not grant.active:raise HTTPException(409,'Accès à la commande retiré')
    from .order_registry_routes import check_order_scope
    check_order_scope(db,publication.launch_id,client_id=org.id)
    row = PartnerPublication(**payload.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, 'Publication déjà attribuée')
    from .partner_notice_routes import emit
    emit(db,org.id,'publication',row.id,'publication','publication:'+row.id,'Une nouvelle version documentaire est publiée pour votre organisation')
    audit(db, user, 'partner.publish', 'partner_publication', row.id)
    db.commit(); return {'id':row.id}

def visible_publication(db, row, account):
    from .sharing_models import ClientPublication
    from .sharing_routes import pub_out
    if not row or row.partner_id != account.partner_id or org_get(db, account.partner_id).kind != 'client':
        return None
    publication = db.get(ClientPublication, row.publication_id)
    from .partner_phase2_models import PartnerClientOrder
    grant = db.scalar(select(PartnerClientOrder).where(PartnerClientOrder.partner_id==account.partner_id,PartnerClientOrder.launch_id==publication.launch_id))
    if grant and not grant.active:
        return None
    launch = db.get(Launch, publication.launch_id)
    if not pub_out(db, publication, launch)['effective']:
        return None
    return publication

@router.get('/api/partner/publications')
def publications(account=Depends(partner), db: Session = Depends(get_db)):
    result = []
    for row in db.scalars(select(PartnerPublication).where(PartnerPublication.partner_id == account.partner_id)):
        publication = visible_publication(db, row, account)
        if publication:
            version = db.get(DocumentVersion, publication.document_version_id)
            result.append({'id':row.id, 'title':version.document.title, 'version':version.number,
                           'published_at':publication.created_at})
    return result

@router.get('/api/partner/publications/{pid}/download')
def client_download(pid: str, account=Depends(partner), db: Session = Depends(get_db)):
    publication = visible_publication(db, db.get(PartnerPublication, pid), account)
    if not publication:
        raise HTTPException(404, 'Publication introuvable')
    version = db.get(DocumentVersion, publication.document_version_id)
    path = STORAGE / version.disk_name
    if not path.is_file():
        raise HTTPException(404, 'Fichier indisponible')
    audit(db, None, 'partner.download', 'partner_publication', pid, {'account_id':account.id})
    db.commit()
    return FileResponse(path, filename=version.original_name, media_type=version.content_type)


@router.get('/api/partner/mail-preference')
def mail_preference(account=Depends(partner), db: Session = Depends(get_db)):
    from .partner_models import PartnerMailPreference
    row = db.get(PartnerMailPreference, account.id)
    return {'enabled': bool(row and row.enabled), 'transport_configured': os.getenv('FRAMATEX_EMAIL_ENABLED') == '1'}

@router.put('/api/partner/mail-preference')
def set_mail_preference(payload: ActiveInput, account=Depends(partner), db: Session = Depends(get_db)):
    from .partner_models import PartnerMailPreference
    row = db.get(PartnerMailPreference, account.id)
    if not row:
        row = PartnerMailPreference(account_id=account.id); db.add(row)
    row.enabled = payload.active
    db.commit(); return {'enabled': row.enabled}

@router.get('/api/partners/mail')
def mail_queue(user=Depends(staff), db: Session = Depends(get_db)):
    from .partner_models import PartnerMail
    return [{'id':m.id,'status':m.status,'attempts':m.attempts,'last_error':m.last_error,
             'next_at':m.next_at,'accepted_at':m.accepted_at}
            for m in db.scalars(select(PartnerMail).order_by(PartnerMail.next_at.desc()).limit(100))]


def attachments_for_request(db,rid):
    from .partner_phase2_models import PartnerAttachment
    from .partner_attachment_routes import out
    return [out(a) for a in db.scalars(select(PartnerAttachment).join(PartnerEvent).where(PartnerEvent.request_id==rid))]


def request_search(db,partner_id,q,status,sort,offset,limit):
    query=select(PartnerRequest)
    if partner_id:query=query.where(PartnerRequest.partner_id==partner_id)
    if q:query=query.where(or_(PartnerRequest.title.ilike('%'+q+'%'),PartnerRequest.order_ref.ilike('%'+q+'%'),PartnerRequest.doc_type.ilike('%'+q+'%')))
    if status:query=query.where(PartnerRequest.status==status)
    order={'newest':PartnerRequest.created_at.desc(),'oldest':PartnerRequest.created_at.asc(),'due':PartnerRequest.due_date.asc().nulls_last()}[sort]
    return [request_out(row) for row in db.scalars(query.order_by(order,PartnerRequest.id).offset(offset).limit(limit))]

@router.get('/api/partner/notifications')
def partner_notifications(account=Depends(partner),db:Session=Depends(get_db),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    from .partner_phase2_models import PartnerEventRead
    rows=db.scalars(select(PartnerEvent).join(PartnerRequest).where(PartnerRequest.partner_id==account.partner_id,PartnerEvent.actor.like('staff:%')).order_by(PartnerEvent.created_at.desc(),PartnerEvent.id).offset(offset).limit(limit))
    return [{'id':e.id,'request_id':e.request_id,'kind':e.kind,'message':e.message,'created_at':e.created_at,'read':db.get(PartnerEventRead,(account.id,e.id)) is not None} for e in rows]

@router.post('/api/partner/notifications/{nid}/read')
def mark_partner_notification(nid:str,account=Depends(partner),db:Session=Depends(get_db)):
    from .partner_phase2_models import PartnerEventRead
    e=db.get(PartnerEvent,nid)
    if not e:raise HTTPException(404,'Notification introuvable')
    req_get(db,e.request_id,account)
    if not db.get(PartnerEventRead,(account.id,nid)):
        db.add(PartnerEventRead(account_id=account.id,event_id=nid))
        try:db.commit()
        except IntegrityError:db.rollback()
    return {'read':True}
