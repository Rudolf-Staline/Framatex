from fastapi.testclient import TestClient
from test_partners import app, setup, organization, activate, post, upload, H


def test_roles_domains_and_no_self_escalation():
    with TestClient(app) as staff, TestClient(app) as first, TestClient(app) as second:
        lid=setup(staff);a=organization(staff,'A');b=organization(staff,'B')
        aa=activate(staff,first,a,'a@sample.local');bb=activate(staff,second,b,'b@sample.local')
        profile={'name':'A légal','trade_name':'A commerce','contact':'Contact nominatif','address':'Adresse fictive','domains':['sample.local'],'administrative':{'identifiant':'FICTIF'}}
        r=staff.put(f'/api/partners/organizations/{a}/profile',json=profile,headers=H);assert r.status_code==200,r.text
        assert r.json()['trade_name']=='A commerce' and r.json()['history'][0]['detail']['after']==profile
        post(staff,f'/api/partners/organizations/{a}/invitations',{'email':'intrus@other.local'},422)
        reader=post(staff,f'/api/partners/organizations/{a}/roles',{'name':'Lecteur','permissions':['read']})
        assert staff.put(f'/api/partners/accounts/{aa["account_id"]}/role',json={'role_id':reader['id']},headers=H).status_code==200
        assert staff.put(f'/api/partners/accounts/{bb["account_id"]}/role',json={'role_id':reader['id']},headers=H).status_code==404
        assert first.put(f'/api/partners/accounts/{aa["account_id"]}/role',json={'role_id':reader['id']},headers=H).status_code==401
        rid=post(staff,'/api/partners/requests',{'partner_id':a,'launch_id':lid,'order_ref':'CMD','title':'Certificat','doc_type':'Certificat'})['id']
        upload(first,rid,code=403)
        post(first,f'/api/partner/requests/{rid}/messages',{'message':'No write'},403)
        post(first,'/api/partner/order-lines/unknown/declarations',{'operation_key':'test-operation','quantity':'1','source_id':'unknown','note':'Test','occurred_on':'2026-11-10'},403)
        assert second.get(f'/api/partner/requests/{rid}').status_code==404
        writer=post(staff,f'/api/partners/organizations/{a}/roles',{'name':'Documents','permissions':['read','document.write']})
        staff.put(f'/api/partners/accounts/{aa["account_id"]}/role',json={'role_id':writer['id']},headers=H)
        upload(first,rid)
        post(first,f'/api/partner/requests/{rid}/messages',{'message':'No write'},403)
        assert first.get('/api/partner/home').json()['permissions']==['document.write','read']
        assert second.get(f'/api/partners/organizations/{a}/profile').status_code==401


def test_supplier_integration_preserves_blob_provenance_and_completeness():
    from app.core import SessionLocal
    from app.models import DocumentVersion
    from app.partner_models import PartnerSubmission
    from app.quality import latest_document_versions
    with TestClient(app) as staff, TestClient(app) as supplier:
        lid=setup(staff);org=organization(staff,'Integrated supplier');activate(staff,supplier,org,'integrate@sample.local')
        rid=post(staff,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD','title':'Certificat','doc_type':'Certificat qualité'})['id']
        profile=post(staff,'/api/admin/completeness/profiles',{'name':'Certificats','description':'Test'})
        post(staff,f'/api/admin/completeness/profiles/{profile["id"]}/rules',{'title':'Certificat','folder':'jaune','document_type':'Certificat qualité','due_phase':'preparation','requires_validation':True})
        assert staff.patch(f'/api/launches/{lid}/completeness/context',json={'profile_id':profile['id'],'phase':'preparation'},headers=H).status_code==200
        version=upload(supplier,rid)
        payload={'submission_id':version['id'],'folder':'jaune'}
        post(staff,f'/api/partners/requests/{rid}/integrate',payload,409)
        post(supplier,f'/api/partners/requests/{rid}/integrate',payload,401)
        post(staff,f'/api/partners/requests/{rid}/decision',{'version_id':version['id'],'decision':'approved','reason':'Certificat vérifié'},200)
        result=post(staff,f'/api/partners/requests/{rid}/integrate',payload)
        internal=result['version_id'];docid=result['document']['id']
        confirmed=post(staff,f'/api/document-versions/{internal}/intake/confirm',{'field_key':'quantite','value':'25','unit':'pièce','source_excerpt':'Quantité : 25 pièces'})
        used=post(staff,f'/api/document-versions/{internal}/data-from-confirmed',{'confirmed_id':confirmed['id'],'field_key':'quantite_lancement'})
        assert used['value']=='25' and used['confirmed_id']==confirmed['id']
        post(staff,f'/api/document-versions/{internal}/data-from-confirmed',{'confirmed_id':confirmed['id'],'field_key':'quantite_lancement'},409)
        post(staff,f'/api/partners/requests/{rid}/integrate',payload,409)
        assert staff.get(f'/api/launches/{lid}/completeness').json()['counts']['present']==1
        assert staff.get(f'/api/documents/{docid}/versions/1/download').content==b'Certificat fictif'
        assert supplier.get(f'/api/documents/{docid}/versions/1/download').status_code==401
        with SessionLocal() as db:
            v=db.get(DocumentVersion,internal);s=db.get(PartnerSubmission,version['id'])
            assert (v.disk_name,v.sha256,v.created_at)==(s.disk_name,s.sha256,s.created_at)
        post(staff,f'/api/partners/requests/{rid}/reopen',{'reason':'Actualisation demandée'},200)
        v2=upload(supplier,rid,b'Nouvelle preuve')
        post(staff,f'/api/partners/requests/{rid}/decision',{'version_id':v2['id'],'decision':'approved','reason':'Version actualisée'},200)
        wrong=post(staff,'/api/launches',{'name':'Autre commande'})['id']
        other=staff.post(f'/api/launches/{wrong}/documents',data={'folder':'jaune','title':'Autre'},files={'file':('x.txt',b'Test','text/plain')},headers=H).json()
        post(staff,f'/api/partners/requests/{rid}/integrate',{'submission_id':v2['id'],'folder':'jaune','document_id':other['id']},409)
        result2=post(staff,f'/api/partners/requests/{rid}/integrate',{'submission_id':v2['id'],'folder':'jaune','document_id':docid})
        assert result2['document']['latest']['number']==2
        origin=staff.get(f'/api/document-versions/{result2["version_id"]}/supplier-origin').json()
        assert origin['account_id']==result['source']['account_id'] and origin['source_version']==2
        post(staff,f'/api/document-versions/{result2["version_id"]}/supplier-withdrawal',{'reason':'Justificatif retiré'},200)
        assert staff.get(f'/api/launches/{lid}/completeness').json()['counts']['missing']==1
        with SessionLocal() as db:assert latest_document_versions(db,lid,'Certificat qualité','jaune')==[]
        assert staff.get(f'/api/documents/{docid}/versions/1/download').status_code==200


def test_client_orders_conversations_attachments_and_revocation(monkeypatch):
    with TestClient(app) as staff, TestClient(app) as client, TestClient(app) as other:
        lid=setup(staff);a=organization(staff,'Client A','client');b=organization(staff,'Client B','client')
        activate(staff,client,a,'clientphase2@sample.local');activate(staff,other,b,'otherclient@sample.local')
        payload={'partner_id':a,'launch_id':lid,'reference':'Commande publique','status':'Confirmée','confirmed_due':'2026-12-01'}
        order=post(staff,'/api/partners/client-orders',payload)
        post(staff,'/api/partners/client-orders',{**payload,'partner_id':b},409)
        public=client.get('/api/partner/client-orders').json()
        assert len(public)==1 and public[0]['progress_percent'] is None
        assert 'launch_id' not in public[0] and 'partner_id' not in public[0]
        assert other.get('/api/partner/client-orders').json()==[]
        endpoint=f'/api/partner/client-orders/{order["id"]}/threads'
        post(other,endpoint,{'title':'Intrusion','message':'Interdit'},404)
        thread=post(client,endpoint,{'title':'Demande documentaire','message':'Quelle version utiliser ?'})
        assert other.get(endpoint).status_code==404
        post(staff,f'/api/partners/threads/{thread["id"]}/messages',{'message':'La version publiée est courante'})
        r=client.post(f'/api/partner/threads/{thread["id"]}/attachments',data={'message':'Pièce explicative'},files={'file':('note.txt',b'Note client privee','text/plain')},headers=H)
        assert r.status_code==201,r.text
        attachment=r.json();url=f'/api/partner/attachments/{attachment["id"]}/download'
        assert client.get(url).content==b'Note client privee'
        assert other.get(url).status_code==404
        monkeypatch.setenv('FRAMATEX_PARTNER_QUOTA_BYTES','1')
        assert client.post(f'/api/partner/threads/{thread["id"]}/attachments',data={'message':'Quota'},files={'file':('note.txt',b'Trop','text/plain')},headers=H).status_code==413
        monkeypatch.delenv('FRAMATEX_PARTNER_QUOTA_BYTES')
        monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE','required')
        monkeypatch.delenv('FRAMATEX_SCANNER_COMMAND',raising=False)
        assert client.post(f'/api/partner/threads/{thread["id"]}/attachments',data={'message':'Scanner'},files={'file':('note.txt',b'Test','text/plain')},headers=H).status_code==503
        monkeypatch.delenv('FRAMATEX_UPLOAD_SCAN_MODE')
        post(staff,f'/api/partners/threads/{thread["id"]}/status',{'status':'waiting_client','reason':'Préciser la référence'},200)
        post(client,f'/api/partner/threads/{thread["id"]}/messages',{'message':'Référence confirmée'})
        post(staff,f'/api/partners/threads/{thread["id"]}/status',{'status':'closed','reason':'Demande traitée'},200)
        post(client,f'/api/partner/threads/{thread["id"]}/messages',{'message':'Échange fermé'},409)
        assert len(client.get(endpoint).json()[0]['attachments'])==1
        assert staff.put(f'/api/partners/client-orders/{order["id"]}',json={**payload,'active':False},headers=H).status_code==200
        assert client.get(url).status_code==404 and client.get(endpoint).status_code==404


def test_supplier_attachment_isolation_and_role():
    with TestClient(app) as staff, TestClient(app) as supplier, TestClient(app) as other:
        lid=setup(staff);a=organization(staff,'A');b=organization(staff,'B')
        account=activate(staff,supplier,a,'attachment@sample.local');activate(staff,other,b,'attachmentother@sample.local')
        rid=post(staff,'/api/partners/requests',{'partner_id':a,'launch_id':lid,'order_ref':'CMD','title':'Certificat','doc_type':'Qualité'})['id']
        endpoint=f'/api/partner/requests/{rid}/attachments'
        assert other.post(endpoint,data={'message':'Intrusion'},files={'file':('test.txt',b'Test','text/plain')},headers=H).status_code==404
        result=supplier.post(endpoint,data={'message':'Justification'},files={'file':('test.txt',b'Justification','text/plain')},headers=H)
        assert result.status_code==201,result.text
        aid=result.json()['id'];assert other.get(f'/api/partner/attachments/{aid}/download').status_code==404
        assert supplier.get(f'/api/partner/requests/{rid}').json()['attachments'][0]['classification']=='partner_private'
        role=post(staff,f'/api/partners/organizations/{a}/roles',{'name':'Lecture','permissions':['read']})
        staff.put(f'/api/partners/accounts/{account["account_id"]}/role',json={'role_id':role['id']},headers=H)
        assert supplier.post(endpoint,data={'message':'Refus'},files={'file':('test.txt',b'Test','text/plain')},headers=H).status_code==403


def test_search_notifications_and_concurrent_upload_quota(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from app.partner_routes import COOKIE
    with TestClient(app) as staff, TestClient(app) as supplier, TestClient(app) as other:
        lid=setup(staff);a=organization(staff,'Search A');b=organization(staff,'Search B')
        activate(staff,supplier,a,'search@sample.local');activate(staff,other,b,'searchother@sample.local')
        requests=[post(staff,'/api/partners/requests',{'partner_id':a,'launch_id':lid,'order_ref':f'CMD-{i}','title':f'Certificat {i}','doc_type':'Qualité'})['id'] for i in range(2)]
        assert len(supplier.get('/api/partner/requests?q=CMD-0&limit=1').json())==1
        assert other.get('/api/partner/requests?q=CMD-0').json()==[]
        assert len(supplier.get('/api/partner/requests?limit=1&offset=1&sort=oldest').json())==1
        notification=supplier.get('/api/partner/notifications').json()[0]
        assert other.get('/api/partner/notifications').json()==[]
        post(other,f'/api/partner/notifications/{notification["id"]}/read',code=404)
        post(supplier,f'/api/partner/notifications/{notification["id"]}/read',code=200)
        assert supplier.get('/api/partner/notifications').json()[0]['read'] is True
        token=supplier.cookies.get(COOKIE)
        monkeypatch.setenv('FRAMATEX_PARTNER_QUOTA_BYTES','10')
        def submit(rid):
            with TestClient(app) as c:
                c.cookies.set(COOKIE,token)
                return c.post(f'/api/partner/requests/{rid}/versions',headers=H,files={'file':('data.txt',b'12345678','text/plain')}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,requests))
        assert sorted(results)==[201,413]

