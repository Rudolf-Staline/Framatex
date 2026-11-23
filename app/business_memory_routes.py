"""Mémoire métier interne, strictement limitée au sous-dossier autorisé."""
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


FOLDER_SLUGS = ('jaune', 'rose', 'bleu', 'vert')


def is_chief(user: User) -> bool:
    from .access_control import is_admin
    return is_admin(user)


def readable_folders(user: User, launch_id: str) -> list[str]:
    """Permissions effectives, jamais une union entre deux commandes."""
    if is_chief(user):
        return list(FOLDER_SLUGS)
    from .access_control import can
    return [slug for slug in FOLDER_SLUGS if can(user, 'document.read', slug, launch_id)]


def memory_launches(db: Session, user: User) -> list[Launch]:
    launches = db.scalars(select(Launch).order_by(Launch.updated_at.desc())).all() if is_chief(user) else visible_launches(db, user)
    return [launch for launch in launches if readable_folders(user, launch.id)]


def rights(user: User, db: Session):
    from .main import must
    must(user, 'launch.read')
    if is_chief(user):
        return
    # Lecture sur n'importe quel sous-dossier suffit pour contribuer à la
    # mémoire de ce sous-dossier. Le dépôt documentaire reste indépendant.
    if not memory_launches(db, user):
        raise HTTPException(403, "Accès interdit : aucune commande ou rubrique consultable")


def visible_ids(db, user):
    return {launch.id for launch in memory_launches(db, user)}


def note_visible(user: User, row: ExperienceNote) -> bool:
    if is_chief(user):
        return True
    # NULL signifie note générale ou historique « à classer » : chef seulement.
    return bool(row.launch_id and row.folder_slug and row.folder_slug in FOLDER_SLUGS
                and row.folder_slug in readable_folders(user, row.launch_id))


def partner_out(row):
    return {'id': row.id, 'party_type': row.party_type, 'name': row.name,
            'business_reference': row.business_reference, 'client_account_id': row.client_account_id,
            'created_at': row.created_at.isoformat(), 'last_activity': row.last_activity.isoformat()}


def scoped_partner(db, user, row, allowed=None):
    notes = db.scalars(select(ExperienceNote).where(ExperienceNote.partner_id == row.id)).all()
    links = db.scalars(select(LaunchPartner).where(LaunchPartner.partner_id == row.id)).all()
    if is_chief(user):
        visible_notes, visible_links = notes, links
    else:
        allowed = visible_ids(db, user) if allowed is None else allowed
        visible_notes = [note for note in notes if note_visible(user, note)]
        # A launch association alone has no folder classification and must not
        # reveal a partner attached only to a confidential workflow.
        visible_links = [link for link in links if link.launch_id in allowed and visible_notes]
    associated = bool(notes or links)
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
    return {'id': row.id, 'partner_id': row.partner_id, 'launch_id': row.launch_id, 'folder_slug': row.folder_slug,
            'party_type': row.party_type, 'party_name': row.party_name, 'category': row.category,
            'body': row.body, 'author': author.name if author else 'Utilisateur',
            'created_at': row.created_at.isoformat(), 'event_date': row.event_date.isoformat() if row.event_date else None,
            'importance': row.importance, 'status': row.status, 'recommendation': row.recommendation,
            'evidence_version_id': row.evidence_version_id,
            'order_ref': (launch.order_ref or launch.name) if launch else None,
            'updated_at': row.updated_at.isoformat() if row.updated_at else row.created_at.isoformat()}


def scoped_notes(db, user, partner_id=None):
    rows = db.scalars(select(ExperienceNote).order_by(ExperienceNote.created_at.desc())).all()
    return [r for r in rows if note_visible(user, r) and (partner_id is None or r.partner_id == partner_id)]


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
    folder_slug: Literal['jaune', 'rose', 'bleu', 'vert'] | None = None
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
def partners(q: str = '', party_type: str = '', launch_id: str = '', folder_slug: str = '',
             user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, db)
    if launch_id:
        must_access(db, user, launch_id)
        if folder_slug not in readable_folders(user, launch_id):
            raise HTTPException(403, 'Accès interdit à ce sous-dossier')
    needle = norm(q)
    rows = db.scalars(select(BusinessPartner).order_by(BusinessPartner.name)).all()
    result = []
    allowed = visible_ids(db, user)
    for row in rows:
        scoped = scoped_partner(db, user, row, allowed)
        if scoped is None:
            # Dans le formulaire d'un sous-dossier autorisé, un partenaire
            # déjà lié à la même commande peut être sélectionné, sans exposer
            # ses retours ni ceux d'autres rubriques.
            linked_here = launch_id and db.scalar(select(LaunchPartner.id).where(
                LaunchPartner.launch_id == launch_id, LaunchPartner.partner_id == row.id))
            if not linked_here:
                continue
            scoped = partner_out(row)
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
    rights(user, db)
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
    rights(user, db)
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
    rights(user, db)
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
    rights(user, db)
    must_access(db, user, launch_id)
    links = db.scalars(select(LaunchPartner).where(LaunchPartner.launch_id == launch_id)).all()
    return [scoped for link in links if (scoped := scoped_partner(db, user, db.get(BusinessPartner, link.partner_id))) is not None]


@router.get('/api/workspace/partners/{partner_id}/vigilance')
def vigilance(partner_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, db)
    row = db.get(BusinessPartner, partner_id)
    scoped = scoped_partner(db, user, row) if row else None
    if scoped is None:
        raise HTTPException(404, 'Partenaire introuvable')
    notes = scoped_notes(db, user, partner_id)
    return {'partner': scoped, 'counts': note_counts(notes),
            'items': [note_out(db, n) for n in notes if n.category != 'retour' and n.importance in ('surveiller', 'important', 'critique')][:10]}


@router.get('/api/workspace/business-memory/options')
def memory_options(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, db)
    launches = memory_launches(db, user)
    return {'can_create': bool(launches), 'can_general': is_chief(user),
            'launches': [{'id': launch.id, 'name': launch.name, 'order_ref': launch.order_ref,
                          'folders': readable_folders(user, launch.id)} for launch in launches]}


@router.get('/api/workspace/business-memory')
def memory(q: str = '', party_type: str = '', category: str = '', importance: str = '', status: str = '',
           launch_id: str = '', folder_slug: str = '',
           date_from: date | None = None, date_to: date | None = None, sort: str = 'date',
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, db)
    rows = scoped_notes(db, user)
    all_rows = rows
    needle = norm(q)
    rows = [r for r in rows if (not party_type or r.party_type == party_type)
            and (not category or r.category == category) and (not importance or r.importance == importance)
            and (not status or r.status == status)
            and (not launch_id or r.launch_id == launch_id) and (not folder_slug or r.folder_slug == folder_slug)
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
    rights(user, db)
    if not is_chief(user) and (not payload.launch_id or not payload.folder_slug):
        raise HTTPException(422, 'Commande et sous-dossier obligatoires pour un collaborateur')
    if not is_chief(user) and bool(payload.launch_id) != bool(payload.folder_slug):
        raise HTTPException(422, 'Commande et sous-dossier doivent être renseignés ensemble')
    if payload.launch_id:
        must_access(db, user, payload.launch_id)
        if payload.folder_slug and payload.folder_slug not in readable_folders(user, payload.launch_id):
            raise HTTPException(403, 'Accès interdit à ce sous-dossier')
    partner = db.get(BusinessPartner, payload.partner_id)
    linked_to_target = bool(payload.launch_id and db.scalar(select(LaunchPartner.id).where(
        LaunchPartner.launch_id == payload.launch_id, LaunchPartner.partner_id == payload.partner_id)))
    if not partner or (scoped_partner(db, user, partner) is None and not linked_to_target):
        raise HTTPException(404, 'Partenaire introuvable')
    if payload.evidence_version_id:
        version = db.get(DocumentVersion, payload.evidence_version_id)
        if not version or not payload.launch_id or version.document.folder.launch_id != payload.launch_id:
            raise HTTPException(422, 'Justificatif hors de la commande associée')
        if version.document.folder.slug != payload.folder_slug or version.document.folder.launch_id != payload.launch_id:
            raise HTTPException(422, 'Justificatif hors du sous-dossier associé')
        if version.document.folder.slug not in readable_folders(user, payload.launch_id):
            raise HTTPException(403, 'Justificatif inaccessible')
    row = ExperienceNote(partner_id=partner.id, party_type=partner.party_type, party_name=partner.name,
                         author_id=user.id, **payload.model_dump(exclude={'partner_id'}))
    db.add(row)
    if payload.launch_id and not linked_to_target:
        db.add(LaunchPartner(launch_id=payload.launch_id, partner_id=partner.id))
    partner.last_activity = utcnow()
    from .main import audit
    db.flush()
    audit(db, user, 'experience.note.create', 'experience_note', row.id,
          {'partner_id': partner.id, 'launch_id': row.launch_id, 'folder_slug': row.folder_slug})
    db.commit()
    return note_out(db, row)


@router.patch('/api/workspace/business-memory/{note_id}')
def change_note(note_id: str, payload: NoteChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, db)
    row = db.get(ExperienceNote, note_id)
    if not row or not note_visible(user, row):
        raise HTTPException(404, 'Retour introuvable')
    if not is_chief(user) and row.author_id != user.id:
        raise HTTPException(403, 'Seul l’auteur peut corriger son retour')
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
    rights(user, db)
    row = db.get(ExperienceNote, note_id)
    if not row or not note_visible(user, row):
        raise HTTPException(404, 'Retour introuvable')
    return note_out(db, row)


@router.get('/api/workspace/business-memory/{note_id}/decisions')
def decisions(note_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rights(user, db)
    row = db.get(ExperienceNote, note_id)
    if not row or not note_visible(user, row):
        raise HTTPException(404, 'Retour introuvable')
    return [{'action': d.action, 'reason': d.reason, 'actor': db.get(User, d.actor_id).name,
             'created_at': d.created_at.isoformat()} for d in db.scalars(select(ExperienceDecision).where(
                 ExperienceDecision.note_id == note_id).order_by(ExperienceDecision.created_at.desc()))]
