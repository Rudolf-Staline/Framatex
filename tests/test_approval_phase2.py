from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_approvals import app,setup_roles,login,H
from app.core import SessionLocal,utcnow
from app.partner_phase2_models import ApprovalStageAssignment


def test_delegation_is_temporary_scoped_revocable_and_preserves_separation():
    with TestClient(app) as c:
        roles,users=setup_roles();login(c,0)
        lid=c.post('/api/launches',json={'name':'Délégation contrôlée'},headers=H).json()['id']
        did=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche', 'doc_type':'Fiche'},files={'file':('test.txt',b'Exemple','text/plain')},headers=H).json()['id']
        t=c.post('/api/admin/approval-templates',json={'name':'Circuit délégué','folder_slug':'jaune','document_type':'Fiche','stages':[{'name':'Technique','reviewer_role_id':roles[1],'due_days':2},{'name':'Qualité','reviewer_role_id':roles[2],'due_days':3}]},headers=H)
        assert t.status_code==201,t.text
        run=c.post(f'/api/documents/{did}/approval-runs',headers=H).json();rid=run['id']
        assert run['stages'][0]['due_at'] and run['stages'][1]['due_at'] is None
        path=f'/api/approval-runs/{rid}/delegation'
        data={'delegate_id':users[2],'expires_at':(utcnow()+timedelta(days=2)).isoformat(),'reason':'Absence du valideur technique'}
        assert c.put(path,json={**data,'delegate_id':users[0]},headers=H).status_code==422
        assert c.put(path,json={**data,'delegate_id':users[3]},headers=H).status_code==422
        assert c.put(path,json={**data,'expires_at':(utcnow()-timedelta(days=1)).isoformat()},headers=H).status_code==422
        assert c.put(path,json=data,headers=H).status_code==200
        login(c,2)
        assert c.put(path,json=data,headers=H).status_code==403
        overview=lambda:c.get(f'/api/launches/{lid}/approval-overview').json()['items'][0]['run']
        assert overview()['can_decide']
        with SessionLocal() as db:
            row=db.scalar(select(ApprovalStageAssignment).where(ApprovalStageAssignment.run_id==rid));row.expires_at=utcnow()-timedelta(seconds=1);db.commit()
        assert not overview()['can_decide']
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==403
        login(c,0);assert c.put(path,json=data,headers=H).status_code==200
        assert c.put(path,json={'reason':'Retour du valideur principal'},headers=H).status_code==200
        login(c,2);assert not overview()['can_decide']
        login(c,0);assert c.put(path,json=data,headers=H).status_code==200
        c.put(f'/api/launches/{lid}/access',json={'restricted':True},headers=H)
        login(c,2);assert c.get(f'/api/launches/{lid}/approval-overview').status_code==404
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==404
        login(c,0);c.put(f'/api/launches/{lid}/access',json={'restricted':False},headers=H)
        login(c,2)
        decided=c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H)
        assert decided.status_code==200,decided.text
        assert decided.json()['stages'][1]['due_at']
        assert not decided.json()['can_decide']  # same person cannot approve both stages
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==403
        login(c,0)
        assert c.put(path,json=data,headers=H).status_code==422  # prior reviewer excluded even for a delegation
