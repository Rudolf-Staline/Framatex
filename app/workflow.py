"""Logique métier des impacts : n'envoie rien hors du système et ne modifie aucun prix.

Les règles sont explicitement configurées par l'administrateur. Une alerte signifie
« une vérification est utile », jamais « l'information est fausse ».
"""
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Document, DocumentVersion
from .workflow_models import ImpactRule, ImpactAlert, DocumentReview

VALUE_FIELDS = {
    'consommation_matiere': ('Consommation matière par pièce', 'm/pièce'),
    'quantite_lancement': ('Quantité du lancement', 'pièce'),
    'besoin_matiere_total': ('Besoin matière total', 'm'),
    'prix_unitaire': ('Prix unitaire', 'MAD/pièce'),
    'cout_matiere_unitaire': ('Coût matière par mètre', 'MAD/m'),
}
REVIEW_STATES = {'approved', 'rejected', 'changes_requested'}
ALERT_STATES = {'acknowledged', 'action_required', 'not_applicable'}


def latest_review(db: Session, version_id: str):
    return db.scalar(select(DocumentReview).where(DocumentReview.document_version_id == version_id)
                     .order_by(DocumentReview.reviewed_at.desc(), DocumentReview.id.desc()).limit(1))


def review_status(db: Session, version_id: str):
    review = latest_review(db, version_id)
    return review.decision if review else 'to_review'


def emit_impacts(db: Session, *, launch_id: str, source_kind: str, source_key: str,
                 source_folder: str, source_ref_id: str, old_value: str | None = None,
                 new_value: str | None = None):
    """Appliquer les règles actives correspondant à une nouvelle valeur ou version."""
    rules = db.scalars(select(ImpactRule).where(
        ImpactRule.active.is_(True), ImpactRule.source_kind == source_kind,
        ImpactRule.source_key == source_key, ImpactRule.source_folder == source_folder
    )).all()
    for rule in rules:
        db.add(ImpactAlert(launch_id=launch_id, rule_id=rule.id,
                           source_ref_id=source_ref_id, old_value=old_value,
                           new_value=new_value))


def emit_document_impacts(db: Session, document: Document, version: DocumentVersion):
    emit_impacts(db, launch_id=document.folder.launch_id, source_kind='document',
                 source_key=document.doc_type, source_folder=document.folder.slug,
                 source_ref_id=version.id, old_value=None, new_value=f'v{version.number}')
