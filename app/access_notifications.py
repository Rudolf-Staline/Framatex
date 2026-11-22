"""Destinataires autorisés d'un événement métier (fondation des futures notifications email).

Aucun email n'est envoyé ici. Le service répond à : « qui doit être prévenu de
cet événement, sur cette commande et ces sous-dossiers, et par quels canaux ? »
en combinant affectations, droits nécessaires et préférences du collaborateur.

Contrat pour les événements documentaires (Codex, ``feat/document-intelligence``) :

    from app.access_notifications import recipients
    rows = recipients(db, launch_id=..., folders=["jaune"], event_type="document.new_version",
                      exclude_user_id=auteur.id)
    # rows = [{"user_id", "name", "email", "folders", "channels": {"internal": bool, "email": bool}}]

Pour une nouvelle version de la fiche d'emploi qui affecte le calcul du besoin,
passer les sous-dossiers source et impactés : seuls les collaborateurs affectés
et habilités sur ces sous-dossiers sont retournés, jamais tous les techniciens.
"""
from __future__ import annotations

from sqlalchemy import select

from .access_control import can, is_admin, launch_accessible, launch_scope

# Type d'événement → (action requise sur le sous-dossier, préférence qui l'autorise)
EVENTS = {
    "document.new_version": ("document.read", "important_changes"),
    "document.new": ("document.read", "important_changes"),
    "document.validation_requested": ("document.review", "validation_requests"),
    "impact.alert": ("impact.review", "important_changes"),
    "coherence.alert": ("controls.read", "important_changes"),
    "reminder": ("document.read", "reminders"),
    "assignment.changed": ("document.read", "new_assignments"),
}


def recipients(db, *, launch_id: str, folders: list[str], event_type: str,
               exclude_user_id: str | None = None, include_admins: bool = False) -> list[dict]:
    from .access_admin_routes import prefs_of
    from .access_models import CollaboratorProfile
    from .models import Launch, User
    if event_type not in EVENTS:
        raise ValueError(f"Événement inconnu : {event_type}")
    action, pref = EVENTS[event_type]
    launch = db.get(Launch, launch_id)
    out = []
    for user in db.scalars(select(User).where(User.active.is_(True)).order_by(User.name)).all():
        if user.id == exclude_user_id or (is_admin(user) and not include_admins):
            continue
        if not launch_accessible(db, user, launch):
            continue
        with launch_scope(launch_id):
            allowed = [f for f in folders if can(user, action, f)]
        if not allowed:
            continue
        prefs = prefs_of(db.get(CollaboratorProfile, user.id))
        if not prefs.get(pref, True):
            continue
        out.append({"user_id": user.id, "name": user.name, "email": user.email, "folders": allowed,
                    "channels": {"internal": prefs.get("internal", True),
                                 # Préférence enregistrée ; aucun envoi tant que la messagerie n'est pas intégrée.
                                 "email": prefs.get("email_future", False)}})
    return out
