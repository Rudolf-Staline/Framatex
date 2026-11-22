"""Notifications internes : pas d'email, SMS, webhook ni destinataire hors des habilitations.

Sécurité à deux niveaux : filtrage à la génération *et* lors de chaque lecture,
ce qui empêche une notification ancienne d'exposer un dossier après retrait d'un droit.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import User
from .approval_models import InternalNotification


PREFERENCE_BY_KIND = {
    'approval': 'validation_requests',
    'approval_result': 'important_changes',
    'impact': 'important_changes',
    'quality_recheck': 'important_changes',
    'reminder': 'reminders',
}


def notification_allowed(db: Session, user: User, kind: str) -> bool:
    """Respecte les préférences au moment de créer la notification interne."""
    from .access_admin_routes import prefs_of
    from .access_models import CollaboratorProfile
    prefs = prefs_of(db.get(CollaboratorProfile, user.id))
    preference = PREFERENCE_BY_KIND.get(kind)
    return prefs.get('internal', True) and (not preference or prefs.get(preference, True))


def permitted_now(user: User, action: str, folder: str | None = None, launch_id: str | None = None):
    # Import différé pour éviter une dépendance circulaire pendant l'enregistrement des routes.
    from .access_control import can
    return can(user, action, folder, launch_id)


def emit_to_role(db: Session, *, role_id: str, launch_id: str, folder: str,
                 event_key: str, kind: str, title: str, message: str,
                 action: str = 'document.review', exclude_user_id: str | None = None):
    from .access import accessible
    from .models import Launch
    launch = db.get(Launch, launch_id)
    for user in db.scalars(select(User).where(User.active.is_(True))).all():
        if (not accessible(db,user,launch) or user.id == exclude_user_id
                or not notification_allowed(db, user, kind)
                or not any(role.id == role_id for role in user.roles)):
            continue
        if not (permitted_now(user, 'launch.read') and permitted_now(user, 'document.read', folder, launch_id)
                and permitted_now(user, action, folder, launch_id)):
            continue
        db.add(InternalNotification(recipient_id=user.id, event_key=event_key, kind=kind,
                                    launch_id=launch_id, folder_slug=folder,
                                    title=title, message=message))


def emit_to_folder(db: Session, *, launch_id: str, source_folder: str, target_folder: str,
                   event_key: str, kind: str, title: str, message: str,
                   action: str = 'impact.review'):
    from .access import accessible
    from .models import Launch
    launch = db.get(Launch, launch_id)
    for user in db.scalars(select(User).where(User.active.is_(True))).all():
        if not accessible(db,user,launch) or not notification_allowed(db, user, kind) or not (permitted_now(user, 'launch.read') and permitted_now(user, 'document.read', source_folder, launch_id)
                and permitted_now(user, 'document.read', target_folder, launch_id)
                and (kind not in {'impact', 'quality_recheck'}
                     or (permitted_now(user, 'controls.read', source_folder, launch_id)
                         and permitted_now(user, 'controls.read', target_folder, launch_id)))
                and permitted_now(user, action, target_folder, launch_id)):
            continue
        db.add(InternalNotification(recipient_id=user.id, event_key=event_key, kind=kind,
                                    launch_id=launch_id, folder_slug=source_folder,
                                    title=title, message=message))


def emit_to_user(db: Session, *, user_id: str, launch_id: str, folder: str,
                 event_key: str, kind: str, title: str, message: str):
    user = db.get(User, user_id)
    from .access import accessible
    from .models import Launch
    if (not user or not notification_allowed(db, user, kind)
            or not accessible(db,user,db.get(Launch,launch_id))
            or not (permitted_now(user, 'launch.read')
                    and permitted_now(user, 'document.read', folder, launch_id))):
        return
    db.add(InternalNotification(recipient_id=user.id, event_key=event_key, kind=kind,
                                launch_id=launch_id, folder_slug=folder,
                                title=title, message=message))
