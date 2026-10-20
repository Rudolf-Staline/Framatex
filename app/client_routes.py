"""Client directory and authenticated portal, isolated from internal APIs."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_db, get_current_user, hash_password
from .models import Client, ClientContact, User, Launch, DocumentVersion
from .sharing_models import ClientPublication
from .main import admin_only, must, permitted, audit, STORAGE
from .cloud_storage import ensure_local

router = APIRouter(tags=['Clients et espace client'])

class ClientInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    contact_email: str | None = Field(default=None, max_length=254)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Renseignez le nom de la société')
        return value

    @field_validator('contact_email')
    @classmethod
    def clean_email(cls, value):
        if value and ('@' not in value or any(c.isspace() for c in value.strip())):
            raise ValueError('Adresse email invalide')
        return value.strip().lower() if value else None

class ContactInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if '@' not in value or any(c.isspace() for c in value):
            raise ValueError('Adresse email invalide')
        return value

class ActiveInput(BaseModel):
    active: bool


def client_or_404(db, client_id):
    row = db.get(Client, client_id)
    if row is None:
        raise HTTPException(404, 'Client introuvable')
    return row


def assign_client(db, launch, client_id):
    if client_id:
        client = client_or_404(db, client_id)
        if not client.active and launch.client_id != client.id:
            raise HTTPException(422, 'Ce client est désactivé')
        launch.client_name = client.name
    launch.client_id = client_id or None


def client_out(db, row, detailed=False):
    data = {'id': row.id, 'name': row.name, 'active': row.active}
    if detailed:
        data.update(contact_email=row.contact_email,
            launch_count=db.scalar(select(func.count()).select_from(Launch).where(Launch.client_id == row.id)),
            contacts=[{'id':u.id,'name':u.name,'email':u.email,'active':u.active}
                      for u in db.scalars(select(User).join(ClientContact, ClientContact.user_id == User.id)
                                          .where(ClientContact.client_id == row.id)).all()])
    return data


@router.get('/api/clients')
def clients(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not (permitted(user,'launch.read') or permitted(user,'launch.create')):
        raise HTTPException(403,'Accès interdit')
    from .main import is_admin
    return [client_out(db, row, is_admin(user)) for row in db.scalars(select(Client).order_by(Client.name)).all()]


@router.post('/api/clients', status_code=201)
def create_client(payload: ClientInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    if db.scalar(select(Client.id).where(func.lower(Client.name) == payload.name.lower())):
        raise HTTPException(409, 'Un client porte déjà ce nom')
    row = Client(**payload.model_dump())
    db.add(row)
    db.flush()
    audit(db, user, 'client.create', 'client', row.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Un client porte déjà ce nom')
    return client_out(db, row, True)


@router.patch('/api/clients/{client_id}')
def update_client(client_id: str, payload: ClientInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    row = client_or_404(db, client_id)
    duplicate = db.scalar(select(Client.id).where(func.lower(Client.name) == payload.name.lower(), Client.id != row.id))
    if duplicate:
        raise HTTPException(409, 'Un client porte déjà ce nom')
    row.name, row.contact_email = payload.name, payload.contact_email
    for launch in db.scalars(select(Launch).where(Launch.client_id == row.id)):
        launch.client_name = row.name
    # Stable identity survives a company rename; legacy unbound publications stay internal.
    for publication in db.scalars(select(ClientPublication).where(ClientPublication.client_id == row.id)):
        publication.client_name = row.name
    audit(db, user, 'client.update', 'client', row.id)
    db.commit()
    return client_out(db, row, True)


@router.patch('/api/clients/{client_id}/active')
def set_client_active(client_id: str, payload: ActiveInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    row = client_or_404(db, client_id)
    row.active = payload.active
    audit(db, user, 'client.active', 'client', row.id, {'active':row.active})
    db.commit()
    return client_out(db, row, True)


@router.post('/api/clients/{client_id}/contacts', status_code=201)
def create_contact(client_id: str, payload: ContactInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    client = client_or_404(db, client_id)
    if not client.active:
        raise HTTPException(409, 'Réactiver la société avant de créer un accès')
    row = User(name=payload.name.strip(), email=payload.email, password_hash=hash_password(payload.password))
    db.add(row)
    try:
        db.flush()
        db.add(ClientContact(user_id=row.id, client_id=client_id))
        audit(db, user, 'client.contact.create', 'client', client_id, {'user_id':row.id})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Cette adresse possède déjà un compte')
    return {'id':row.id,'name':row.name,'email':row.email,'active':row.active}


@router.patch('/api/clients/{client_id}/contacts/{user_id}/active')
def set_contact_active(client_id: str, user_id: str, payload: ActiveInput,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    contact = db.get(ClientContact, user_id)
    if not contact or contact.client_id != client_id:
        raise HTTPException(404, 'Contact introuvable')
    row = db.get(User, user_id)
    row.active = payload.active
    audit(db, user, 'client.contact.active', 'user', row.id, {'active':row.active})
    db.commit()
    return {'id':row.id,'active':row.active}


def portal_client(db, user):
    contact = db.get(ClientContact, user.id)
    row = db.get(Client, contact.client_id) if contact else None
    if not row or not row.active or not user.active:
        raise HTTPException(403, 'Compte client actif requis')
    return row


def portal_launch(db, user, launch_id):
    client = portal_client(db, user)
    launch = db.get(Launch, launch_id)
    if not launch or launch.client_id != client.id:
        raise HTTPException(404, 'Dossier introuvable')
    return launch


def summary(launch):
    # No internal reference, author, permissions or audit metadata is exposed.
    return {'id':launch.id, 'name':launch.name, 'order_ref':launch.order_ref,
            'status':launch.status, 'updated_at':launch.updated_at.isoformat()}


def portal_publications(db, launch):
    from .sharing_routes import pub_out
    return [p for p in db.scalars(select(ClientPublication).where(
        ClientPublication.launch_id == launch.id, ClientPublication.client_id == launch.client_id,
        ClientPublication.status == 'published')).all() if pub_out(db, p, launch)['effective']]


@router.get('/api/portal/home')
def portal_home(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    client = portal_client(db, user)
    rows = db.scalars(select(Launch).where(Launch.client_id == client.id).order_by(Launch.updated_at.desc())).all()
    return {'client':{'id':client.id,'name':client.name}, 'launches':[summary(l) for l in rows]}


@router.get('/api/portal/launches/{launch_id}')
def portal_detail(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    launch = portal_launch(db, user, launch_id)
    documents = []
    for publication in portal_publications(db, launch):
        version = db.get(DocumentVersion, publication.document_version_id)
        documents.append({'id':publication.id, 'title':version.document.title, 'version':version.number,
                          'published_at':publication.created_at.isoformat()})
    return {**summary(launch), 'documents':documents}


@router.get('/api/portal/documents/{publication_id}/download')
def portal_download(publication_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    publication = db.get(ClientPublication, publication_id)
    if not publication:
        raise HTTPException(404, 'Document introuvable')
    launch = portal_launch(db, user, publication.launch_id)
    if publication not in portal_publications(db, launch):
        raise HTTPException(404, 'Document introuvable')
    version = db.get(DocumentVersion, publication.document_version_id)
    path = ensure_local(version.disk_name, STORAGE)
    if not path.is_file():
        raise HTTPException(404, 'Fichier indisponible')
    audit(db, user, 'client.download', 'client_publication', publication.id)
    db.commit()
    return FileResponse(path, filename=version.original_name, media_type=version.content_type)
