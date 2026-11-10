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
