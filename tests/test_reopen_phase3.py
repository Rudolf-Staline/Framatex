from fastapi.testclient import TestClient
from sqlalchemy import select
from test_approvals import app,setup_roles,login,H
from app.core import SessionLocal
from app.approval_models import ApprovalDecision,ApprovalRun
from app.sharing_routes import is_approved
from app.models import DocumentVersion


def test_reopen_preserves_decisions_invalidates_approval_and_rechecks_version():
    with TestClient(app) as c:
        roles,_=setup_roles();login(c,0)
        lid=c.post('/api/launches',json={'name':'Réouverture'},headers=H).json()['id']
        doc=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche','doc_type':'Fiche technique'},files={'file':('fiche.txt',b'synthese','text/plain')},headers=H).json()
        template=c.post('/api/admin/approval-templates',json={'name':'Contrôle technique','folder_slug':'jaune','document_type':'Fiche technique','stages':[{'name':'Contrôle','reviewer_role_id':roles[1]}]},headers=H)
        assert template.status_code==201,template.text
        run=c.post(f'/api/documents/{doc["id"]}/approval-runs',headers=H).json();rid=run['id'];vid=doc['latest']['id']
        login(c,1)
        assert c.post(f'/api/approval-runs/{rid}/decisions',json={'decision':'approved'},headers=H).status_code==200
        payload={'reason':'Nouvel examen motivé de la pièce','expected_version_id':vid}
        assert c.post(f'/api/approval-runs/{rid}/reopen',json=payload,headers=H).status_code==403
        login(c,0)
        new=c.post(f'/api/approval-runs/{rid}/reopen',json=payload,headers=H)
        assert new.status_code==201,new.text
        assert new.json()['cycle']==2 and new.json()['previous_run_id']==rid
        with SessionLocal() as db:
            v=db.get(DocumentVersion,vid)
            assert not is_approved(db,v,v.document)
            assert db.get(ApprovalRun,rid).status=='approved'
            assert len(list(db.scalars(select(ApprovalDecision).where(ApprovalDecision.run_id==rid))))==1
        assert c.post(f'/api/approval-runs/{rid}/reopen',json=payload,headers=H).status_code==409
        login(c,1)
        assert c.post(f'/api/approval-runs/{new.json()["id"]}/decisions',json={'decision':'rejected','comment':'Pièce à refaire après contrôle'},headers=H).status_code==200
        login(c,0)
        v2=c.post(f'/api/documents/{doc["id"]}/versions',files={'file':('fiche.txt',b'corrigee','text/plain')},headers=H).json()['latest']['id']
        assert c.post(f'/api/approval-runs/{new.json()["id"]}/reopen',json=payload,headers=H).status_code==409
        payload['expected_version_id']=v2
        third=c.post(f'/api/approval-runs/{new.json()["id"]}/reopen',json=payload,headers=H)
        assert third.status_code==201,third.text
        assert third.json()['version_id']==v2 and third.json()['status']=='pending'
        overview=c.get(f'/api/launches/{lid}/approval-overview').json()['items'][0]
        assert overview['run']['id']==third.json()['id'] and len(overview['previous'])==2
        # Two operators reopening the same terminal sequence cannot create two successors.
        login(c,1)
        assert c.post(f'/api/approval-runs/{third.json()["id"]}/decisions',json={'decision':'approved'},headers=H).status_code==200
        login(c,0)
        cookies=dict(c.cookies)
        from concurrent.futures import ThreadPoolExecutor
        def reopen(_):
            with TestClient(app) as concurrent:
                concurrent.cookies.update(cookies)
                return concurrent.post(f'/api/approval-runs/{third.json()["id"]}/reopen',json=payload,headers=H).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(reopen,range(2)))
        assert sorted(statuses)==[201,409]
