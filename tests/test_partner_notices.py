from datetime import date,timedelta
from fastapi.testclient import TestClient
from test_partners import app,setup,post,organization,activate,H

def test_client_messages_publications_due_dates_are_scoped_readable_and_revocable():
    with TestClient(app) as staff,TestClient(app) as client,TestClient(app) as other:
        lid=setup(staff);org=organization(staff,'Client A','client');wrong=organization(staff,'Client B','client')
        activate(staff,client,org,'notice-client@sample.local');activate(staff,other,wrong,'notice-other@sample.local')
        payload={'partner_id':org,'launch_id':lid,'reference':'CMD-NOTICE','confirmed_due':str(date.today()+timedelta(days=1))}
        order=post(staff,'/api/partners/client-orders',payload)
        thread=post(client,f'/api/partner/client-orders/{order["id"]}/threads',{'title':'Date confirmée','message':'Quelle date retenir ?'})
        assert any(n['kind']=='client_message' for n in staff.get('/api/notifications').json()['items'])
        post(staff,f'/api/partners/threads/{thread["id"]}/messages',{'message':'La date affichée est confirmée.'})
        doc=staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Pub','doc_type':'Fiche technique'},files={'file':('pub.txt',b'Fiche fictive','text/plain')},headers=H).json()
        post(staff,f'/api/documents/{doc["id"]}/reviews',{'decision':'approved'})
        pub=post(staff,f'/api/launches/{lid}/client-publications',{'document_version_id':doc['latest']['id'],'reason':'Partage confirmé de la fiche'})
        post(staff,'/api/partners/publications',{'partner_id':org,'publication_id':pub['id']})
        for _ in range(2):post(staff,'/api/partners/notifications/refresh-deadlines',{},200)
        notices=client.get('/api/partner/notice-center').json()
        assert sorted(n['kind'] for n in notices)==['deadline','message','publication']
        assert other.get('/api/partner/notice-center').json()==[]
        for notice in notices:
            path=f'/api/partner/notice-center/{notice["id"]}/read'
            post(other,path,{},404);post(client,path,{},200);post(client,path,{},200)
        assert all(n['read'] for n in client.get('/api/partner/notice-center').json())
        assert len(client.get('/api/partner/notice-center?offset=1&limit=1').json())==1
        post(staff,f'/api/client-publications/{pub["id"]}/revoke',{'reason':'Fin du partage de cette fiche'},200)
        assert len(client.get('/api/partner/notice-center').json())==2
        assert staff.put(f'/api/partners/client-orders/{order["id"]}',json={**payload,'active':False},headers=H).status_code==200
        assert client.get('/api/partner/notice-center').json()==[]
        for notice in notices:post(client,f'/api/partner/notice-center/{notice["id"]}/read',{},404)

def test_supplier_deadlines_idempotent_and_incoming_messages_notify_owner():
    with TestClient(app) as staff,TestClient(app) as supplier,TestClient(app) as other:
        lid=setup(staff);org=organization(staff,'Supplier A');wrong=organization(staff,'Supplier B')
        activate(staff,supplier,org,'notice-supplier@sample.local');activate(staff,other,wrong,'notice-supplier-other@sample.local')
        req=post(staff,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD-NOTICE','title':'Document dû','doc_type':'Fiche technique','due_date':str(date.today())})
        for _ in range(2):post(staff,'/api/partners/notifications/refresh-deadlines',{},200)
        assert len(supplier.get('/api/partner/notice-center').json())==1
        assert other.get('/api/partner/notice-center').json()==[]
        post(supplier,f'/api/partner/requests/{req["id"]}/messages',{'message':'Document en préparation'})
        assert any(n['kind']=='supplier_message' for n in staff.get('/api/notifications').json()['items'])
