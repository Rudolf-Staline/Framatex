"""Synthetic Chromium smoke for launch search beyond the first hundred choices."""
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


def main():
    with tempfile.TemporaryDirectory(prefix='framatex-selectors-browser-') as directory:
        os.environ['FRAMATEX_DATA_DIR']=directory
        os.environ['FRAMATEX_SECRET_KEY']='selectors-browser-synthetic-'*3
        os.environ.pop('DATABASE_URL',None)
        sys.path.insert(0,str(ROOT/'tests'))
        from test_consolidation_selectors import test_launch_selectors_search_beyond_first_hundred_without_disclosing_restricted_matches
        from test_partners import H,PWD
        test_launch_selectors_search_beyond_first_hundred_without_disclosing_restricted_matches()
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        with open(Path(directory)/'server.log','w') as log:
            server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=log)
            try:
                with httpx.Client(base_url=base,headers=H) as admin,httpx.Client(base_url=base,headers=H) as buyer:
                    for _ in range(100):
                        try:
                            if admin.get('/api/health').status_code==200:break
                        except httpx.ConnectError:pass
                        time.sleep(.1)
                    admin.post('/api/auth/login',json={'email':'admin@sample.local','password':PWD}).raise_for_status()
                    buyer.post('/api/auth/login',json={'email':'selectors@sample.local','password':PWD}).raise_for_status()
                    target=buyer.get('/api/launches?page=true&q=A_RECHERCHER').json()['items'][0]['id']
                    client=admin.post('/api/partners/organizations',json={'name':'Client cible','kind':'client'});client.raise_for_status()
                    order=admin.post('/api/orders',json={'client_id':client.json()['id'],'reference':'CMD-TARGET'});order.raise_for_status();oid=order.json()['id']
                    errors=[]
                    with sync_playwright() as p:
                        browser=p.chromium.launch(executable_path=os.getenv('FRAMATEX_BROWSER_EXECUTABLE'),headless=True,args=['--no-sandbox'])
                        admin_context=browser.new_context();admin_context.add_cookies([{'name':c.name,'value':c.value,'url':base} for c in admin.cookies.jar]);page=admin_context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                        page.goto(base+'/');page.get_by_role('button',name='Commandes',exact=True).first.click();page.get_by_role('button',name='Ouvrir le Dossier Jaune de CMD-TARGET',exact=True).click();page.get_by_role('button',name='Rattacher un lancement historique',exact=True).click()
                        page.get_by_label('Rechercher un lancement historique',exact=True).fill('A_RECHERCHER ancienne')
                        select=page.locator('#order-historical-launch');expect(select.locator('option')).to_have_count(1);assert select.input_value()==target
                        page.keyboard.press('Escape');expect(page.get_by_role('dialog')).to_have_count(0)
                        context=browser.new_context();context.add_cookies([{'name':c.name,'value':c.value,'url':base} for c in buyer.cookies.jar]);daily=context.new_page();daily.on('pageerror',lambda error:errors.append(str(error)))
                        daily.goto(base+'/partners');daily.locator('#staff').click();form=daily.locator('#request');expect(form).to_be_visible()
                        select=form.locator('select[name=launch_id]');search=form.get_by_label('Rechercher un lancement',exact=True)
                        search.fill('A_RECHERCHER');expect(select.locator('option')).to_have_count(1);assert select.input_value()==target;assert 'secret' not in select.inner_text()
                        expect(form.get_by_role('status')).to_contain_text('1 lancement(s) autorisé(s)')
                        search.fill('');expect(select.locator('option')).to_have_count(100);form.get_by_role('button',name='Lancements suivants',exact=True).click();expect(select.locator('option')).to_have_count(22);assert target in select.locator('option').evaluate_all('(options)=>options.map(option=>option.value)')
                        assert not errors,errors
                        result={'synthetic':True,'browser':'Chromium','scenarios':['historical order picker search beyond100','nonadmin daily search excludes restricted match','nonadmin daily next page reaches old launch'],'javascript_errors':errors,'result':'passed'}
                        (ROOT/'artifacts'/'consolidation-selectors-browser.json').write_text(json.dumps(result,indent=2)+'\n')
                        browser.close()
                    print('PASS: historical and nonadmin launch selectors beyond100; search and pagination preserve ACL')
            finally:
                server.terminate();server.wait(timeout=10)


if __name__=='__main__':main()
