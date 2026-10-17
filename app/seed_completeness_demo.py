"""Ajoute uniquement un profil et des règles FICTIVES aux lancements démo.

Utilisation après bootstrap_admin + seed_demo : python -m app.seed_completeness_demo
Ne modifie pas les lancements de Framatex et n'utilise pas de règles métier non validées.
"""
from sqlalchemy import select
from .core import Base, SessionLocal, engine
from .models import User, Launch
from .completeness_models import CompletenessProfile, RequirementRule, LaunchCompleteness
from .seed_demo import ROWS

RULES = [
    ('Fiche d’emploi', 'jaune', 'Fiche d’emploi', 'preparation', True,
     'Simulation : vérifier la dernière version de la fiche d’emploi.'),
    ('Dossier technique client', 'jaune', 'Dossier technique client', 'preparation', False,
     'Simulation : vérifier le dépôt d’une spécification client.'),
    ('Bon de livraison', 'rose', 'Bon de livraison', 'approvisionnement', False,
     'Simulation : bon attendu seulement au stade approvisionnement.'),
    ('Pièce douanière', 'bleu', 'Pièce douanière', 'expedition', False,
     'Simulation : pièce non exigible avant expédition.'),
    ('Facture', 'vert', 'Facture', 'cloture', False,
     'Simulation : facture attendue à la clôture du lancement.'),
]


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        admin = db.scalar(select(User).join(User.roles).where(User.email.is_not(None)))
        if not admin:
            raise SystemExit('Créer un administrateur avant de lancer cette démonstration.')
        name = 'DÉMONSTRATION — règles fictives (non validées)'
        profile = db.scalar(select(CompletenessProfile).where(CompletenessProfile.name == name))
        if not profile:
            profile = CompletenessProfile(name=name, description='Profil fictif de validation des parcours UI. Aucune règle ne reflète automatiquement les pratiques de Framatex.', created_by=admin.id)
            db.add(profile); db.flush()
            for title, folder, typ, phase, validate, note in RULES:
                db.add(RequirementRule(profile_id=profile.id, title=title, folder_slug=folder, document_type=typ, due_phase=phase, requires_validation=validate, guidance=note))
        count = 0
        for i, (name, *_rest) in enumerate(ROWS):
            launch = db.scalar(select(Launch).where(Launch.name == name))
            if launch and not db.get(LaunchCompleteness, launch.id):
                db.add(LaunchCompleteness(launch_id=launch.id, profile_id=profile.id,
                                           phase=['preparation','approvisionnement','expedition'][i]))
                count += 1
        db.commit()
    print(f'Profil de démonstration chargé ; {count} lancement(s) fictif(s) associé(s).')

if __name__ == '__main__': main()
