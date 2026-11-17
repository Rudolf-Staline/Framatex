"""SQL pages count only authorized objects, with a corpus-independent query budget."""
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from test_partners import app,setup,post,organization,H,PWD
from app.core import SessionLocal,engine,hash_password
from app.models import User,Role,RolePermission,Document,DocumentVersion,Folder
from app.order_documents import OrderDossier,OrderMember


def seed(oid,amount,actor):
    with SessionLocal() as db:
        root=db.scalar(select(OrderDossier).where(OrderDossier.order_id==oid))
        folder=db.scalar(select(Folder).where(Folder.dossier_id==root.id,Folder.slug=='jaune'))
        for number in range(amount):
            doc=Document(folder_id=folder.id,title=f'Pièce {number:05}',doc_type='Certificat',created_by=actor)
            db.add(doc);db.flush()
            db.add_all([DocumentVersion(document_id=doc.id,number=v,original_name=f'v{v}.txt',disk_name=f'{doc.id}-{v}',size=1,sha256='a'*64,content_type='text/plain',uploaded_by=actor) for v in (1,2,3)])
        db.commit()


def measured(client,path):
    statements=[]
    def count(_conn,_cursor,statement,*_args):statements.append(statement)
    event.listen(engine,'before_cursor_execute',count)
    try:
        response=client.get(path);assert response.status_code==200,response.text
        return response.json(),len(statements)
    finally:event.remove(engine,'before_cursor_execute',count)


def test_canonical_client_search_and_sql_pages_before_permissions():
    with TestClient(app) as admin,TestClient(app) as reader:
        setup(admin);cid=organization(admin,'Même client','client');homonym=organization(admin,'Même client','client')
        visible=post(admin,'/api/orders',{'client_id':cid,'reference':'VISIBLE'})['id']
        hidden=post(admin,'/api/orders',{'client_id':homonym,'reference':'HIDDEN'})['id']
        with SessionLocal() as db:
            actor=db.scalar(select(User).where(User.email=='admin@sample.local')).id
            role=Role(name='Lecteur requêtes',grants=[RolePermission(action='launch.read'),RolePermission(action='document.read',folder_slug='jaune'),RolePermission(action='order.create')])
            user=User(name='Lecteur',email='queries@sample.local',password_hash=hash_password(PWD),roles=[role]);db.add(user);db.flush();db.add(OrderMember(order_id=visible,user_id=user.id));db.commit()
        seed(hidden,70,actor);seed(visible,30,actor)
        post(reader,'/api/auth/login',{'email':'queries@sample.local','password':PWD},200)
        result,small=measured(reader,'/api/document-search?limit=7&client=Même%20client')
        assert result['total']==30 and len(result['items'])==7
        assert {r['order_id'] for r in result['items']}=={visible}
        assert {r['client'] for r in result['items']}=={'Même client'}
        assert reader.get('/api/document-search',params={'client_id':homonym}).json()['total']==0
        assert reader.get('/api/document-search',params={'client_id':cid}).json()['total']==30
        seed(visible,130,actor)
        result,large=measured(reader,'/api/document-search?limit=7&client=Même%20client')
        assert result['total']==160 and len(result['items'])==7
        assert large<=small+2 and large<25,(small,large)
        page=reader.get('/api/orders?page=true&limit=1&sort=reference').json()
        assert page['total']==1 and page['items'][0]['id']==visible
        assert reader.get('/api/orders?page=true&offset=1').json()['items']==[]
        summary=reader.get(f'/api/orders/{visible}/dossier?summary=true').json()
        section=next(s for s in summary['sections'] if s['slug']=='jaune')
        assert section['total']==160 and section['documents']==[]
        docs=reader.get(f'/api/orders/{visible}/document-page?limit=7').json()
        assert docs['total']==160 and len(docs['items'])==7
        assert all('versions' not in d and d['latest']['number']==3 for d in docs['items'])
        doc=docs['items'][0]
        history=reader.get(f'/api/documents/{doc["id"]}/history?limit=2').json()
        assert history['total']==3 and [v['number'] for v in history['items']]==[3,2]
        assert len(reader.get(f'/api/documents/{doc["id"]}/history?offset=2').json()['items'])==1
        hidden_doc=admin.get(f'/api/orders/{hidden}/document-page?limit=1').json()['items'][0]['id']
        assert reader.get(f'/api/documents/{hidden_doc}/history').status_code==404

        assert reader.get('/api/partners/organizations').status_code==403
        clients=reader.get('/api/order-clients').json()
        assert {item['id'] for item in clients['items']}=={cid,homonym}
        assert all(set(item)=={'id','name'} for item in clients['items'])
        created=post(reader,'/api/orders',{'client_id':cid,'reference':'NON-ADMIN-CREATED'})
        assert reader.get(f'/api/orders/{created["id"]}/dossier').status_code==200
