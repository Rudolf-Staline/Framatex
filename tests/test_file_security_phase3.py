import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from test_partners import app,setup,H
from app.document_storage import STORAGE
from app.intake import read_document


def archive(entries):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in entries:z.writestr(name,content)
    return data.getvalue()


def test_adversarial_formats_names_and_cleanup():
    with TestClient(app) as c:
        lid=setup(c);before=set(STORAGE.iterdir())
        files=[('../escape.txt',b'path'),('fake.png',b'\x89PNG\r\n\x1a\ninvalid'),('fake.jpg',b'\xff\xd8\xffinvalid'),('active.txt',b'MZ-executable'),('broken.pdf',b'%PDF-1.7\ncorrupt'),('binary.txt',b'\0binary'),('macro.docx',archive([('[Content_Types].xml','xml'),('word/document.xml','xml'),('word/vbaProject.bin','active')])),('bomb.xlsx',archive([('[Content_Types].xml','xml'),('xl/workbook.xml','x'*2_000_000)])),('traversal.docx',archive([('[Content_Types].xml','xml'),('word/document.xml','xml'),('../escape','no')]))]
        for filename,data in files:
            response=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Refus'},files={'file':(filename,data,'application/octet-stream')},headers=H)
            assert response.status_code==422,(filename,response.text)
            assert set(STORAGE.iterdir())==before
        for payload in [{'folder':'inconnue','title':'Refus'},{'folder':'jaune','title':'x'*221},{'folder':'rose','title':'   '}]:
            assert c.post(f'/api/launches/{lid}/documents',data=payload,files={'file':('x.txt',b'valid')},headers=H).status_code==422


def test_synthetic_docx_pdf_image_protected_and_provenance(tmp_path):
    from docx import Document
    from PIL import Image
    from pypdf import PdfWriter
    word=Document();word.add_paragraph('Quantite : 123 m');path=tmp_path/'document';word.save(path)
    result=read_document(path,'document.docx')
    assert result['method']=='docx_text' and '123' in result['text'] and result['provenance']['human_confirmation_required']
    writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.encrypt('synthetic-password');writer.write(path)
    assert read_document(path,'protected.pdf')['method']=='protected'
    Image.new('RGB',(32,32),'white').save(path,format='PNG')
    result=read_document(path,'image.png');assert result['method'] in ('image_ocr','ocr_unavailable')
    assert result['method']=='image_ocr' or result['warnings']


def test_private_storage_quota_and_concurrent_writer_lock(tmp_path,monkeypatch):
    import fcntl,os
    from app import document_storage
    private=tmp_path/'files';private.mkdir()
    monkeypatch.setattr(document_storage,'STORAGE',private);monkeypatch.setenv('FRAMATEX_STORAGE_QUOTA_BYTES','32')
    with TestClient(app) as c:
        lid=setup(c)
        def upload(data):return c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Quota'},files={'file':('quota.txt',data,'text/plain')},headers=H)
        for _ in range(2):assert upload(b'x'*16).status_code==201
        assert upload(b'x').status_code==413
        assert sum(p.stat().st_size for p in private.iterdir())==32
        assert all(p.stat().st_mode&0o077==0 for p in private.iterdir())
        fd=os.open(tmp_path/'.upload-budget.lock',os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            assert upload(b'x').status_code==409
        finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
        assert len(list(private.iterdir()))==2


def test_blob_name_collision_never_deletes_an_existing_file(tmp_path,monkeypatch):
    from app import document_storage
    private=tmp_path/'files';private.mkdir();historical=private/'collision';historical.write_bytes(b'Historical bytes')
    monkeypatch.setattr(document_storage,'STORAGE',private)
    with TestClient(app) as c:
        lid=setup(c)
        monkeypatch.setattr(document_storage.secrets,'token_hex',lambda _size:'collision')
        response=c.post(f'/api/launches/{lid}/documents',data={'folder':'jaune','title':'Conflit'},files={'file':('x.txt',b'New bytes','text/plain')},headers=H)
        assert response.status_code==409,response.text
        assert historical.read_bytes()==b'Historical bytes'
