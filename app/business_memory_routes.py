"""Mémoire métier interne, limitée aux dossiers visibles et aux droits du Dossier Jaune."""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access import must_access
from .core import get_current_user, get_db, utcnow
from .internal_models import BusinessPartner, PartnerAlias, LaunchPartner, ExperienceNote, ExperienceDecision
from .internal_service import visible_launches
from .models import DocumentVersion, Launch, User

router = APIRouter(tags=["Mémoire métier interne"])


def norm(value: str) -> str:
    clean = unicodedata.normalize('NFKD', value.casefold())
    clean = ''.join(char for char in clean if not unicodedata.combining(char))
    return ' '.join(re.findall(r'[\w]+', clean, flags=re.UNICODE))


def rights(user: User, write=False):
    from .main import must
    from .access_control import access_mode
    must(user, 'launch.read')
    if access_mode(user) == 'assignments':
        # Collaborateur affecté : mémoire ouverte s'il consulte (ou alimente) le sous-dossier
        # Technique d'au moins une commande qui lui est attribuée. Les notes générales (sans
        # commande) sont alors consultables ; une note liée à une commande ne l'est que si
        # Technique y est consultable (visible_ids).
        from sqlalchemy.orm import object_session
        action = 'document.write' if write else 'document.read'
        if not technique_launches(object_session(user), user, action):
            from fastapi import HTTPException
            raise HTTPException(403, "Accès interdit : habilitation insuffisante")
        return
    must(user, 'document.read', 'jaune')
    if write:
        must(user, 'document.write', 'jaune')


def technique_launches(db, user, action='document.read'):
    from .access_control import can
    return {launch.id for launch in visible_launches(db, user) if can(user, action, 'jaune', launch.id)}


def visible_ids(db, user):
    return technique_launches(db, user)


def partner_out(row):
    return {'id': row.id, 'party_type': row.party_type, 'name': row.name,
            'business_reference': row.business_reference, 'client_account_id': row.client_account_id,
            'created_at': row.created_at.isoformat(), 'last_activity': row.last_activity.isoformat()}


def scoped_partner(db, user, row, allowed=None):
    allowed = visible_ids(db, user) if allowed is None else allowed
    notes = db.scalars(select(ExperienceNote).where(ExperienceNote.partner_id == row.id)).all()
    links = db.scalars(select(LaunchPartner).where(LaunchPartner.partner_id == row.id)).all()
    associated = bool(notes or links)
    visible_notes = [note for note in notes if note.launch_id is None or note.launch_id in allowed]
    visible_links = [link for link in links if link.launch_id in allowed]
    if associated and not visible_notes and not visible_links:
        return None
    result = partner_out(row)
    result['last_activity'] = max([row.created_at.isoformat()]
                                  + [note.created_at.isoformat() for note in visible_notes]
                                  + [link.created_at.isoformat() for link in visible_links])
    return result


def note_out(db, row):
    author = db.get(User, row.author_id)
    launch = db.get(Launch, row.launch_id) if row.launch_id else None
    return {'id': row.id, 'partner_id': row.partner_id, 'launch_id': row.launch_id,
            'party_type': row.party_type, 'party_name': row.party_name, 'category': row.category,
            'body': row.body, 'author': author.name if author else 'Utilisateur',
            'created_at': row.created_at.isoformat(), 'event_date': row.event_date.isoformat() if row.event_date else None,
            'importance': row.importance, 'status': row.status, 'recommendation': row.recommendation,
            'evidence_version_id': row.evidence_version_id,
            'order_ref': (launch.order_ref or launch.name) if launch else None,
            'updated_at': row.updated_at.isoformat() if row.updated_at else row.created_at.isoformat()}


def scoped_notes(db, user, partner_id=None):
    allowed = visible_ids(db, user)
    rows = db.scalars(select(ExperienceNote).order_by(ExperienceNote.created_at.desc())).all()
    return [r for r in rows if (r.launch_id is None or r.launch_id in allowed)
            and (partner_id is None or r.partner_id == partner_id)]


def note_counts(notes):
    categories = ['incident', 'retard', 'qualite', 'documentaire', 'retour']
    return {**{key: sum(r.category == key for r in notes) for key in categories},
            'open_vigilance': sum(r.status == 'open' and r.category != 'retour' and r.importance in ('important', 'critique') for r in notes)}


class PartnerInput(BaseModel):
    party_type: Literal['client', 'fournisseur', 'atelier']
    name: str = Field(min_length=2, max_length=180)
    business_reference: str | None = Field(default=None, max_length=100)
    client_account_id: str | None = None


class NoteInput(BaseModel):
    partner_id: str
    launch_id: str | None = None
    category: Literal['incident', 'retard', 'qualite', 'documentaire', 'modification', 'communication', 'retour', 'recommandation', 'autre']
    event_date: date
    body: str = Field(min_length=12, max_length=2000)
    importance: Literal['information', 'surveiller', 'important', 'critique'] = 'information'
    recommendation: str | None = Field(default=None, max_length=2000)
    evidence_version_id: str | None = None
    status: Literal['open', 'resolved'] = 'open'


class NoteChange(BaseModel):
    body: str | None = Field(default=None, min_length=12, max_length=2000)
    category: Literal['incident', 'retard', 'qualite', 'documentaire', 'modification', 'communication', 'retour', 'recommandation', 'autre'] | None = None
    event_date: date | None = None
    recommendation: str | None = Field(default=None, max_length=2000)
    importance: Literal['information', 'surveiller', 'important', 'critique'] | None = None
    status: Literal['open', 'resolved'] | None = None
    reason: str = Field(min_length=12, max_length=1000)


class LinkInput(BaseModel):
    partner_id: str


class ClientLinkInput(BaseModel):
    client_account_id: str


@router.get('/api/workspace/partners')
def partners(q: str = '', party_type: str = '', user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    needle = norm(q)
    rows = db.scalars(select(BusinessPartner).order_by(BusinessPartner.name)).all()
    result = []
    allowed = visible_ids(db, user)
    for row in rows:
        scoped = scoped_partner(db, user, row, allowed)
        if scoped is None:
            continue
        if party_type and row.party_type != party_type:
            continue
        names = [row.normalized_name] + [a.normalized_name for a in db.scalars(select(PartnerAlias).where(PartnerAlias.partner_id == row.id))]
        exact = needle and needle in names
        partial = needle and any(needle in name or name in needle for name in names)
        similar = needle and any(SequenceMatcher(None, needle, name).ratio() >= .78 for name in names)
        if needle and not (exact or partial or similar):
            continue
        result.append({**scoped, 'match': 'exact' if exact else 'possible' if similar and not partial else 'partial' if partial else None})
    return result[:30 if needle else 200]


@router.post('/api/workspace/partners', status_code=201)
def create_partner(payload: PartnerInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, True)
    name = payload.name.strip()
    normalized = norm(name)
    if len(normalized) < 2:
        raise HTTPException(422, 'Nom requis')
    same = db.scalars(select(BusinessPartner).where(BusinessPartner.party_type == payload.party_type,
                                                       BusinessPartner.normalized_name == normalized)).all()
    if same:
        raise HTTPException(409, 'Partenaire déjà référencé : sélectionner sa fiche existante')
    if payload.client_account_id:
        from .client_models import ClientAccount
        from .main import admin_only
        admin_only(user)
        client = db.get(ClientAccount, payload.client_account_id)
        if payload.party_type != 'client' or not client:
            raise HTTPException(422, 'Compte Client invalide')
        if db.scalar(select(BusinessPartner.id).where(BusinessPartner.client_account_id == client.id)):
            raise HTTPException(409, 'Ce compte Client possède déjà une fiche partenaire')
    row = BusinessPartner(party_type=payload.party_type, name=name, normalized_name=normalized,
                          business_reference=payload.business_reference, client_account_id=payload.client_account_id)
    db.add(row)
    db.flush()
    # Only exact normalized historical names are linked. Similar names remain for human review.
    for note in db.scalars(select(ExperienceNote).where(ExperienceNote.partner_id.is_(None),
                       ExperienceNote.party_type == row.party_type)):
        if norm(note.party_name) == normalized:
            note.partner_id = row.id
    from .main import audit
    audit(db, user, 'business.partner.create', 'business_partner', row.id, {'party_type': row.party_type})
    db.commit()
    return partner_out(row)


@router.get('/api/workspace/partners/{partner_id}')
def partner_detail(partner_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    row = db.get(BusinessPartner, partner_id)
    scoped = scoped_partner(db, user, row) if row else None
    if scoped is None:
        raise HTTPException(404, 'Partenaire introuvable')
    notes = scoped_notes(db, user, row.id)
    allowed = visible_ids(db, user)
    linked = db.scalars(select(LaunchPartner).where(LaunchPartner.partner_id == row.id)).all()
    launch_ids = {r.launch_id for r in linked if r.launch_id in allowed} | {r.launch_id for r in notes if r.launch_id}
    launches = [db.get(Launch, lid) for lid in launch_ids]
    return {**scoped, 'aliases': [a.name for a in db.scalars(select(PartnerAlias).where(PartnerAlias.partner_id == row.id))],
            'order_count': len(launch_ids), 'orders': [{'id': l.id, 'name': l.name, 'order_ref': l.order_ref} for l in launches if l],
            'counts': note_counts(notes), 'notes': [note_out(db, r) for r in notes]}


@router.post('/api/workspace/partners/{partner_id}/client-account')
def link_client_account(partner_id: str, payload: ClientLinkInput,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import admin_only, audit
    admin_only(user)
    partner = db.get(BusinessPartner, partner_id)
    from .client_models import ClientAccount
    client = db.get(ClientAccount, payload.client_account_id)
    if not partner or partner.party_type != 'client' or not client:
        raise HTTPException(404, 'Fiche ou compte Client introuvable')
    if partner.client_account_id not in (None, client.id):
        raise HTTPException(409, 'Cette fiche est déjà liée à un autre compte')
    existing = db.scalar(select(BusinessPartner).where(BusinessPartner.client_account_id == client.id))
    if existing and existing.id != partner.id:
        raise HTTPException(409, 'Ce compte Client possède déjà une fiche partenaire')
    partner.client_account_id = client.id
    audit(db, user, 'business.partner.client_link', 'business_partner', partner.id,
          {'client_account_id': client.id})
    db.commit()
    return partner_out(partner)


@router.post('/api/launches/{launch_id}/partners', status_code=201)
def link_partner(launch_id: str, payload: LinkInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, True)
    must_access(db, user, launch_id)
    row = db.get(BusinessPartner, payload.partner_id)
    if not row or scoped_partner(db, user, row) is None:
        raise HTTPException(404, 'Partenaire introuvable')
    existing = db.scalar(select(LaunchPartner).where(LaunchPartner.launch_id == launch_id, LaunchPartner.partner_id == row.id))
    if existing:
        return partner_out(row)
    db.add(LaunchPartner(launch_id=launch_id, partner_id=row.id))
    row.last_activity = utcnow()
    from .main import audit
    audit(db, user, 'business.partner.link', 'launch', launch_id, {'partner_id': row.id})
    db.commit()
    return partner_out(row)


@router.get('/api/launches/{launch_id}/partners')
def launch_partners(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    must_access(db, user, launch_id)
    links = db.scalars(select(LaunchPartner).where(LaunchPartner.launch_id == launch_id)).all()
    return [partner_out(db.get(BusinessPartner, link.partner_id)) for link in links]


@router.get('/api/workspace/partners/{partner_id}/vigilance')
def vigilance(partner_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    row = db.get(BusinessPartner, partner_id)
    scoped = scoped_partner(db, user, row) if row else None
    if scoped is None:
        raise HTTPException(404, 'Partenaire introuvable')
    notes = scoped_notes(db, user, partner_id)
    return {'partner': scoped, 'counts': note_counts(notes),
            'items': [note_out(db, n) for n in notes if n.category != 'retour' and n.importance in ('surveiller', 'important', 'critique')][:10]}


@router.get('/api/workspace/business-memory')
def memory(q: str = '', party_type: str = '', category: str = '', importance: str = '', status: str = '',
           date_from: date | None = None, date_to: date | None = None, sort: str = 'date',
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    rows = scoped_notes(db, user)
    all_rows = rows
    needle = norm(q)
    rows = [r for r in rows if (not party_type or r.party_type == party_type)
            and (not category or r.category == category) and (not importance or r.importance == importance)
            and (not status or r.status == status)
            and (not date_from or (r.event_date or r.created_at.date()) >= date_from)
            and (not date_to or (r.event_date or r.created_at.date()) <= date_to)
            and (not needle or needle in norm(r.party_name + ' ' + r.body))]
    if sort == 'importance':
        rank = {'critique': 0, 'important': 1, 'surveiller': 2, 'information': 3}
        rows.sort(key=lambda r: (rank.get(r.importance, 3), -(r.created_at.timestamp())))
    else:
        rows.sort(key=lambda r: r.created_at, reverse=True)
    allowed = visible_ids(db, user)
    partner_count = sum(scoped_partner(db, user, row, allowed) is not None
                        for row in db.scalars(select(BusinessPartner)))
    return {'stats': {'partners': partner_count,
                      'returns': len(all_rows), **note_counts(all_rows)},
            'items': [note_out(db, r) for r in rows[:200]]}


@router.post('/api/workspace/business-memory', status_code=201)
def create_note(payload: NoteInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, True)
    partner = db.get(BusinessPartner, payload.partner_id)
    if not partner or scoped_partner(db, user, partner) is None:
        raise HTTPException(404, 'Partenaire introuvable')
    if payload.launch_id:
        must_access(db, user, payload.launch_id)
    if payload.evidence_version_id:
        version = db.get(DocumentVersion, payload.evidence_version_id)
        if not version or not payload.launch_id or version.document.folder.launch_id != payload.launch_id:
            raise HTTPException(422, 'Justificatif hors de la commande associée')
        from .main import must
        must(user, 'document.read', version.document.folder.slug)
    row = ExperienceNote(partner_id=partner.id, party_type=partner.party_type, party_name=partner.name,
                         author_id=user.id, **payload.model_dump(exclude={'partner_id'}))
    db.add(row)
    partner.last_activity = utcnow()
    from .main import audit
    db.flush()
    audit(db, user, 'experience.note.create', 'experience_note', row.id, {'partner_id': partner.id, 'launch_id': row.launch_id})
    db.commit()
    return note_out(db, row)


@router.patch('/api/workspace/business-memory/{note_id}')
def change_note(note_id: str, payload: NoteChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, True)
    row = db.get(ExperienceNote, note_id)
    if not row or (row.launch_id and row.launch_id not in visible_ids(db, user)):
        raise HTTPException(404, 'Retour introuvable')
    values = payload.model_dump(exclude_unset=True, exclude={'reason'})
    if not values:
        raise HTTPException(422, 'Aucune modification')
    previous = {key: getattr(row, key) for key in values}
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = utcnow()
    action = 'close' if values.get('status') == 'resolved' else 'update'
    db.add(ExperienceDecision(note_id=row.id, actor_id=user.id, action=action, reason=payload.reason.strip()))
    from .main import audit
    audit(db, user, f'experience.note.{action}', 'experience_note', row.id,
          {'fields': list(values), 'previous_status': previous.get('status'), 'reason': payload.reason.strip()})
    db.commit()
    return note_out(db, row)


@router.get('/api/workspace/business-memory/{note_id}')
def get_note(note_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    row = db.get(ExperienceNote, note_id)
    if not row or (row.launch_id and row.launch_id not in visible_ids(db, user)):
        raise HTTPException(404, 'Retour introuvable')
    return note_out(db, row)


@router.get('/api/workspace/business-memory/{note_id}/decisions')
def decisions(note_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user)
    row = db.get(ExperienceNote, note_id)
    if not row or (row.launch_id and row.launch_id not in visible_ids(db, user)):
        raise HTTPException(404, 'Retour introuvable')
    return [{'action': d.action, 'reason': d.reason, 'actor': db.get(User, d.actor_id).name,
             'created_at': d.created_at.isoformat()} for d in db.scalars(select(ExperienceDecision).where(
                 ExperienceDecision.note_id == note_id).order_by(ExperienceDecision.created_at.desc()))]
