import hashlib
import sqlite3
import zipfile
import pytest
from sqlalchemy import create_engine, text, inspect
from app.core import Base
from app import migrate
from app.backup import backup, restore


def test_additive_migration_and_complete_restore(tmp_path,monkeypatch):
    source=tmp_path/'original';source.mkdir();(source/'files').mkdir()
    database=source/'framat.db';old=create_engine('sqlite:///'+str(database))
    Base.metadata.create_all(old)
    data=b'Synthetic historical document';sha=hashlib.sha256(data).hexdigest();(source/'files'/'blob1').write_bytes(data)
    with old.begin() as c:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name.startswith('partner'):table.drop(c)
        c.execute(text("INSERT INTO users(id,email,name,password_hash,active,created_at) VALUES ('u','u@example.local','Ancien','hash',1,'2026-01-01')"))
        c.execute(text("INSERT INTO launches(id,name,status,created_by,created_at,updated_at,restricted) VALUES ('l','Commande existante','En cours','u','2026-01-01','2026-01-01',1)"))
        c.execute(text("INSERT INTO folders(id,launch_id,slug,label) VALUES ('f','l','jaune','Technique')"))
        c.execute(text("INSERT INTO documents(id,folder_id,title,doc_type,created_by,created_at) VALUES ('d','f','Pièce','Certificat','u','2026-01-01')"))
        c.execute(text("INSERT INTO document_versions(id,document_id,number,original_name,disk_name,size,sha256,content_type,uploaded_by,created_at) VALUES ('v','d',1,'doc.txt','blob1',:size,:sha,'text/plain','u','2026-01-01')"),{'size':len(data),'sha':sha})
        for revision in migrate.REVISIONS[:-1]:c.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),{'v':revision,'d':'2026-01-01'})
    monkeypatch.setattr(migrate,'engine',old)
    migrate.migrate();migrate.migrate()
    with old.connect() as c:
        assert 'partner_accounts' in inspect(c).get_table_names()
        assert c.execute(text('SELECT restricted FROM launches')).scalar_one()==1
        assert c.execute(text('SELECT sha256 FROM document_versions')).scalar_one()==sha
    archive=backup(source,tmp_path/'backup.zip');restored=restore(archive,tmp_path/'restored')
    assert (restored/'files'/'blob1').read_bytes()==data
    with sqlite3.connect(restored/'framat.db') as db:
        assert db.execute('SELECT document_id FROM document_versions').fetchone()==('d',)
        assert db.execute('SELECT created_by FROM documents').fetchone()==('u',)
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
    with pytest.raises(ValueError):restore(archive,restored)
    with pytest.raises(ValueError):backup(source,archive)
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w') as z:
        z.writestr('manifest.json','{"../escape":"x", "framat.db":"x"}')
        z.writestr('../escape','bad');z.writestr('framat.db','bad')
    with pytest.raises(ValueError):restore(bad,tmp_path/'unsafe')
    assert not (tmp_path/'escape').exists()
    old.dispose()


def test_demo_requires_explicit_mode(monkeypatch):
    from app.demo_guard import require_demo
    monkeypatch.delenv('FRAMATEX_MODE',raising=False)
    with pytest.raises(SystemExit):require_demo()
    monkeypatch.setenv('FRAMATEX_MODE','DEMO')
    require_demo()
