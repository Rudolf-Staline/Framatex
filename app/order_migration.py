"""0021: versioned canonical dossiers. Never infer order identity from text."""
import json
from sqlalchemy import inspect, text
from .models import uid
from .core import utcnow
from .order_documents import SECTIONS


def preflight(conn):
    problems=[]
    for r in conn.execute(text('''SELECT l.id, l.order_ref, l.client_name, b.reference, p.name
        FROM business_order_launches x JOIN launches l ON l.id=x.launch_id
        JOIN business_orders b ON b.id=x.order_id JOIN partners p ON p.id=b.client_id''')):
        if (r[1] and r[1]!=r[3]) or (r[2] or '').strip().casefold() != r[4].strip().casefold():
            problems.append(r[0])
    orphan=[r[0] for r in conn.execute(text('SELECT id FROM launches WHERE id NOT IN (SELECT launch_id FROM business_order_launches)'))]
    return {'incompatible_links':problems,'unlinked_launches':orphan,'inference_performed':False}


def upgrade(conn):
    from .core import Base
    report=preflight(conn)
    if report['incompatible_links']:
        raise RuntimeError('Rattachements incompatibles : '+json.dumps(report['incompatible_links']))
    for name in ('order_dossiers','order_members'):
        Base.metadata.tables[name].create(bind=conn,checkfirst=True)
    columns={c['name'] for c in inspect(conn).get_columns('folders')}
    if 'dossier_id' not in columns:
        # SQLite's documented generalized ALTER procedure. FK enforcement is
        # disabled only on this migration connection, checked before commit.
        conn.exec_driver_sql('''CREATE TABLE folders_new (
            id VARCHAR(36) PRIMARY KEY, launch_id VARCHAR(36) REFERENCES launches(id),
            dossier_id VARCHAR(36) REFERENCES order_dossiers(id), canonical_id VARCHAR(36) REFERENCES folders(id),
            slug VARCHAR(10) NOT NULL, label VARCHAR(70) NOT NULL,
            UNIQUE(launch_id,slug), UNIQUE(dossier_id,slug),
            CHECK ((launch_id IS NOT NULL) != (dossier_id IS NOT NULL)))''')
        conn.exec_driver_sql('INSERT INTO folders_new(id,launch_id,slug,label) SELECT id,launch_id,slug,label FROM folders')
        conn.exec_driver_sql('DROP TABLE folders')
        conn.exec_driver_sql('ALTER TABLE folders_new RENAME TO folders')
    columns={c['name'] for c in inspect(conn).get_columns('documents')}
    if 'launch_id' not in columns:
        conn.exec_driver_sql('ALTER TABLE documents ADD COLUMN launch_id VARCHAR(36) REFERENCES launches(id)')
    conn.exec_driver_sql('UPDATE documents SET launch_id=(SELECT launch_id FROM folders WHERE folders.id=documents.folder_id) WHERE launch_id IS NULL')
    for oid, in conn.execute(text('SELECT id FROM business_orders')):
        root=conn.execute(text('SELECT id FROM order_dossiers WHERE order_id=:o'),{'o':oid}).scalar()
        if not root:
            root=uid();conn.execute(text('INSERT INTO order_dossiers(id,order_id,created_at) VALUES (:i,:o,:t)'),{'i':root,'o':oid,'t':utcnow()})
        for slug,label in SECTIONS:
            fid=conn.execute(text('SELECT id FROM folders WHERE dossier_id=:d AND slug=:s'),{'d':root,'s':slug}).scalar()
            if not fid:
                fid=uid();conn.execute(text('INSERT INTO folders(id,dossier_id,slug,label) VALUES (:i,:d,:s,:l)'),{'i':fid,'d':root,'s':slug,'l':label})
            old=list(conn.execute(text('SELECT f.id FROM folders f JOIN business_order_launches x ON x.launch_id=f.launch_id WHERE x.order_id=:o AND f.slug=:s'),{'o':oid,'s':slug}))
            for old_id, in old:
                conn.execute(text('UPDATE documents SET folder_id=:f WHERE folder_id=:old'),{'f':fid,'old':old_id})
                conn.execute(text('UPDATE folders SET canonical_id=:f WHERE id=:old'),{'f':fid,'old':old_id})
    for name in ('ix_folders_launch_id','ix_folders_dossier_id','ix_documents_launch_id'):
        table='documents' if name.startswith('ix_documents') else 'folders'
        column=name[len('ix_'+table+'_'):]
        conn.exec_driver_sql(f'CREATE INDEX IF NOT EXISTS {name} ON {table}({column})')
    # Database constraints protect clients bypassing the API, too.
    for operation in ('INSERT','UPDATE'):
        conn.exec_driver_sql(f'''CREATE TRIGGER IF NOT EXISTS canonical_document_{operation.lower()}
            BEFORE {operation} ON documents BEGIN
            SELECT CASE WHEN EXISTS(SELECT 1 FROM folders WHERE id=NEW.folder_id AND canonical_id IS NOT NULL)
                THEN RAISE(ABORT,'legacy folder is read-only') END;
            SELECT CASE WHEN NEW.launch_id IS NOT NULL AND EXISTS(
                SELECT 1 FROM folders f JOIN order_dossiers d ON d.id=f.dossier_id
                WHERE f.id=NEW.folder_id AND NOT EXISTS(SELECT 1 FROM business_order_launches x
                WHERE x.launch_id=NEW.launch_id AND x.order_id=d.order_id))
                THEN RAISE(ABORT,'document launch/order mismatch') END;
            END''')
    conn.exec_driver_sql('''CREATE TRIGGER IF NOT EXISTS preserve_document_order BEFORE DELETE ON business_order_launches
        WHEN EXISTS(SELECT 1 FROM documents WHERE launch_id=OLD.launch_id)
        BEGIN SELECT RAISE(ABORT,'documented launch cannot be detached'); END''')
    return report
