"""Contrôles du dossier unique, fondés sur des attentes et valeurs explicites."""
from __future__ import annotations
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import Document, User
from .global_library_models import GlobalDocumentEntry
from .global_library_routes import SLUGS, authorized, ready
from .experience_models import DocumentExpectation
from .quality_models import CrossDocumentRule, DocumentDatum
from .quality_routes import DatumIn, normalized_decimal
from .workflow import VALUE_FIELDS
from .access import accessible

router = APIRouter(prefix="/api/dossier-jaune", tags=["Vérifications documentaires"])


def norm(value):
    return " ".join((value or "").casefold().split())


def visible_documents(db, user):
    from .main import permitted
    rows = db.execute(select(Document, GlobalDocumentEntry).join(GlobalDocumentEntry)).all()
    return [(doc, entry) for doc, entry in rows if doc.versions
            and permitted(user, "document.read", entry.folder_slug)
            and accessible(db, user, doc.folder.launch)]


def current_values(db, doc):
    if not doc.versions:
        raise HTTPException(422, "Document sans version exploitable")
    version = max(doc.versions, key=lambda v: v.number)
    values = db.scalars(select(DocumentDatum).where(DocumentDatum.document_version_id == version.id)).all()
    return version, {datum.field_key: datum for datum in values}


def global_comparison(db, docs, rule, ref):
    left = [(d, e) for d, e in docs if e.folder_slug == rule.left_folder
            and norm(d.doc_type) == norm(rule.left_doc_type) and norm(e.orli_ref) == norm(ref)]
    right = [(d, e) for d, e in docs if e.folder_slug == rule.right_folder
             and norm(d.doc_type) == norm(rule.right_doc_type) and norm(e.orli_ref) == norm(ref)]
    row = {"rule_id": rule.id, "name": rule.name, "orli_ref": ref,
           "folders": [rule.left_folder, rule.right_folder], "field_key": rule.field_key,
           "tolerance": rule.tolerance_text, "status": "unavailable",
           "reason": "Pièce attendue non disponible parmi les documents accessibles", "pair": []}
    if not left or not right:
        return row
    if len(left) != 1 or len(right) != 1 or left[0][0].id == right[0][0].id:
        row.update(status="ambiguous", reason="Plusieurs documents candidats : précisez les types ou la référence ORLI")
        return row
    for doc, entry in (left[0], right[0]):
        version, values = current_values(db, doc)
        datum = values.get(rule.field_key)
        row["pair"].append({"document_id": doc.id, "title": doc.title, "folder": entry.folder_slug,
                            "version": version.number, "value": datum.value_text if datum else None,
                            "unit": datum.unit if datum else None})
    a, b = row["pair"]
    if a["value"] is None or b["value"] is None:
        row["reason"] = "Valeur à relever sur la version courante de chaque document"
    elif a["unit"] != b["unit"]:
        row.update(status="unit_mismatch", reason="Unités différentes : aucune conversion automatique")
    else:
        delta = abs(Decimal(a["value"]) - Decimal(b["value"]))
        state = "consistent" if delta <= Decimal(rule.tolerance_text) else "difference"
        row.update(status=state, difference=format(delta, "f"),
                   reason="Écart dans la tolérance" if state == "consistent" else "Écart à examiner")
    return row


@router.get("/controls")
def controls(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import permitted, is_admin
    ready(db)
    docs = visible_documents(db, user)
    expected = []
    for rule in db.scalars(select(DocumentExpectation).where(DocumentExpectation.active.is_(True))
                           .order_by(DocumentExpectation.created_at)).all():
        if not permitted(user, "document.read", rule.folder_slug):
            continue
        matched = [doc for doc, entry in docs if entry.folder_slug == rule.folder_slug
                   and norm(doc.doc_type) == norm(rule.document_type)
                   and (not rule.orli_ref or norm(entry.orli_ref) == norm(rule.orli_ref))]
        expected.append({"id": rule.id, "title": rule.title, "folder": rule.folder_slug,
                         "orli_ref": rule.orli_ref, "document_type": rule.document_type,
                         "status": "present" if matched else "missing",
                         "documents": [{"id": d.id, "title": d.title} for d in matched],
                         "can_edit": permitted(user, "completeness.review", rule.folder_slug)})
    comparisons = []
    rules = db.scalars(select(CrossDocumentRule).where(CrossDocumentRule.active.is_(True))
                       .order_by(CrossDocumentRule.name)).all()
    visible_rules = []
    for rule in rules:
        if not all(permitted(user, "document.read", slug) for slug in (rule.left_folder, rule.right_folder)):
            continue
        visible_rules.append({"id": rule.id, "name": rule.name})
        # Never compare arbitrary documents with no reference, or documents from
        # different ORLI references. An ambiguous source remains an uncertainty.
        refs = sorted({entry.orli_ref for doc, entry in docs if entry.orli_ref
                       and ((entry.folder_slug == rule.left_folder and norm(doc.doc_type) == norm(rule.left_doc_type))
                            or (entry.folder_slug == rule.right_folder and norm(doc.doc_type) == norm(rule.right_doc_type)))})
        seen = set()
        for ref in refs:
            if norm(ref) not in seen:
                seen.add(norm(ref)); comparisons.append(global_comparison(db, docs, rule, ref))
    documents = []
    for doc, entry in docs:
        version, values = current_values(db, doc)
        documents.append({"id": doc.id, "title": doc.title, "folder": entry.folder_slug,
                          "orli_ref": entry.orli_ref, "doc_type": doc.doc_type, "version": version.number,
                          "can_write": permitted(user, "document.write", entry.folder_slug),
                          "values": [{"field_key": k, "value": d.value_text, "unit": d.unit} for k, d in values.items()]})
    return {"expectations": expected, "comparisons": comparisons, "documents": documents,
            "rules": visible_rules, "can_manage_rules": is_admin(user),
            "expectation_folders": [s for s in SLUGS if permitted(user, "document.read", s)
                                    and permitted(user, "completeness.review", s)],
            "fields": [{"key": k, "label": label, "unit": unit} for k, (label, unit) in VALUE_FIELDS.items()],
            "scope": "Documents accessibles uniquement. Les valeurs sont relevées par un utilisateur sur chaque version.",
            "counts": {"missing": sum(r["status"] == "missing" for r in expected),
                       "differences": sum(r["status"] in ("difference", "unit_mismatch") for r in comparisons)}}


class ExpectationInput(BaseModel):
    folder: Literal["jaune", "rose", "bleu", "vert"]
    title: str = Field(min_length=3, max_length=180)
    document_type: str = Field(min_length=2, max_length=100)
    orli_ref: str | None = Field(default=None, max_length=100)

    @field_validator("title", "document_type", "orli_ref", mode="before")
    @classmethod
    def strip(cls, value):
        return value.strip() if isinstance(value, str) else value


@router.post("/expectations", status_code=201)
def create_expectation(payload: ExpectationInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import must, audit
    ready(db)
    must(user, "document.read", payload.folder); must(user, "completeness.review", payload.folder)
    row = DocumentExpectation(folder_slug=payload.folder, title=payload.title,
                              document_type=payload.document_type, orli_ref=payload.orli_ref or None, created_by=user.id)
    db.add(row); db.flush()
    audit(db, user, "expectation.create", "expectation", row.id, {"folder": row.folder_slug})
    db.commit()
    return {"id": row.id}


@router.delete("/expectations/{expectation_id}")
def deactivate_expectation(expectation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import must, audit, permitted
    row = db.get(DocumentExpectation, expectation_id)
    if not row or not permitted(user, "document.read", row.folder_slug):
        raise HTTPException(404, "Attente introuvable")
    must(user, "completeness.review", row.folder_slug)
    row.active = False
    audit(db, user, "expectation.deactivate", "expectation", row.id)
    db.commit()
    return {"active": False}


@router.post("/documents/{doc_id}/data", status_code=201)
def record_datum(doc_id: str, payload: DatumIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import must, audit
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    entry = authorized(db, user, doc, "document.read")
    must(user, "document.write", entry.folder_slug)
    if payload.field_key not in VALUE_FIELDS or not payload.unit.strip():
        raise HTTPException(422, "Champ ou unité invalide")
    version, values = current_values(db, doc)
    if payload.field_key in values:
        raise HTTPException(409, "Valeur déjà consignée : déposez une nouvelle version pour la corriger")
    row = DocumentDatum(document_version_id=version.id, field_key=payload.field_key,
                        value_text=normalized_decimal(payload.value), unit=payload.unit.strip(), recorded_by=user.id)
    db.add(row); db.flush()
    audit(db, user, "quality.datum.record", "document_version", version.id, {"field_key": payload.field_key, "datum": row.id})
    db.commit()
    return {"id": row.id, "version": version.number}
