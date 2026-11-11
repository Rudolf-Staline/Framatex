from fastapi.testclient import TestClient
from test_partners import app,setup,post,H

def test_reference_confirmation_provenance_exact_comparison_and_resource_bounds():
    with TestClient(app) as staff:
        lid=setup(staff)
        versions=[]
        for title in ('Commande','Réception'):
            doc=staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':title,'doc_type':title},files={'file':('piece.txt',b'Reference matiere TISSU-A\nQuantite 100 m','text/plain')},headers=H).json()
            versions.append(doc['latest']['id'])
        rule=post(staff,'/api/admin/quality-rules',{'name':'Références matière','field_key':'reference_matiere','left_doc_type':'Commande','right_doc_type':'Réception','left_folder':'jaune','right_folder':'jaune'})
        def report():return staff.get(f'/api/launches/{lid}/quality').json()['rows'][0]
        assert report()['status']=='unavailable'
        fields=[]
        for vid,value in zip(versions,['TISSU-A','TISSU-B']):
            field=post(staff,f'/api/document-versions/{vid}/intake/confirm',{'field_key':'reference_matiere','value':value,'source_excerpt':'Référence matière vérifiée'})
            fields.append(field)
            post(staff,f'/api/document-versions/{vid}/data-from-confirmed',{'confirmed_id':field['id'],'field_key':'reference_matiere'})
        assert report()['status']=='difference'
        assert {p['confirmed_field_id'] for p in report()['pair']}=={f['id'] for f in fields}
        post(staff,f'/api/document-versions/{versions[0]}/data-from-confirmed',{'confirmed_id':fields[1]['id'],'field_key':'reference_matiere'},422)
        for value in ['1e-999999999','0e99999999','NaN','Infinity']:
            post(staff,f'/api/document-versions/{versions[0]}/data',{'field_key':'prix_unitaire','value':value,'unit':'MAD/pièce'},422)
        post(staff,f'/api/document-versions/{versions[0]}/data',{'field_key':'prix_unitaire','value':'12.123456789012','unit':'MAD/pièce'})
        post(staff,f'/api/launches/{lid}/quality/{rule["id"]}/decisions',{'signature':report()['signature'],'decision':'justified','note':'Équivalence vérifiée dans cet exemple fictif'})
        assert report()['decision']['status']=='justified'

def test_all_numeric_fields_multiple_sources_and_unit_mismatch():
    with TestClient(app) as staff:
        lid=setup(staff);documents=[]
        for title in ('Prévision','Réception'):
            documents.append(staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':title,'doc_type':title},files={'file':('piece.txt',b'Donnees fictives','text/plain')},headers=H).json())
        fields={'consommation_matiere':'m/pièce','quantite_lancement':'pièce','besoin_matiere_total':'m','prix_unitaire':'MAD/pièce','quantite_livree':'m','quantite_recue':'m','montant_total':'MAD'}
        for key,unit in fields.items():
            post(staff,'/api/admin/quality-rules',{'name':'Comparer '+key,'field_key':key,'left_doc_type':'Prévision','right_doc_type':'Réception','left_folder':'jaune','right_folder':'jaune','tolerance':'0.5'})
            for doc,value in zip(documents,['10','10.4']):post(staff,f'/api/document-versions/{doc["latest"]["id"]}/data',{'field_key':key,'value':value,'unit':unit})
        assert staff.get(f'/api/launches/{lid}/quality').json()['counts']['consistent']==7
        # Unit compatibility is checked before subtraction, never guessed or converted.
        post(staff,'/api/admin/quality-rules',{'name':'Unités incompatibles','field_key':'cout_matiere_unitaire','left_doc_type':'Prévision','right_doc_type':'Réception','left_folder':'jaune','right_folder':'jaune'})
        for doc,unit in zip(documents,['MAD/m','EUR/m']):post(staff,f'/api/document-versions/{doc["latest"]["id"]}/data',{'field_key':'cout_matiere_unitaire','value':'10','unit':unit})
        assert staff.get(f'/api/launches/{lid}/quality').json()['counts']['unit_mismatch']==1
        staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Autre prévision','doc_type':'Prévision'},files={'file':('autre.txt',b'Autre source','text/plain')},headers=H)
        assert staff.get(f'/api/launches/{lid}/quality').json()['counts']['ambiguous']==8
