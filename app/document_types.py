"""Stable document type IDs; conservative aliases, original labels preserved."""
from datetime import datetime
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, ForeignKey, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from .core import Base, utcnow, get_db, get_current_user
from .models import Document
from .access import must
from .order_documents import document_accessible
from .audit import audit

router=APIRouter(tags=['Types documentaires'])
# Catalogue technique initial : catégories déjà présentes dans les exemples,
# sans prétendre définir les obligations officielles de l'entreprise.
CATALOGUE = [
 {'id':'employment-sheet','label':'Fiche d’emploi','folders':['jaune'],'aliases':["Fiche d'emploi"]},
 {'id':'price-sheet','label':'Fiche de prix','folders':['jaune'],'aliases':[]},
 {'id':'technical-file','label':'Dossier technique','folders':['jaune'],'aliases':[]},
 {'id':'receipt-note','label':'Bon de réception','folders':['rose'],'aliases':[]},
 {'id':'customs-declaration','label':'Déclaration douanière','folders':['bleu'],'aliases':[]},
 {'id':'client-technical-file','label':'Dossier technique client','folders':['jaune'],'aliases':[]},
 {'id':'technical-sheet','label':'Fiche technique','folders':['jaune'],'aliases':[]},
 {'id':'provisional-launch','label':'Lancement provisoire','folders':['jaune'],'aliases':[]},
 {'id':'final-launch','label':'Lancement définitif','folders':['jaune'],'aliases':[]},
 {'id':'delivery-note','label':'Bon de livraison','folders':['rose'],'aliases':[]},
 {'id':'certificate','label':'Certificat','folders':['jaune','rose'],'aliases':[]},
 {'id':'customs-document','label':'Pièce douanière','folders':['bleu'],'aliases':[]},
 {'id':'invoice','label':'Facture','folders':['vert'],'aliases':[]},
 {'id':'email','label':'Email','folders':['rose'],'aliases':['Courriel']},
 {'id':'unclassified','label':'À classer','folders':['jaune','rose','bleu','vert'],'aliases':['Autre','A classer']},
]

def normalize(value):
    return unicodedata.normalize('NFKC',str(value)).replace('’',"'").strip().casefold()

def resolve_type(value):
    candidates=[t for t in CATALOGUE if normalize(value) in {normalize(v) for v in [t['id'],t['label'],*t['aliases']]}]
    return candidates[0] if len(candidates)==1 else None

def equivalent_types(value):
    row=resolve_type(value)
    return [row['id'],row['label'],*row['aliases']] if row else [value]

class DocumentTypeAssignment(Base):
    __tablename__='document_type_assignments'
    document_id: Mapped[str]=mapped_column(ForeignKey('documents.id'),primary_key=True)
    type_id: Mapped[str]=mapped_column(String(80))
    original_label: Mapped[str]=mapped_column(String(100))
    assigned_by: Mapped[str | None]=mapped_column(ForeignKey('users.id'),nullable=True)
    assigned_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)


def register_type(db, doc):
    assignment=db.get(DocumentTypeAssignment,doc.id)
    if assignment:return assignment
    row=resolve_type(doc.doc_type)
    # A known label in the wrong section is retained unclassified.
    type_id=row['id'] if row and doc.folder.slug in row['folders'] else 'unclassified'
    assignment=DocumentTypeAssignment(document_id=doc.id,type_id=type_id,original_label=doc.doc_type)
    db.add(assignment)
    return assignment


def type_out(db,doc):
    assignment=db.get(DocumentTypeAssignment,doc.id)
    row=resolve_type(assignment.type_id if assignment else doc.doc_type)
    if not row or doc.folder.slug not in row['folders']:row=resolve_type('unclassified')
    return {'id':row['id'],'label':row['label'],'original_label':assignment.original_label if assignment else doc.doc_type,
            'needs_classification':row['id']=='unclassified'}


def matches_type(db,doc,required):
    return matches_classification(doc,db.get(DocumentTypeAssignment,doc.id),required)


def matches_classification(doc,assignment,required):
    """Pure matcher for batch-loaded classification, without per-document SQL."""
    wanted=resolve_type(required)
    if assignment and wanted:return assignment.type_id==wanted['id']
    actual=resolve_type(doc.doc_type)
    return actual['id']==wanted['id'] if wanted and actual else doc.doc_type==required

@router.get('/api/document-types')
def document_types(folder:str|None=Query(None,pattern='^(jaune|rose|bleu|vert)$'),user=Depends(get_current_user)):
    must(user,'launch.read')
    return {'items':[t for t in CATALOGUE if not folder or folder in t['folders']],
            'provisional':True,'notice':'Référentiel évolutif, sans définition implicite des exigences métier.'}

class ClassificationInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    type_id:str=Field(min_length=1,max_length=80)
    expected_label:str=Field(max_length=100)

@router.patch('/api/documents/{doc_id}/classification')
def classify(doc_id:str,payload:ClassificationInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    doc=db.get(Document,doc_id)
    if not doc or not document_accessible(db,user,doc):raise HTTPException(404,'Document introuvable')
    must(user,'document.read',doc.folder.slug);must(user,'document.write',doc.folder.slug)
    from sqlalchemy import update
    db.execute(update(Document).where(Document.id==doc_id).values(id=Document.id));db.refresh(doc)
    if doc.doc_type!=payload.expected_label:raise HTTPException(409,'Classement modifié. Actualisez le document.')
    row=resolve_type(payload.type_id)
    if not row or row['id']!=payload.type_id or doc.folder.slug not in row['folders']:
        raise HTTPException(422,'Type documentaire incompatible avec cette rubrique')
    assignment=register_type(db,doc);assignment.type_id=row['id'];assignment.assigned_by=user.id;assignment.assigned_at=utcnow()
    # Existing rule equality remains compatible; the original is retained in assignment and audit.
    previous=doc.doc_type;doc.doc_type=row['label']
    audit(db,user,'document.classify','document',doc.id,{'previous':previous,'type_id':row['id']})
    db.commit();return {'document_id':doc.id,'doc_type':doc.doc_type,'classification':type_out(db,doc)}


def migrate_known_labels(conn):
    """Add metadata only for unique aliases. Never merge documents or rewrite labels."""
    from .models import Folder
    table=DocumentTypeAssignment.__table__
    for doc_id,label,folder in conn.execute(select(Document.id,Document.doc_type,Folder.slug).join(Folder)):
        if conn.scalar(select(table.c.document_id).where(table.c.document_id==doc_id)):continue
        row=resolve_type(label)
        type_id=row['id'] if row and folder in row['folders'] else 'unclassified'
        conn.execute(table.insert().values(document_id=doc_id,type_id=type_id,original_label=label,assigned_at=utcnow()))
