"""Comptes de démonstration des habilitations — base ISOLÉE uniquement.

    python scripts/seed_access_demo.py --data-dir /chemin/vers/un/dossier/vide

Le script refuse :
  * le dossier de données par défaut (``data/``) et tout dossier contenant déjà
    une base qu'il n'a pas créée lui-même (marqueur ``.framatex-access-demo``) ;
  * toute variable ``DATABASE_URL`` (base externe) ;
  * toute base contenant déjà un compte hors domaine ``example.test``.

Il crée un chef de démonstration, quatre techniciens fictifs
(``technicien.a|b|c|d@example.test``), cinq commandes fictives et les
affectations couvrant les scénarios demandés. Les mots de passe sont générés
à l'exécution, affichés UNE fois dans le terminal et jamais écrits sur disque ;
chaque compte devra les remplacer à la première connexion.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = '.framatex-access-demo'
DOMAIN = '@example.test'

# Scénarios : technicien → {commande: {sous-dossier: preset}}
SCENARIOS = {
    'a': ('Technicien A', 'Technicien méthodes', {'DEMO-001': {'jaune': 'depot', 'rose': 'depot'},
                                                  'DEMO-003': {'bleu': 'lecture', 'vert': 'lecture'}}),
    'b': ('Technicien B', 'Technicien logistique', {'DEMO-001': {'bleu': 'responsable'},
                                                   'DEMO-002': {s: 'responsable' for s in ('jaune', 'rose', 'bleu', 'vert')}}),
    'c': ('Technicien C', 'Technicien (nouvel arrivant)', {}),
    'd': ('Technicien D', 'Assistant qualité', {'DEMO-003': {'jaune': 'lecture'}}),
}
LAUNCHES = {
    'DEMO-001': 'Une commande, deux techniciens sur des sous-dossiers différents',
    'DEMO-002': 'Un technicien responsable des quatre sous-dossiers',
    'DEMO-003': 'Lecture seule (D) et consultation Bleu + Vert (A)',
    'DEMO-004': 'Commande gérée par le chef seul',
}


def refuse(message):
    print(f'Refusé : {message}', file=sys.stderr)
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data-dir', type=Path, required=True, help='Dossier de données isolé (vide ou déjà créé par ce script)')
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    if os.getenv('DATABASE_URL'):
        refuse('DATABASE_URL est défini ; ce script ne travaille que sur une base SQLite isolée.')
    if data_dir == (ROOT / 'data').resolve() or ROOT / 'data' in data_dir.parents and data_dir.name == 'data':
        refuse('le dossier de données par défaut ne doit jamais recevoir de comptes fictifs.')
    if data_dir.exists() and any(data_dir.iterdir()) and not (data_dir / MARKER).exists():
        refuse(f'{data_dir} n’est pas vide et n’a pas été créé par ce script.')
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / MARKER).write_text('Base de démonstration des habilitations — comptes fictifs uniquement.\n')
    os.environ['FRAMATEX_DATA_DIR'] = str(data_dir)
    sys.path.insert(0, str(ROOT))

    from sqlalchemy import select
    from app.core import SessionLocal, hash_password
    from app.migrate import migrate
    from app.models import Launch, Role, User
    from app.access_models import CollaboratorProfile, LaunchAssignment
    from app.access_control import PRESETS, normalize_actions
    from app.main import audit  # importe aussi tous les modèles
    from app.access_admin_routes import default_role
    from app.standard_profile import apply_standard_profile

    migrate()
    shown = []
    with SessionLocal() as db:
        foreign = [u.email for u in db.scalars(select(User)).all() if not u.email.endswith(DOMAIN)]
        if foreign:
            refuse('la base contient des comptes réels ; aucun compte fictif ne sera ajouté.')
        chef = db.scalar(select(User).where(User.email == f'chef.demo{DOMAIN}'))
        if not chef:
            password = secrets.token_urlsafe(14)
            chef = User(name='Chef (démo)', email=f'chef.demo{DOMAIN}', password_hash=hash_password(password),
                        roles=[Role(name='Administrateur')])
            db.add(chef)
            db.flush()
            db.add(CollaboratorProfile(user_id=chef.id, job_title='Chef d’atelier', must_change_password=True))
            shown.append((chef.email, password))
        launches = {}
        for ref, label in LAUNCHES.items():
            launch = db.scalar(select(Launch).where(Launch.order_ref == ref))
            if not launch:
                launch = Launch(name=label, order_ref=ref, client_name='Client fictif', created_by=chef.id)
                db.add(launch)
                db.flush()
                apply_standard_profile(db, launch, chef, reason='launch_create')
            launches[ref] = launch
        collaborator = default_role(db)
        for key, (name, job, plan) in SCENARIOS.items():
            email = f'technicien.{key}{DOMAIN}'
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                password = secrets.token_urlsafe(14)
                user = User(name=name, email=email, password_hash=hash_password(password), roles=[collaborator])
                db.add(user)
                db.flush()
                db.add(CollaboratorProfile(user_id=user.id, job_title=job, must_change_password=True))
                shown.append((email, password))
            for ref, folders in plan.items():
                for slug, preset in folders.items():
                    exists = db.scalar(select(LaunchAssignment).where(LaunchAssignment.launch_id == launches[ref].id,
                                                                      LaunchAssignment.user_id == user.id,
                                                                      LaunchAssignment.folder_slug == slug))
                    if not exists:
                        db.add(LaunchAssignment(launch_id=launches[ref].id, user_id=user.id, folder_slug=slug,
                                                actions=json.dumps(normalize_actions(PRESETS[preset]['actions'])), granted_by=chef.id))
                        audit(db, chef, 'access.assignment.grant', 'launch', launches[ref].id,
                              {'user_id': user.id, 'folder': slug, 'after': PRESETS[preset]['actions'], 'origin': 'demo'})
        db.commit()
    print(f'Base de démonstration : {data_dir / "framat.db"}')
    print('Scénarios : A (2 commandes, dépôt sans validation sur 001), B (001 Bleu + 002 complète),'
          ' C (aucune commande), D (lecture seule sur 003), DEMO-004 (chef seul).')
    if shown:
        print('\nMots de passe temporaires — affichés une seule fois, à remplacer à la première connexion :')
        for email, password in shown:
            print(f'  {email:32} {password}')
    else:
        print('Comptes déjà présents : mots de passe inchangés (utilisez « Réinitialiser » dans l’interface du chef).')
    print(f'\nLancer : FRAMATEX_DATA_DIR={data_dir} python -m uvicorn app.main:app --port 8000')


if __name__ == '__main__':
    main()
