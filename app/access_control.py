"""Point de contrôle central des habilitations FRAMATEX.

Question unique : « cet utilisateur peut-il réaliser cette action sur ce
sous-dossier de cette commande ? » → ``can(user, action, folder, launch_id)``.

Règles
- Administrateur (rôle « Administrateur ») : accès complet, inchangé.
- Collaborateur en mode « affectations » (tous les comptes créés ou migrés par
  l'application) : refus par défaut. Une commande n'est visible que si le chef
  y a affecté le collaborateur ; chaque sous-dossier porte sa propre liste
  d'actions. Une affectation ne donne jamais de droit d'administration.
- Mode « hérité » (utilisateur sans profil, bases de test historiques
  uniquement) : comportement par rôles d'avant la migration, conservé pour ne
  pas affaiblir les tests existants. Aucun écran ni aucune API ne crée ce mode.

La commande courante est connue par une variable de contexte : posée pour
chaque requête par le middleware (URL directe ou indirecte : document, version,
notification, alerte…), et explicitement par ``launch_scope`` dans les vues qui
parcourent plusieurs commandes. Sans commande connue, une action de
sous-dossier est refusée à un collaborateur : un oubli ne peut que masquer,
jamais révéler.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import select
from sqlalchemy.orm import object_session

FOLDERS = ("jaune", "rose", "bleu", "vert")
FOLDER_NAMES = {"jaune": "Technique (Jaune)", "rose": "Réception (Rose)", "bleu": "Dédouanement (Bleu)", "vert": "Factures (Vert)"}

# Actions attribuables par sous-dossier, dans l'ordre d'affichage.
ACTION_CATALOG = [
    ("document.read", "Consulter les documents", "Voir la liste, les titres, les versions et l'historique."),
    ("document.download", "Télécharger", "Récupérer le fichier original. Ne protège pas contre la copie d'un contenu consulté."),
    ("document.write", "Déposer de nouveaux fichiers", "Ajouter une nouvelle pièce dans le sous-dossier."),
    ("document.version", "Déposer une nouvelle version", "Remplacer une pièce existante par une version suivante."),
    ("document.comment", "Ajouter des commentaires", "Commenter une version."),
    ("controls.read", "Consulter les contrôles", "Complétude, cohérence, alertes et doublons du sous-dossier."),
    ("impact.review", "Traiter les alertes", "Prendre en compte une alerte d'impact ou un engagement."),
    ("value.write", "Confirmer les informations extraites", "Relever ou confirmer une valeur, une lecture OCR."),
    ("quality.review", "Justifier un écart", "Qualifier un écart de cohérence, une exigence, une ambiguïté."),
    ("document.review", "Valider les documents", "Décision métier de validation (distincte du dépôt)."),
]
ACTION_KEYS = [key for key, _, _ in ACTION_CATALOG]
ACTION_LABELS = {key: label for key, label, _ in ACTION_CATALOG}
# Actions historiques du backend ramenées à l'action attribuable correspondante.
ALIASES = {"completeness.review": "document.review", "requirement.review": "quality.review",
           "ambiguity.review": "quality.review", "commitment.review": "impact.review"}
# Actions globales (hors sous-dossier) : elles relèvent de la fonction, donc du rôle.
GLOBAL_ACTIONS = {"launch.create", "launch.update", "audit.read"}
# Nouvelles actions vérifiées par l'application ; en mode hérité, l'ancien droit fait foi.
LEGACY_FALLBACK = {"document.download": "document.read", "document.version": "document.write",
                   "document.comment": "document.write", "controls.read": "document.read"}
# Modèles proposés au chef : ils préremplissent la matrice, rien n'est appliqué sans confirmation.
PRESETS = {
    "lecture": {"label": "Lecture seule", "actions": ["document.read"]},
    "lecture_telechargement": {"label": "Lecture et téléchargement", "actions": ["document.read", "document.download", "controls.read"]},
    "depot": {"label": "Dépôt sans validation", "actions": ["document.read", "document.download", "document.write",
                                                           "document.version", "document.comment", "controls.read"]},
    "responsable": {"label": "Responsable complet", "actions": list(ACTION_KEYS)},
}

_scope: ContextVar[str | None] = ContextVar("framatex_launch_scope", default=None)
_cache: ContextVar[dict | None] = ContextVar("framatex_access_cache", default=None)


@contextmanager
def launch_scope(launch_id: str | None):
    """Évalue les droits de sous-dossier dans le contexte d'une commande précise."""
    token = _scope.set(launch_id)
    try:
        yield
    finally:
        _scope.reset(token)


@contextmanager
def request_context(launch_id: str | None = None):
    """Une requête HTTP : commande éventuelle et petit cache recalculé à chaque requête."""
    t1, t2 = _scope.set(launch_id), _cache.set({})
    try:
        yield
    finally:
        _scope.reset(t1)
        _cache.reset(t2)


def current_launch() -> str | None:
    return _scope.get()


def invalidate():
    cache = _cache.get()
    if cache is not None:
        cache.clear()


def normalize_actions(actions) -> list[str]:
    """Actions connues uniquement, dans l'ordre du catalogue ; toute action implique la consultation."""
    chosen = {ALIASES.get(a, a) for a in (actions or [])} & set(ACTION_KEYS)
    if chosen:
        chosen.add("document.read")
    return [key for key in ACTION_KEYS if key in chosen]


def is_admin(user) -> bool:
    return any(role.name == "Administrateur" for role in user.roles)


def _cached(key, compute):
    cache = _cache.get()
    if cache is None:
        return compute()
    if key not in cache:
        cache[key] = compute()
    return cache[key]


def profile_of(user, db=None):
    from .access_models import CollaboratorProfile
    session = db or object_session(user)
    if session is None:
        return None
    return _cached(("profile", user.id), lambda: session.get(CollaboratorProfile, user.id))


def access_mode(user, db=None) -> str:
    if is_admin(user):
        return "admin"
    profile = profile_of(user, db)
    return profile.access_scope if profile is not None else "legacy"


def assignments_for(user, launch_id: str, db=None) -> dict[str, set[str]]:
    """{sous-dossier: actions} d'un collaborateur sur une commande (vide si aucune affectation)."""
    from .access_models import LaunchAssignment
    session = db or object_session(user)
    if session is None or not launch_id:
        return {}

    def load():
        rows = session.scalars(select(LaunchAssignment).where(
            LaunchAssignment.user_id == user.id, LaunchAssignment.launch_id == launch_id)).all()
        result = {}
        for row in rows:
            actions = set(json.loads(row.actions or "[]"))
            if actions:
                result[row.folder_slug] = actions
        return result
    return _cached(("assign", user.id, launch_id), load)


def _role_permitted(user, action, folder):
    for role in user.roles:
        for grant in role.grants:
            if grant.action == action and (folder is None and grant.folder_slug is None
                                           or folder is not None and grant.folder_slug in (None, folder)):
                return True
    return False


def can(user, action: str, folder: str | None = None, launch_id: str | None = None) -> bool:
    """Point de contrôle unique : action sur un sous-dossier d'une commande."""
    if user is None or not user.active:
        return False
    if is_admin(user):
        return True
    mode = access_mode(user)
    if mode != "assignments":
        # Mode hérité : rôles d'avant la migration ; les nouvelles actions suivent l'ancien droit.
        return _role_permitted(user, action, folder) or (
            action in LEGACY_FALLBACK and _role_permitted(user, LEGACY_FALLBACK[action], folder))
    if action == "launch.read":
        return True                      # la visibilité de chaque commande est vérifiée par launch_accessible
    if action in GLOBAL_ACTIONS:
        return _role_permitted(user, action, None)
    action = ALIASES.get(action, action)
    if action not in ACTION_KEYS:
        return False
    launch_id = launch_id or _scope.get()
    if not launch_id:
        return False
    grants = assignments_for(user, launch_id)
    if folder is not None:
        return action in grants.get(folder, ())
    return any(action in actions for actions in grants.values())


def launch_accessible(db, user, launch) -> bool:
    """La commande est-elle visible pour ce compte ? (affectation explicite pour un collaborateur)."""
    from .models import LaunchMember
    if launch is None or user is None or not user.active:
        return False
    if is_admin(user):
        return True
    if access_mode(user, db) == "assignments":
        return bool(assignments_for(user, launch.id, db))
    # Mode hérité (0.15) : commande non restreinte, créateur ou membre explicite.
    if not launch.restricted or launch.created_by == user.id:
        return True
    return db.scalar(select(LaunchMember.id).where(
        LaunchMember.launch_id == launch.id, LaunchMember.user_id == user.id)) is not None


def readable_folders(user, launch_id: str) -> list[str]:
    return [slug for slug in FOLDERS if can(user, "document.read", slug, launch_id)]
