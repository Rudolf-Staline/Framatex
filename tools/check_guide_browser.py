"""Full Guide journeys with temporary DB, fake Gemini and no business action from a tour."""
import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];H={'X-Framatex-Request':'1'};PWD='GuideBrowserPassword2026!'


def expect_step(page,number,target):
 expect(page.locator('.driver-popover-title')).to_contain_text(f'{number}/4')
 expect(page.locator('.driver-active-element')).to_have_attribute('data-guide-target',target)
 expect(page.locator('.driver-active-element')).to_be_visible()


def exercise_upload_tour(page,order_id):
 # Enter through the UI, preserving the scenario that failed on main.
 page.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click()
 page.get_by_label('Rechercher dans l’aide',exact=True).fill('Ajouter une fiche technique')
 page.locator('#guide-panel form button').click();page.locator('[data-guide-procedure=upload_technical_document]').click()
 expect(page.locator('#guide-status')).to_contain_text('IA indisponible')
 page.get_by_role('button',name='Me montrer comment faire',exact=True).click()
 expect_step(page,1,'orders-screen');page.locator('.driver-popover-next-btn').click()
 page.get_by_label('Objet autorisé',exact=True).select_option(order_id)
 page.get_by_role('button',name='Utiliser cette sélection',exact=True).click()
 expect_step(page,2,'order-dossier')
 page.locator('.driver-popover-next-btn').click();expect_step(page,3,'order-section-jaune')
 page.keyboard.press('ArrowLeft');expect_step(page,2,'order-dossier')
 page.locator('.driver-popover-next-btn').click();expect_step(page,3,'order-section-jaune')
 page.get_by_role('button',name='Retour',exact=True).click();expect_step(page,2,'order-dossier')
 page.keyboard.press('ArrowRight');expect_step(page,3,'order-section-jaune')
 page.keyboard.press('ArrowRight');expect_step(page,4,'order-document-form')
 field=page.locator('#order-document-title');field.fill('Fiche de recette')
 field.press('Home');field.press('ArrowRight');field.press('ArrowLeft');page.keyboard.type('X')
 expect(field).to_have_value('XFiche de recette');expect_step(page,4,'order-document-form')
 page.locator('#order-document-origin').focus();page.keyboard.press('ArrowLeft')
 expect_step(page,4,'order-document-form')
 field.focus();page.keyboard.press('Escape');expect(page.locator('.driver-popover')).to_have_count(0)
 page.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click();page.get_by_role('button',name='Mes visites',exact=True).click()
 card=page.locator('#guide-content article').filter(has=page.get_by_role('heading',name='Ajouter une fiche technique',exact=True))
 expect(card).to_contain_text('En pause');card.get_by_role('button',name='Reprendre',exact=True).click()
 expect_step(page,4,'order-document-form');expect(field).to_have_value('XFiche de recette')
 page.screenshot(path=str(ROOT/'artifacts/guide-tour.png'),full_page=True)
 page.get_by_role('button',name='Terminer',exact=True).click();expect(page.locator('.driver-popover')).to_have_count(0)


def main():
 with tempfile.TemporaryDirectory(prefix='framat-guide-browser-') as temp:
  env={**os.environ,'FRAMATEX_DATA_DIR':temp,'FRAMATEX_SECRET_KEY':'guide-browser-secret-'*4,'FRAMATEX_GUIDE_AI_ENABLED':'1','GEMINI_API_KEY':'synthetic-test-key','FRAMATEX_GUIDE_REQUESTS_PER_MINUTE':'200','FRAMATEX_GUIDE_HTTP_REQUESTS_PER_MINUTE':'2000'};env.pop('DATABASE_URL',None)
  subprocess.run([sys.executable,'-c',"from app.main import app;from app.migrate import migrate;migrate();from app.core import SessionLocal,hash_password;from app.models import User,Role;db=SessionLocal();u=User(name='Admin Guide',email='admin@guide.local',password_hash=hash_password('GuideBrowserPassword2026!'));u.roles.append(Role(name='Administrateur'));db.add(u);db.commit()"],env=env,cwd=ROOT,check=True)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  base=f'http://127.0.0.1:{port}'
  server_code="import uvicorn;from app import guide_gemini;\ndef unavailable(_):raise TimeoutError('synthetic timeout')\nguide_gemini.generate=unavailable\nuvicorn.run('app.main:app',host='127.0.0.1',port="+str(port)+")"
  with open(Path(temp)/'server.log','w') as log:
   server=subprocess.Popen([sys.executable,'-c',server_code],cwd=ROOT,env=env,stdout=log,stderr=log)
   try:
    with httpx.Client(base_url=base,headers=H) as api:
     for _ in range(100):
      try:
       if api.get('/api/health').status_code==200:break
      except httpx.ConnectError:pass
      time.sleep(.1)
     def post(path,payload):
      r=api.post(path,json=payload);r.raise_for_status();return r.json()
     post('/api/auth/login',{'email':'admin@guide.local','password':PWD})
     org=post('/api/partners/organizations',{'kind':'client','name':'Client Guide'})
     order=post('/api/orders',{'client_id':org['id'],'reference':'CMD-GUIDE'})
     lid=post('/api/launches',{'order_id':order['id'],'name':'LF-GUIDE'})['id']
     supplier=post('/api/partners/organizations',{'kind':'supplier','name':'Fournisseur Guide'})
     srole=post(f'/api/partners/organizations/{supplier["id"]}/roles',{'name':'Guide fournisseur','permissions':['read','document.write','message.write','delivery.write']})
     sinvite=post(f'/api/partners/organizations/{supplier["id"]}/invitations',{'email':'supplier@guide.local','role_id':srole['id']})
     request=post('/api/partners/requests',{'partner_id':supplier['id'],'launch_id':lid,'order_ref':'CMD-GUIDE','title':'Certificat Guide','doc_type':'Certificat'})
     crole=post(f'/api/partners/organizations/{org["id"]}/roles',{'name':'Guide client','permissions':['read','message.write']})
     cinvite=post(f'/api/partners/organizations/{org["id"]}/invitations',{'email':'client@guide.local','role_id':crole['id']})
     client_order=post('/api/partners/client-orders',{'partner_id':org['id'],'launch_id':lid,'reference':'CMD-GUIDE'})
     rrole=post('/api/admin/roles',{'name':'Guide réception','permissions':[{'action':'launch.read'},{'action':'document.read','folder':'rose'}]})
     post('/api/admin/users',{'name':'Lecteur Guide','email':'reader@guide.local','password':PWD,'role_ids':[rrole['id']]})
     with sync_playwright() as p:
      browser=p.chromium.launch(executable_path=os.getenv('FRAMATEX_BROWSER_EXECUTABLE'),headless=True,args=['--no-sandbox']);ctx=browser.new_context(reduced_motion="reduce");page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
      page.goto(base+'/');page.get_by_label('Adresse email').fill('admin@guide.local');page.get_by_label('Mot de passe',exact=True).fill(PWD);page.get_by_role('button',name='Se connecter',exact=False).click()
      page.get_by_text('Bienvenue sur Framatex ! Souhaitez-vous découvrir votre espace de travail ?',exact=True).wait_for()
      page.get_by_role('button',name='Plus tard',exact=True).click()
      exercise_upload_tour(page,order['id'])
      assert sum(len(s['documents']) for s in api.get(f'/api/orders/{order["id"]}/dossier').json()['sections'])==0
      progress=api.get('/api/guide/progress').json();assert next(r for r in progress if r['tour_id']=='tour_upload_technical_document')['status']=='finished'
      # Two fresh sessions exercise the same entry and assertions with slow frames.
      for iteration in range(2):
       repeated=browser.new_context(reduced_motion='reduce');trial=repeated.new_page();trial.on('pageerror',lambda e:errors.append(str(e)))
       trial.add_init_script("const nativeRAF=window.requestAnimationFrame;window.requestAnimationFrame=callback=>nativeRAF.call(window,time=>setTimeout(()=>callback(time),200));")
       trial.goto(base+'/');trial.get_by_label('Adresse email').fill('admin@guide.local');trial.get_by_label('Mot de passe',exact=True).fill(PWD);trial.get_by_role('button',name='Se connecter',exact=False).click();trial.locator('.sidebar').wait_for()
       exercise_upload_tour(trial,order['id']);repeated.close()
      assert sum(len(s['documents']) for s in api.get(f'/api/orders/{order["id"]}/dossier').json()['sections'])==0
      # A conditional target is absent until the user opens a form: explicit suspension.
      page.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click();page.get_by_label('Rechercher dans l’aide').fill('Créer une commande');page.locator('#guide-panel form button').click();page.locator('[data-guide-procedure=create_order]').click();page.get_by_role('button',name='Me montrer comment faire',exact=True).click();page.locator('.driver-popover-next-btn').click();page.locator('.driver-popover-next-btn').click()
      expect(page.locator('#guide-status')).to_contain_text('La visite est suspendue',timeout=10000)
      assert next(r for r in api.get('/api/guide/progress').json() if r['tour_id']=='tour_create_order')['status']=='missing'
      page.get_by_role('button',name='Quitter la visite',exact=True).click()
      # Multi-page tour: application -> dedicated document search, then pause/resume.
      page.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click();page.get_by_label('Rechercher dans l’aide').fill('Rechercher et filtrer les documents');page.locator('#guide-panel form button').click();page.locator('[data-guide-procedure=search_documents]').click();page.get_by_role('button',name='Me montrer comment faire',exact=True).click()
      page.wait_for_url('**/search');page.locator('.driver-popover-title').wait_for();page.locator('.driver-popover-next-btn').click();page.keyboard.press('Escape');expect(page.locator('.driver-popover')).to_have_count(0);assert next(r for r in api.get('/api/guide/progress').json() if r['tour_id']=='tour_search_documents')['status']=='paused'
      page.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click();page.get_by_role('button',name='Mes visites',exact=True).click()
      card=page.locator('#guide-content article').filter(has=page.get_by_role('heading',name='Rechercher et filtrer les documents',exact=True));card.get_by_role('button',name='Reprendre',exact=True).click();expect(page.locator('.driver-popover-progress-text')).to_contain_text('2')
      page.locator('.driver-popover-close-btn').click()
      page.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click()
      audits=[]
      for width in (360,390,768,1440):
       page.set_viewport_size({'width':width,'height':960});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
       page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text());issues=page.evaluate("async()=>{let r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(x=>({id:x.id,nodes:x.nodes.map(n=>n.target)}))}");audits.append({'width':width,'issues':issues});assert not issues,issues
      page.screenshot(path=str(ROOT/'artifacts/guide-internal.png'),full_page=True)
      # The full-page procedure can resume a real order tour in the main application.
      help_page=ctx.new_page();help_page.on('pageerror',lambda e:errors.append(str(e)));help_page.goto(base+'/help?surface=internal#procedure/upload_technical_document');help_page.get_by_role('heading',name='Ajouter une fiche technique',exact=True).wait_for();help_page.screenshot(path=str(ROOT/'artifacts/guide-help.png'),full_page=True);help_page.get_by_role('button',name='Me montrer comment faire',exact=True).click();help_page.locator('.driver-popover-next-btn').click();help_page.get_by_label('Objet autorisé',exact=True).select_option(order['id']);help_page.get_by_role('button',name='Utiliser cette sélection',exact=True).click();help_page.wait_for_url(base+'/');expect(help_page.locator('.driver-popover-title')).to_contain_text('2/4');help_page.locator('.driver-popover-close-btn').click();help_page.close()
      # Help remains useful for an employee without administrative or green access.
      restricted=browser.new_context();rp=restricted.new_page();rp.goto(base+'/');rp.get_by_label('Adresse email').fill('reader@guide.local');rp.get_by_label('Mot de passe',exact=True).fill(PWD);rp.get_by_role('button',name='Se connecter',exact=False).click();rp.locator('.sidebar').wait_for();rp.get_by_role('button',name='Commencer la visite',exact=True).click();rp.locator('.driver-popover').wait_for();rp.locator('.driver-popover-close-btn').click();rp.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click();rp.get_by_label('Rechercher dans l’aide').fill('Où trouver une facture ?');rp.locator('#guide-panel form button').click();expect(rp.locator('#guide-content')).to_contain_text('ne dispose pas de procédure');assert rp.locator('[data-guide-procedure=find_invoice]').count()==0
      rp.get_by_role('button',name='Mes visites',exact=True).click();employee_card=rp.locator('#guide-content article').filter(has=rp.get_by_role('heading',name='Découvrir mon espace',exact=True));employee_card.get_by_role('button',name='Ignorer cette visite',exact=True).click();expect(rp.locator('#guide-content article').filter(has=rp.get_by_role('heading',name='Découvrir mon espace',exact=True))).to_contain_text('Ignorée')
      # Separate partner identities, onboarding and contextual request selection.
      for kind,invite,email in [('supplier',sinvite,'supplier@guide.local'),('client',cinvite,'client@guide.local')]:
       partner=browser.new_context();pp=partner.new_page();pp.on('pageerror',lambda e:errors.append(str(e)));pp.goto(base+'/partners');pp.get_by_text('Activer ou récupérer mon compte',exact=True).click();pp.locator('#activate input[name=token]').fill(invite['activation_token']);pp.locator('#activate input[name=password]').fill(PWD);pp.locator('#activate button').click();pp.get_by_text('Compte activé. Vous pouvez vous connecter.',exact=True).wait_for();pp.locator('#login input[name=email]').fill(email);pp.locator('#login input[name=password]').fill(PWD);pp.locator('#login button').click();pp.locator('#workspace').wait_for(state='visible');pp.get_by_role('button',name='Commencer la visite',exact=True).click();pp.locator('.driver-popover').wait_for();pp.locator('.driver-popover-next-btn').click();pp.locator('.driver-popover-close-btn').click();pp.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click();pp.get_by_role('button',name='Mes visites',exact=True).click();assert pp.get_by_role('heading',name='Gérer les comptes et droits',exact=True).count()==0
       pp.get_by_role('button',name='Fermer Framatex Guide',exact=True).click()
       if kind=='supplier':
        awaitable="tour_supplier_upload"
       else:awaitable="tour_client_questions"
       pp.evaluate("id=>{void FramatexGuide.startTour(id)}",awaitable)
       if kind=='supplier':pp.locator('.driver-popover-next-btn').click()
       pp.get_by_label('Objet autorisé',exact=True).select_option(request['id'] if kind=='supplier' else client_order['id'])
       pp.get_by_role('button',name='Utiliser cette sélection',exact=True).click();pp.locator('.driver-popover').wait_for();pp.locator('.driver-popover-close-btn').click()
       if kind=='supplier':assert api.get('/api/partners/requests/'+request['id']).json()['versions']==[]
       else:assert api.get('/api/partners/client-orders/'+client_order['id']+'/threads').json()==[]
       pp.get_by_role('button',name='Ouvrir Framatex Guide',exact=True).click()
       pp.screenshot(path=str(ROOT/f'artifacts/guide-{kind}.png'),full_page=True)
      # Every declared target is checked by source contracts; real order and portal targets above.
      assert not errors,errors
      (ROOT/'artifacts/guide-browser.json').write_text(json.dumps({'synthetic':True,'gemini':'simulated timeout','audits':audits,'console_errors':errors,'no_business_write_from_tour':True,'keyboard':{'runs':3,'delayed_frame_runs':2,'frame_delay_ms':200,'left_3_to_2':True,'highlighted_target_verified':True,'previous_button':True,'text_and_select_arrows_preserved':True,'escape_and_resume':True,'finished':True}},indent=2))
      browser.close();print('PASS Guide: first login, local fallback, order selection, multi-page tours, progress, resume, four profiles, keyboard and mobile/axe')
   finally:
    server.terminate();server.wait(timeout=10)
    if sys.exc_info()[0]:print((Path(temp)/'server.log').read_text()[-6000:],file=sys.stderr)

if __name__=='__main__':main()
