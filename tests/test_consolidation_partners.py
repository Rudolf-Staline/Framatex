"""Business-grant journeys: real local API, synthetic identities, no SMTP."""
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_partners import app, setup, post, organization, activate, upload, H, PWD
from app.core import SessionLocal, hash_password
from app.models import User, Role, RolePermission, Launch, LaunchMember


def employee(client,email,actions,launch_id=None):
    with SessionLocal() as db:
        role=Role(name=email)
        role.grants=[RolePermission(action=a) for a in actions]
        user=User(name=email,email=email,password_hash=hash_password(PWD),roles=[role])
        db.add(user);db.flush()
        if launch_id:db.add(LaunchMember(launch_id=launch_id,user_id=user.id,granted_by=db.get(Launch,launch_id).created_by))
        uid=user.id;db.commit()
    post(client,'/api/auth/login',{'email':email,'password':PWD},200)
    return uid


def test_off_portal_purchase_quality_receipt_journey_without_admin_or_supplier_account():
    from app.partner_models import PartnerAccount,PartnerSubmission
    from app.models import DocumentVersion
    with TestClient(app) as admin,TestClient(app) as buyer,TestClient(app) as quality,TestClient(app) as reception:
        lid=setup(admin);org=organization(admin,'Hors portail')
        with SessionLocal() as db:
            db.get(Launch,lid).restricted=True;db.commit()
        common=['launch.read','document.read']
        buyid=employee(buyer,'purchasing@sample.local',common+['supplier.read','supplier.request','document.write'],lid)
        qualityid=employee(quality,'quality@sample.local',common+['supplier.read','supplier.review','document.write','document.review'],lid)
        employee(reception,'reception@sample.local',common+['receipt.read','receipt.write'],lid)
        assert not buyer.get('/api/auth/me').json()['admin']
        assert buyer.get('/api/partners/staff-home').json()['admin'] is False
        assert buyer.get('/api/partners/organizations').status_code==403
        rid=post(buyer,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD','title':'Bon hors portail','doc_type':'Bon livraison'})['id']
        result=buyer.post(f'/api/partners/requests/{rid}/received-versions',data={'received_via':'email','note':'Reçu dans la boîte achats, expéditeur vérifié'},files={'file':('bon.txt',b'Bon original hors portail','text/plain')},headers=H)
        assert result.status_code==201,result.text
        version=result.json();assert version['origin']=='staff_received'
        with SessionLocal() as db:
            assert db.scalar(select(PartnerAccount.id).where(PartnerAccount.partner_id==org)) is None
            source=db.get(PartnerSubmission,version['id']);assert source.account_id is None and source.received_by==buyid
        post(buyer,f'/api/partners/requests/{rid}/decision',{'version_id':version['id'],'decision':'approved','reason':'Hors droit'},403)
        post(quality,f'/api/partners/requests/{rid}/decision',{'version_id':version['id'],'decision':'rejected','reason':'Signature manquante'},200)
        retry=buyer.post(f'/api/partners/requests/{rid}/received-versions',data={'received_via':'handover','note':'Original signé remis aux achats'},files={'file':('bon.txt',b'Bon signe','text/plain')},headers=H)
        assert retry.status_code==201,retry.text
        version2=retry.json();assert version2['number']==2
        post(quality,f'/api/partners/requests/{rid}/decision',{'version_id':version2['id'],'decision':'approved','reason':'Signature vérifiée'},200)
        from concurrent.futures import ThreadPoolExecutor
        from app.core import COOKIE
        token=quality.cookies.get(COOKIE)
        def integrate_once(_):
            with TestClient(app) as concurrent:
                concurrent.cookies.set(COOKIE,token)
                response=concurrent.post(f'/api/partners/requests/{rid}/integrate',json={'submission_id':version2['id'],'folder':'rose'},headers=H)
                return response.status_code,response.json()
        with ThreadPoolExecutor(max_workers=2) as pool:attempts=list(pool.map(integrate_once,range(2)))
        assert sorted(code for code,_ in attempts)==[201,409],attempts
        integrated=next(result for code,result in attempts if code==201)
        assert integrated['source']['received_by']==buyid and integrated['source']['received_via']=='handover'
        assert integrated['source']['reviewed_by']==qualityid
        post(quality,f'/api/partners/requests/{rid}/integrate',{'submission_id':version2['id'],'folder':'rose'},409)
        line=post(buyer,'/api/partners/order-lines',{'partner_id':org,'launch_id':lid,'order_ref':'CMD','material_ref':'M1','unit':'m','ordered':'10.125'})
        base=f'/api/partners/order-lines/{line["id"]}'
        payload={'kind':'received','operation_key':'reception-key-1','quantity':'4.125','source_id':version2['id'],'occurred_on':'2026-11-17','note':'Première réception normale'}
        first=post(reception,base+'/receipts',payload);assert first['remaining']=='6.000' and first['assessment']=='normal_progress'
        assert post(reception,base+'/receipts',payload)['received']=='4.125'
        post(buyer,base+'/receipts',payload,403)
        second=post(reception,base+'/receipts',{**payload,'quantity':'6.000','operation_key':'reception-key-2'})
        assert second['status']=='complete'
        returned=post(reception,base+'/receipts',{**payload,'kind':'returned','quantity':'0.125','operation_key':'return-key-1'})
        mid=next(m['id'] for m in returned['movements'] if m['kind']=='returned')
        cancelled=post(reception,base+f'/movements/{mid}/cancel',{'reason':'Retour saisi par erreur'},200)
        assert cancelled['received']=='10.125'
        rows=reception.get('/api/receipts').json();assert rows[0]['launch_id']==lid and rows[0]['order_id'] is None and 'movements' not in rows[0]
        history=reception.get(base+'/history?limit=2').json();assert history['total']==4 and len(history['items'])==2
        assert buyer.get('/api/receipts').status_code==403
        with SessionLocal() as db:assert db.get(DocumentVersion,integrated['version_id']).number==1


def test_contextual_rights_filter_requests_and_receipts_before_pagination_and_revocation():
    with TestClient(app) as admin,TestClient(app) as reader:
        lid=setup(admin);org=organization(admin,'Permissions')
        hidden=post(admin,'/api/launches',{'name':'Confidentiel'})['id']
        with SessionLocal() as db:
            db.get(Launch,lid).restricted=True;db.get(Launch,hidden).restricted=True;db.commit()
        uid=employee(reader,'reader-partner@sample.local',['launch.read','document.read','supplier.read','supplier.request','receipt.read','receipt.write'],lid)
        visible=post(admin,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD','title':'Visible','doc_type':'Bon'})
        secret=post(admin,'/api/partners/requests',{'partner_id':org,'launch_id':hidden,'order_ref':'SECRET','title':'Confidentiel','doc_type':'Bon'})
        line=post(admin,'/api/partners/order-lines',{'partner_id':org,'launch_id':lid,'order_ref':'CMD','material_ref':'A','unit':'kg','ordered':'2'})
        post(admin,'/api/partners/order-lines',{'partner_id':org,'launch_id':hidden,'order_ref':'SECRET','material_ref':'B','unit':'kg','ordered':'2'})
        assert [r['id'] for r in reader.get('/api/partners/requests?limit=1').json()]==[visible['id']]
        assert reader.get(f'/api/partners/requests/{secret["id"]}').status_code==404
        assert reader.get('/api/receipts?limit=1').json()[0]['id']==line['id']
        with SessionLocal() as db:
            db.delete(db.scalar(select(LaunchMember).where(LaunchMember.user_id==uid,LaunchMember.launch_id==lid)));db.commit()
        assert reader.get(f'/api/partners/requests/{visible["id"]}').status_code==404
        assert reader.get('/api/partners/requests').json()==[] and reader.get('/api/receipts').json()==[]
        with SessionLocal() as db:db.get(User,uid).active=False;db.commit()
        assert reader.get('/api/partners/staff-home').status_code==401


def test_portal_client_kind_cannot_read_supplier_requests_even_with_corrupt_assignment():
    from app.partner_models import PartnerRequest
    with TestClient(app) as admin,TestClient(app) as client:
        lid=setup(admin);org=organization(admin,'Client uniquement','client')
        activate(admin,client,org,'client-only@sample.local')
        with SessionLocal() as db:
            creator=db.scalar(select(User.id));row=PartnerRequest(partner_id=org,launch_id=lid,order_ref='BAD',title='Doit rester interne',doc_type='Bon',created_by=creator)
            db.add(row);db.flush();rid=row.id;db.commit()
        assert client.get('/api/partner/requests').json()==[]
        assert client.get(f'/api/partner/requests/{rid}').status_code==404
        assert client.get('/api/partner/order-lines').json()==[]


def test_received_sources_migration_preserves_history_references_and_is_repeatable():
    from sqlalchemy import create_engine,text,inspect
    from app.partner_submission_migration import upgrade
    engine=create_engine('sqlite://')
    with engine.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE users(id VARCHAR(36) PRIMARY KEY)')
        conn.exec_driver_sql('CREATE TABLE partner_accounts(id VARCHAR(36) PRIMARY KEY)')
        conn.exec_driver_sql('CREATE TABLE partner_requests(id VARCHAR(36) PRIMARY KEY)')
        conn.exec_driver_sql("CREATE TABLE partner_submissions(id VARCHAR(36) PRIMARY KEY,request_id VARCHAR(36) NOT NULL,number INTEGER NOT NULL,account_id VARCHAR(36) NOT NULL,original_name VARCHAR(240) NOT NULL,disk_name VARCHAR(64) NOT NULL,sha256 VARCHAR(64) NOT NULL,size INTEGER NOT NULL,content_type VARCHAR(160) NOT NULL,status VARCHAR(20) NOT NULL,reason TEXT NOT NULL,reviewed_by VARCHAR(36),created_at DATETIME NOT NULL,UNIQUE(request_id,number))")
        conn.exec_driver_sql("CREATE TABLE preserved_link(source_id VARCHAR(36) REFERENCES partner_submissions(id))")
        conn.exec_driver_sql("INSERT INTO users VALUES ('u')");conn.exec_driver_sql("INSERT INTO partner_accounts VALUES ('a')");conn.exec_driver_sql("INSERT INTO partner_requests VALUES ('r')")
        conn.exec_driver_sql("INSERT INTO partner_submissions VALUES ('s','r',1,'a','original.txt','blob','hash',3,'text/plain','approved','Conforme','u','2026-11-17')")
        conn.exec_driver_sql("INSERT INTO preserved_link VALUES ('s')")
        upgrade(conn);upgrade(conn)
        assert conn.execute(text('SELECT id,account_id,status,reason,received_by,received_via FROM partner_submissions')).one()==('s','a','approved','Conforme',None,'portal')
        assert conn.exec_driver_sql('PRAGMA foreign_key_check').all()==[]
        assert next(c for c in inspect(conn).get_columns('partner_submissions') if c['name']=='account_id')['nullable']


def test_validation_queue_sql_page_and_visible_counts_ignore_old_versions_and_hidden_docs():
    from app.models import Document,DocumentVersion,Folder
    from app.approval_models import ApprovalTemplate,ApprovalStage,ApprovalRun
    from app.core import engine
    from sqlalchemy import event
    with TestClient(app) as admin,TestClient(app) as reader:
        lid=setup(admin)
        hidden=post(admin,'/api/launches',{'name':'Secret validations'})['id']
        with SessionLocal() as db:db.get(Launch,lid).restricted=True;db.get(Launch,hidden).restricted=True;db.commit()
        uid=employee(reader,'queue-reader@sample.local',['launch.read','document.read','document.review'],lid)
        with SessionLocal() as db:
            author=db.get(Launch,lid).created_by;role=db.get(User,uid).roles[0]
            template=ApprovalTemplate(name='Revue synthétique',folder_slug='jaune',document_type='Certificat',created_by=author);db.add(template);db.flush()
            db.add(ApprovalStage(template_id=template.id,position=1,name='Examen',reviewer_role_id=role.id))
            for i in range(31):
                folder=db.scalar(select(Folder).where(Folder.launch_id==lid if i<30 else Folder.launch_id==hidden,Folder.slug=='jaune'))
                doc=Document(folder_id=folder.id,title=f'Document {i}',doc_type='Certificat',created_by=author);db.add(doc);db.flush()
                for number in range(1,4):
                    v=DocumentVersion(document_id=doc.id,number=number,original_name='test.txt',disk_name=f'queue-{i}-{number}',content_type='text/plain',size=1,sha256='0'*64,uploaded_by=author);db.add(v);db.flush()
                    db.add(ApprovalRun(template_id=template.id,document_version_id=v.id,started_by=author,status='pending' if number==3 else 'approved'))
            db.commit()
        statements=[]
        def count(*args):statements.append(args[2])
        event.listen(engine,'before_cursor_execute',count)
        try:r=reader.get('/api/validation-queue?limit=5&offset=5')
        finally:event.remove(engine,'before_cursor_execute',count)
        assert r.status_code==200,r.text
        report=r.json();assert report['total']==30 and report['pending']==30 and len(report['items'])==5
        assert all(row['version']==3 and row['can_decide'] and row['launch_id']==lid for row in report['items'])
        assert len(statements)<30, len(statements)


def test_receipt_summary_query_budget_is_bounded_with_many_movements():
    from app.partner_models import PartnerRequest,PartnerSubmission,PartnerOrderLine,PartnerDelivery
    from app.core import engine
    from sqlalchemy import event
    from datetime import date
    from decimal import Decimal
    with TestClient(app) as admin:
        lid=setup(admin);org=organization(admin,'Volumétrie réceptions')
        with SessionLocal() as db:
            actor=db.get(Launch,lid).created_by
            request=PartnerRequest(partner_id=org,launch_id=lid,order_ref='CORPUS',title='Justificatif synthétique',doc_type='Bon',created_by=actor);db.add(request);db.flush()
            source=PartnerSubmission(request_id=request.id,number=1,received_by=actor,account_id=None,received_via='paper',original_name='source.txt',disk_name='synthetic-only',sha256='0'*64,size=1,content_type='text/plain',status='approved');db.add(source);db.flush()
            for i in range(50):
                line=PartnerOrderLine(partner_id=org,launch_id=lid,order_ref='CORPUS',material_ref=f'M-{i}',unit='kg',ordered=Decimal('100'),created_by=actor);db.add(line);db.flush()
                db.add_all([PartnerDelivery(line_id=line.id,operation_key=f'movement-{j}',kind='received',quantity=Decimal('.125'),source_id=source.id,actor='staff:'+actor,note='Synthétique',occurred_on=date(2026,11,17)) for j in range(40)])
            db.commit()
        statements=[]
        def count(*args):statements.append(args[2])
        event.listen(engine,'before_cursor_execute',count)
        try:r=admin.get('/api/receipts?page=true&limit=25&offset=25')
        finally:event.remove(engine,'before_cursor_execute',count)
        assert r.status_code==200,r.text
        report=r.json();assert report['total']==50 and len(report['items'])==25
        assert all(row['received']=='5.000' and row['remaining']=='95.000' and 'movements' not in row for row in report['items'])
        assert len(statements)<20,len(statements)
