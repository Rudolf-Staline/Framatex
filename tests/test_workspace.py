"""Contrats 0.9 : priorisation explicable, filtrage par rubrique, aide sans fuite de données."""
from __future__ import annotations
import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

os.environ["FRAMATEX_DATA_DIR"] = tempfile.mkdtemp(prefix="framat-workspace-test-")
os.environ["FRAMATEX_SECRET_KEY"] = "workspace-test-strong-secret-" * 3

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core import SessionLocal, hash_password
from app.main import app
from app.models import Role, RolePermission, User, Document, DocumentVersion
from app.spec_models import ClientRequirement, SpecificationAmbiguity
from app.mail_models import EmailCommitment, ArchivedEmail
from app.completeness_models import CompletenessProfile, RequirementRule, LaunchCompleteness

HEADERS={"X-Framatex-Request":"1"}


def test_workspace_priorities_and_access():
    with TestClient(app) as c:
        with SessionLocal() as db:
            admin_role=Role(name="Administrateur")
            rose_role=Role(name="Réception")
            rose_role.grants.extend([RolePermission(action="launch.read",folder_slug=None),
                                    RolePermission(action="document.read",folder_slug="rose")])
            db.add_all([admin_role,rose_role]);db.flush()
            admin=User(name="Admin",email="workspace-admin@local.test",password_hash=hash_password("Password_WorkspaceAdmin_2026"))
            rose=User(name="Utilisateur Rose",email="workspace-rose@local.test",password_hash=hash_password("Password_WorkspaceRose_2026"))
            admin.roles.append(admin_role);rose.roles.append(rose_role);db.add_all([admin,rose]);db.commit()
        assert c.get('/api/workspace/priorities').status_code==401
        assert c.post('/api/auth/login',json={"email":"workspace-admin@local.test","password":"Password_WorkspaceAdmin_2026"},headers=HEADERS).status_code==200
        launch=c.post('/api/launches',json={'name':'Lot test pour priorités'},headers=HEADERS).json()
        launch_id=launch['id']
        v=c.post(f'/api/launches/{launch_id}/documents',data={'folder':'jaune','title':'Techpack','doc_type':'Dossier technique client'},files={'file':('tech.txt',b'Tissu exige bleu','text/plain')},headers=HEADERS)
        assert v.status_code==201,v.text
        source=v.json()['latest']['id']
        with SessionLocal() as db:
            from app.models import Launch, Folder
            profile=CompletenessProfile(name='Profil priorites',created_by=admin.id)
            db.add(profile);db.flush()
            rule=RequirementRule(profile_id=profile.id,title='Bon de livraison',folder_slug='rose',document_type='Bon de livraison',due_phase='preparation',requires_validation=False)
            db.add(rule)
            db.add(LaunchCompleteness(launch_id=launch_id,profile_id=profile.id,phase='preparation'))
            db.add(ClientRequirement(launch_id=launch_id,source_version_id=source,title='Couleur tissu',category='Couleur',description='Tissu doit etre bleu',source_excerpt='Tissu exige bleu',created_by=admin.id))
            db.add(SpecificationAmbiguity(launch_id=launch_id,source_version_id=source,excerpt='Tissu doit etre bleu',kind='indication',question='Quel bleu exactement ?',confirmed_by=admin.id))
            rose_folder=db.scalar(select(Folder).where(Folder.launch_id==launch_id,Folder.slug=='rose'))
            mail_doc=Document(folder_id=rose_folder.id,title='Mail',doc_type='Courriel',created_by=admin.id);db.add(mail_doc);db.flush()
            mail_v=DocumentVersion(document_id=mail_doc.id,number=1,original_name='mail.eml',disk_name='mail-workspace-test.eml',content_type='message/rfc822',size=1,sha256='0'*64,uploaded_by=admin.id);db.add(mail_v);db.flush()
            mail=ArchivedEmail(launch_id=launch_id,document_version_id=mail_v.id,archived_by=admin.id,subject='Confirmation',sender='fournisseur@test',recipients='test@test',message_id='workspace-test');db.add(mail);db.flush()
            yesterday=(datetime.now(ZoneInfo('Africa/Casablanca')).date()-timedelta(days=1)).isoformat()
            db.add(EmailCommitment(launch_id=launch_id,email_id=mail.id,description='Envoyer une confirmation de livraison',responsible='Fournisseur',due_date=yesterday,status='pending',confirmed_by=admin.id))
            db.commit()
        overview=c.get('/api/workspace/priorities')
        assert overview.status_code==200,overview.text
        items=overview.json()['items']
        assert {x['kind'] for x in items}>={'missing','requirement','ambiguity','commitment'}
        assert items[0]['kind']=='commitment' and items[0]['priority']=='urgent'
        assert overview.json()['counts']['urgent']==1
        assert overview.json()['actionable_count']==len(items)
        assert all(x['can_act'] and x['next_step'] for x in items)
        assert all(x['action']=='open_launch' and x['launch_id']==launch_id for x in items)
        assert all(not x['title'].startswith('Stock') for x in items)
        # Comptage et métadonnées strictement filtrés, même sans droit à traiter les pièces.
        assert c.post('/api/auth/login',json={'email':'workspace-rose@local.test','password':'Password_WorkspaceRose_2026'},headers=HEADERS).status_code==200
        limited=c.get('/api/workspace/priorities')
        assert limited.status_code==200,limited.text
        names={x['kind'] for x in limited.json()['items']}
        assert names=={'missing','commitment'},names
        assert limited.json()['actionable_count']==0
        assert limited.json()['followup_count']==limited.json()['total']
        assert all(x['can_act'] is False for x in limited.json()['items'])
        assert 'Couleur tissu' not in str(limited.json())
        # L'assistant ne suggère jamais d'ouvrir un sous-dossier non autorisé.
        denied=c.post('/api/assistant/guide',json={'question':'Ou deposer une facture ?', 'launch_id':launch_id},headers=HEADERS)
        assert denied.status_code==200
        assert denied.json()['destination'] is None
        email=c.post('/api/assistant/guide',json={'question':'Ou trouver les engagements email ?', 'launch_id':launch_id},headers=HEADERS)
        assert email.status_code==200 and email.json()['area']=='mail'
        assert email.json()['launch_id']==launch_id
        assert c.post('/api/assistant/guide',json={'question':'administration et roles'},headers=HEADERS).json()['destination'] is None
        assert c.post('/api/assistant/guide',json={'question':'Bonjour'},headers=HEADERS).json()['destination'] is None
        assert c.post('/api/assistant/guide',json={'question':'bonjour','launch_id':'abc'},headers=HEADERS).status_code==404
        assert c.post('/api/assistant/guide',json={'question':'a'},headers=HEADERS).status_code==422
        # Les appels POST de navigation restent protégés par l'en-tête de requête.
        assert c.post('/api/assistant/guide',json={'question':'mes actions'}).status_code==403
