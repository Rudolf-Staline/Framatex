"""One persisted synthetic journey across orders, portals, decisions and restore.

Run with a fresh FRAMATEX_DATA_DIR; no real SMTP or production data.
"""
from contextlib import ExitStack
import hashlib
import sqlite3
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_partners import app, setup, post, organization, activate, upload, H
from test_consolidation_partners import employee
from test_consolidation_completeness import policy, context, report
from app.core import DATA_DIR, SessionLocal
from app.models import User
from app.backup import backup, restore, validate


def test_cross_module_synthetic_journey_and_fresh_restore(tmp_path, monkeypatch):
    from app import partner_mail
    monkeypatch.setenv('FRAMATEX_EMAIL_ENABLED','0')
    def forbidden_smtp(*args, **kwargs):
        raise AssertionError('No real SMTP is permitted in the synthetic journey')
    monkeypatch.setattr(partner_mail,'smtp_send',forbidden_smtp)
    with ExitStack() as clients:
        admin,buyer,quality,reception,supplier,other_supplier,customer,other_customer=[
            clients.enter_context(TestClient(app)) for _ in range(8)]
        legacy=setup(admin)
        client_a=organization(admin,'Client synthétique commun','client')
        client_b=organization(admin,'Autre client synthétique','client')
        supplier_a=organization(admin,'Fournisseur synthétique A')
        supplier_b=organization(admin,'Fournisseur synthétique B')
        launchless=post(admin,'/api/orders',{'client_id':client_a,'reference':'RECETTE-SANS-LANCEMENT'})['id']
        multiple=post(admin,'/api/orders',{'client_id':client_a,'reference':'RECETTE-DEUX-LANCEMENTS'})['id']
        assert admin.patch(f'/api/launches/{legacy}',json={'client_name':'Client synthétique commun','order_ref':'RECETTE-DEUX-LANCEMENTS'},headers=H).status_code==200
        post(admin,f'/api/orders/{multiple}/launches',{'launch_id':legacy})
        second=post(admin,'/api/launches',{'name':'Second atelier synthétique','order_id':multiple})['id']
        for lid in (legacy,second):
            assert admin.put(f'/api/launches/{lid}/access',json={'restricted':True},headers=H).status_code==200
        common=['launch.read','document.read']
        buyid=employee(buyer,'journey-buyer@sample.local',common+['order.create','supplier.read','supplier.request','document.write'])
        qualityid=employee(quality,'journey-quality@sample.local',common+['supplier.read','supplier.review','document.write','document.review'])
        receiptid=employee(reception,'journey-reception@sample.local',common+['receipt.read','receipt.write'])
        for uid in (buyid,qualityid,receiptid):
            for oid in (launchless,multiple):
                post(admin,f'/api/orders/{oid}/members',{'user_id':uid,'reason':'Habilitation synthétique pour recette transversale'})
            for lid in (legacy,second):post(admin,f'/api/launches/{lid}/access/members',{'user_id':uid})
        for staff in (buyer,quality,reception):assert staff.get('/api/auth/me').json()['admin'] is False
        activate(admin,supplier,supplier_a,'journey-supplier-a@sample.local')
        activate(admin,other_supplier,supplier_b,'journey-supplier-b@sample.local')
        activate(admin,customer,client_a,'journey-client-a@sample.local')
        activate(admin,other_customer,client_b,'journey-client-b@sample.local')

        # A configurable profile exercises missing/future/optional/waived states
        # on the same command that has no manufacturing launch.
        profile=post(admin,'/api/admin/completeness/profiles',{'name':'Recette synthétique transversale'})['id']
        rules={}
        for key,kind in [('technical','Fiche technique'),('optional','Facultatif synthétique'),
                         ('future','Futur synthétique'),('waived','Dispensé synthétique'),('missing','Absent synthétique')]:
            rules[key]=post(admin,f'/api/admin/completeness/profiles/{profile}/rules',{
                'title':key+' de recette','folder':'jaune','document_type':kind,'due_phase':'preparation',
                'requires_validation':key=='technical'})['id']
        policy(admin,rules['technical'],requires_client_publication=True,obligation_scope='launch')
        policy(admin,rules['optional'],optional=True)
        policy(admin,rules['future'],days_after_launch=30,deadline_reference='order_created')
        for oid in (launchless,multiple):
            context(admin,oid,profile)
            assert admin.put(f'/api/orders/{oid}/completeness/rules/{rules["waived"]}/exception',
                json={'reason':'Dispense synthétique motivée sans présence de pièce'},headers=H).status_code==200
        states={row['rule_id']:row['status'] for row in report(buyer,launchless)['rows']}
        assert states[rules['optional']]=='optional' and states[rules['future']]=='not_due'
        assert states[rules['waived']]=='exception' and states[rules['missing']]=='missing'
        actions=buyer.get('/api/workspace/priorities').json()['items']
        assert any(a.get('order_id')==launchless and a['launch_id'] is None for a in actions)

        def put(oid,title,lid=None):
            data={'folder':'jaune','title':title,'doc_type':'Fiche technique'}
            if lid:data['launch_id']=lid
            result=buyer.post(f'/api/orders/{oid}/documents',data=data,
                files={'file':('fiche.txt',title.encode(),'text/plain')},headers=H)
            assert result.status_code==201,result.text
            return result.json()
        common_doc=put(launchless,'Pièce commune sans lancement')
        common_multiple=put(multiple,'Pièce commune du dossier à deux lancements')
        assert common_doc['launch_id'] is None and common_multiple['launch_id'] is None
        assert admin.get(f'/api/orders/{launchless}').json()['launches']==[]
        origin=put(multiple,'Fiche origine premier atelier',legacy)
        other_origin=put(multiple,'Fiche origine second atelier',second)
        search=buyer.get('/api/document-search',params={'client':'Client synthétique commun'}).json()
        assert {d['order_id'] for d in search['items']}=={launchless,multiple}
        assert {d['document_id'] for d in search['items']}=={common_doc['id'],common_multiple['id'],origin['id'],other_origin['id']}
        with SessionLocal() as db:
            quality_role=db.get(User,qualityid).roles[0].id
        post(admin,'/api/admin/approval-templates',{'name':'Validation synthétique qualité','folder_slug':'jaune',
            'document_type':'Fiche technique','stages':[{'name':'Contrôle qualité','reviewer_role_id':quality_role}]})
        run=post(buyer,f'/api/documents/{origin["id"]}/approval-runs')
        post(buyer,f'/api/approval-runs/{run["id"]}/decisions',{'decision':'approved'},403)
        decision=post(quality,f'/api/approval-runs/{run["id"]}/decisions',{'decision':'approved','comment':'Vérification synthétique documentée'},200)
        assert decision['status']=='approved'
        publication=post(admin,f'/api/launches/{legacy}/client-publications',{
            'document_version_id':origin['latest']['id'],'reason':'Publication synthétique explicitement autorisée'})
        binding=post(admin,'/api/partners/publications',{'partner_id':client_a,'publication_id':publication['id']})
        public_url=f'/api/partner/publications/{binding["id"]}/download'
        assert customer.get(public_url).content==b'Fiche origine premier atelier'
        assert other_customer.get(public_url).status_code==404
        assert supplier.get(public_url).status_code==404
        assert other_supplier.get(public_url).status_code==404
        assert any(r['status']=='present' for r in report(quality,multiple)['rows'] if r['rule_id']==rules['technical'])
        post(admin,f'/api/client-publications/{publication["id"]}/revoke',{'reason':'Retrait synthétique puis réexamen'},200)
        assert customer.get(public_url).status_code==404
        assert next(r for r in report(quality,multiple)['rows'] if r['rule_id']==rules['technical'] and r['launch_id']==legacy)['status']=='pending_publication'
        version2=buyer.post(f'/api/documents/{origin["id"]}/versions',files={'file':('v2.txt',b'Nouvelle version technique','text/plain')},headers=H)
        assert version2.status_code==201,version2.text
        version2=version2.json()['latest']['id']
        assert next(r for r in report(quality,multiple)['rows'] if r['rule_id']==rules['technical'] and r['launch_id']==legacy)['status']=='pending_validation'
        reopened=post(admin,f'/api/approval-runs/{run["id"]}/reopen',{
            'expected_version_id':version2,'reason':'Nouvelle version nécessitant une nouvelle approbation'})
        assert reopened['previous_run_id']==run['id'] and reopened['status']=='pending'
        post(quality,f'/api/approval-runs/{reopened["id"]}/decisions',{'decision':'approved','comment':'Nouvelle version contrôlée'},200)

        # Supplier portal correction -> non-admin quality -> canonical dossier.
        request=post(buyer,'/api/partners/requests',{'partner_id':supplier_a,'launch_id':legacy,
            'order_ref':'RECETTE-DEUX-LANCEMENTS','title':'Certificat de réception','doc_type':'Certificat'})
        rid=request['id']
        assert other_supplier.get(f'/api/partner/requests/{rid}').status_code==404
        assert customer.get(f'/api/partner/requests/{rid}').status_code==404
        assert other_customer.get(f'/api/partner/requests/{rid}').status_code==404
        initial=upload(supplier,rid,b'Certificat incomplet')
        post(quality,f'/api/partners/requests/{rid}/decision',{'version_id':initial['id'],'decision':'rejected','reason':'Signature synthétique absente'},200)
        corrected=upload(supplier,rid,b'Certificat signe avec provenance')
        assert corrected['number']==2
        post(quality,f'/api/partners/requests/{rid}/decision',{'version_id':corrected['id'],'decision':'approved','reason':'Signature synthétique vérifiée'},200)
        integrated=post(quality,f'/api/partners/requests/{rid}/integrate',{'submission_id':corrected['id'],'folder':'rose'})
        assert integrated['source']['account_id'] and integrated['source']['reviewed_by']==qualityid
        post(quality,f'/api/partners/requests/{rid}/integrate',{'submission_id':corrected['id'],'folder':'rose'},409)
        post(buyer,f'/api/partners/requests/{rid}/close',code=200)
        assert buyer.get(f'/api/orders/{multiple}/dossier').json()['order_id']==multiple
        assert supplier.get(f'/api/documents/{integrated["document"]["id"]}/versions/1/download').status_code==401

        # Planned, announced, declared, received, returned and cancelled differ.
        line=post(buyer,'/api/partners/order-lines',{'partner_id':supplier_a,'launch_id':legacy,
            'order_ref':'RECETTE-DEUX-LANCEMENTS','material_ref':'MAT-SYNTH','unit':'m','ordered':'10.125'})
        line_url=f'/api/partners/order-lines/{line["id"]}'
        payload={'source_id':corrected['id'],'quantity':'4.125','occurred_on':'2026-11-17',
                 'note':'Réception fractionnée normale','operation_key':'journey-first-receipt'}
        post(supplier,f'/api/partner/order-lines/{line["id"]}/announcements',{**payload,'operation_key':'journey-announcement'})
        post(supplier,f'/api/partner/order-lines/{line["id"]}/declarations',{**payload,'operation_key':'journey-declaration'})
        post(reception,line_url+'/receipts',{**payload,'kind':'planned','quantity':'10.125','operation_key':'journey-planned'})
        first=post(reception,line_url+'/receipts',{**payload,'kind':'received'})
        assert first['remaining']=='6.000' and first['assessment']=='normal_progress'
        assert (first['ordered'],first['planned'],first['announced'],first['declared'],first['received'],first['returned'])==('10.125','10.125','4.125','4.125','4.125','0.000')
        assert post(reception,line_url+'/receipts',{**payload,'kind':'received'})['received']=='4.125'
        second_receipt=post(reception,line_url+'/receipts',{**payload,'kind':'received','quantity':'6.000','operation_key':'journey-second-receipt'})
        assert second_receipt['status']=='complete'
        returned=post(reception,line_url+'/receipts',{**payload,'kind':'returned','quantity':'0.125','operation_key':'journey-return'})
        assert returned['received']=='10.000' and returned['returned']=='0.125' and returned['remaining']=='0.125'
        movement=next(m for m in returned['movements'] if m['kind']=='returned')
        cancelled=post(reception,line_url+f'/movements/{movement["id"]}/cancel',{'reason':'Retour synthétique saisi par erreur'},200)
        assert cancelled['received']=='10.125' and cancelled['remaining']=='0.000'
        receipt=next(r for r in reception.get('/api/receipts').json() if r['id']==line['id'])
        assert receipt['order_id']==multiple and receipt['launch_id']==legacy
        assert any(r['id']==line['id'] for r in supplier.get('/api/partner/order-lines').json())
        assert other_supplier.get('/api/partner/order-lines').json()==[]
        assert customer.get('/api/partner/order-lines').json()==[]

        # Revocation removes discovery and direct access even to historical bytes.
        assert buyer.get(f'/api/documents/{origin["id"]}/versions/1/download').status_code==200
        assert admin.delete(f'/api/orders/{multiple}/members/{buyid}',headers=H).json()['effective_access'] is False
        assert buyer.get(f'/api/documents/{origin["id"]}/versions/1/download').status_code==404
        assert buyer.get(f'/api/partners/requests/{rid}').status_code==404
        assert {r['order_id'] for r in buyer.get('/api/document-search').json()['items']}=={launchless}
        assert all(a.get('order_id')!=multiple for a in buyer.get('/api/workspace/priorities').json()['items'])
        assert quality.get(f'/api/documents/{origin["id"]}/versions/1/download').status_code==200
        expected_ids={common_doc['id'],common_multiple['id'],origin['id'],other_origin['id'],integrated['document']['id']}
        expected_decisions={run['id'],reopened['id']}

    # HTTP clients stopped: archive and restore real SQLite+blobs into a new root.
    archive=backup(DATA_DIR,tmp_path/'journey-backup.zip')
    fresh=restore(archive,tmp_path/'fresh-installation')
    validate(fresh/'framat.db',fresh/'files')
    with sqlite3.connect(fresh/'framat.db') as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
        assert expected_ids <= {r[0] for r in db.execute('SELECT id FROM documents')}
        assert expected_decisions == {r[0] for r in db.execute('SELECT run_id FROM approval_decisions')}
        assert db.execute('SELECT status FROM approval_runs WHERE id=?',(run['id'],)).fetchone()[0]=='approved'
        assert db.execute('SELECT status FROM approval_runs WHERE id=?',(reopened['id'],)).fetchone()[0]=='approved'
        assert db.execute('SELECT previous_run_id FROM approval_runs WHERE id=?',(reopened['id'],)).fetchone()[0]==run['id']
        assert db.execute('SELECT COUNT(*) FROM document_versions WHERE document_id=?',(origin['id'],)).fetchone()[0]==2
        assert db.execute('SELECT account_id,number,status FROM partner_submissions WHERE id=?',(corrected['id'],)).fetchone()[1:]==(2,'approved')
        assert db.execute('SELECT status,reason FROM partner_submissions WHERE id=?',(initial['id'],)).fetchone()==('rejected','Signature synthétique absente')
        assert db.execute('SELECT submission_id FROM partner_integrations WHERE version_id=?',(integrated['version_id'],)).fetchone()[0]==corrected['id']
        assert db.execute('SELECT status FROM client_publications WHERE id=?',(publication['id'],)).fetchone()[0]=='revoked'
        assert db.execute('SELECT COUNT(*) FROM partner_movement_cancellations').fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM partner_tokens WHERE consumed=0").fetchone()[0]==0
        for table in ('document_versions','partner_submissions'):
            for disk,digest in db.execute(f'SELECT disk_name,sha256 FROM {table}'):
                assert hashlib.sha256((fresh/'files'/disk).read_bytes()).hexdigest()==digest
