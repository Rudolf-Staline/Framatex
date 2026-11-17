"""Explain list indexes in an isolated, migrated SQLite schema (no configured DB)."""
import json
import os
import sys
import tempfile

if 'app.core' in sys.modules:
    raise RuntimeError('Run standalone to avoid reusing a configured database')
with tempfile.TemporaryDirectory(prefix='framatex-plans-') as directory:
    os.environ['FRAMATEX_DATA_DIR']=directory
    os.environ['DATABASE_URL']='sqlite:///'+directory+'/plans.db'
    from app.migrate import migrate
    from app.core import engine
    migrate()
    queries={
        'folder_page':('SELECT id FROM documents WHERE folder_id=? ORDER BY created_at DESC,id DESC LIMIT 25',('synthetic-folder',)),
        'client_order_page':('SELECT id FROM business_orders WHERE client_id=? ORDER BY created_at DESC,id DESC LIMIT 25',('synthetic-client',)),
        'latest_document_version':('SELECT id FROM document_versions WHERE document_id=? ORDER BY number DESC LIMIT 1',('synthetic-document',)),
    }
    plans={}
    with engine.connect() as db:
        for label,(sql,params) in queries.items():
            plans[label]=[dict(row._mapping) for row in db.exec_driver_sql('EXPLAIN QUERY PLAN '+sql,params)]
    print(json.dumps({'conditions':'SQLite migrated empty synthetic schema; index selection only, no throughput claim','plans':plans},indent=2))
