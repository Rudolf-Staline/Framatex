"""One evaluator for explicit order/launch obligations and historical adapters.

A requirement is scoped to an order or to a particular launch. Common documents
never stand in for several distinct launch obligations. Exceptions keep their
original launch scope; they are not documents and do not validate any version.
"""
from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload, aliased
from .core import utcnow
from .models import Document, DocumentVersion, Folder, Launch
from .completeness_models import (CompletenessProfile, LaunchCompleteness,
    RequirementValidation, RequirementException)

PHASES = [("preparation", "Préparation"), ("approvisionnement", "Approvisionnement"),
          ("fabrication", "Fabrication"), ("expedition", "Expédition"), ("cloture", "Clôture")]
PHASE_RANK = {code: position for position, (code, _) in enumerate(PHASES)}
STATES = ('present', 'pending_validation', 'pending_publication', 'missing',
          'not_due', 'exception', 'optional', 'not_applicable')
EXPLANATIONS = {
    'not_applicable': 'Type de commande hors condition configurée',
    'optional': 'Pièce facultative non déposée',
    'pending_publication': 'Publication accessible à un compte client actif attendue',
    'pending_validation': 'Version courante présente, validation attendue',
    'present': 'Version courante conforme aux conditions documentaires',
    'not_due': 'Phase, échéance ou événement de référence non atteint',
    'missing': 'Aucune version courante utilisable pour cette obligation',
    'exception': 'Obligation couverte par une exception justifiée ; aucune présence présumée',
}


def publication_available(db, version_ids):
    """Use the portal's canonical availability check with an eligible reader.

    A nominal ``published`` status or an internal preview is insufficient. The
    same recipient restrictions as the actual client download must hold.
    """
    from .partner_models import PartnerPublication, PartnerAccount, Partner
    from .sharing_models import ClientPublication
    from .partner_routes import visible_publication
    from .partner_permissions import email_allowed, permissions
    from . import document_storage
    version_ids = [version_ids] if isinstance(version_ids, str) else version_ids
    if not version_ids: return False
    for binding in db.scalars(select(PartnerPublication).join(ClientPublication,
            PartnerPublication.publication_id == ClientPublication.id).where(
            ClientPublication.document_version_id.in_(version_ids))):
        recipient = db.get(Partner, binding.partner_id)
        if not recipient or not recipient.active or recipient.kind != 'client':
            continue
        for account in db.scalars(select(PartnerAccount).where(
                PartnerAccount.partner_id == binding.partner_id,
                PartnerAccount.active.is_(True), PartnerAccount.password_hash.is_not(None))):
            if not email_allowed(db, binding.partner_id, account.email) or 'read' not in permissions(db, account):
                continue
            publication = visible_publication(db, binding, account)
            if publication:
                from .models import DocumentVersion
                version = db.get(DocumentVersion, publication.document_version_id)
                if version and (document_storage.STORAGE / version.disk_name).is_file():
                    return True
    return False


def _owner_order(db, launch):
    from .order_documents import launch_order
    from .partner_phase2_models import BusinessOrder
    link = launch_order(db, launch.id)
    return db.get(BusinessOrder, link.order_id) if link else None


def _documents(db, kind, target, rule, user):
    from .order_documents import OrderDossier, document_access_clause
    query = select(Document).join(Folder).where(Folder.slug == rule.folder_slug).order_by(Document.created_at.desc(), Document.id)
    if kind == 'order':
        query = query.join(OrderDossier, Folder.dossier_id == OrderDossier.id).where(
            OrderDossier.order_id == target.id, Document.launch_id.is_(None))
    else:
        query = query.where(or_(Document.launch_id == target.id,
            (Document.launch_id.is_(None) & (Folder.launch_id == target.id))))
    # Classification overrides and unambiguous aliases share the same matcher.
    from .document_types import DocumentTypeAssignment, matches_classification
    older = aliased(DocumentVersion)
    latest_number = select(func.max(older.number)).where(older.document_id == Document.id).correlate(Document).scalar_subquery()
    documents = db.execute(query.add_columns(DocumentTypeAssignment, DocumentVersion).outerjoin(
        DocumentTypeAssignment, DocumentTypeAssignment.document_id == Document.id).join(
        DocumentVersion, (DocumentVersion.document_id == Document.id) & (DocumentVersion.number == latest_number)).where(
        document_access_clause(user)).options(selectinload(Document.folder))).all()
    return [(doc, version) for doc, assignment, version in documents if matches_classification(doc, assignment, rule.document_type)]


def _validated(db, rule, candidates, kind, target):
    if not rule.requires_validation:
        return {v.id for _, v in candidates}
    if not candidates: return set()
    version_ids = [v.id for _, v in candidates]
    validated = set(db.scalars(select(RequirementValidation.document_version_id).where(
        RequirementValidation.rule_id == rule.id, RequirementValidation.launch_id == target.id,
        RequirementValidation.document_version_id.in_(version_ids)))) if kind == 'launch' else set()
    # Batch the same version-specific precedence as sharing.is_approved: the
    # current approval cycle, otherwise the latest documentary decision, with
    # the legacy requirement validation retained only when no review exists.
    from .approval_models import ApprovalTemplate, ApprovalRun
    from .workflow_models import DocumentReview
    from fastapi import HTTPException
    templates = {}
    for template in db.scalars(select(ApprovalTemplate).where(ApprovalTemplate.active.is_(True),
            ApprovalTemplate.folder_slug == rule.folder_slug,
            ApprovalTemplate.document_type.in_({d.doc_type for d, _ in candidates}))):
        if template.document_type in templates:
            raise HTTPException(409, 'Plusieurs circuits actifs pour ce type de document')
        templates[template.document_type] = template
    reviews = select(DocumentReview.document_version_id.label('version_id'), DocumentReview.decision,
        func.row_number().over(partition_by=DocumentReview.document_version_id,
            order_by=(DocumentReview.reviewed_at.desc(), DocumentReview.id.desc())).label('position')).where(
        DocumentReview.document_version_id.in_(version_ids)).subquery()
    decisions = dict(db.execute(select(reviews.c.version_id, reviews.c.decision).where(reviews.c.position == 1)).all())
    runs = select(ApprovalRun.document_version_id.label('version_id'), ApprovalRun.status,
        func.row_number().over(partition_by=ApprovalRun.document_version_id,
            order_by=(ApprovalRun.cycle.desc(), ApprovalRun.started_at.desc())).label('position')).where(
        ApprovalRun.document_version_id.in_(version_ids)).subquery()
    approvals = dict(db.execute(select(runs.c.version_id, runs.c.status).where(runs.c.position == 1)).all()) if templates else {}
    for doc, version in candidates:
        if doc.doc_type in templates:
            if approvals.get(version.id) == 'approved': validated.add(version.id)
            else: validated.discard(version.id)
        elif version.id in decisions:
            if decisions[version.id] == 'approved': validated.add(version.id)
            else: validated.discard(version.id)
    return validated


def _row(db, rule, policy, kind, target, phase, order_type, user, permitted, source_kind, source_id):
    from .order_documents import launch_order
    from .partner_phase2_models import PartnerIntegration
    applicable = not policy or not policy.order_type or policy.order_type == order_type
    optional = bool(policy and policy.optional)
    reference = policy.deadline_reference if policy else 'launch_created'
    reference_date = None
    if target:
        if reference == 'launch_created' and kind == 'launch': reference_date = target.created_at.date()
        elif reference == 'order_created':
            order = target if kind == 'order' else _owner_order(db, target)
            reference_date = order.created_at.date() if order else None
    has_delay = bool(policy and policy.days_after_launch is not None)
    deadline = reference_date + timedelta(days=policy.days_after_launch) if has_delay and reference_date else None
    reference_missing = not target or (has_delay and reference_date is None)
    due = applicable and not optional and not reference_missing and PHASE_RANK[phase] >= PHASE_RANK[rule.due_phase] and (deadline is None or utcnow().date() >= deadline)
    candidates = _documents(db, kind, target, rule, user) if target else []
    unavailable = set(db.scalars(select(PartnerIntegration.version_id).where(PartnerIntegration.active.is_(False), PartnerIntegration.version_id.in_([v.id for _, v in candidates])))) if candidates else set()
    candidates = [(d, v) for d, v in candidates if v.id not in unavailable]
    validated = _validated(db, rule, candidates, kind, target) if target else set()
    accepted = [(d, v) for d, v in candidates if not rule.requires_validation or v.id in validated]
    published = not policy or not policy.requires_client_publication or publication_available(db, [v.id for _, v in accepted])
    exception = db.scalar(select(RequirementException).where(
        RequirementException.launch_id == target.id, RequirementException.rule_id == rule.id,
        RequirementException.active.is_(True))) if target and kind == 'launch' else None
    if target and kind == 'order':
        from .completeness_models import OrderRequirementException
        exception = db.get(OrderRequirementException, (target.id, rule.id))
        if exception and not exception.active: exception = None
    if not applicable: status = 'not_applicable'
    elif accepted and published: status = 'present'
    elif exception: status = 'exception'
    elif accepted: status = 'pending_publication'
    elif candidates: status = 'pending_validation'
    elif optional: status = 'optional'
    elif not due: status = 'not_due'
    else: status = 'missing'
    accepted_ids = {v.id for _, v in accepted}
    evidence = accepted + [(d, v) for d, v in candidates if v.id not in accepted_ids]
    target_id = target.id if target else source_id
    order_id = target.id if target and kind == 'order' else None
    if target and kind == 'launch':
        link = launch_order(db, target.id)
        order_id = link.order_id if link else None
    return {
        'id': rule.id, 'rule_id': rule.id, 'obligation_key': f'{kind}:{target_id}:{rule.id}',
        'obligation_scope': kind, 'order_id': order_id,
        'launch_id': target.id if target and kind == 'launch' else None,
        'source_kind': source_kind, 'source_id': source_id,
        'title': rule.title, 'folder': rule.folder_slug, 'document_type': rule.document_type,
        'due_phase': rule.due_phase, 'requires_validation': rule.requires_validation,
        'guidance': rule.guidance, 'due': due, 'status': status, 'optional': optional,
        'applicable': applicable, 'due_date': deadline.isoformat() if deadline else None,
        'deadline_reference': reference, 'deadline_reference_date': reference_date.isoformat() if reference_date else None,
        'deadline_reference_missing': reference_missing, 'explanation': EXPLANATIONS[status],
        'exception_reason': exception.reason if exception and status == 'exception' else None,
        'exception_recorded_by': exception.recorded_by if exception and status == 'exception' else None,
        'exception_updated_at': exception.updated_at.isoformat() if exception and status == 'exception' else None,
        'documents': [{'id': doc.id, 'title': doc.title, 'version': version.number,
                       'validated': version.id in validated if rule.requires_validation else None}
                      for doc, version in evidence[:20]],
        'document_count': len(candidates), 'documents_truncated': len(candidates) > 20,
        'can_review': target is not None and permitted(user, 'completeness.review', rule.folder_slug) and permitted(user, 'document.read', rule.folder_slug),
    }


def evaluate_context(db, kind, target, context, user, permitted):
    """Canonical rows for one profile attachment; endpoints only adapt naming."""
    from .partner_phase2_models import RequirementPolicy, LaunchOrderContext, BusinessOrderLaunch
    from .access import accessible
    phase = context.phase if context else 'preparation'
    profile = db.get(CompletenessProfile, context.profile_id) if context and context.profile_id else None
    rules = sorted((r for r in profile.rules if r.active), key=lambda r: (PHASE_RANK[r.due_phase], r.folder_slug, r.title.casefold())) if profile else []
    visible = [r for r in rules if permitted(user, 'document.read', r.folder_slug)]
    if kind == 'order': order_type = context.order_type if context else ''
    else:
        oc = db.get(LaunchOrderContext, target.id)
        order_type = oc.order_type if oc else ''
    rows = []; partial = len(visible) < len(rules)
    for rule in visible:
        policy = db.get(RequirementPolicy, rule.id)
        scope = policy.obligation_scope if policy and policy.obligation_scope != 'context' else kind
        if scope == kind: targets = [target]
        elif scope == 'order':
            owner = _owner_order(db, target)
            targets = [owner] if owner else [None]
        else:
            launches = list(db.scalars(select(Launch).join(BusinessOrderLaunch).where(BusinessOrderLaunch.order_id == target.id)))
            targets = [l for l in launches if accessible(db, user, l)]
            partial = partial or len(targets) < len(launches)
            if not launches: targets = [None]
        for item in targets:
            rows.append(_row(db, rule, policy, scope, item, phase, order_type, user, permitted, kind, target.id))
    return {'profile_id': profile.id if profile else None, 'profile_name': profile.name if profile else None,
            'phase': phase, 'order_type': order_type, 'configured': bool(profile and rules),
            'partial_visibility': partial, 'rows': rows}


def report_summary(report):
    rows = report['rows']
    report.update({'phases': [{'code': c, 'label': l} for c, l in PHASES],
        'visible_rules': len(rows), 'counts': {s: sum(r['status'] == s for r in rows) for s in STATES},
        'due_count': sum(r['due'] for r in rows),
        'business_rules_confirmed': None, 'business_rules_status': 'not_recorded',
        'notice': "Règles configurées par l'administration ; aucune confirmation officielle Framatex enregistrée. Les dérogations ne valent pas présence."})
    return report


def evaluate(db, launch, user, permitted):
    report = evaluate_context(db, 'launch', launch, db.get(LaunchCompleteness, launch.id), user, permitted)
    report.update({'launch_id': launch.id, 'can_change_context': permitted(user, 'launch.update')})
    return report_summary(report)
