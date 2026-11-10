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
