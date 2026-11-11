"""Isolated browser acceptance: real local server, synthetic data, no external sends."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import socket
import httpx
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
PWD='BrowserTestPassword2026!'
H={'X-Framatex-Request':'1'}

def main():
    with tempfile.TemporaryDirectory(prefix='framat-browser-') as directory:
        env={**os.environ,'FRAMATEX_DATA_DIR':directory,'FRAMATEX_SECRET_KEY':'browser-test-secret-'*4}
        env.pop('DATABASE_URL',None)
        subprocess.run([str(ROOT/'.venv/bin/python'),'-c',
            "from app.main import app; from app.migrate import migrate; migrate(); from app.core import SessionLocal,hash_password; from app.models import User,Role; db=SessionLocal(); u=User(name='Admin',email='admin@example.local',password_hash=hash_password('BrowserTestPassword2026!')); u.roles.append(Role(name='Administrateur')); db.add(u); db.commit()"],cwd=ROOT,env=env,check=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        with open(Path(directory)/'server.log','w') as log:
            server=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                with httpx.Client(base_url=base,headers=H) as api:
                    for _ in range(100):
                        try:
                            if api.get('/partners').status_code==200:break
                        except httpx.ConnectError:pass
                        time.sleep(.1)
                    def post(path,data):
                        r=api.post(path,json=data);r.raise_for_status();return r.json()
                    post('/api/auth/login',{'email':'admin@example.local','password':PWD})
                    lid=post('/api/launches',{'name':'Commande navigateur','client_name':'Client fictif'})['id']
                    org=post('/api/partners/organizations',{'name':'Fournisseur navigateur','kind':'supplier'})['id']
                    supplier_role=post(f'/api/partners/organizations/{org}/roles',{'name':'Fournisseur actif','permissions':['read','document.write','message.write','delivery.write']})
                    invitation=post(f'/api/partners/organizations/{org}/invitations',{'email':'supplier@example.local','role_id':supplier_role['id']})
                    post('/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD-BROWSER','title':'Certificat navigateur','doc_type':'Certificat'})
                    with sync_playwright() as p:
                        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
                        supplier=browser.new_context();page=supplier.new_page();errors=[]
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        page.goto(base+'/partners');page.get_by_text('Activer ou récupérer mon compte').click()
                        page.locator('#activate input[name=token]').fill(invitation['activation_token'])
                        page.locator('#activate input[name=password]').fill(PWD)
                        page.locator('#activate button').click();page.get_by_text('Compte activé. Vous pouvez vous connecter.').wait_for()
                        page.locator('#login input[name=email]').fill('supplier@example.local');page.locator('#login input[name=password]').fill(PWD)
                        page.locator('#login button').click();page.get_by_role('button',name='Ouvrir',exact=True).click()
                        page.get_by_label('Document à transmettre').set_input_files({'name':'certificat.txt','mimeType':'text/plain','buffer':b'Certificat fictif version 1'})
                        page.get_by_role('button',name='Transmettre une version').click();page.get_by_text('Version 1 · Vérification en attente',exact=False).wait_for()
                        admin=browser.new_context();admin.add_cookies([{'name':c.name,'value':c.value,'url':base} for c in api.cookies.jar])
                        review=admin.new_page();review.goto(base+'/partners');review.get_by_role('button',name='Administration',exact=False).click()
                        review.get_by_role('button',name='Ouvrir',exact=True).click();review.get_by_label('Motif de la décision').fill('Signature manquante')
                        review.get_by_role('button',name='Demander une correction').click();review.get_by_text('Version 1 · Correction demandée',exact=False).wait_for()
                        page.get_by_role('button',name='Actualiser',exact=True).click();page.get_by_role('button',name='Ouvrir',exact=True).click()
                        page.get_by_label('Document à transmettre').set_input_files({'name':'certificat.txt','mimeType':'text/plain','buffer':b'Certificat fictif signe version 2'})
                        page.get_by_role('button',name='Transmettre une version').click();page.get_by_text('Version 2 · Vérification en attente',exact=False).wait_for()
                        review.get_by_role('button',name='Actualiser',exact=True).click();review.get_by_role('button',name='Ouvrir',exact=True).click()
                        review.get_by_label('Motif de la décision').fill('Certificat conforme');review.get_by_role('button',name='Approuver',exact=True).click()
                        review.get_by_role('button',name='Intégrer au dossier interne',exact=True).click();review.get_by_text('Document intégré : Certificat navigateur',exact=True).wait_for()
                        review.get_by_role('button',name='Clôturer',exact=True).click();review.locator('#detail > p').filter(has_text='Clôturé').wait_for()
                        page.get_by_role('button',name='Actualiser',exact=True).click();page.get_by_role('button',name='Ouvrir',exact=True).click()
                        page.locator('#detail > p').filter(has_text='Clôturé').wait_for()
                        request_id=api.get('/api/partners/requests').json()[0]['id']
                        source_id=api.get(f'/api/partners/requests/{request_id}').json()['versions'][-1]['id']
                        line=post('/api/partners/order-lines',{'partner_id':org,'launch_id':lid,'order_ref':'CMD-BROWSER','material_ref':'TISSU-NAV','unit':'m','ordered':'100'})
                        for kind,quantity in [('planned','90'),('received','40')]:post(f'/api/partners/order-lines/{line["id"]}/receipts',{'kind':kind,'quantity':quantity,'operation_key':'browser-'+kind,'source_id':source_id,'note':'Mouvement navigateur vérifié','occurred_on':'2026-11-11'})
                        page.get_by_role('button',name='Actualiser',exact=True).click()
                        page.get_by_text('Historique des écarts et situations successives',exact=True).click()
                        page.get_by_text('Commandé − prévu : 10.000 · Déclaré − reçu : -40.000',exact=False).wait_for()
                        page.get_by_label('Intitulé administratif').fill('Attestation navigateur')
                        page.get_by_label('Fichier administratif').set_input_files({'name':'attestation.txt','mimeType':'text/plain','buffer':b'Attestation fictive'})
                        page.get_by_role('button',name='Déposer la pièce administrative').click()
                        page.get_by_role('link',name='Télécharger attestation.txt').wait_for()
                        review.get_by_role('button',name='Actualiser',exact=True).click()
                        review.get_by_text('Fiche administrative, historique et rôles',exact=True).click()
                        review.get_by_label('Motif de vérification administrative').fill('Attestation contrôlée')
                        review.get_by_role('button',name='Valider la pièce administrative').click()
                        expect(review.get_by_text('Attestation navigateur · v1 · Approuvé',exact=False)).to_have_count(1)
                        search=admin.new_page();search.goto(base+'/search')
                        search.get_by_label('Fournisseur d’origine').fill('Fournisseur navigateur')
                        search.get_by_role('button',name='Rechercher',exact=True).click()
                        expect(search.locator('#search-status')).to_have_text('1 version(s) autorisée(s) · Page 1')
                        with search.expect_download() as searched:search.get_by_role('link',name='Télécharger',exact=True).click()
                        assert Path(searched.value.path()).read_bytes()==b'Certificat fictif signe version 2'
                        search.get_by_label('Fournisseur d’origine').fill('Organisation inconnue')
                        search.get_by_role('button',name='Rechercher',exact=True).click()
                        expect(search.locator('#search-status')).to_have_text('0 version(s) autorisée(s) · Page 1')
                        search.close()
                        page.set_viewport_size({'width':390,'height':844})
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                        assert not errors,errors
                        screenshot=ROOT/'artifacts/partner-browser.png';screenshot.parent.mkdir(exist_ok=True)
                        page.screenshot(path=str(screenshot),full_page=True)
                        # Client journey: explicit order grant, publication, clarification and withdrawal.
                        client_org=post('/api/partners/organizations',{'name':'Client fictif','kind':'client'})['id']
                        client_role=post(f'/api/partners/organizations/{client_org}/roles',{'name':'Contact client','permissions':['read','message.write']})
                        client_invite=post(f'/api/partners/organizations/{client_org}/invitations',{'email':'client@example.local','role_id':client_role['id']})
                        order=post('/api/partners/client-orders',{'partner_id':client_org,'launch_id':lid,'reference':'Commande client navigateur','status':'Confirmée'})
                        doc_response=api.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Fiche client','doc_type':'Fiche technique'},files={'file':('client.txt',b'Publication client fictive','text/plain')})
                        doc_response.raise_for_status();doc=doc_response.json()
                        post(f'/api/documents/{doc["id"]}/reviews',{'decision':'approved'})
                        publication=post(f'/api/launches/{lid}/client-publications',{'document_version_id':doc['latest']['id'],'reason':'Publication client contrôlée navigateur'})
                        post('/api/partners/publications',{'partner_id':client_org,'publication_id':publication['id']})
                        client_context=browser.new_context();cp=client_context.new_page();cp.on('pageerror',lambda e:errors.append(str(e)))
                        cp.goto(base+'/partners');cp.get_by_text('Activer ou récupérer mon compte').click()
                        cp.locator('#activate input[name=token]').fill(client_invite['activation_token']);cp.locator('#activate input[name=password]').fill(PWD)
                        cp.locator('#activate button').click();cp.get_by_text('Compte activé. Vous pouvez vous connecter.').wait_for()
                        cp.locator('#login input[name=email]').fill('client@example.local');cp.locator('#login input[name=password]').fill(PWD);cp.locator('#login button').click()
                        cp.get_by_role('heading',name='Commande client navigateur',exact=True).wait_for()
                        with cp.expect_download() as download_info:cp.get_by_role('link',name='Télécharger la version publiée').click()
                        download=download_info.value
                        assert Path(download.path()).read_bytes()==b'Publication client fictive'
                        cp.get_by_label('Objet de la demande').fill('Clarification navigateur');cp.get_by_label('Votre question',exact=True).fill('Quelle version utiliser ?')
                        cp.get_by_role('button',name='Poser une question').click();cp.get_by_role('heading',name='Clarification navigateur · open',exact=True).wait_for()
                        thread_panel=cp.locator('#client-orders section').first
                        thread_panel.get_by_label('Pièce jointe privée').set_input_files({'name':'question.txt','mimeType':'text/plain','buffer':b'Question client fictive'})
                        thread_panel.get_by_label('Description de la pièce').fill('Information client');thread_panel.get_by_role('button',name='Joindre le fichier').click()
                        cp.get_by_role('link',name='Pièce jointe : question.txt',exact=False).wait_for()
                        review.get_by_role('button',name='Actualiser',exact=True).click()
                        review.get_by_label('Réponse à la clarification').fill('Utiliser la version publiée');review.get_by_role('button',name='Répondre',exact=True).click();review.get_by_text('Framatex : Utiliser la version publiée',exact=False).wait_for()
                        review.get_by_label('Motif du changement de traitement').fill('Réponse complète');review.get_by_role('button',name='Clôturer l’échange',exact=True).click()
                        review.get_by_role('heading',name='Clarification navigateur · closed',exact=True).wait_for()
                        cp.get_by_role('button',name='Actualiser',exact=True).click();cp.get_by_role('heading',name='Clarification navigateur · closed',exact=True).wait_for()
                        cp.set_viewport_size({'width':390,'height':844});assert cp.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                        cp.screenshot(path=str(ROOT/'artifacts/client-browser.png'),full_page=True)
                        post(f'/api/client-publications/{publication["id"]}/revoke',{'reason':'Retrait confirmé pendant recette navigateur'})
                        cp.get_by_role('button',name='Actualiser',exact=True).click()
                        cp.get_by_role('heading',name='Clarification navigateur · closed',exact=True).wait_for()
                        expect(cp.get_by_role('link',name='Télécharger la version publiée')).to_have_count(0)
                        review.get_by_role('button',name='Actualiser',exact=True).click()
                        review.get_by_text('Référentiel commandes et lancements',exact=True).click()
                        review.locator('#business-order select').select_option(client_org)
                        review.locator('#business-order input[name=reference]').fill('CMD-BROWSER')
                        review.get_by_role('button',name='Créer la commande',exact=True).click()
                        review.get_by_role('button',name='Rattacher à cette commande').click();review.get_by_role('button',name='Détacher ce lancement').wait_for()
                        review.get_by_role('button',name='Consulter la synthèse commande').click()
                        review.get_by_text('2 document(s), 1 demande(s) fournisseur',exact=False).wait_for()
                        profile=post('/api/admin/completeness/profiles',{'name':'Navigateur','description':'Profil contrôlé'})
                        rule=post(f'/api/admin/completeness/profiles/{profile["id"]}/rules',{'title':'Fiche publiée','folder':'jaune','document_type':'Fiche technique','due_phase':'preparation','requires_validation':True})
                        review.get_by_role('button',name='Actualiser',exact=True).click()
                        review.get_by_text('Conditions de complétude documentaire',exact=True).click()
                        review.locator('#policy-rule').select_option(rule['id'])
                        review.get_by_label('Type de commande requis').fill('Export')
                        review.get_by_label('Pièce facultative').check()
                        review.get_by_role('button',name='Enregistrer les conditions').click()
                        expect(review.locator('#notice')).to_have_text('Opération confirmée.')
                        policy=api.get('/api/admin/completeness/policies').json()[0]
                        assert policy['order_type']=='Export' and policy['optional']
                        permissions=[{'action':'launch.read'},{'action':'document.read','folder':'jaune'},{'action':'document.review','folder':'jaune'}]
                        role=post('/api/admin/roles',{'name':'Valideur navigateur','permissions':permissions})
                        deputy_role=post('/api/admin/roles',{'name':'Suppléant navigateur','permissions':permissions})
                        deputy=post('/api/admin/users',{'name':'Suppléant','email':'deputy@example.local','password':PWD,'role_ids':[deputy_role['id']]})
                        internal_page=admin.new_page();internal_page.on('pageerror',lambda e:errors.append(str(e)))
                        internal_page.goto(base+'/');internal_page.locator('[data-view=admin]').click()
                        internal_page.locator('#approval-new-template').click()
                        internal_page.locator('#at-name').fill('Circuit navigateur');internal_page.locator('#at-type').fill('Certificat')
                        internal_page.locator('.approval-stage-name').fill('Validation technique');internal_page.locator('.approval-stage-role').select_option(role['id'])
                        internal_page.locator('.approval-stage-days').fill('2');internal_page.locator('#approval-template-form button[type=submit]').click()
                        expect(internal_page.locator('#approval-template-form')).to_have_count(0)
                        internal_page.locator('[data-view=launches]').click();internal_page.locator(f'[data-launch="{lid}"]').click()
                        internal_page.locator('[data-approval-start]').click();internal_page.get_by_text('Échéance :',exact=False).wait_for()
                        internal_page.get_by_role('button',name='Déléguer l’étape').click()
                        internal_page.locator('#delegation-user').select_option(deputy['id'])
                        from datetime import datetime,timedelta
                        internal_page.locator('#delegation-expiry').fill((datetime.now()+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'))
                        internal_page.locator('#delegation-reason').fill('Remplacement temporaire du valideur')
                        internal_page.locator('#delegation-form button').click()
                        internal_page.get_by_text('Délégation : Suppléant',exact=False).wait_for()
                        source=api.get('/api/document-search?supplier=Fournisseur%20navigateur').json()['items'][0]
                        post(f'/api/document-versions/{source["version_id"]}/intake/confirm',{'field_key':'reference_matiere','value':'TISSU-NAV','source_excerpt':'Référence vérifiée pour cet essai'})
                        internal_page.locator('#quality-add-data').click()
                        internal_page.locator('#qd-version').select_option(source['version_id']);internal_page.locator('#qd-field').select_option('reference_matiere')
                        internal_page.once('dialog',lambda d:d.accept());internal_page.locator('#qd-confirmed').click()
                        expect(internal_page.locator('#quality-data-form')).to_have_count(0)
                        internal_page.locator('#quality-new-rule').click()
                        internal_page.locator('#qr-name').fill('Références navigateur');internal_page.locator('#qr-field').select_option('reference_matiere')
                        internal_page.locator('#qr-left-type').fill('Certificat');internal_page.locator('#qr-right-type').fill('Fiche technique')
                        internal_page.locator('#quality-rule-form button[type=submit]').click()
                        internal_page.get_by_text('Références navigateur',exact=True).wait_for()
                        internal_page.locator('#upload-doc').click()
                        internal_page.locator('#doc-file').set_input_files([{'name':'lot-1.txt','mimeType':'text/plain','buffer':b'Bon de livraison\nReference matiere : TISSU-LOT\nQuantite : 25 m'},{'name':'lot-2.txt','mimeType':'text/plain','buffer':b'Second document de lot'}])
                        data_transfer=internal_page.evaluate_handle("""() => {const dt=new DataTransfer();dt.items.add(new File(['extension interdite'],'bad.exe',{type:'application/octet-stream'}));return dt;}""")
                        internal_page.locator('#upload-drop').dispatch_event('drop',{'dataTransfer':data_transfer})
                        internal_page.locator('[data-upload-row="1"] [data-folder]').select_option('rose')
                        internal_page.locator('#upload-submit').click()
                        expect(internal_page.locator('#upload-status')).to_contain_text('2 / 3 fichier(s) déposé(s)')
                        internal_page.locator('#upload-submit').click()
                        expect(internal_page.locator('#upload-submit')).to_be_enabled()
                        expect(internal_page.locator('#upload-status')).to_contain_text('2 / 3 fichier(s) déposé(s)')
                        detail=api.get(f'/api/launches/{lid}').json()
                        assert sum(d['title']=='lot-1' for f in detail['folders'] for d in f['documents'])==1
                        assert next(f for f in detail['folders'] if f['slug']=='rose')['documents'][0]['title']=='lot-2'
                        internal_page.locator('#upload-finish').click()
                        lot=next(d for f in detail['folders'] for d in f['documents'] if d['title']=='lot-1')
                        internal_page.locator(f'[data-intake-version="{lot["latest"]["id"]}"]').click()
                        internal_page.locator('#if-quantite').fill('25')
                        internal_page.locator('[data-intake-confirm="quantite"]').click()
                        internal_page.get_by_text('quantite : 25 m',exact=True).wait_for()
                        internal_page.keyboard.press('Escape')
                        internal_page.locator('#intake-open').click()
                        internal_page.locator('#intake-file').set_input_files({'name':'bon-de-livraison.txt','mimeType':'text/plain','buffer':b'BON DE LIVRAISON\nQuantite : 25 m'})
                        internal_page.locator('#intake-file-form button[type=submit]').click()
                        expect(internal_page.locator('#intake-folder')).to_have_value('rose')
                        internal_page.locator('#intake-title').fill('Classement confirmé navigateur')
                        internal_page.locator('#intake-confirm-form button[type=submit]').click()
                        expect(internal_page.locator('#intake-confirm-form')).to_have_count(0)
                        assert api.get('/api/document-search?q=Classement%20confirm').json()['items'][0]['folder']=='rose'
                        internal_page.locator('[data-view=admin]').click()
                        internal_page.locator(f'[data-user-access="{deputy["id"]}"]').click()
                        internal_page.locator('#employee-active').uncheck();internal_page.locator('#employee-reason').fill('Fin de la délégation de démonstration')
                        internal_page.locator('#employee-access-form button').click()
                        expect(internal_page.locator('#employee-access-form')).to_have_count(0)
                        assert next(u for u in api.get('/api/admin/users').json() if u['id']==deputy['id'])['active'] is False
                        assert not errors,errors
                        browser.close()
                        print('PASS: supplier/client journeys, isolation revocation, administrative files, integration, search, order registry, completeness, approval delegation, batch drag-and-drop with partial failure, classification, human confirmation, employee access, mobile layouts')
            finally:
                server.terminate();server.wait(timeout=10)

if __name__=='__main__':main()
