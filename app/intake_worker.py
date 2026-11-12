"""Linux parser worker; intentionally independent from application DB/auth imports."""
import json,resource,sys
from pathlib import Path

def main():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(25,25))
    resource.setrlimit(resource.RLIMIT_FSIZE,(30*1024*1024,30*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    payload=json.loads(sys.stdin.read(8192))
    from .intake import _read_document
    from .file_validation import validate_format
    path=Path(payload['path']);suffix=Path(payload['filename']).suffix.lower()
    try:
        validate_format(path,suffix)
        result=_read_document(path,payload['filename'])
    except Exception as exc:
        result={'text':'','method':'invalid_format','warnings':['Format réel invalide, corrompu ou non autorisé : vérification manuelle nécessaire']}
    result['provenance']={'filename':payload['filename'],'parser':result['method'],'limits':{'pdf_pages':3,'text_characters':16000,'xlsx_sheets':3,'xlsx_rows':120,'xlsx_columns':16},'human_confirmation_required':True}
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
