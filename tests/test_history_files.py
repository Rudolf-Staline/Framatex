from tests.test_order_sheet import H, chef
from tests.test_document_preview import upload
import uuid

def test_deleted_document_history_records_every_version_and_author():
    c = chef()
    lid = c.post('/api/order-sheets', headers=H, json={'name':'Historique fichiers '+uuid.uuid4().hex[:6]}).json()['id']
    doc = upload(c, lid, 'ancien.txt', b'first version', folder='vert')
    r = c.post(f"/api/documents/{doc['id']}/versions", headers=H, files={'file': ('nouveau.txt', b'second version', 'text/plain')})
    assert r.status_code == 201, r.text
    r = c.request('DELETE', f"/api/documents/{doc['id']}", headers={**H, 'Content-Type':'application/json'}, content=b'{"reason":"Doublon historique"}')
    assert r.status_code == 204, r.text
    event = next(x for x in c.get('/api/workspace/activity',params={'launch_id':lid}).json()['items'] if x['action']=='document.delete')
    assert event['folder']=='vert' and event['actor']=='Chef fiche'
    assert {(f['number'],f['original_name']) for f in event['files']} == {(1,'ancien.txt'),(2,'nouveau.txt')}
