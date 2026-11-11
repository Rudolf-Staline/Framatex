from fastapi.testclient import TestClient
from test_partners import app,setup,post,organization,activate,H,upload

def test_historical_differences_survive_later_returns_and_cancellations():
    with TestClient(app) as staff,TestClient(app) as supplier,TestClient(app) as other:
        lid=setup(staff);org=organization(staff,'Historique A');wrong=organization(staff,'Historique B')
        activate(staff,supplier,org,'history-a@sample.local');activate(staff,other,wrong,'history-b@sample.local')
        rid=post(staff,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'CMD-HIST','title':'Bon matière','doc_type':'Bon'})['id']
        version=upload(supplier,rid,b'Bon fictif')
        post(staff,f'/api/partners/requests/{rid}/decision',{'version_id':version['id'],'decision':'approved','reason':'Pièce contrôlée'},200)
        line=post(staff,'/api/partners/order-lines',{'partner_id':org,'launch_id':lid,'order_ref':'CMD-HIST','material_ref':'TISSU','unit':'m','ordered':'100'})
        base=f'/api/partners/order-lines/{line["id"]}'
        def move(kind,quantity,key):return post(staff,base+'/receipts',{'kind':kind,'quantity':quantity,'operation_key':key,'source_id':version['id'],'note':'Opération vérifiée','occurred_on':'2026-11-11'})
        move('planned','90','planned-history');first=move('received','40','receipt-history')
        frozen=first['discrepancy_history']
        assert frozen[-1]['received_minus_ordered']=='-60.000' and frozen[-1]['ordered_minus_planned']=='10.000'
        returned=move('returned','5','return-history')
        assert returned['discrepancy_history'][:2]==frozen and returned['received']=='35.000'
        mid=next(m['id'] for m in returned['movements'] if m['kind']=='returned')
        cancelled=post(staff,base+f'/movements/{mid}/cancel',{'reason':'Retour saisi deux fois, correction justifiée'},200)
        assert cancelled['discrepancy_history'][:3]==returned['discrepancy_history']
        last=cancelled['discrepancy_history'][-1]
        assert last['operation']=='cancelled' and last['remaining']=='60.000' and last['source_id']==version['id']
        assert supplier.get('/api/partner/order-lines').json()[0]['discrepancy_history']==cancelled['discrepancy_history']
        assert other.get('/api/partner/order-lines').json()==[]
