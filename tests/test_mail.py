"""0.8 : archivage, suggestions, contrôle humain, cloisonnement et audit."""
import os
import tempfile
from email.message import EmailMessage
os.environ['FRAMATEX_DATA_DIR']=tempfile.mkdtemp(prefix='framat-mail-')
os.environ['FRAMATEX_SECRET_KEY']='mail-tests-super-secret-key-'*3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core import Base, engine, SessionLocal, hash_password
from app.main import app
from app.models import Role, RolePermission, User, AuditEvent

H={'X-Framatex-Request':'1'}
PASSWORD='TestPasswordSecure18!'

@pytest.fixture
def c():
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            admin=Role(name='Administrateur')
            reception=Role(name='Reception',grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='rose')])
            yellow=Role(name='Technique',grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='jaune')])
            db.add_all([User(name='Admin',email='admin@mail.test',password_hash=hash_password(PASSWORD),roles=[admin]),
                        User(name='Reception',email='rose@mail.test',password_hash=hash_password(PASSWORD),roles=[reception]),
                        User(name='Technique',email='jaune@mail.test',password_hash=hash_password(PASSWORD),roles=[yellow])])
            db.commit()
        login(client,'admin@mail.test')
        yield client
    Base.metadata.drop_all(engine)


def login(c,email):
    r=c.post('/api/auth/login',json={'email':email,'password':PASSWORD},headers=H)
    assert r.status_code==200,r.text


def launch(c):
    r=c.post('/api/launches',json={'name':'Lancement chemise laboratoire'},headers=H)
    assert r.status_code==201,r.text
    return r.json()['id']


def eml(subject='Confirmation tissu', message='Nous vous transmettrons la confirmation le 20/10/2026, sous réserve du contrôle qualité.'):
    msg=EmailMessage()
    msg['From']='Fournisseur <supplier@example.test>'
    msg['To']='atelier@example.test'
    msg['Subject']=subject
    msg['Date']='Sat, 17 Oct 2026 12:00:00 +0000'
    msg['Message-ID']='<test-42@example.test>'
    msg.set_content(message)
    msg.add_attachment(b'PDF-TEST',maintype='application',subtype='pdf',filename='certificat.pdf')
    return msg.as_bytes()


def upload(c,lid,blob=None):
    return c.post(f'/api/launches/{lid}/emails/import',files={'file':('recu.eml',blob if blob is not None else eml(),'message/rfc822')},headers=H)


def test_import_email_retains_attachment_and_link_to_rose(c):
    lid=launch(c)
    imported=upload(c,lid)
    assert imported.status_code==201,imported.text
    result=imported.json()
    assert result['email']['sender'].startswith('Fournisseur')
    assert result['email']['attachments'][0]['filename']=='certificat.pdf'
    assert result['document']['folder']=='rose'
    assert result['document']['latest']['original_name']=='recu.eml'
    email_list=c.get(f'/api/launches/{lid}/emails').json()
    assert len(email_list['emails'])==1 and email_list['commitments']==[]
    r=c.get(f'/api/documents/{result["document"]["id"]}/versions/1/download')
    assert r.status_code==200 and b'certificat.pdf' in r.content
    with SessionLocal() as db:
        logs=db.scalars(select(AuditEvent).where(AuditEvent.action=='email.archive')).all()
        assert len(logs)==1


def test_suggestions_human_commitment_and_status(c):
    lid=launch(c);uploaded=upload(c,lid).json()['email']
    r=c.get(f'/api/launches/{lid}/emails/{uploaded["id"]}/suggestions')
    assert r.status_code==200
    suggestions=r.json();assert suggestions['human_confirmation_required']
    assert len(suggestions['candidates'])==1
    candidate=suggestions['candidates'][0]
    assert candidate['due_date']=='2026-10-20'
    assert 'réserve' in candidate['condition']
    assert c.get(f'/api/launches/{lid}/emails').json()['commitments']==[]
    payload={'email_id':uploaded['id'],**candidate}
    saved=c.post(f'/api/launches/{lid}/commitments',json=payload,headers=H)
    assert saved.status_code==201,saved.text
    item=saved.json();assert item['status']=='pending'
    r=c.patch(f'/api/launches/{lid}/commitments/{item["id"]}',json={'status':'done','note':'Confirmation reçue et vérifiée'},headers=H)
    assert r.status_code==200,r.text
    assert r.json()['status']=='done'
    with SessionLocal() as db:
        events=db.scalars(select(AuditEvent).where(AuditEvent.action=='commitment.update')).all()
        assert len(events)==1


def test_access_rules_prevent_email_metadata_leak(c):
    lid=launch(c);eid=upload(c,lid).json()['email']['id']
    login(c,'jaune@mail.test')
    assert c.get(f'/api/launches/{lid}/emails').status_code==403
    assert c.get(f'/api/launches/{lid}/emails/{eid}/suggestions').status_code==403
    assert upload(c,lid).status_code==403
    login(c,'rose@mail.test')
    assert c.get(f'/api/launches/{lid}/emails').status_code==200
    assert c.get(f'/api/launches/{lid}/emails/{eid}/suggestions').status_code==200
    assert upload(c,lid).status_code==403
    assert c.post(f'/api/launches/{lid}/commitments',json={'email_id':eid,'description':'Confirmer la livraison mardi','responsible':'Fournisseur'},headers=H).status_code==403


def test_eml_validation_and_source_quote(c):
    lid=launch(c)
    bad=c.post(f'/api/launches/{lid}/emails/import',files={'file':('x.txt',b'email bogus')},headers=H)
    assert bad.status_code==422
    bad=upload(c,lid,b'ceci n est pas un email')
    assert bad.status_code==422
    eid=upload(c,lid).json()['email']['id']
    result=c.post(f'/api/launches/{lid}/commitments',json={'email_id':eid,'description':'Confirmer la disponibilite','responsible':'Fournisseur','source_excerpt':'Citation inventee'},headers=H)
    assert result.status_code==422
    assert c.get(f'/api/launches/{lid}/emails').json()['commitments']==[]


def test_launch_boundary_and_csrf(c):
    lid=launch(c);other=launch(c)
    eid=upload(c,lid).json()['email']['id']
    assert c.get(f'/api/launches/{other}/emails/{eid}/suggestions').status_code==404
    assert c.post(f'/api/launches/{lid}/commitments',json={'email_id':eid,'description':'Confirmation à recevoir','responsible':'Fournisseur'}).status_code==403
    assert c.post(f'/api/launches/{other}/commitments',json={'email_id':eid,'description':'Confirmation à recevoir','responsible':'Fournisseur'},headers=H).status_code==404


def test_relative_date_not_invented_and_html_not_rendered(c):
    lid=launch(c)
    raw=eml(message='Nous vous transmettrons la confirmation vendredi, sous réserve du contrôle qualité.\n<script>alert(1)</script>')
    eid=upload(c,lid,raw).json()['email']['id']
    result=c.get(f'/api/launches/{lid}/emails/{eid}/suggestions').json()
    assert result['candidates'][0]['due_date'] is None
    assert not c.get(f'/api/launches/{lid}/emails').json()['commitments']
