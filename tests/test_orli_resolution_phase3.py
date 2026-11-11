from fastapi.testclient import TestClient
from test_partners import app,setup,post,H


def test_ambiguous_candidates_explicit_rejection_acceptance_and_reimport():
    with TestClient(app) as c:
        lid=setup(c)
        c.patch(f'/api/launches/{lid}',json={'order_ref':'CMD-1','orli_ref':'LF-01'},headers=H)
        second=post(c,'/api/launches',{'name':'Candidat B','client_name':'Client B','order_ref':'CMD-1','orli_ref':'LF-01'})['id']
        def imported(qty):
            import json
            r=c.post('/api/orli/imports',data={'mapping':json.dumps({k:k for k in ('orli_ref','order_ref','client_name','quantity')})},files={'file':('orli.csv',f'orli_ref,order_ref,client_name,quantity\nLF-01,CMD-1,Client A,{qty}\n'.encode(),'text/csv')},headers=H)
            assert r.status_code==201,r.text
            return c.get(f'/api/orli/imports/{r.json()["id"]}').json()['rows'][0]['id']
        record=imported(100);report=c.get(f'/api/orli/records/{record}/resolution').json()
        assert report['ambiguous'] and len(report['candidates'])==2
        assert any('client' in x['conflicts'] for x in report['candidates'] if x['launch_id']==second)
        payload={'decision':'reject','snapshot':report['snapshot'],'reason':'Références comparées, aucune association retenue actuellement'}
        post(c,f'/api/orli/records/{record}/resolution',payload)
        assert len(c.get(f'/api/orli/records/{record}/resolution').json()['history'])==1
        post(c,f'/api/orli/records/{record}/resolution',{**payload,'decision':'accept','launch_id':lid,'snapshot':'0'*64},409)
        post(c,f'/api/orli/records/{record}/resolution',{**payload,'decision':'accept','launch_id':lid})
        assert c.get(f'/api/launches/{lid}/orli-reconciliation').json()['linked']['record_id']==record
        changed=imported(120)
        assert c.get(f'/api/orli/records/{changed}/resolution').json()['history']==[]
        assert c.get(f'/api/launches/{lid}/orli-reconciliation').json()['linked']['record_id']==record
