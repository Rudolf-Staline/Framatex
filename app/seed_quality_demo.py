"""Scénario de démonstration 0.4 (documents fictifs, jamais des données Framatex)."""
from __future__ import annotations
import hashlib
import io
import secrets
from sqlalchemy import select
from openpyxl import Workbook
from .core import Base,SessionLocal,engine
from .main import STORAGE
from .models import User,Launch,Document,DocumentVersion
from .quality_models import CrossDocumentRule,DocumentDatum,ExcelInspection
from .quality_routes import auto_inspect_excel


def workbook(formula:str|int):
    w=Workbook();s=w.active;s.title='Consommation';s['A1']=1500;s['A2']=1.9;s['B1']=formula
    b=io.BytesIO();w.save(b);return b.getvalue()


def add_doc(db,launch,user,title,kind,blob,filename):
    folder=next(f for f in launch.folders if f.slug=='jaune')
    doc=Document(folder_id=folder.id,title=title,doc_type=kind,created_by=user.id)
    db.add(doc);db.flush()
    data=bytes(blob);disk=secrets.token_hex(24);(STORAGE/disk).write_bytes(data)
    v=DocumentVersion(document_id=doc.id,number=1,original_name=filename,disk_name=disk,
       content_type='application/octet-stream',size=len(data),sha256=hashlib.sha256(data).hexdigest(),uploaded_by=user.id)
    db.add(v);db.flush();auto_inspect_excel(db,v,user.id)
    return doc,v


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user=db.scalar(select(User).where(User.email.is_not(None)))
        launch=db.scalar(select(Launch).where(Launch.name=='Chemises manches longues · pilote B'))
        if not user or not launch:
            raise SystemExit('Exécutez bootstrap_admin puis seed_demo avant seed_quality_demo.')
        rule_name='Quantité provisoire / définitive — démonstration'
        if db.scalar(select(CrossDocumentRule).where(CrossDocumentRule.name==rule_name)):
            print('Jeu de qualité 0.4 déjà présent');return
        pairs=[('Lancement provisoire',b'Lancement fictif : 1500 pieces\n', '1500'),
               ('Lancement définitif',b'Lancement fictif : 1450 pieces\n','1450')]
        for kind,data,value in pairs:
            doc,v=add_doc(db,launch,user,kind+' · exemple',kind,data,kind.replace(' ','_')+'.txt')
            db.add(DocumentDatum(document_version_id=v.id,field_key='quantite_lancement',
                                 value_text=value,unit='pièce',recorded_by=user.id))
        db.add(CrossDocumentRule(name=rule_name,field_key='quantite_lancement',
            left_doc_type='Lancement provisoire',right_doc_type='Lancement définitif',
            left_folder='jaune',right_folder='jaune',tolerance_text='0',created_by=user.id))
        doc,v1=add_doc(db,launch,user,'Feuille de besoins · Excel fictif','Feuille de besoins',
                       workbook('=A1*A2'),'besoins-v1.xlsx')
        blob=workbook(2850);disk=secrets.token_hex(24);(STORAGE/disk).write_bytes(blob)
        v2=DocumentVersion(document_id=doc.id,number=2,original_name='besoins-v2.xlsx',
            disk_name=disk,content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            size=len(blob),sha256=hashlib.sha256(blob).hexdigest(),uploaded_by=user.id)
        db.add(v2);db.flush();auto_inspect_excel(db,v2,user.id)
        db.commit()
        print('Démonstration 0.4 : écart 1500/1450 pièces et formule Excel remplacée en version 2.')

if __name__=='__main__':main()
