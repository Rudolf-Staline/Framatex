"""Bounded format validation, shared by upload and extraction workers."""
import json
import resource
import sys
import zipfile
from pathlib import Path, PurePosixPath

MAX_EXPANDED=100*1024*1024


def validate_format(path,extension):
    with path.open('rb') as stream:start=stream.read(16)
    if extension in ('.docx','.xlsx'):
        try:
            with zipfile.ZipFile(path) as archive:
                infos=archive.infolist();names={i.filename for i in infos}
                if len(infos)>5000 or len(infos)!=len(names) or sum(i.file_size for i in infos)>MAX_EXPANDED:
                    raise ValueError('Archive disproportionnée ou entrées dupliquées')
                for item in infos:
                    parts=PurePosixPath(item.filename).parts
                    if item.filename.startswith('/') or '..' in parts or '\\' in item.filename or item.flag_bits&1:
                        raise ValueError('Archive protégée ou chemins non autorisés')
                    if item.file_size>60*1024*1024 or item.file_size>max(1024*1024,item.compress_size*250):
                        raise ValueError('Taux de compression excessif')
                    lower=item.filename.lower()
                    if any(x in lower for x in ('vbaproject','activex/','embeddings/','externallinks/')):
                        raise ValueError('Contenu actif ou lien externe non autorisé')
                expected='word/document.xml' if extension=='.docx' else 'xl/workbook.xml'
                if '[Content_Types].xml' not in names or expected not in names or archive.testzip():
                    raise ValueError('Structure Office invalide')
                for name in names:
                    if name.endswith('.xml'):
                        data=archive.read(name)
                        if b'<!ENTITY' in data.upper() or b'<!DOCTYPE' in data.upper():raise ValueError('Déclarations XML non autorisées')
                        if b'DDEAUTO' in data.upper() or b'DDELINK' in data.upper():raise ValueError('Document actif non autorisé')
        except (zipfile.BadZipFile,RuntimeError,OSError,KeyError) as exc:
            raise ValueError('Archive Office illisible ou protégée') from exc
    elif extension=='.pdf':
        if not start.startswith(b'%PDF-'):raise ValueError('Format PDF non reconnu')
        try:
            from pypdf import PdfReader
            reader=PdfReader(path,strict=False)
            if not reader.is_encrypted:
                root=reader.trailer['/Root']
                if '/OpenAction' in root or '/AA' in root or '/JavaScript' in root.get('/Names',{}):
                    raise ValueError('Actions PDF non autorisées')
                if len(reader.pages)>2000:raise ValueError('PDF dépassant 2000 pages')
        except ValueError:raise
        except Exception as exc:raise ValueError('PDF corrompu ou illisible') from exc
    elif extension in ('.png','.jpg','.jpeg'):
        try:
            from PIL import Image
            with Image.open(path) as image:
                expected='PNG' if extension=='.png' else 'JPEG'
                if image.format!=expected:raise ValueError('Format image différent de son extension')
                if image.width*image.height>12_000_000:raise ValueError('Image dépassant 12 millions de pixels')
                image.verify()
        except ValueError:raise
        except Exception as exc:raise ValueError('Image corrompue ou illisible') from exc
    elif extension in ('.txt','.eml'):
        data=path.read_bytes()
        if b'\0' in data or start.startswith((b'MZ',b'\x7fELF',b'PK\x03\x04')):raise ValueError('Contenu incompatible avec un fichier texte')
        try:data.decode('utf-8')
        except UnicodeDecodeError as exc:raise ValueError('Texte UTF-8 attendu') from exc
    else:raise ValueError('Format non autorisé')


def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(8,8));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    payload=json.loads(sys.stdin.read(8192))
    try:
        validate_format(Path(payload['path']),payload['extension']);print(json.dumps({'valid':True}))
    except Exception as exc:
        # Only our fixed validation messages can cross the worker boundary.
        message=str(exc) if isinstance(exc,ValueError) else 'Structure de fichier illisible'
        print(json.dumps({'valid':False,'message':message[:180]}))

if __name__=='__main__':main()
