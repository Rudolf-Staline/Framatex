"""Temporary SQLite, synthetic documents, real browser and axe checks; never production."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
H={'X-Framatex-Request':'1'}
PWD='BrowserTestPassword2026!'


def main():
    with tempfile.TemporaryDirectory(prefix='framat-phase3-browser-') as directory:
        env={**os.environ,'FRAMATEX_DATA_DIR':directory,'FRAMATEX_SECRET_KEY':'browser-phase3-test-'*4}
        env.pop('DATABASE_URL',None)
        subprocess.run([sys.executable,'-c',"from app.main import app;from app.migrate import migrate;migrate();from app.core import SessionLocal,hash_password;from app.models import User,Role;db=SessionLocal();u=User(name='Admin navigateur',email='admin@example.local',password_hash=hash_password('BrowserTestPassword2026!'));u.roles.append(Role(name='Administrateur'));db.add(u);db.commit()"],cwd=ROOT,env=env,check=True)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        with open(Path(directory)/'server.log','w') as log:
            server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                with httpx.Client(base_url=base,headers=H) as api:
                    for _ in range(100):
                        try:
                            if api.get('/api/health').status_code==200:break
                        except httpx.ConnectError:pass
                        time.sleep(.1)
                    def post(path,body):
                        r=api.post(path,json=body);r.raise_for_status();return r.json()
                    post('/api/auth/login',{'email':'admin@example.local','password':PWD})
                    client=post('/api/partners/organizations',{'name':'Client navigateur','kind':'client'})
                    order=post('/api/orders',{'client_id':client['id'],'reference':'CMD-NAV-001'})
                    other=post('/api/orders',{'client_id':client['id'],'reference':'CMD-NAV-002'})
                    for name in ('LF-NAV-001','LF-NAV-002'):post('/api/launches',{'name':name,'order_id':order['id']})
                    with sync_playwright() as p:
                        browser=p.chromium.launch(executable_path=os.getenv('FRAMATEX_BROWSER_EXECUTABLE'),headless=True,args=['--no-sandbox'])
                        context=browser.new_context();page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                        page.goto(base+'/');page.get_by_label('Adresse email').fill('admin@example.local');page.get_by_label('Mot de passe',exact=True).fill(PWD);page.get_by_role('button',name='Se connecter').click()
                        page.get_by_role('button',name='Commandes',exact=True).wait_for();page.get_by_role('button',name='Commandes',exact=True).click()
                        page.get_by_label('Rechercher une commande ou un client').fill('NAV-001')
                        expect(page.locator('#order-count')).to_have_text('1 commande(s) · Page 1')
                        page.get_by_role('button',name='Ouvrir le Dossier Jaune de CMD-NAV-001',exact=True).click()
                        page.get_by_role('heading',name='Dossier Jaune · CMD-NAV-001',exact=True).wait_for()
                        page.get_by_text('Déposer un document dans CMD-NAV-001',exact=False).click()
                        page.get_by_label('Titre',exact=True).fill('Fiche navigateur')
                        page.get_by_label('Type documentaire',exact=True).fill('Dossier technique')
                        page.get_by_label('Lancement d’origine (facultatif)').select_option(label='LF-NAV-001')
                        page.get_by_label('Fichier privé (20 Mo maximum)').set_input_files({'name':'fiche.txt','mimeType':'text/plain','buffer':b'Version navigateur 1'})
                        page.get_by_role('button',name='Déposer dans cette rubrique',exact=True).click()
                        page.get_by_role('link',name='Télécharger Fiche navigateur',exact=True).wait_for()
                        page.get_by_label('Filtrer par lancement').select_option(label='LF-NAV-002')
                        expect(page.get_by_text('Aucun document ne correspond à ces filtres.',exact=True)).to_be_visible()
                        page.get_by_label('Filtrer par lancement').select_option(label='LF-NAV-001')
                        page.get_by_role('button',name='Versions et historique',exact=True).click()
                        dialog=page.get_by_role('dialog');expect(dialog).to_be_visible()
                        for _ in range(8):
                            page.keyboard.press('Tab')
                            assert dialog.evaluate('(dialog)=>dialog.contains(document.activeElement)')
                        page.keyboard.press('Shift+Tab')
                        assert dialog.evaluate('(dialog)=>dialog.contains(document.activeElement)')
                        page.get_by_label('Nouvelle version',exact=True).set_input_files({'name':'fiche.txt','mimeType':'text/plain','buffer':b'Version navigateur 2'})
                        page.get_by_role('button',name='Enregistrer la nouvelle version',exact=True).click()
                        expect(page.get_by_role('cell',name='v2',exact=True)).to_be_visible()
                        with page.expect_download() as download:page.get_by_role('link',name='Télécharger Fiche navigateur',exact=True).click()
                        assert Path(download.value.path()).read_bytes()==b'Version navigateur 2'
                        page.get_by_role('button',name='Versions et historique',exact=True).click()
                        page.keyboard.press('Escape');expect(page.get_by_role('dialog')).to_have_count(0)
                        results=[]
                        for width in (360,390,768,1440):
                            page.set_viewport_size({'width':width,'height':960})
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'overflow {width}'
                            page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
                            report=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
                            results.append({'screen':'dossier','width':width,'violations':report})
                            assert not report,report
                        page.screenshot(path=str(ROOT/'artifacts/phase3-order-browser.png'),full_page=True)
                        page.set_viewport_size({'width':1440,'height':960});page.get_by_role('button',name='Commandes',exact=True).first.click()
                        page.get_by_role('button',name='Ouvrir le Dossier Jaune de CMD-NAV-002',exact=True).click()
                        expect(page.get_by_text('Aucun document ne correspond à ces filtres.',exact=True)).to_be_visible()
                        page.route('**/api/orders',lambda route:route.abort('failed'))
                        page.get_by_role('button',name='Commandes',exact=True).first.click()
                        expect(page.locator('#toast')).to_contain_text('Connexion interrompue')
                        page.unroute('**/api/orders')
                        page.get_by_role('button',name='Commandes',exact=True).first.click()
                        expect(page.locator('#order-count')).to_have_text('2 commande(s) · Page 1')
                        page.locator('.sidebar [data-view="orli"]').click()
                        page.get_by_label('Correspondance des colonnes (JSON)').fill(json.dumps({key:key for key in ('orli_ref','order_ref','client_name','quantity')}))
                        page.get_by_label('Fichier CSV UTF-8 ou XLSX (3 Mo maximum)').set_input_files({'name':'orli-synthetic.csv','mimeType':'text/csv','buffer':b'orli_ref,order_ref,client_name,quantity\nLF-ORLI-001,CMD-NAV-001,Client navigateur,100\n'})
                        page.get_by_role('button',name='Importer sans modifier les lancements',exact=True).click()
                        page.get_by_role('button',name='Examiner les associations',exact=True).click()
                        page.get_by_label('Justification de la décision').fill('Candidats examinés, association rejetée provisoirement pour contrôle')
                        page.get_by_role('button',name='Enregistrer cette décision',exact=True).click()
                        page.get_by_role('button',name='Voir les lignes',exact=True).click()
                        page.get_by_role('button',name='Examiner les associations',exact=True).click()
                        page.get_by_text('Historique des décisions (1)',exact=True).wait_for()
                        page.get_by_label('Candidat retenu').select_option(label='LF-NAV-001 · CMD-NAV-001')
                        page.get_by_label('Décision',exact=True).select_option('accept')
                        page.get_by_label('Justification de la décision').fill('Commande et client vérifiés, sélection explicite du premier lancement')
                        page.get_by_label('J’ai examiné les divergences présentées.').check()
                        page.get_by_role('button',name='Enregistrer cette décision',exact=True).click()
                        page.get_by_role('heading',name='Imports ORLI.',exact=False).wait_for()
                        for i in range(28):post('/api/launches',{'name':f'Pagination {i:02d}','order_id':other['id']})
                        # Check the existing internal surfaces, not just the new dossier screen.
                        for view in ('home','orders','suppliers','clients','receipts','validations','launches','actions','notifications','orli','admin','audit'):
                            page.locator(f'.sidebar [data-view="{view}"]').click()
                            page.wait_for_function('(view)=>document.querySelector(".sidebar .active")?.dataset.view===view',arg=view)
                            for width in (360,390,768,1440):
                                page.set_viewport_size({'width':width,'height':960})
                                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(view,width)
                                page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
                                violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
                                results.append({'screen':view,'width':width,'violations':violations})
                        page.locator('.sidebar [data-view="launches"]').click()
                        page.get_by_role('button',name='Page suivante',exact=True).click()
                        expect(page.locator('.table-pagination [role=status]')).to_contain_text('Page 2 / 2')
                        page.locator('#launch-search').fill('LF-NAV-001')
                        page.get_by_role('button',name='Ouvrir le lancement LF-NAV-001',exact=True).click()
                        page.locator('.detail-layout').wait_for()
                        for width in (360,390,768,1440):
                            page.set_viewport_size({'width':width,'height':960})
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),('launch-detail',width)
                            page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
                            violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
                            results.append({'screen':'launch-detail','width':width,'violations':violations})
                        page.goto(base+'/search');page.get_by_label('Commande',exact=True).fill('CMD-NAV-001');page.get_by_role('button',name='Rechercher',exact=True).click()
                        expect(page.locator('#search-status')).to_have_text('1 version(s) autorisée(s) · Page 1')
                        for url in ('/search','/partners'):
                            page.goto(base+url)
                            for width in (360,390,768,1440):
                                page.set_viewport_size({'width':width,'height':960})
                                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(url,width)
                                page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
                                violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))}")
                                results.append({'screen':url,'width':width,'violations':violations});assert not violations,violations
                        assert not errors,errors
                        (ROOT/'artifacts/phase3-browser.json').write_text(json.dumps({'synthetic_data':True,'checks':results,'console_errors':errors,'full_wcag_audit':False},indent=2))
                        assert not [r for r in results if r['violations']], [r for r in results if r['violations']]
                        browser.close();print('Browser phase 3: order isolation, upload, origin filters, versions, downloads, keyboard and axe/mobile checks passed')
            finally:
                server.terminate();server.wait(timeout=10)
                if sys.exc_info()[0]:print((Path(directory)/'server.log').read_text()[-5000:],file=sys.stderr)

if __name__=='__main__':main()
