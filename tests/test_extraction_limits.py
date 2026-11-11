from pathlib import Path
from openpyxl import Workbook
from app.intake import read_document,MAX_TEXT,_READERS

def test_bounded_worker_partial_text_and_opaque_excel_paths(tmp_path):
    text=tmp_path/'opaque-text';text.write_text('Référence matière TISSU-A\n'+'x'*MAX_TEXT)
    result=read_document(text,'fiche.txt')
    assert result['method']=='plain_text' and len(result['text'])==MAX_TEXT
    assert any('partielle' in w for w in result['warnings'])
    book=Workbook();book.active['A1']='Quantite : 100 m';book.active['A121']='EXCLUDED'
    path=tmp_path/'opaque-excel';book.save(path)
    result=read_document(path,'fiche.xlsx')
    assert result['method']=='xlsx_values' and '100 m' in result['text'] and 'EXCLUDED' not in result['text']
    assert result['warnings']
    _READERS.acquire();_READERS.acquire()
    try:assert read_document(text,'fiche.txt')['method']=='limited'
    finally:_READERS.release();_READERS.release()
    oversized=tmp_path/'large'
    with oversized.open('wb') as stream:stream.truncate(21*1024*1024)
    assert read_document(oversized,'large.pdf')['method']=='limited'

def test_pdf_page_limit_and_corrupt_document_are_explained(tmp_path):
    import fitz
    pdf=fitz.open()
    for i in range(4):pdf.new_page().insert_text((50,50),f'PAGE-{i+1} Quantite : 100 m')
    path=tmp_path/'opaque-pdf';pdf.save(path);pdf.close()
    result=read_document(path,'document.pdf')
    assert result['method']=='pdf_text' and 'PAGE-3' in result['text'] and 'PAGE-4' not in result['text']
    assert result['warnings']
    broken=tmp_path/'broken';broken.write_bytes(b'not a document')
    assert read_document(broken,'document.docx')['warnings']
