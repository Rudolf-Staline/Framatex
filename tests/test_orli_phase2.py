from fastapi.testclient import TestClient
from test_partners import app,setup,post,H

def test_mapping_snapshot_comparison_and_explicit_refresh():
    with TestClient(app) as staff:
        lid=setup(staff)
        staff.patch(f'/api/launches/{lid}',json={'order_ref':'CMD','orli_ref':'O-1'},headers=H)
        profile=post(staff,'/api/orli/profiles',{'name':'Export standard','mapping':{'orli_ref':'ORLI','order_ref':'Commande','quantity':'Quantite','client_name':'Client'}})
        def imported(quantity):
            r=staff.post('/api/orli/imports',data={'profile_id':profile['id']},files={'file':('export.csv',f'ORLI,Commande,Quantite,Client\nO-1,CMD,{quantity},Client A\n'.encode(),'text/csv')},headers=H)
            assert r.status_code==201,r.text
            b=r.json();return b,staff.get(f'/api/orli/imports/{b["id"]}').json()['rows'][0]
        first,old=imported(100);second,new=imported(120)
        diff=staff.get(f'/api/orli/compare?previous={first["id"]}&current={second["id"]}').json()
        assert diff['rows'][0]['status']=='changed' and diff['rows'][0]['changes']['quantity']=={'before':'100','after':'120'}
        post(staff,f'/api/launches/{lid}/orli-reconciliation/link',{'record_id':old['id'],'confirmation':True,'reason':'Référence commande vérifiée'})
        payload={'expected_record_id':old['id'],'record_id':new['id'],'decision':'keep','reason':'Conserver provisoirement les valeurs précédentes'}
        post(staff,f'/api/orli/launches/{lid}/refresh',payload)
        assert staff.get(f'/api/launches/{lid}/orli-reconciliation').json()['linked']['record_id']==old['id']
        post(staff,f'/api/orli/launches/{lid}/refresh',{**payload,'decision':'accept'})
        post(staff,f'/api/orli/launches/{lid}/refresh',payload,409)
        assert staff.get(f'/api/launches/{lid}/orli-reconciliation').json()['linked']['record_id']==new['id']
        assert len(staff.get('/api/orli/refresh-decisions').json())==2
        assert staff.get(f'/api/orli/imports/{first["id"]}').json()['rows'][0]['quantity']=='100'
        with TestClient(app) as anonymous:assert anonymous.get('/api/orli/profiles').status_code==401
