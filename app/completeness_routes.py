"""Completeness profiles, contextual rules and decisions HTTP endpoints."""
from __future__ import annotations
from fastapi import APIRouter
from .order_documents import document_in_launch
from .access import permitted, must, admin_only
from .audit import audit
from .launches import get_launch, SLUGS
from .order_documents import get_doc
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import User
from .completeness_models import CompletenessProfile, RequirementRule, LaunchCompleteness, RequirementValidation, RequirementException
from .completeness import PHASE_RANK, evaluate
from .approval_models import ApprovalRun
from .workflow import latest_review

router = APIRouter()

class ProfilePayload(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=1200)


class RequirementPayload(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    folder: str
    document_type: str = Field(min_length=2, max_length=100)
    due_phase: str = "preparation"
    requires_validation: bool = False
    guidance: str = Field(default="", max_length=1600)


class RequirementPatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    due_phase: str | None = None
    requires_validation: bool | None = None
    guidance: str | None = Field(default=None, max_length=1600)
    active: bool | None = None


class ContextPayload(BaseModel):
    profile_id: str | None = None
    phase: str = "preparation"


class ValidationPayload(BaseModel):
    document_id: str


class ExceptionPayload(BaseModel):
    reason: str = Field(default="", max_length=2000)
    active: bool = True


def rule_out(r: RequirementRule):
    return {"id": r.id, "title": r.title, "folder": r.folder_slug,
            "document_type": r.document_type, "due_phase": r.due_phase,
            "requires_validation": r.requires_validation, "active": r.active,
            "guidance": r.guidance}


def profile_out(p: CompletenessProfile, include_rules=False):
    data = {"id": p.id, "name": p.name, "description": p.description,
            "active_rules": sum(r.active for r in p.rules)}
    if include_rules:
        data["rules"] = [rule_out(r) for r in sorted(p.rules, key=lambda x: (PHASE_RANK[x.due_phase], x.title))]
    return data


@router.get("/api/completeness/profiles")
def public_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    return [profile_out(p) for p in db.scalars(select(CompletenessProfile).order_by(CompletenessProfile.name)).all()]


@router.get("/api/admin/completeness/profiles")
def admin_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    return [profile_out(p, True) for p in db.scalars(select(CompletenessProfile).order_by(CompletenessProfile.name)).all()]


@router.post("/api/admin/completeness/profiles", status_code=201)
def create_profile(payload: ProfilePayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    profile = CompletenessProfile(name=payload.name.strip(), description=payload.description.strip(), created_by=user.id)
    db.add(profile)
    try:
        db.flush()
        audit(db, user, "completeness.profile.create", "completeness_profile", profile.id, {"name": profile.name})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ce nom de profil existe déjà")
    return profile_out(profile, True)


@router.post("/api/admin/completeness/profiles/{profile_id}/rules", status_code=201)
def add_requirement(profile_id: str, payload: RequirementPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    if payload.folder not in SLUGS or payload.due_phase not in PHASE_RANK:
        raise HTTPException(422, "Sous-dossier ou étape invalide")
    profile = db.get(CompletenessProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profil introuvable")
    rule = RequirementRule(profile_id=profile.id, title=payload.title.strip(), folder_slug=payload.folder,
                           document_type=payload.document_type.strip(), due_phase=payload.due_phase,
                           requires_validation=payload.requires_validation, guidance=payload.guidance.strip())
    db.add(rule)
    try:
        db.flush()
        audit(db, user, "completeness.rule.create", "completeness_rule", rule.id,
              {"profile": profile.id, "type": rule.document_type, "due_phase": rule.due_phase})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ce type documentaire existe déjà dans ce sous-dossier et ce profil")
    return rule_out(rule)


@router.patch("/api/admin/completeness/rules/{rule_id}")
def patch_requirement(rule_id: str, payload: RequirementPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only(user)
    rule = db.get(RequirementRule, rule_id)
    if not rule:
        raise HTTPException(404, "Règle introuvable")
    changes = payload.model_dump(exclude_unset=True)
    if "due_phase" in changes and changes["due_phase"] not in PHASE_RANK:
        raise HTTPException(422, "Étape inconnue")
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(422, "Modifications invalides")
    for field, value in changes.items():
        setattr(rule, field, value.strip() if isinstance(value, str) else value)
    audit(db, user, "completeness.rule.update", "completeness_rule", rule.id, {"changed": changes})
    db.commit()
    return rule_out(rule)


@router.patch("/api/launches/{launch_id}/completeness/context")
def set_completeness_context(launch_id: str, payload: ContextPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.update")
    launch = get_launch(db, launch_id)
    if payload.phase not in PHASE_RANK:
        raise HTTPException(422, "Étape inconnue")
    if payload.profile_id is not None and not db.get(CompletenessProfile, payload.profile_id):
        raise HTTPException(422, "Profil de complétude inconnu")
    context = db.get(LaunchCompleteness, launch.id)
    if not context:
        context = LaunchCompleteness(launch_id=launch.id)
        db.add(context)
    context.profile_id, context.phase = payload.profile_id, payload.phase
    audit(db, user, "completeness.context.update", "launch", launch.id,
          {"profile": payload.profile_id, "phase": payload.phase})
    db.commit()
    return evaluate(db, launch, user, permitted)


@router.get("/api/launches/{launch_id}/completeness")
def get_completeness(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    return evaluate(db, get_launch(db, launch_id), user, permitted)


def require_active_launch_rule(db, launch_id, rule_id):
    launch = get_launch(db, launch_id)
    rule = db.get(RequirementRule, rule_id)
    context = db.get(LaunchCompleteness, launch.id)
    if not rule or not rule.active or not context or context.profile_id != rule.profile_id:
        raise HTTPException(404, "Règle non applicable à ce lancement")
    return launch, rule


@router.post("/api/launches/{launch_id}/completeness/rules/{rule_id}/validate")
def validate_requirement(launch_id: str, rule_id: str, payload: ValidationPayload,
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    launch, rule = require_active_launch_rule(db, launch_id, rule_id)
    must(user, "completeness.review", rule.folder_slug)
    must(user, "document.read", rule.folder_slug)
    if not rule.requires_validation:
        raise HTTPException(422, "Cette exigence ne nécessite pas de validation distincte")
    doc = get_doc(db, payload.document_id)
    if not document_in_launch(db, doc, launch.id) or doc.folder.slug != rule.folder_slug or doc.doc_type != rule.document_type:
        raise HTTPException(422, "Document non conforme au type et au lancement de la règle")
    if not doc.versions:
        raise HTTPException(422, "Document sans version")
    version = max(doc.versions, key=lambda v: v.number)
    # Une exigence de complétude ne remplace pas le circuit métier configuré.
    from .approval_routes import applicable_template
    if applicable_template(db, doc):
        from .approval_models import ApprovalRun
        approved = db.scalar(select(ApprovalRun).where(
            ApprovalRun.document_version_id == version.id, ApprovalRun.status == 'approved'))
        if not approved:
            raise HTTPException(409, 'Circuit de validation non achevé pour cette version')
    review_decision = latest_review(db, version.id)
    if review_decision and review_decision.decision in {'rejected', 'changes_requested'}:
        raise HTTPException(409, 'Version refusée ou à reprendre : le contrôle documentaire doit être régularisé')
    existing = db.scalar(select(RequirementValidation).where(
        RequirementValidation.rule_id == rule.id,
        RequirementValidation.document_version_id == version.id
    ))
    if existing:
        raise HTTPException(409, "Cette version a déjà été validée")
    db.add(RequirementValidation(rule_id=rule.id, document_version_id=version.id,
                                 launch_id=launch.id, validated_by=user.id))
    audit(db, user, "completeness.validate", "document_version", version.id,
          {"rule": rule.id, "launch": launch.id, "version": version.number})
    db.commit()
    return evaluate(db, launch, user, permitted)


@router.put("/api/launches/{launch_id}/completeness/rules/{rule_id}/exception")
def set_requirement_exception(launch_id: str, rule_id: str, payload: ExceptionPayload,
                              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    must(user, "launch.read")
    launch, rule = require_active_launch_rule(db, launch_id, rule_id)
    must(user, "completeness.review", rule.folder_slug)
    must(user, "document.read", rule.folder_slug)
    if payload.active and len(payload.reason.strip()) < 12:
        raise HTTPException(422, "Précisez une justification d'au moins 12 caractères")
    exception = db.scalar(select(RequirementException).where(
        RequirementException.launch_id == launch.id, RequirementException.rule_id == rule.id
    ))
    if not exception and payload.active:
        exception = RequirementException(launch_id=launch.id, rule_id=rule.id, recorded_by=user.id)
        db.add(exception)
    if exception:
        exception.active = payload.active
        exception.reason = payload.reason.strip() if payload.active else exception.reason
        exception.recorded_by = user.id
    audit(db, user, "completeness.exception.set", "completeness_rule", rule.id,
          {"launch": launch.id, "active": payload.active, "reason": payload.reason.strip() if payload.active else ""})
    db.commit()
    return evaluate(db, launch, user, permitted)
