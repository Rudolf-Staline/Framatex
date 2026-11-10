"""Local SQLite + private file backup. Run in maintenance mode (no writers).
Restore only to a new directory. Never operates on a remote database.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile
import zipfile


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def validate(database, files):
    with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Base SQLite incohérente')
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Relations invalides')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('document_versions','partner_submissions'):
            if table not in tables:continue
            for name, expected in db.execute(f'SELECT disk_name, sha256 FROM {table}'):
                if Path(name).name != name or not (files/name).is_file() or sha(files/name) != expected:
                    raise ValueError('Pièce manquante ou empreinte incorrecte')


def backup(source: Path, destination: Path):
    source=source.resolve();destination=destination.resolve()
    if not (source/'framat.db').is_file():raise ValueError('Base SQLite locale absente')
    if destination.exists():raise ValueError('La destination existe déjà')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        stage=Path(tmp);database=stage/'framat.db'
        with sqlite3.connect(f'file:{source / "framat.db"}?mode=ro',uri=True) as origin, sqlite3.connect(database) as target:
            origin.backup(target)
        shutil.copytree(source/'files',stage/'files') if (source/'files').exists() else (stage/'files').mkdir()
        validate(database,stage/'files')
        paths=[p for p in stage.rglob('*') if p.is_file()]
        manifest={str(p.relative_to(stage)):sha(p) for p in paths}
        fd=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        try:
            with os.fdopen(fd,'wb') as out, zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in paths:archive.write(path,path.relative_to(stage))
                archive.writestr('manifest.json',json.dumps(manifest,sort_keys=True))
        except Exception:
            destination.unlink(missing_ok=True);raise
    return destination


def restore(archive: Path, destination: Path):
    destination=destination.resolve()
    if destination.exists():raise ValueError('Restaurer uniquement vers un nouveau répertoire')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        stage=Path(tmp)/'restore';stage.mkdir(mode=0o700)
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            if len(names)!=len(set(names)):raise ValueError('Entrées dupliquées')
            if 'manifest.json' not in names:raise ValueError('Manifeste absent')
            manifest=json.loads(z.read('manifest.json'))
            if set(names)!=(set(manifest)|{'manifest.json'}):raise ValueError('Manifeste incomplet')
            if 'framat.db' not in manifest:raise ValueError('Base absente du manifeste')
            for name, expected in manifest.items():
                path=Path(name)
                if path.is_absolute() or '..' in path.parts or not (name=='framat.db' or (len(path.parts)==2 and path.parts[0]=='files')):
                    raise ValueError('Chemin non autorisé')
                target=stage/path;target.parent.mkdir(exist_ok=True)
                with z.open(name) as src,target.open('xb') as out:shutil.copyfileobj(src,out)
                if sha(target)!=expected:raise ValueError('Empreinte du manifeste incorrecte')
        (stage/'files').mkdir(exist_ok=True)
        validate(stage/'framat.db',stage/'files')
        # The restored installation starts with no active external sessions.
        with sqlite3.connect(stage/'framat.db') as db:
            if db.execute("SELECT name FROM sqlite_master WHERE name='partner_tokens'").fetchone():
                db.execute('UPDATE partner_tokens SET consumed=1')
        stage.rename(destination)
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['backup','restore']);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    print((backup if args.operation=='backup' else restore)(args.source,args.destination))

if __name__=='__main__':main()
