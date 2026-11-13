"""API 0.4 : cohérence inter-documents et inspection de l'intégrité des formules Excel."""
from __future__ import annotations
from .order_documents import folder_ids
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db, utcnow
from .models import Document, DocumentVersion, Folder, User
from .quality_models import DocumentDatum, CrossDocumentRule, QualityDecision, ExcelInspection
from .quality import comparison, analyze_workbook, QUALITY_FIELDS, TEXT_FIELDS
from .access import must, permitted, admin_only
from . import document_storage
from .order_documents import get_doc
from .launches import get_launch, SLUGS
from .audit import audit

router=APIRouter()


class DatumIn(BaseModel):
    field_key: str
    value: str = Field(min_length=1,max_length=50)
    unit: str = Field(min_length=1,max_length=30)


class RuleIn(BaseModel):
    name: str = Field(min_length=3,max_length=140)
    field_key: str
    left_doc_type: str = Field(min_length=2,max_length=100)
    right_doc_type: str = Field(min_length=2,max_length=100)
    left_folder: str
    right_folder: str
    tolerance: str = Field(default='0',max_length=50)


class QualityDecisionIn(BaseModel):
    signature: str = Field(min_length=64,max_length=64)
    decision: Literal['justified','to_correct']
    note: str = Field(min_length=12,max_length=1800)


def normalized_decimal(raw:str, *, tolerance=False):
    try:
        v=Decimal(raw.strip().replace(',','.'))
    except (InvalidOperation,ValueError):
        raise HTTPException(422,'Nombre décimal incorrect')
    if not v.is_finite() or v.as_tuple().exponent < -12 or v.as_tuple().exponent > 15 or v.copy_abs()>Decimal('1e15') or (tolerance and v<0):
        raise HTTPException(422,'Valeur numérique non autorisée')
    return format(v,'f')


def normalized_datum(field,value,unit):
    if not value.strip() or len(value)>50 or not unit.strip():raise HTTPException(422,'Valeur (50 caractères maximum) et unité requises')
    if field in TEXT_FIELDS:
        if unit!='référence':raise HTTPException(422,'Une référence doit utiliser l’unité « référence »')
        return value.strip()
    return normalized_decimal(value)


def version_doc(db,version_id):
    version=db.get(DocumentVersion,version_id)
    if not version: raise HTTPException(404,'Version introuvable')
    doc=db.get(Document,version.document_id)
    return version,doc


def rule_out(r):
    return {'id':r.id,'name':r.name,'field_key':r.field_key,'left_doc_type':r.left_doc_type,
            'right_doc_type':r.right_doc_type,'left_folder':r.left_folder,'right_folder':r.right_folder,
            'tolerance':r.tolerance_text,'active':r.active}


@router.get('/api/quality/fields')
def fields(user:User=Depends(get_current_user)):
    must(user,'launch.read')
    return [{'key':k,'label':label,'suggested_unit':unit,'type':'text' if k in TEXT_FIELDS else 'decimal'} for k,(label,unit) in QUALITY_FIELDS.items()]


@router.post('/api/document-versions/{version_id}/data',status_code=201)
def save_datum(version_id:str,payload:DatumIn,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    version,doc=version_doc(db,version_id)
    must(user,'launch.read')
    must(user,'document.read',doc.folder.slug)
    must(user,'document.write',doc.folder.slug)
    if payload.field_key not in QUALITY_FIELDS: raise HTTPException(422,'Champ métier inconnu')
    if version.number != max(v.number for v in doc.versions):
        raise HTTPException(409,'La valeur doit être saisie sur la version courante')
    if db.scalar(select(DocumentDatum).where(DocumentDatum.document_version_id==version.id,
                                           DocumentDatum.field_key==payload.field_key)):
        raise HTTPException(409,'Valeur déjà consignée : utiliser une nouvelle version documentaire')
    num=normalized_datum(payload.field_key,payload.value,payload.unit)
    item=DocumentDatum(document_version_id=version.id, field_key=payload.field_key,
                       value_text=num,unit=payload.unit.strip(),recorded_by=user.id)
    db.add(item);db.flush()
    audit(db,user,'quality.datum.record','document_version',version.id,
          {'field_key':payload.field_key,'datum':item.id})
    db.commit()
    return {'id':item.id,'field_key':item.field_key,'value':item.value_text,'unit':item.unit}


@router.get('/api/launches/{launch_id}/quality')
def quality_report(launch_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');get_launch(db,launch_id)
    rules=db.scalars(select(CrossDocumentRule).where(CrossDocumentRule.active.is_(True))
                     .order_by(CrossDocumentRule.name)).all()
    rows=[]
    for r in rules:
        if not (permitted(user,'document.read',r.left_folder) and permitted(user,'document.read',r.right_folder)):
            continue
        item=comparison(db,launch_id,r)
        if item['status']=='difference':
            decision=db.scalar(select(QualityDecision).where(QualityDecision.launch_id==launch_id,
                QualityDecision.rule_id==r.id,QualityDecision.evidence_signature==item['signature'])
                .order_by(QualityDecision.decided_at.desc(),QualityDecision.id.desc()).limit(1))
            if decision:
                item['decision']={'status':decision.decision,'note':decision.note,
                                  'date':decision.decided_at.isoformat()}
        item['can_review']=permitted(user,'quality.review',r.left_folder) and permitted(user,'quality.review',r.right_folder)
        rows.append(item)
    return {'rows':rows,'counts':{name:sum(x['status']==name for x in rows) for name in
            ('consistent','difference','unavailable','ambiguous','unit_mismatch')}}


@router.post('/api/launches/{launch_id}/quality/{rule_id}/decisions',status_code=201)
def decide_quality(launch_id:str,rule_id:str,payload:QualityDecisionIn,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');get_launch(db,launch_id)
    rule=db.get(CrossDocumentRule,rule_id)
    if not rule or not rule.active: raise HTTPException(404,'Règle inactive ou inexistante')
    for folder in (rule.left_folder,rule.right_folder):
        must(user,'document.read',folder);must(user,'quality.review',folder)
    item=comparison(db,launch_id,rule)
    if item['status']!='difference' or payload.signature!=item['signature']:
        raise HTTPException(409,'Constat changé : actualisez et recommencez')
    dec=QualityDecision(launch_id=launch_id,rule_id=rule_id,evidence_signature=item['signature'],
                        decision=payload.decision,note=payload.note.strip(),decided_by=user.id)
    db.add(dec);db.flush()
    audit(db,user,'quality.decision','quality_rule',rule_id,{'decision':dec.decision,'launch':launch_id})
    db.commit()
    return {'id':dec.id,'decision':dec.decision,'note':dec.note}


@router.get('/api/admin/quality-rules')
def get_rules(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only(user)
    return [rule_out(x) for x in db.scalars(select(CrossDocumentRule).order_by(CrossDocumentRule.created_at)).all()]


@router.post('/api/admin/quality-rules',status_code=201)
def add_rule(payload:RuleIn,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only(user)
    if payload.field_key not in QUALITY_FIELDS or payload.left_folder not in SLUGS or payload.right_folder not in SLUGS:
        raise HTTPException(422,'Configuration de règle incorrecte')
    if payload.left_doc_type.strip()==payload.right_doc_type.strip() and payload.left_folder==payload.right_folder:
        raise HTTPException(422,'Deux sources documentaires distinctes sont nécessaires')
    if payload.field_key in TEXT_FIELDS and Decimal(normalized_decimal(payload.tolerance,tolerance=True))!=0:
        raise HTTPException(422,'Les références utilisent une comparaison exacte, sans tolérance numérique')
    item=CrossDocumentRule(name=payload.name.strip(),field_key=payload.field_key,
        left_doc_type=payload.left_doc_type.strip(),right_doc_type=payload.right_doc_type.strip(),
        left_folder=payload.left_folder,right_folder=payload.right_folder,
        tolerance_text=normalized_decimal(payload.tolerance,tolerance=True),created_by=user.id)
    db.add(item);db.flush();audit(db,user,'quality.rule.create','quality_rule',item.id)
    db.commit()
    return rule_out(item)


@router.patch('/api/admin/quality-rules/{rule_id}')
def toggle_rule(rule_id:str,payload:dict,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only(user)
    if set(payload)!={'active'} or not isinstance(payload['active'],bool): raise HTTPException(422,'Statut invalide')
    item=db.get(CrossDocumentRule,rule_id)
    if not item:raise HTTPException(404,'Règle introuvable')
    item.active=payload['active'];audit(db,user,'quality.rule.toggle','quality_rule',item.id,{'active':item.active})
    db.commit();return rule_out(item)


def inspection_out(db:Session,item:ExcelInspection):
    v=db.get(DocumentVersion,item.document_version_id)
    return {'id':item.id,'version_id':v.id,'version':v.number,'status':item.status,
            'scanned_cells':item.scanned_cells,'formula_count':item.formula_count,
            'findings':json.loads(item.findings_json),'inspected_at':item.inspected_at.isoformat()}


def auto_inspect_excel(db:Session,version:DocumentVersion, user_id:str):
    """Called during upload. Store first-version baseline and subsequent static findings."""
    if Path(version.original_name).suffix.lower()!='.xlsx': return
    doc=db.get(Document,version.document_id)
    prev=next((v for v in doc.versions if v.number==version.number-1),None)
    baseline=prev if prev and Path(prev.original_name).suffix.lower()=='.xlsx' else None
    from .partner_phase2_models import DocumentExcelPolicy
    policy=db.get(DocumentExcelPolicy,doc.id)
    result=analyze_workbook(document_storage.STORAGE/version.disk_name,document_storage.STORAGE/baseline.disk_name if baseline else None,json.loads(policy.cells_json) if policy else [])
    item=ExcelInspection(document_version_id=version.id,baseline_version_id=baseline.id if baseline else None,
         status=result['status'],scanned_cells=result['scanned_cells'],formula_count=result['formula_count'],
         findings_json=json.dumps(result['findings'],ensure_ascii=False),inspected_by=user_id)
    db.add(item)


@router.get('/api/launches/{launch_id}/excel-inspections')
def list_excel_inspections(launch_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    must(user,'launch.read');get_launch(db,launch_id)
    docs=db.scalars(select(Document).join(Folder).where(Folder.id.in_(folder_ids(db, launch_id)))).all()
    rows=[]
    for doc in docs:
        if not permitted(user,'document.read',doc.folder.slug):continue
        for v in doc.versions:
            if Path(v.original_name).suffix.lower()!='.xlsx': continue
            inspection=db.scalar(select(ExcelInspection).where(ExcelInspection.document_version_id==v.id))
            rows.append({'document_id':doc.id,'document_title':doc.title,'folder':doc.folder.slug,
                         'version_id':v.id,'version':v.number,
                         'inspection':inspection_out(db,inspection) if inspection else None})
    return sorted(rows,key=lambda x:(x['document_title'],x['version']))


class CriticalCell(BaseModel):
    sheet: str=Field(min_length=1,max_length=31)
    cell: str=Field(pattern=r'^[A-Z]{1,3}[1-9][0-9]{0,6}$')
class ExcelPolicyInput(BaseModel):
    cells: list[CriticalCell]=Field(max_length=200)

@router.put('/api/documents/{doc_id}/excel-policy')
def configure_excel(doc_id:str,payload:ExcelPolicyInput,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    from .partner_phase2_models import DocumentExcelPolicy
    doc=get_doc(db,doc_id);must(user,'document.read',doc.folder.slug);must(user,'document.write',doc.folder.slug)
    row=db.get(DocumentExcelPolicy,doc_id)
    if not row:row=DocumentExcelPolicy(document_id=doc_id,configured_by=user.id);db.add(row)
    row.cells_json=json.dumps([cell.model_dump() for cell in payload.cells]);row.configured_by=user.id
    audit(db,user,'excel.policy','document',doc_id,payload.model_dump());db.commit()
    return {'cells':payload.cells,'applies_to':'future_inspections'}

@router.get('/api/documents/{doc_id}/excel-policy')
def excel_policy(doc_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    from .partner_phase2_models import DocumentExcelPolicy
    doc=get_doc(db,doc_id);must(user,'document.read',doc.folder.slug)
    row=db.get(DocumentExcelPolicy,doc_id)
    return {'cells':json.loads(row.cells_json) if row else []}
