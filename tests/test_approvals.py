"""Contrats 0.13 : séquencement des rôles, version exacte et confidentialité des notifications."""
from __future__ import annotations
import os
import tempfile

os.environ['FRAMATEX_DATA_DIR'] = tempfile.mkdtemp(prefix='framat-approvals-test-')
os.environ['FRAMATEX_SECRET_KEY'] = 'approval-test-key-' * 5

from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core import SessionLocal, hash_password, Base, engine
from app.models import User, Role, RolePermission
from app.approval_models import ApprovalRun, ApprovalDecision, InternalNotification
from app.workflow_models import DocumentReview

H={'X-Framatex-Request':'1'}
PASSWORD='Approval-Password-2026!'


def setup_roles():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        admin_role=Role(name='Administrateur')
        tech_role=Role(name='Bureau technique')
        quality_role=Role(name='Contrôle qualité')
        rose_role=Role(name='Réception limitée')
        for role in (tech_role, quality_role):
            role.grants.extend([RolePermission(action='launch.read',folder_slug=None),
                                RolePermission(action='document.read',folder_slug='jaune'),
                                RolePermission(action='document.review',folder_slug='jaune')])
        rose_role.grants.extend([RolePermission(action='launch.read',folder_slug=None),
                                RolePermission(action='document.read',folder_slug='rose'),
                                RolePermission(action='document.review',folder_slug='rose')])
        roles=[admin_role,tech_role,quality_role,rose_role]
        users=[]
        for i,role in enumerate(roles):
            db.add(role)
            u=User(name=f'Personne {i}',email=f'approval{i}@local.test',password_hash=hash_password(PASSWORD))
            u.roles.append(role)
            db.add(u);users.append(u)
        db.commit()
        return [r.id for r in roles], [u.id for u in users]


def login(c,i):
    assert c.post('/api/auth/login',json={'email':f'approval{i}@local.test','password':PASSWORD},headers=H).status_code==200


def test_multi_stage_review_notifications_and_stale_versions():
    with TestClient(app) as c:
        roles, users = setup_roles()
        login(c,0)
        launch=c.post('/api/launches',json={'name':'Lancement de tests 0.13'},headers=H).json()
        lid=launch['id']
        created=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche de consommation',
             'doc_type':'Fiche d’emploi'},files={'file':('fiche.txt',b'Version 1, consommation 1.8','text/plain')},headers=H)
        assert created.status_code==201,created.text
        doc=created.json();did=doc['id'];oldv=doc['latest']['id']
        template=c.post('/api/admin/approval-templates',json={'name':'Circuit double contrôle',
             'folder_slug':'jaune','document_type':'Fiche d’emploi',
             'stages':[{'name':'Contrôle bureau technique','reviewer_role_id':roles[1]},
                       {'name':'Confirmation qualité','reviewer_role_id':roles[2]}]},headers=H)
        assert template.status_code==201,template.text
        assert c.post('/api/admin/approval-templates',json={'name':'Doublon','folder_slug':'jaune',
             'document_type':'Fiche d’emploi','stages':[{'name':'Validation','reviewer_role_id':roles[1]}]},headers=H).status_code==409
        assert c.post(f'/api/documents/{did}/reviews',json={'decision':'approved','comment':''},headers=H).status_code==409
        started=c.post(f'/api/documents/{did}/approval-runs',headers=H)
        assert started.status_code==201,started.text
        run=started.json();rid=run['id']
        assert run['current_position']==1 and run['status']=='pending'
        assert c.post(f'/api/documents/{did}/approval-runs',headers=H).status_code==409
        # Aucune approbation ne peut être donnée par l'auteur de la version.
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==403
        # Enchaînement obligatoire ; le rôle qualité ne valide pas la première étape.
        login(c,2)
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==403
        assert c.get('/api/notifications').json()['unread']==0
        login(c,3)
        assert c.get(f'/api/launches/{lid}/approval-overview').json()['items']==[]
        assert c.get('/api/notifications').json()['items']==[]
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==403
        login(c,1)
        inbox=c.get('/api/notifications').json()
        assert inbox['unread']==1 and len(inbox['items'])==1
        first=inbox['items'][0]
        assert c.post(f'/api/notifications/{first["id"]}/read',headers=H).json()['read_at']
        assert c.get('/api/notifications').json()['unread']==0
        decided=c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved','comment':'Fiche examinée'},headers=H)
        assert decided.status_code==200,decided.text
        assert decided.json()['current_position']==2
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==403
        login(c,2)
        assert c.get('/api/notifications').json()['unread']==1
        final=c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved','comment':'Conforme'},headers=H)
        assert final.status_code==200,final.text
        assert final.json()['status']=='approved'
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==409
        with SessionLocal() as db:
            rows=db.scalars(select(DocumentReview).where(DocumentReview.document_version_id==oldv)).all()
            assert len(rows)==1 and rows[0].decision=='approved'
            assert len(db.scalars(select(ApprovalDecision).where(ApprovalDecision.run_id==rid)).all())==2
        login(c,0)
        new=c.post(f'/api/documents/{did}/versions',files={'file':('fiche2.txt',b'Version 2, consommation 1.9','text/plain')},headers=H)
        assert new.status_code==201,new.text
        overview=c.get(f'/api/launches/{lid}/approval-overview').json()['items'][0]
        assert overview['can_start'] and overview['run'] is None
        assert overview['previous'][0]['status']=='stale'
        login(c,1)
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==409
        # Retrait de l'accès = disparition immédiate de l'ancienne notification.
        with SessionLocal() as db:
            role=db.get(Role,roles[1])
            for g in list(role.grants):
                if g.action=='document.read':db.delete(g)
            db.commit()
        assert c.get('/api/notifications').json()['items']==[]
        assert c.post(f'/api/notifications/{first["id"]}/read',headers=H).status_code==404


def test_rejections_notes_and_no_automatic_restarts():
    with TestClient(app) as c:
        roles,users=setup_roles()
        login(c,0)
        lid=c.post('/api/launches',json={'name':'Lancement test de refus'},headers=H).json()['id']
        did=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Spécification source',
             'doc_type':'Fiche prix'},files={'file':('source.txt',b'prix test','text/plain')},headers=H).json()['id']
        template=c.post('/api/admin/approval-templates',json={'name':'Circuit prix',
            'folder_slug':'jaune','document_type':'Fiche prix',
            'stages':[{'name':'Contrôle technique','reviewer_role_id':roles[1]}]},headers=H)
        assert template.status_code==201,template.text
        run=c.post(f'/api/documents/{did}/approval-runs',headers=H).json()
        login(c,1)
        assert c.post(f'/api/approval-runs/{run["id"]}/decisions',json={'decision':'rejected','comment':'court'},headers=H).status_code==422
        result=c.post(f'/api/approval-runs/{run["id"]}/decisions',json={'decision':'changes_requested',
            'comment':'La fiche de prix doit être revue.'},headers=H)
        assert result.status_code==200,result.text
        assert result.json()['status']=='changes_requested'
        assert c.post(f'/api/approval-runs/{run["id"]}/decisions',json={'decision':'approved'},headers=H).status_code==409
        login(c,0)
        assert c.post(f'/api/documents/{did}/approval-runs',headers=H).status_code==409
        # Un nouveau dépôt est requis pour un nouveau circuit.
        assert c.post(f'/api/documents/{did}/versions',files={'file':('v2.txt',b'prix corrige','text/plain')},headers=H).status_code==201
        assert c.post(f'/api/documents/{did}/approval-runs',headers=H).status_code==201


def test_header_and_unauthenticated_notifications():
    with TestClient(app) as c:
        assert c.get('/api/notifications').status_code==401
        assert c.post('/api/notifications/nonexistent/read').status_code==403


def test_targeted_cross_service_impact_notification():
    """L'alerte source Jaune -> cible Rose ne doit pas fuiter au rôle Rose seul."""
    with TestClient(app) as c:
        roles, users = setup_roles()
        with SessionLocal() as db:
            role=db.get(Role,roles[2])
            role.grants.extend([RolePermission(action='document.read',folder_slug='rose'),
                                RolePermission(action='impact.review',folder_slug='rose')])
            db.commit()
        login(c,0)
        lid=c.post('/api/launches',json={'name':'Lancement de propagation'},headers=H).json()['id']
        doc=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche modifiée',
            'doc_type':'Fiche technique'},files={'file':('fiche.txt',b'premier calcul','text/plain')},headers=H).json()
        rule=c.post('/api/admin/impact-rules',json={'name':'Prévenir réception',
            'source_kind':'document','source_key':'Fiche technique','source_folder':'jaune',
            'target_folder':'rose','instruction':'Vérifier la réception après nouvelle version de la fiche'},headers=H)
        assert rule.status_code==201,rule.text
        new=c.post(f'/api/documents/{doc["id"]}/versions',files={'file':('revision.txt',b'nouveau calcul','text/plain')},headers=H)
        assert new.status_code==201,new.text
        login(c,2)
        allowed=c.get('/api/notifications').json()
        assert any(n['kind']=='impact' for n in allowed['items'])
        login(c,3)
        assert c.get('/api/notifications').json()['items']==[]
