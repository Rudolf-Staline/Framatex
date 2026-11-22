"""Comparaisons explicites et inspection statique Excel sans exécuter de formules.

Les constats sont des pistes de vérification, jamais des non-conformités automatiques.
"""
from __future__ import annotations
import hashlib
import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Document, DocumentVersion, Folder
from .quality_models import DocumentDatum, CrossDocumentRule, QualityDecision
from .document_intake_models import DocumentIdentification
from .intake_models import ConfirmedField
from .intake import normalized

MAX_XLSX_BYTES = 5 * 1024 * 1024
MAX_CELLS = 40000
MAX_FINDINGS = 200
QUALITY_FIELDS_EXTRA = {'reference_commande': ('Référence de commande', 'référence'),
                        'reference_article': ('Référence article', 'référence'),
                        'prix_total': ('Prix total hors taxes', 'MAD')}
REFERENCE_KEYS = {'reference_commande', 'reference_article'}
EXTRACTED_KEYS = {'besoin_matiere_total': ('besoin_matiere',)}


def source_unit(unit):
    key = normalized(unit).replace(' ', '')
    return {'pieces': 'pièce', 'piece': 'pièce', 'pcs': 'pièce', 'pc': 'pièce',
            'metres': 'm', 'metre': 'm', 'm/piece': 'm/pièce', 'm/pc': 'm/pièce',
            'kg/piece': 'kg/pièce', 'kg/pc': 'kg/pièce', 'dh': 'mad',
            'dh/piece': 'mad/pièce', 'mad/piece': 'mad/pièce', 'eur/piece': 'eur/pièce',
            'usd/piece': 'usd/pièce', '€/piece': 'eur/pièce', '€': 'eur'}.get(key, key)


def extracted_value(db, version, doc, key):
    if key == 'quantite_lancement':
        mapped = ('quantite_commandee', 'quantite') if doc.doc_type == 'Commande client' else ('quantite_produite', 'quantite')
    else:
        mapped = EXTRACTED_KEYS.get(key, (key,))
    field = None
    for candidate in mapped:
        field = db.scalar(select(ConfirmedField).where(ConfirmedField.document_version_id == version.id,
                                                       ConfirmedField.field_key == candidate))
        if field:
            break
    if not field or not field.value.strip():
        return None
    if key in REFERENCE_KEYS:
        return field.value.strip(), 'référence', field.source_excerpt
    unit = source_unit(field.unit)
    if not unit:
        return None
    # A generic quantity in a delivery note can be a delivered amount, not an
    # order quantity. Only reuse the extracted field for these production pieces.
    if key == 'quantite_lancement' and (unit != 'pièce' or doc.folder.slug != 'jaune' or doc.doc_type not in
            {'Commande client', 'Fiche d’emploi', 'Lancement provisoire', 'Lancement définitif'}):
        return None
    if key == 'prix_unitaire' and not unit.endswith('/pièce'):
        return None
    raw = field.value.strip().replace('\u202f', ' ').replace('\xa0', ' ')
    if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?: \d{3})+)(?:[.,]\d+)?', raw):
        return None
    value = Decimal(raw.replace(' ', '').replace(',', '.'))
    if abs(value) > Decimal('1e15'):
        return None
    return format(value, 'f'), unit, field.source_excerpt


def latest_document_versions(db: Session, launch_id: str, doc_type: str, folder: str):
    docs = db.scalars(select(Document).join(Folder).where(
        Folder.launch_id == launch_id, Folder.slug == folder, Document.doc_type == doc_type
    )).all()
    return [(d, max(d.versions, key=lambda x:x.number)) for d in docs if d.versions]


def comparison(db: Session, launch_id: str, rule: CrossDocumentRule):
    """Do not guess when several documents could be the expected source."""
    left = latest_document_versions(db, launch_id, rule.left_doc_type, rule.left_folder)
    right = latest_document_versions(db, launch_id, rule.right_doc_type, rule.right_folder)
    status = 'unavailable'; reason = 'Pièce manquante'; pair = []; delta = None
    if not left or not right:
        reason = 'Pièce requise absente' if not left or not right else reason
    elif len(left) != 1 or len(right) != 1 or left[0][0].id == right[0][0].id:
        status = 'ambiguous'; reason = 'Plusieurs documents candidats : sélectionner une source métier précise'
    else:
        for d, v in [left[0], right[0]]:
            identification = db.get(DocumentIdentification, v.id)
            datum = db.scalar(select(DocumentDatum).where(
                DocumentDatum.document_version_id == v.id, DocumentDatum.field_key == rule.field_key
            ))
            value, unit, excerpt, provenance = None, None, '', None
            if not identification or identification.status in {'matched', 'confirmed'}:
                if datum:
                    value, unit, provenance = datum.value_text, datum.unit, 'Relevé manuel'
                elif extracted := extracted_value(db, v, d, rule.field_key):
                    value, unit, excerpt = extracted
                    provenance = 'Lecture documentaire confirmée'
            else:
                provenance = 'Type documentaire à vérifier'
            pair.append({'document_id': d.id, 'document_title': d.title, 'version_id': v.id,
                         'version': v.number, 'folder': d.folder.slug, 'value': value, 'unit': unit,
                         'provenance': provenance, 'source_excerpt': excerpt})
        if not all(x['value'] is not None for x in pair):
            status = 'unavailable'; reason = 'Valeur non relevée sur une ou plusieurs versions courantes'
        elif source_unit(pair[0]['unit']) != source_unit(pair[1]['unit']):
            status = 'unit_mismatch'; reason = 'Unités incompatibles : conversion manuelle requise'
        elif rule.field_key in REFERENCE_KEYS:
            status = 'consistent' if pair[0]['value'].casefold() == pair[1]['value'].casefold() else 'difference'
            reason = 'Références identiques' if status == 'consistent' else 'Références différentes à examiner'
        else:
            delta = abs(Decimal(pair[0]['value'])-Decimal(pair[1]['value']))
            status = 'consistent' if delta <= Decimal(rule.tolerance_text) else 'difference'
            reason = 'Écart dans la tolérance' if status == 'consistent' else 'Écart à examiner'
    source = {'rule':rule.id,'pairs':[(p['version_id'],p['value'],p['unit']) for p in pair]}
    signature = hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
    outcome = {'consistent':'coherent', 'difference':'deviation', 'unavailable':'missing_data',
               'ambiguous':'ambiguous_sources', 'unit_mismatch':'incompatible_units'}.get(status, 'control_impossible')
    return {'rule_id':rule.id,'name':rule.name, 'field_key':rule.field_key,
            'left_doc_type':rule.left_doc_type, 'right_doc_type':rule.right_doc_type,
            'folders':[rule.left_folder,rule.right_folder], 'tolerance':rule.tolerance_text,
            'status':status,'outcome':outcome,'reason':reason,'pair':pair,'signature':signature,
            'delta':format(delta, 'f') if delta is not None else None}


def notify_quality_rechecks(db: Session, document: Document, version: DocumentVersion):
    """Signale uniquement les règles configurées qui utilisent le document modifié."""
    rules = db.scalars(select(CrossDocumentRule).where(CrossDocumentRule.active.is_(True))).all()
    for rule in rules:
        left = (rule.left_folder, rule.left_doc_type)
        right = (rule.right_folder, rule.right_doc_type)
        source = (document.folder.slug, document.doc_type)
        if source not in {left, right}:
            continue
        target_folder = rule.right_folder if source == left else rule.left_folder
        from .internal_notifications import emit_to_folder
        emit_to_folder(db, launch_id=document.folder.launch_id,
            source_folder=document.folder.slug, target_folder=target_folder,
            event_key=f'quality-recheck:{rule.id}:{version.id}', kind='quality_recheck',
            title='Cohérence documentaire à revérifier',
            message=f'{rule.name} doit être recalculée après le dépôt de la version {version.number}.',
            action='quality.review')


def _read_cells(path: Path):
    if path.stat().st_size > MAX_XLSX_BYTES:
        raise ValueError('Analyse limitée aux classeurs de 5 Mo maximum')
    with zipfile.ZipFile(path) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 24 * 1024 * 1024:
            raise ValueError('Classeur trop volumineux après décompression')
    # Les fichiers sont conservés sous un nom opaque, sans extension : fournir un flux.
    stream = path.open("rb")
    try:
        book = load_workbook(stream, read_only=True, data_only=False, keep_links=False)
    except Exception:
        stream.close()
        raise
    data = {}; seen = 0; formula_count=0
    try:
        for sheet in book:
            if sheet.max_row * sheet.max_column > MAX_CELLS * 10:
                raise ValueError('Classeur trop volumineux : inspection manuelle nécessaire')
            for row in sheet.iter_rows():
                for cell in row:
                    seen+=1
                    if seen > MAX_CELLS:
                        raise ValueError('Plus de 40 000 cellules : inspection non réalisée')
                    v = cell.value
                    if v is None: continue
                    is_formula = cell.data_type == 'f' or (isinstance(v,str) and v.startswith('='))
                    if is_formula: formula_count+=1
                    data[(sheet.title,cell.coordinate)] = (is_formula, str(v)[:400] if is_formula else str(v)[:120])
    finally:
        book.close()
        stream.close()
    return data,seen,formula_count


def analyze_workbook(path: Path, baseline: Path | None):
    """Static formula-integrity checks only; does not calculate or execute Excel."""
    try:
        current, scanned, formulas = _read_cells(path)
        before,_,_ = _read_cells(baseline) if baseline else ({},0,0)
    except Exception as ex:
        return {'status':'limited','scanned_cells':0,'formula_count':0,
                'findings':[{'type':'inspection_limit','level':'warning','sheet':'','cell':'',
                             'message':str(ex)[:200]}]}
    findings=[]
    def add(kind, level, sheet, coord, message, before=None, after=None):
        if len(findings) < MAX_FINDINGS:
            findings.append({'type':kind,'level':level,'sheet':sheet,'cell':coord,'message':message,
                             'before':before,'after':after})
    for (sheet,coord),(is_formula, value) in current.items():
        if is_formula and '#REF!' in value.upper():
            add('broken_reference','critical',sheet,coord,'Référence #REF! détectée dans la formule', after=value)
    if baseline:
        for (sheet,coord),(was_formula, prev) in before.items():
            if not was_formula:continue
            now=current.get((sheet,coord))
            if now is None or not now[0]:
                add('formula_removed','critical',sheet,coord,'Formule remplacée ou supprimée depuis la version précédente', prev, now[1] if now else None)
            elif now[1] != prev:
                add('formula_changed','warning',sheet,coord,'Formule modifiée : vérifier la logique du calcul', prev, now[1])
        status='reviewed'
    else:
        status='first_version'
    if len(findings)==MAX_FINDINGS:
        add('truncated','warning','','','Affichage plafonné à 200 constats')
    return {'status':status,'scanned_cells':scanned,'formula_count':formulas,'findings':findings}
