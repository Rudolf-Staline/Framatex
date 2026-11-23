"""Parcours Chromium réel de la mémoire métier sur une base jetable."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from qa_platform_review import QA, platform_server, start_server, H, write_report
from demo_full_platform import Browser, internal_login
from windows_runtime import browser_executable


def run(qa, browser, server, captures):
    base=server.base
    view=Browser(browser,base,1440,captures)
    page=view.page
    page.set_default_timeout(12000)
    failures=[]
    page.on('requestfailed',lambda request:failures.append(request.url))
    page.on('dialog',lambda dialog:dialog.accept())
    page.on('response',lambda response: print('API_ERROR',response.status,response.url,response.text()[:500],flush=True) if response.status>=400 and '/api/workspace/' in response.url else None)
    try:
        internal_login(view,'recette@framatex.test',server.password)
        page.locator('.sidebar [data-ops-view="experience"]').click()
        expect(page.locator('h1')).to_contain_text('Mémoire métier')
        expect(page.locator('#bm-add')).to_be_visible()
        qa.check('Mémoire navigateur','Page et bouton Ajouter un retour',True)
        def add(category,body,launch=None,importance='important'):
            page.locator('#bm-add').click()
            page.select_option('#bm-type','fournisseur')
            page.fill('#bm-partner-search','Tissage Atlas Recette')
            page.locator('[data-bm-results] [data-bm-id], [data-bm-results] [data-bm-new]').first.wait_for()
            if category=='retard':
                page.locator('[data-bm-results] [data-bm-new]').click()
            else:
                page.locator('[data-bm-results] [data-bm-id]').first.click()
            if launch:
                page.select_option('#bm-launch',launch)
                expect(page.locator('#bm-folder')).to_have_value('jaune')
            page.select_option('#bm-category',category)
            page.select_option('#bm-importance',importance)
            page.fill('#bm-body',body)
            page.fill('#bm-recommendation','Vérifier la confirmation avant toute nouvelle commande.')
            page.locator('#bm-note-form button[type=submit]').click()
            expect(page.locator('#bm-results')).to_contain_text(body)
        add('retard','Livraison reçue avec douze jours de retard.',server.ids['B'])
        add('documentaire','Certificat transmis après la date demandée.',server.ids['B'])
        add('retour','Équipe réactive lors de la dernière livraison.',server.ids['B'],'information')
        page.fill('#q','Tissage Atlas Recette')
        expect(page.locator('#bm-results .bm-note')).to_have_count(3)
        page.locator('[data-bm-partner]').first.click()
        expect(page.locator('.bm-sheet .bm-note')).to_have_count(3)
        page.screenshot(path=str(captures/'1440-fiche-partenaire.png'),full_page=True)
        page.locator('.bm-sheet .bm-note',has_text='Retard de livraison').locator('[data-bm-edit]').click()
        page.select_option('#bm-edit-status','resolved')
        page.fill('#bm-edit-reason','Date confirmée et action corrective terminée.')
        page.locator('#bm-edit button[type=submit]').click()
        expect(page.locator('.bm-sheet .bm-note',has_text='Retard de livraison')).to_contain_text('Résolu')
        qa.check('Mémoire navigateur','Trois retours et fiche unique',True)
        page.locator('#close-modal').click()
        page.fill('#q','TISSAGE  ATLAS RECETTE')
        expect(page.locator('#bm-partners .bm-partner')).to_have_count(1)
        page.fill('#q','Tissage Atlas')
        expect(page.locator('#bm-partners .bm-partner')).to_have_count(1)
        qa.check('Mémoire navigateur','Recherche accent et casse',True)
        partner_id=page.locator('#bm-partners .bm-partner').first.get_attribute('data-bm-partner')
        page.locator('.sidebar [data-view="launches"]').click()
        expect(page.locator('h1')).to_contain_text('Commandes et lancements')
        page.locator('#ops-create').click()
        page.fill('#l-name','Nouvelle commande fournisseur mémoire')
        page.fill('#bm-launch-supplier','Tissage Atlas Recette')
        page.locator('[data-bm-id]').first.click()
        page.locator('#new-launch-form button[type=submit]').click()
        expect(page.locator('.bm-context')).to_contain_text('Historique du fournisseur')
        expect(page.locator('.bm-context')).to_contain_text('retard(s)')
        expect(page.locator('.bm-context')).to_contain_text('Source :')
        assert page.locator('.bm-context').count()==1
        qa.check('Mémoire navigateur','Nouvelle commande et vigilance sourcée',True)
        launch_id=page.evaluate('state.detail.id')
        page.locator('#dj-folders-back').click()
        expect(page.locator('.dj-folder')).to_have_count(4)
        page.locator('#dj-tab-controles').click()
        expect(page.locator('.dj-control-group')).to_have_count(3)
        page.screenshot(path=str(captures/'1440-categories-controles.png'),full_page=True)
        page.locator('#dj-tab-documents').click()
        page.locator('.dj-folder[data-folder="jaune"]').click()
        page.locator('#upload-doc').click()
        expect(page.locator('.du-optional-note')).not_to_have_attribute('open','')
        page.screenshot(path=str(captures/'1440-note-repliee.png'),full_page=True)
        page.locator('#close-modal').click()
        page.locator('#bm-qr').click()
        expect(page.locator('.paper-qr-image')).to_be_visible()
        page.screenshot(path=str(captures/'1440-qr-dossier.png'),full_page=True)
        label=page.locator('#paper-print')
        assert label.is_visible()
        with page.expect_download() as download:
            page.locator('.paper-qr-content a[download]').click()
        assert Path(download.value.path()).read_bytes().startswith(b'\x89PNG')
        page.locator('#close-modal').click()
        page.locator('#dj-folders-back').click()
        qa.check('Document navigateur','QR réel et téléchargement',True)
        for width in (1920,1440,1024,820,390):
            page.set_viewport_size({'width':width,'height':860})
            if width<=820 and page.locator('.drawer-open').count():page.keyboard.press('Escape')
            view.width=width
            view.check_page('commande-memoire')
            if width<=820:page.locator('.ops-drawer-toggle').click()
            page.locator('.sidebar [data-ops-view="experience"]').click()
            if width<=820 and page.locator('.drawer-open').count():page.keyboard.press('Escape')
            expect(page.locator('#bm-stats')).to_be_visible()
            view.check_page('memoire-metier')
            if width<=820:page.locator('.ops-drawer-toggle').click()
            page.locator('.sidebar [data-view="launches"]').click()
            if width<=820 and page.locator('.drawer-open').count():page.keyboard.press('Escape')
            page.evaluate('(id)=>openLaunch(id)',launch_id)
            expect(page.locator('.bm-context')).to_be_visible()
        qa.check('Mémoire navigateur','Cinq largeurs sans débordement',True)
        assert not view.errors and not failures,(view.errors,failures)
        qa.check('Mémoire navigateur','Aucune erreur JavaScript ou réseau',True)
    finally:view.close()
    # The same SQLite directory is reopened by a new Uvicorn process.
    server.server.terminate();server.server.wait(timeout=10)
    server.server,server.base=start_server(server.env)
    import httpx
    with httpx.Client(base_url=server.base,headers=H,timeout=20) as api:
        assert api.post('/api/auth/login',json={'email':'recette@framatex.test','password':server.password}).status_code==200
        detail=api.get(f'/api/workspace/partners/{partner_id}')
        assert detail.status_code==200 and len(detail.json()['notes'])==3
        assert api.get(f'/api/launches/{launch_id}/partners').json()[0]['id']==partner_id
    qa.check('Mémoire navigateur','Persistance après redémarrage réel du serveur',True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();captures=args.output/'captures';captures.mkdir(parents=True,exist_ok=True)
    qa=QA()
    with platform_server(qa) as server,sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=browser_executable(),headless=True)
        try:run(qa,browser,server,captures)
        finally:browser.close()
    return write_report(qa,args.output,'business-memory-results.json')

if __name__=='__main__':raise SystemExit(main())
