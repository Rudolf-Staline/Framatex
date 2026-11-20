"""The restoration preserves ACLs and annotations create immutable versions."""
import fitz
from fastapi.testclient import TestClient

from test_consolidation_access import grant, reader
from test_partners import H, PWD, app, organization, post, setup


def test_pdf_annotations_use_the_version_pipeline():
    with TestClient(app) as admin, TestClient(app) as member:
        setup(admin)
        client_id=organization(admin,'Client PDF','client')
        oid=post(admin,'/api/orders',{'client_id':client_id,'reference':'AT-PDF'})['id']
        with fitz.open() as source:
            source.new_page().insert_text((90, 110), 'Plan atelier')
            raw=source.tobytes()
        uploaded=admin.post(f'/api/orders/{oid}/documents',data={'folder':'jaune','title':'Plan PDF','doc_type':'Dossier technique'},
                            files={'file':('plan.pdf',raw,'application/pdf')},headers=H)
        assert uploaded.status_code==201, uploaded.text
        doc=uploaded.json()
        base=f"/api/documents/{doc['id']}"
        version=doc['latest']['id']
        raster=f'/api/document-versions/{version}/pdf-pages/1'
        assert admin.get(base+'/pdf').json()['can_write']
        assert admin.get(raster).headers['content-type']=='image/jpeg'
        assert admin.get(raster.rsplit('/',1)[0]+'/2').status_code==404
        payload={'base_version_id':version,'annotations':[{'kind':'text','page':1,
                 'points':[{'x':.2,'y':.2},{'x':.8,'y':.4}],'text':'Cote a verifier'}]}
        uid=reader()
        post(member,'/api/auth/login',{'email':'consolidation-reader@sample.local','password':PWD},200)
        assert member.get(raster).status_code==404
        assert member.post(base+'/pdf-annotations',json=payload,headers=H).status_code==404
        grant(admin,oid,uid)
        assert member.get(raster).status_code==200
        saved=post(admin,base+'/pdf-annotations',payload)
        assert saved['latest']['number']==2
        assert admin.get(base+'/versions/1/download').content==raw
        with fitz.open(stream=admin.get(base+'/versions/2/download').content,filetype='pdf') as annotated:
            page=annotated[0]
            assert next(page.annots()).info['content']=='Cote a verifier'
        assert not admin.get(base+'/pdf',params={'version_id':version}).json()['can_write']
        assert admin.post(base+'/pdf-annotations',json=payload,headers=H).status_code==409


def test_experience_search_resolves_cases_and_respects_order_membership():
    with TestClient(app) as admin, TestClient(app) as member:
        setup(admin)
        client_id=organization(admin,'Client REX','client')
        oid=post(admin,'/api/orders',{'client_id':client_id,'reference':'AT-REX'})['id']
        base='/api/order-experience'
        details={'title':'Mesure du gabarit','problem':'Le gabarit provoque un décalage.'}
        entry=post(admin,base,dict(details,order_id=oid,folder='jaune'))
        uid=reader()
        post(member,'/api/auth/login',{'email':'consolidation-reader@sample.local','password':PWD},200)
        assert member.get(base).json()['total']==0
        assert member.get(base,params={'order_id':oid}).status_code==404
        path=base+'/'+entry['id']
        update=dict(details,status='resolu',solution='Recentrer le gabarit et mesurer la première pièce.',revision=1)
        assert member.patch(path,json=update,headers=H).status_code==404
        grant(admin,oid,uid)
        assert member.get(base,params={'q':'gabarit','status':'ouvert'}).json()['total']==1
        response=member.patch(path,json=update,headers=H)
        assert response.status_code==200,response.text
        assert response.json()['revision']==2
        assert member.patch(path,json=update,headers=H).status_code==409
        assert member.get(base,params={'status':'resolu'}).json()['total']==1
        assert admin.delete(f'/api/orders/{oid}/members/{uid}',headers=H).status_code==200
        assert member.get(base).json()['total']==0
