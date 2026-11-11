import io
from openpyxl import Workbook
from fastapi.testclient import TestClient
from test_partners import app,setup,H

def workbook(changed=False):
    book=Workbook();sheet=book.active;sheet.title='Calcul';sheet['A1']=20 if changed else 10;sheet['B1']=42 if changed else '=A1*2'
    book.create_sheet('Nouvelle' if changed else 'Ancienne')
    if changed:sheet['D5']='=#REF!'
    output=io.BytesIO();book.save(output);return output.getvalue()

def test_excel_policy_and_static_structure_changes():
    with TestClient(app) as staff:
        lid=setup(staff)
        r=staff.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Classeur critique','doc_type':'Calcul'},files={'file':('classeur.xlsx',workbook(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},headers=H)
        assert r.status_code==201,r.text
        doc=r.json()
        r=staff.put(f'/api/documents/{doc["id"]}/excel-policy',json={'cells':[{'sheet':'Calcul','cell':'A1'}]},headers=H)
        assert r.status_code==200,r.text
        r=staff.post(f'/api/documents/{doc["id"]}/versions',files={'file':('classeur.xlsx',workbook(True),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},headers=H)
        assert r.status_code==201,r.text
        result=staff.get(f'/api/launches/{lid}/excel-inspections').json()
        assert len(result)==2
        findings=result[-1]['inspection']['findings']
        assert {'sheet_added','sheet_removed','structure_changed','critical_cell_changed','formula_removed','broken_reference'}<={f['type'] for f in findings}
        assert staff.get(f'/api/documents/{doc["id"]}/excel-policy').json()['cells']==[{'sheet':'Calcul','cell':'A1'}]


def test_excel_resource_limit_and_truncated_findings(tmp_path):
    from app.quality import analyze_workbook
    huge=Workbook();huge.active['A40001']='too far';path=tmp_path/'large.xlsx';huge.save(path)
    result=analyze_workbook(path,None)
    assert result['status']=='limited' and result['findings'][0]['type']=='inspection_limit'
    old=Workbook()
    for i in range(1,301):old.active.cell(i,1,'=1+1')
    previous=tmp_path/'previous.xlsx';old.save(previous)
    new=Workbook();current=tmp_path/'current.xlsx';new.save(current)
    findings=analyze_workbook(current,previous)['findings']
    assert len(findings)==200 and findings[-1]['type']=='truncated'
