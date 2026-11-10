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
                    invitation=post(f'/api/partners/organizations/{org}/invitations',{'email':'supplier@example.local'})
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
                        page.set_viewport_size({'width':390,'height':844})
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                        assert not errors,errors
                        screenshot=ROOT/'artifacts/partner-browser.png';screenshot.parent.mkdir(exist_ok=True)
                        page.screenshot(path=str(screenshot),full_page=True)
                        # Client journey: explicit order grant, publication, clarification and withdrawal.
                        client_org=post('/api/partners/organizations',{'name':'Client fictif','kind':'client'})['id']
                        client_invite=post(f'/api/partners/organizations/{client_org}/invitations',{'email':'client@example.local'})
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
                        assert not errors,errors
                        browser.close()
                        print('PASS: supplier integration and client order/publication/download/conversation/attachment/closure/withdrawal, mobile layouts')
            finally:
                server.terminate();server.wait(timeout=10)

if __name__=='__main__':main()
