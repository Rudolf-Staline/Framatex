"""Real persisted supplier/client journeys and adversarial cross-tenant access."""
import os
import tempfile
os.environ.setdefault('FRAMATEX_DATA_DIR', tempfile.mkdtemp(prefix='framat-partners-'))
os.environ.setdefault('FRAMATEX_SECRET_KEY', 'partner-tests-' * 5)
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core import Base, engine, SessionLocal, hash_password
from app.models import User, Role
from app.partner_models import PartnerToken
from app.partner_routes import COOKIE
from app.approval_models import InternalNotification

H={'X-Framatex-Request':'1'}
PWD='PartnerTestPassword2026!'

def post(c, url, data=None, code=201, **kwargs):
    r=c.post(url, json=data, headers=H, **kwargs)
    assert r.status_code == code, r.text
    return r.json()

def setup(c):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with SessionLocal() as db:
        role=Role(name='Administrateur')
        user=User(name='Admin test', email='admin@sample.local', password_hash=hash_password(PWD))
        user.roles.append(role); db.add(user); db.commit()
    post(c,'/api/auth/login',{'email':'admin@sample.local','password':PWD},200)
    return post(c,'/api/launches',{'name':'Commande fictive','client_name':'Client A'})['id']

def organization(c, name, kind='supplier'):
    return post(c,'/api/partners/organizations',{'kind':kind,'name':name})['id']

def activate(c, external, org, email):
    invite=post(c,f'/api/partners/organizations/{org}/invitations',{'email':email})
    assert invite['email_status']=='not_sent'
    post(external,'/api/partner-auth/activate',{'token':invite['activation_token'],'password':PWD},200)
    post(external,'/api/partner-auth/activate',{'token':invite['activation_token'],'password':PWD},400)
    post(external,'/api/partner-auth/login',{'email':email,'password':PWD},200)
    return invite

def upload(c, rid, text=b'Certificat fictif', code=201):
    r=c.post(f'/api/partner/requests/{rid}/versions',headers=H,files={'file':('certificat.txt',text,'text/plain')})
    assert r.status_code==code,r.text
    return r.json()

def test_supplier_journey_isolation_and_revocation():
    with TestClient(app) as staff, TestClient(app) as supplier, TestClient(app) as other:
        lid=setup(staff); a=organization(staff,'Fournisseur A'); b=organization(staff,'Fournisseur B')
        inv=activate(staff,supplier,a,'a@sample.local'); activate(staff,other,b,'b@sample.local')
        rid=post(staff,'/api/partners/requests',{'partner_id':a,'launch_id':lid,'order_ref':'CMD-1','title':'Certificat','doc_type':'Qualité'})['id']
        assert supplier.get('/api/partner/requests').json()[0]['id']==rid
        assert other.get('/api/partner/requests').json()==[]
        assert other.get(f'/api/partner/requests/{rid}').status_code==404
        upload(other,rid,code=404)
        post(other,f'/api/partner/requests/{rid}/messages',{'message':'Intrusion'},404)
        assert supplier.get('/api/launches').status_code==401
        assert supplier.get('/api/partners/organizations').status_code==401
        v1=upload(supplier,rid)
        with SessionLocal() as db:
            assert db.scalar(select(InternalNotification).where(InternalNotification.kind=='supplier_submission'))
        upload(supplier,rid,code=409)
        post(staff,f'/api/partners/requests/{rid}/close',code=409)
        post(staff,f'/api/partners/requests/{rid}/decision',{'version_id':v1['id'],'decision':'rejected','reason':'Signature manquante'},200)
        assert supplier.get(f'/api/partner/requests/{rid}').json()['versions'][0]['reason']=='Signature manquante'
        post(supplier,f'/api/partner/requests/{rid}/messages',{'message':'Voici la correction.'})
        v2=upload(supplier,rid,b'Certificat signe fictif')
        assert v2['number']==2 and v2['status']=='pending'
        post(staff,f'/api/partners/requests/{rid}/decision',{'version_id':v1['id'],'decision':'approved','reason':'Mauvaise version'},409)
        post(staff,f'/api/partners/requests/{rid}/decision',{'version_id':v2['id'],'decision':'approved','reason':'Conforme au besoin'},200)
        post(staff,f'/api/partners/requests/{rid}/close',code=200)
        detail=supplier.get(f'/api/partner/requests/{rid}').json()
        assert detail['status']=='closed' and len(detail['versions'])==2 and len(detail['history'])==7
        url=f'/api/partner/requests/{rid}/versions/{v2["id"]}/download'
        assert supplier.get(url).content==b'Certificat signe fictif'
        assert other.get(url).status_code==404
        cookie=supplier.cookies.get(COOKIE)
        assert staff.patch(f'/api/partners/accounts/{inv["account_id"]}',json={'active':False},headers=H).status_code==200
        assert supplier.get(url).status_code==401
        staff.patch(f'/api/partners/accounts/{inv["account_id"]}',json={'active':True},headers=H)
        supplier.cookies.set(COOKIE,cookie)
        assert supplier.get(url).status_code==401

def test_client_publication_download_stale_and_withdrawal():
    with TestClient(app) as staff, TestClient(app) as client, TestClient(app) as other:
        lid=setup(staff); a=organization(staff,'Client A','client'); b=organization(staff,'Client B','client')
        activate(staff,client,a,'ca@sample.local'); activate(staff,other,b,'cb@sample.local')
        r=staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche technique','doc_type':'Fiche technique'},files={'file':('fiche.txt',b'Fiche technique fictive','text/plain')},headers=H)
        assert r.status_code==201,r.text
        doc=r.json()
        post(staff,f'/api/documents/{doc["id"]}/reviews',{'decision':'approved'})
        pub=post(staff,f'/api/launches/{lid}/client-publications',{'document_version_id':doc['latest']['id'],'reason':'Publication technique approuvee'})
        post(staff,'/api/partners/publications',{'partner_id':b,'publication_id':pub['id']},409)
        binding=post(staff,'/api/partners/publications',{'partner_id':a,'publication_id':pub['id']})
        url=f'/api/partner/publications/{binding["id"]}/download'
        assert client.get(url).content==b'Fiche technique fictive'
        assert other.get(url).status_code==404
        assert other.get('/api/partner/publications').json()==[]
        assert client.get('/api/partner/publications').json()[0]['version']==1
        assert client.get(f'/api/documents/{doc["id"]}').status_code==401
        changed=staff.post(f'/api/documents/{doc["id"]}/versions',files={'file':('new.txt',b'Nouvelle version','text/plain')},headers=H)
        assert changed.status_code==201,changed.text
        assert client.get(url).status_code==404
        assert client.get('/api/partner/publications').json()==[]
        post(staff,f'/api/client-publications/{pub["id"]}/revoke',{'reason':'Retrait de cette publication obsolete'},200)
        assert client.get(url).status_code==404

def test_tokens_logout_recovery_expiry_and_upload_validation():
    from datetime import timedelta
    from app.core import utcnow
    with TestClient(app) as staff, TestClient(app) as supplier:
        lid=setup(staff); a=organization(staff,'Fournisseur A')
        inv=activate(staff,supplier,a,'recovery@sample.local')
        old=supplier.cookies.get(COOKIE)
        post(supplier,'/api/partner-auth/logout',code=200)
        supplier.cookies.set(COOKIE,old)
        assert supplier.get('/api/partner/home').status_code==401
        inv=post(staff,f'/api/partners/organizations/{a}/invitations',{'email':'recovery@sample.local'})
        with SessionLocal() as db:
            token=db.scalar(select(PartnerToken).where(PartnerToken.kind=='invite',PartnerToken.consumed.is_(False)))
            token.expires_at=utcnow()-timedelta(seconds=1);db.commit()
        post(supplier,'/api/partner-auth/activate',{'token':inv['activation_token'],'password':PWD},400)
        inv=post(staff,f'/api/partners/organizations/{a}/invitations',{'email':'recovery@sample.local'})
        post(supplier,'/api/partner-auth/activate',{'token':inv['activation_token'],'password':PWD+'new'},200)
        supplier.cookies.clear()
        post(supplier,'/api/partner-auth/login',{'email':'recovery@sample.local','password':PWD+'new'},200)
        rid=post(staff,'/api/partners/requests',{'partner_id':a,'launch_id':lid,'order_ref':'CMD','title':'Certificat','doc_type':'Qualité'})['id']
        bad=supplier.post(f'/api/partner/requests/{rid}/versions',headers=H,files={'file':('bad.pdf',b'Not a PDF','application/pdf')})
        assert bad.status_code==422
        assert supplier.get(f'/api/partner/requests/{rid}').json()['status']=='requested'
        assert supplier.post('/api/partner-auth/logout').status_code==403
        staff.patch(f'/api/partners/organizations/{a}',json={'active':False},headers=H)
        assert supplier.get('/api/partner/home').status_code==401
