"""Migration 0013_access_management : passage sûr au modèle par affectations.

- Crée les tables additives (profils, affectations, propositions héritées).
- Chaque compte existant reçoit un profil en mode « affectations » : refus par
  défaut, aucune commande n'est ouverte automatiquement, le mot de passe n'est
  pas modifié (le compte chef ``admin.test@framatex.com`` est conservé tel quel).
- Les accès d'avant (rôles par sous-dossier sur les commandes non restreintes,
  appartenance explicite, création) sont enregistrés comme **propositions** que
  le chef confirme ou écarte : rien n'est perdu silencieusement, rien n'est
  ouvert involontairement.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from .access_control import ALIASES, FOLDERS, normalize_actions

TABLES = ("collaborator_profiles", "launch_assignments", "legacy_access_proposals")


def migrate_0013(conn, metadata):
    for name in TABLES:
        metadata.tables[name].create(bind=conn, checkfirst=True)
    now = datetime.now(timezone.utc).isoformat()
    users = conn.execute(text("SELECT id FROM users")).scalars().all()
    admins = set(conn.execute(text(
        "SELECT ur.user_id FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE r.name = 'Administrateur'")).scalars())
    existing = set(conn.execute(text("SELECT user_id FROM collaborator_profiles")).scalars())
    launches = conn.execute(text("SELECT id, restricted, created_by FROM launches")).all()
    members = set(conn.execute(text("SELECT launch_id, user_id FROM launch_members")).all())
    for user_id in users:
        if user_id not in existing:
            conn.execute(text("INSERT INTO collaborator_profiles (user_id, job_title, access_scope, must_change_password, "
                              "notification_prefs, updated_at) VALUES (:u, '', 'assignments', 0, '{}', :d)"),
                         {"u": user_id, "d": now})
        if user_id in admins:
            continue
        grants = conn.execute(text(
            "SELECT rp.action, rp.folder_slug FROM role_permissions rp JOIN user_roles ur ON ur.role_id = rp.role_id "
            "WHERE ur.user_id = :u"), {"u": user_id}).all()
        folders = {}
        for slug in FOLDERS:
            actions = normalize_actions([ALIASES.get(a, a) for a, f in grants if f in (None, slug)])
            if "document.read" in {a for a, f in grants if f in (None, slug)}:
                # Les nouvelles actions suivent l'ancien droit : lecture → téléchargement, dépôt → version.
                actions = normalize_actions(actions + ["document.download", "controls.read"]
                                            + (["document.version", "document.comment"] if "document.write" in actions else []))
                folders[slug] = actions
        for launch_id, restricted, created_by in launches:
            origin = ("creator" if created_by == user_id else "member" if (launch_id, user_id) in members
                      else "role" if not restricted else None)
            if origin is None or not (folders or origin != "role"):
                continue
            conn.execute(text("INSERT OR IGNORE INTO legacy_access_proposals (id, launch_id, user_id, origin, folders, status, created_at) "
                              "VALUES (:i, :l, :u, :o, :f, 'pending', :d)"),
                         {"i": str(uuid.uuid4()), "l": launch_id, "u": user_id, "o": origin, "f": json.dumps(folders), "d": now})
