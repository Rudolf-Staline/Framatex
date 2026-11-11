from fastapi.testclient import TestClient
from test_partners import app,setup,post,H,organization,activate

def test_order_type_optional_deadline_and_effective_publication_conditions():
    with TestClient(app) as staff:
        lid=setup(staff);profile=post(staff,'/api/admin/completeness/profiles',{'name':'Conditions','description':'Test'})
        rule=post(staff,f'/api/admin/completeness/profiles/{profile["id"]}/rules',{'title':'Fiche','folder':'jaune','document_type':'Fiche technique','due_phase':'preparation','requires_validation':True})
        staff.patch(f'/api/launches/{lid}/completeness/context',json={'profile_id':profile['id'],'phase':'preparation'},headers=H)
        def state():return staff.get(f'/api/launches/{lid}/completeness').json()['rows'][0]
        url=f'/api/admin/completeness/rules/{rule["id"]}/policy'
        assert state()['status']=='missing'
        assert staff.put(url,json={'order_type':'Export','optional':True},headers=H).status_code==200
        assert state()['status']=='not_applicable'
        assert staff.put(f'/api/launches/{lid}/order-context',json={'order_type':'Export'},headers=H).status_code==200
        assert state()['status']=='optional' and not state()['due']
        staff.put(url,json={'days_after_launch':30},headers=H)
        assert state()['status']=='not_due' and state()['due_date']
        staff.put(url,json={'requires_client_publication':True},headers=H)
        doc=staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche technique','doc_type':'Fiche technique'},files={'file':('fiche.txt',b'Fiche fictive','text/plain')},headers=H).json()
        assert state()['status']=='pending_validation'
        post(staff,f'/api/documents/{doc["id"]}/reviews',{'decision':'approved'})
        assert state()['status']=='pending_publication'
        pub=post(staff,f'/api/launches/{lid}/client-publications',{'document_version_id':doc['latest']['id'],'reason':'Fiche approuvée pour ce client'})
        assert state()['status']=='pending_publication'  # simulated internal publication alone is insufficient
        org=organization(staff,'Client A','client')
        post(staff,'/api/partners/publications',{'partner_id':org,'publication_id':pub['id']})
        assert state()['status']=='pending_publication'
        with TestClient(app) as client:activate(staff,client,org,'completeness-client@sample.local')
        assert state()['status']=='present'
        post(staff,f'/api/client-publications/{pub["id"]}/revoke',{'reason':'Retrait décidé explicitement'},200)
        assert state()['status']=='pending_publication'
