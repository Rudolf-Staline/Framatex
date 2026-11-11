from fastapi.testclient import TestClient
from test_partners import app,setup,post,organization,H

def test_additive_order_links_multiple_launches_and_preserves_documents():
    with TestClient(app) as staff:
        first=setup(staff);client=organization(staff,'Client A','client');supplier=organization(staff,'Supplier')
        second=post(staff,'/api/launches',{'name':'Second lancement','client_name':'Client A','order_ref':'CMD-ROOT','orli_ref':'ORLI-2'})['id']
        staff.patch(f'/api/launches/{first}',json={'order_ref':'CMD-ROOT','orli_ref':'ORLI-1'},headers=H)
        root=post(staff,'/api/orders',{'client_id':client,'reference':'CMD-ROOT'})
        for lid in [first,second]:post(staff,f'/api/orders/{root["id"]}/launches',{'launch_id':lid})
        for changes in [{'order_ref':'WRONG'},{'client_name':'Client B'},{'order_ref':None}]:
            assert staff.patch(f'/api/launches/{first}',json=changes,headers=H).status_code==409
        assert staff.patch(f'/api/launches/{first}',json={'name':'Nom corrigé'},headers=H).status_code==200
        doc=staff.post(f'/api/launches/{second}/documents',data={'folder':'rose','title':'Réception','doc_type':'Bon'},files={'file':('bon.txt',b'Reception','text/plain')},headers=H).json()
        post(staff,'/api/partners/requests',{'partner_id':supplier,'launch_id':first,'order_ref':'WRONG','title':'Certificat','doc_type':'Bon'},409)
        request=post(staff,'/api/partners/requests',{'partner_id':supplier,'launch_id':first,'order_ref':'CMD-ROOT','title':'Certificat','doc_type':'Bon'})
        result=staff.get(f'/api/orders/{root["id"]}').json()
        assert len(result['launches'])==2 and result['documents'][0]['id']==doc['id']
        assert result['documents'][0]['versions'][0]['sha256']==doc['latest']['sha256']
        assert result['supplier_requests'][0]['id']==request['id']
        assert {l['orli_ref'] for l in result['launches']}=={'ORLI-1','ORLI-2'}
        wrong=post(staff,'/api/launches',{'name':'Autre','client_name':'Client B','order_ref':'CMD-ROOT'})['id']
        post(staff,f'/api/orders/{root["id"]}/launches',{'launch_id':wrong},409)
        post(staff,f'/api/orders/{root["id"]}/launches',{'launch_id':first},409)
        assert staff.request('DELETE',f'/api/orders/{root["id"]}/launches/{second}',json={'reason':'Rattachement corrigé'},headers=H).status_code==409
        assert staff.get(f'/api/documents/{doc["id"]}/versions/1/download').content==b'Reception'
        with TestClient(app) as anonymous:assert anonymous.get(f'/api/orders/{root["id"]}').status_code==401
