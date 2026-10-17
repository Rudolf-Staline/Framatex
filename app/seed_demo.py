"""Données de démonstration entièrement fictives (ne jamais utiliser en production)."""
from pathlib import Path
import hashlib
from sqlalchemy import select
from .core import Base, SessionLocal, engine
from .main import FOLDERS, STORAGE
from .models import User, Launch, Folder, Document, DocumentVersion

ROWS = [
    ("Vestes coton · pilote A", "Client fictif A", "CMD-DEMO-001", None, "À compléter"),
    ("Chemises manches longues · pilote B", "Client fictif B", "CMD-DEMO-002", "ORLI-DEMO-082", "En cours"),
    ("Pantalons toile · pilote C", "Client fictif C", "CMD-DEMO-003", "ORLI-DEMO-083", "En validation"),
]

def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = db.scalar(select(User).join(User.roles).where(User.email.is_not(None)))
        if not user:
            raise SystemExit("Créez d'abord l'administrateur via python -m app.bootstrap_admin")
        if db.scalar(select(Launch).where(Launch.name == ROWS[0][0])):
            print("Jeu de démonstration déjà présent")
            return
        for i,(name, client, order, orli, status) in enumerate(ROWS):
            launch=Launch(name=name, client_name=client, order_ref=order, orli_ref=orli, status=status, created_by=user.id)
            db.add(launch);db.flush()
            folders={}
            for slug,label in FOLDERS:
                folder=Folder(launch_id=launch.id, slug=slug, label=label)
                db.add(folder);db.flush();folders[slug]=folder
            if i==1:
                doc=Document(folder_id=folders['jaune'].id,title='Fiche d’emploi — échantillon',doc_type='Fiche d’emploi',created_by=user.id)
                db.add(doc);db.flush()
                for n,consumption in enumerate(['1,8','1,9'],start=1):
                    contents=f"DEMONSTRATION (donnees entierement fictives)\nConsommation tissu : {consumption} m par piece\n".encode()
                    disk_name=f'demo_{doc.id}_{n}'
                    (STORAGE / disk_name).write_bytes(contents)
                    db.add(DocumentVersion(document_id=doc.id,number=n,original_name=f'fiche-demo-v{n}.txt',disk_name=disk_name,content_type='text/plain',size=len(contents),sha256=hashlib.sha256(contents).hexdigest(),uploaded_by=user.id))
        db.commit()
        print('3 lancements fictifs créés, avec un document comportant deux versions.')
if __name__=='__main__':main()
