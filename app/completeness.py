"""Évalue les exigences selon leur exigibilité, la version courante et les droits."""
from __future__ import annotations
from .order_documents import folder_ids

from datetime import timedelta
from .core import utcnow
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Document, Folder, Launch
from .workflow import latest_review
from .completeness_models import (CompletenessProfile, LaunchCompleteness,
    RequirementRule, RequirementValidation, RequirementException)

# Étapes provisoires configurées pour la démonstration ; vocabulaire à valider par Framatex.
PHASES = [
    ("preparation", "Préparation"),
    ("approvisionnement", "Approvisionnement"),
    ("fabrication", "Fabrication"),
    ("expedition", "Expédition"),
    ("cloture", "Clôture"),
]
PHASE_RANK = {code: position for position, (code, _) in enumerate(PHASES)}


def evaluate(db: Session, launch: Launch, user, permitted):
    """Ne renvoie aucune règle d'un sous-dossier que l'utilisateur ne peut lire."""
    context = db.get(LaunchCompleteness, launch.id)
    phase = context.phase if context else "preparation"
    profile = db.get(CompletenessProfile, context.profile_id) if context and context.profile_id else None
    rules = [] if not profile else sorted((r for r in profile.rules if r.active),
                                          key=lambda r: (PHASE_RANK[r.due_phase], r.folder_slug, r.title.casefold()))
    visible = [r for r in rules if permitted(user, "document.read", r.folder_slug)]
    from .partner_phase2_models import RequirementPolicy,LaunchOrderContext
    order_context=db.get(LaunchOrderContext,launch.id)
    rows = []
    for rule in visible:
        policy=db.get(RequirementPolicy,rule.id)
        applicable=not policy or not policy.order_type or bool(order_context and order_context.order_type==policy.order_type)
        optional=bool(policy and policy.optional)
        deadline=(launch.created_at.date()+timedelta(days=policy.days_after_launch)) if policy and policy.days_after_launch is not None else None
        matching = db.scalars(select(Document).join(Folder).where(
            Folder.id.in_(folder_ids(db, launch.id)), Folder.slug == rule.folder_slug,
            Document.doc_type == rule.document_type
        )).all()
        candidates = []
        for document in matching:
            if document.versions:
                version = max(document.versions, key=lambda v: v.number)
                from .partner_integration_routes import business_available
                if business_available(db, version.id):
                    candidates.append((document, version))
        # Une validation d'une version ancienne ne valide jamais la version courante.
        validated = set()
        if candidates and rule.requires_validation:
            version_ids = [version.id for _, version in candidates]
            validations = db.scalars(select(RequirementValidation).where(
                RequirementValidation.rule_id == rule.id,
                RequirementValidation.launch_id == launch.id,
                RequirementValidation.document_version_id.in_(version_ids)
            )).all()
            validated = {v.document_version_id for v in validations}
            # Les décisions documentaires 0.3 ont priorité sur les validations 0.2
            # lorsqu'elles portent sur la même version courante.
            for candidate_doc, current_version in candidates:
                from .approval_routes import applicable_template
                from .sharing_routes import is_approved
                if applicable_template(db,candidate_doc):
                    if is_approved(db,current_version,candidate_doc): validated.add(current_version.id)
                    else: validated.discard(current_version.id)
                    continue
                decision = latest_review(db, current_version.id)
                if decision:
                    if decision.decision == 'approved':
                        validated.add(current_version.id)
                    else:
                        validated.discard(current_version.id)
        exception = db.scalar(select(RequirementException).where(
            RequirementException.launch_id == launch.id, RequirementException.rule_id == rule.id,
            RequirementException.active.is_(True)
        ))
        due = applicable and not optional and PHASE_RANK[phase] >= PHASE_RANK[rule.due_phase] and (deadline is None or utcnow().date()>=deadline)
        publication_ready=True
        if policy and policy.requires_client_publication:
            from .partner_models import PartnerPublication,Partner,PartnerAccount
            from .sharing_models import ClientPublication
            from .sharing_routes import pub_out
            from .partner_phase2_models import PartnerClientOrder
            publication_ready=False
            for document,version in candidates:
                for publication in db.scalars(select(ClientPublication).where(ClientPublication.document_version_id==version.id)):
                    for binding in db.scalars(select(PartnerPublication).where(PartnerPublication.publication_id==publication.id)):
                        recipient=db.get(Partner,binding.partner_id)
                        grant=db.scalar(select(PartnerClientOrder).where(PartnerClientOrder.partner_id==binding.partner_id,PartnerClientOrder.launch_id==launch.id))
                        from .partner_permissions import email_allowed,permissions
                        contacts=list(db.scalars(select(PartnerAccount).where(PartnerAccount.partner_id==binding.partner_id,PartnerAccount.active.is_(True),PartnerAccount.password_hash.is_not(None))))
                        usable=any(email_allowed(db,binding.partner_id,a.email) and 'read' in permissions(db,a) for a in contacts)
                        if recipient and recipient.active and usable and (not grant or grant.active) and pub_out(db,publication,launch)['effective']:
                            publication_ready=True
        if not applicable:
            status='not_applicable'
        elif candidates and (not rule.requires_validation or any(v.id in validated for _, v in candidates)):
            status = "present" if publication_ready else "pending_publication"
        elif candidates:
            status = "pending_validation"
        elif optional:
            status='optional'
        elif not due:
            status = "not_due"
        elif exception:
            status = "exception"
        else:
            status = "missing"
        rows.append({
            "id": rule.id, "title": rule.title, "folder": rule.folder_slug,
            "document_type": rule.document_type, "due_phase": rule.due_phase,
            "requires_validation": rule.requires_validation, "guidance": rule.guidance,
            "due": due, "status": status, "optional":optional, "applicable":applicable, "due_date":deadline.isoformat() if deadline else None,
            "explanation": {"not_applicable":"Type de commande hors condition configurée","optional":"Pièce facultative non déposée","pending_publication":"Publication effective vers un client actif attendue","pending_validation":"Version courante présente, validation attendue","present":"Version courante conforme aux conditions documentaires","not_due":"Phase ou échéance configurée non atteinte","missing":"Aucune version courante utilisable pour cette exigence","exception":"Absence couverte par une exception justifiée"}[status],
            "exception_reason": exception.reason if exception and status == "exception" else None,
            "documents": [{"id": doc.id, "title": doc.title, "version": version.number,
                           "validated": version.id in validated if rule.requires_validation else None}
                          for doc, version in candidates],
            "can_review": permitted(user, "completeness.review", rule.folder_slug)
                           and permitted(user, "document.read", rule.folder_slug),
        })
    counts = {code: sum(row["status"] == code for row in rows)
              for code in ("present", "pending_validation", "missing", "not_due", "exception", "optional", "not_applicable", "pending_publication")}
    # Un total nul n'est pas une complétude à 100 %. Une dérogation ne vaut pas présence.
    exigible = sum(row["due"] for row in rows)
    return {
        "launch_id": launch.id, "profile_id": profile.id if profile else None,
        "profile_name": profile.name if profile else None, "phase": phase,
        "phases": [{"code": c, "label": l} for c, l in PHASES],
        "configured": bool(profile and rules), "visible_rules": len(rows),
        "partial_visibility": len(visible) < len(rules), "counts": counts,
        "due_count": exigible, "rows": rows,
        "can_change_context": permitted(user, "launch.update"),
    }
