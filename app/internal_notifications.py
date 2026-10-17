"""Notifications internes : pas d'email, SMS, webhook ni destinataire hors des habilitations.

Sécurité à deux niveaux : filtrage à la génération *et* lors de chaque lecture,
ce qui empêche une notification ancienne d'exposer un dossier après retrait d'un droit.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import User
from .approval_models import InternalNotification


def permitted_now(user: User, action: str, folder: str | None = None):
    # Import différé pour éviter une dépendance circulaire pendant l'enregistrement des routes.
    from .main import permitted
    return permitted(user, action, folder)


def emit_to_role(db: Session, *, role_id: str, launch_id: str, folder: str,
                 event_key: str, kind: str, title: str, message: str,
                 action: str = 'document.review', exclude_user_id: str | None = None):
    for user in db.scalars(select(User).where(User.active.is_(True))).all():
        if user.id == exclude_user_id or not any(role.id == role_id for role in user.roles):
            continue
        if not (permitted_now(user, 'launch.read') and permitted_now(user, 'document.read', folder)
                and permitted_now(user, action, folder)):
            continue
        db.add(InternalNotification(recipient_id=user.id, event_key=event_key, kind=kind,
                                    launch_id=launch_id, folder_slug=folder,
                                    title=title, message=message))


def emit_to_folder(db: Session, *, launch_id: str, source_folder: str, target_folder: str,
                   event_key: str, kind: str, title: str, message: str,
                   action: str = 'impact.review'):
    for user in db.scalars(select(User).where(User.active.is_(True))).all():
        if not (permitted_now(user, 'launch.read') and permitted_now(user, 'document.read', source_folder)
                and permitted_now(user, 'document.read', target_folder)
                and permitted_now(user, action, target_folder)):
            continue
        db.add(InternalNotification(recipient_id=user.id, event_key=event_key, kind=kind,
                                    launch_id=launch_id, folder_slug=source_folder,
                                    title=title, message=message))


def emit_to_user(db: Session, *, user_id: str, launch_id: str, folder: str,
                 event_key: str, kind: str, title: str, message: str):
    user = db.get(User, user_id)
    if not user or not user.active or not (permitted_now(user, 'launch.read') and permitted_now(user, 'document.read', folder)):
        return
    db.add(InternalNotification(recipient_id=user.id, event_key=event_key, kind=kind,
                                launch_id=launch_id, folder_slug=folder,
                                title=title, message=message))
