"""Exercise real saved PDF bytes, authorization and immutable version semantics."""
import io
import fitz
from tests.test_meeting_corrections import system, login, launch, doc, H, PASSWORD


def pdf_bytes(rotation=0):
    pdf=fitz.open(); page=pdf.new_page(width=400,height=600)
    page.insert_text((30,40),'Framatex - Fiche technique')
    page.set_rotation(rotation)
    pdf.new_page(width=400,height=600)
    return pdf.tobytes()


def marks():
    return [{'kind':'highlight','page':1,'points':[{'x':.1,'y':.1},{'x':.5,'y':.15}]},
            {'kind':'ink','page':2,'points':[{'x':.1,'y':.1},{'x':.5,'y':.2},{'x':.3,'y':.3}]},
            {'kind':'text','page':1,'points':[{'x':.1,'y':.4},{'x':.7,'y':.6}],'text':'Revoir les dimensions.'}]


def test_actual_pdf_annotations_and_original_preserved(system):
    c=system; original=pdf_bytes(); d=doc(c,launch(c),filename='technique.pdf',content=original)
    path=f'/api/documents/{d["id"]}'
    meta=c.get(path+'/pdf').json()
    assert meta['can_write'] and len(meta['pages'])==2 and meta['version']==1
    image=c.get(f'/api/document-versions/{d["latest"]["id"]}/pdf-pages/1')
    assert image.status_code==200 and image.content.startswith(b'\x89PNG')
    payload={'base_version_id':d['latest']['id'],'annotations':marks()}
    saved=c.post(path+'/pdf-annotations',json=payload,headers=H)
    assert saved.status_code==201,saved.text
    assert saved.json()['latest']['number']==2
    assert c.get(path+'/versions/1/download').content==original
    with fitz.open(stream=c.get(path+'/versions/2/download').content,filetype='pdf') as pdf:
        assert len(list(pdf[0].annots()))==2
        assert len(list(pdf[1].annots()))==1
        text=list(pdf[0].annots())[-1].info['content']
        assert text=='Revoir les dimensions.'
    assert c.post(path+'/pdf-annotations',json=payload,headers=H).status_code==409
    assert not c.get(path+'/pdf',params={'version_id':d['latest']['id']}).json()['can_write']
    assert c.get(path+'/pdf').json()['version']==2


def test_rotated_pdf_and_invalid_annotations(system):
    c=system; d=doc(c,launch(c),filename='tourne.pdf',content=pdf_bytes(90)); path=f'/api/documents/{d["id"]}'
    meta=c.get(path+'/pdf').json(); assert meta['pages'][0]['width']==600
    payload={'base_version_id':d['latest']['id'],'annotations':marks()}
    for invalid in [{**marks()[0],'page':3},{**marks()[0],'page':True},{**marks()[0],'points':[{'x':2,'y':0},{'x':.5,'y':.5}]},{**marks()[2],'text':''}]:
        assert c.post(path+'/pdf-annotations',json={**payload,'annotations':[invalid]},headers=H).status_code==422
    saved=c.post(path+'/pdf-annotations',json=payload,headers=H)
    assert saved.status_code==201,saved.text
    # Annotation corners map back to the same normalized visual location after page rotation.
    with fitz.open(stream=c.get(path+'/versions/2/download').content,filetype='pdf') as pdf:
        page=pdf[0]; annotation=list(page.annots())[0]
        rect=annotation.rect*page.rotation_matrix
        assert abs(rect.x0/600-.1)<.04
        assert abs(rect.y0/400-.1)<.04
    assert c.get(f'/api/document-versions/{d["latest"]["id"]}/pdf-pages/3').status_code==404


def test_reader_access_and_space_routing(system):
    c=system; lid=launch(c);d=doc(c,lid,filename='fiche.pdf',content=pdf_bytes());path=f'/api/documents/{d["id"]}'
    wrong=c.post('/api/auth/login',json={'email':'admin@meeting.local','password':PASSWORD,'space':'client'},headers=H)
    assert wrong.status_code==403 and 'set-cookie' not in wrong.headers
    login(c,'reader@meeting.local')
    assert c.get(path+'/pdf').json()['can_write'] is False
    assert c.post(path+'/pdf-annotations',json={'base_version_id':d['latest']['id'],'annotations':marks()},headers=H).status_code==403
    login(c,'rose@meeting.local');assert c.get(path+'/pdf').status_code==403
    login(c)
    company=c.post('/api/clients',json={'name':'Entreprise PDF'},headers=H).json()
    assert c.post(f'/api/clients/{company["id"]}/contacts',json={'name':'Client PDF','email':'pdf@client.local','password':PASSWORD},headers=H).status_code==201
    assert c.post('/api/auth/login',json={'email':'pdf@client.local','password':PASSWORD,'space':'internal'},headers=H).status_code==403
    assert c.post('/api/auth/login',json={'email':'pdf@client.local','password':PASSWORD,'space':'client'},headers=H).status_code==200
    assert c.get(path+'/pdf').status_code==403
    assert c.get(f'/api/document-versions/{d["latest"]["id"]}/pdf-pages/1').status_code==403
