"""Repair the supplier line key and preserve historical approval decisions."""
import json

from sqlalchemy import inspect, select, text
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.sqlite import insert
from .core import Base
from .document_types import type_key



def _invalidate_legacy_reclassifications(conn):
    # Older releases logged type changes but left previous approvals in force.
    # Use the assignment when the corresponding audit history has been purged.
    changes = {}
    for doc, before, after, actor, stamp in conn.exec_driver_sql("""
            SELECT a.document_id, a.original_label, a.type_id, a.assigned_by, a.assigned_at
            FROM document_type_assignments a WHERE a.assigned_by IS NOT NULL"""):
        if type_key(before) != type_key(after):
            changes[doc] = (actor, stamp)
    history = {}
    for doc, actor, stamp, detail in conn.exec_driver_sql("""
            SELECT target_id, actor_id, occurred_at, detail FROM audit_events
            WHERE action='document.classify' ORDER BY occurred_at, id"""):
        info = json.loads(detail)
        if actor and 'previous' in info and 'type_id' in info and type_key(info['previous']) != type_key(info['type_id']):
            history[doc] = (actor, stamp)
    changes.update(history)
    for doc, (actor, stamp) in changes.items():
        params = {'actor': actor, 'stamp': stamp, 'doc': doc}
        conn.execute(text("""
            UPDATE approval_runs SET obsolete=1
            WHERE started_at<=:stamp AND document_version_id IN
            (SELECT id FROM document_versions WHERE document_id=:doc)
        """), params)
        conn.execute(text("""
            INSERT INTO document_reviews(id,document_version_id,decision,comment,reviewed_by,reviewed_at)
            SELECT lower(hex(randomblob(16))), v.id, 'to_review', 'Reclassement du document', :actor, :stamp
            FROM document_versions v WHERE v.document_id=:doc AND v.created_at<=:stamp
            AND NOT EXISTS (SELECT 1 FROM document_reviews r WHERE r.document_version_id=v.id AND r.reviewed_at>=:stamp)
        """), params)
        conn.execute(text("""
            UPDATE client_publications SET status='revoked',revoked_by=:actor,revoked_at=:stamp,
                revoked_reason='Reclassement du document'
            WHERE status='published' AND created_at<=:stamp AND document_version_id IN
            (SELECT id FROM document_versions WHERE document_id=:doc)
        """), params)


def upgrade(conn):
    inspector = inspect(conn)
    if 'expires_at' not in {c['name'] for c in inspector.get_columns('guide_budgets')}:
        conn.exec_driver_sql('ALTER TABLE guide_budgets ADD COLUMN expires_at INTEGER NOT NULL DEFAULT 0')
        for key, in conn.exec_driver_sql('SELECT key FROM guide_budgets'):
            prefix, _, bucket = key.rpartition(':')
            if bucket.isdigit():
                window = 86400 if prefix.startswith(('ai-user:', 'ai-global')) else 60
                conn.execute(text('UPDATE guide_budgets SET expires_at=:end WHERE key=:key'),
                             {'end':(int(bucket)+1)*window,'key':key})
    conn.exec_driver_sql('CREATE INDEX IF NOT EXISTS ix_guide_budgets_expires_at ON guide_budgets(expires_at)')
    # Already detached launches can have missing sections or links to the old dossier.
    from .launches import FOLDERS
    from .models import Folder, uid
    conn.exec_driver_sql("""
        UPDATE folders SET canonical_id=NULL WHERE canonical_id IS NOT NULL AND launch_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM business_order_launches b WHERE b.launch_id=folders.launch_id)
    """)
    for slug, label in FOLDERS:
        missing = conn.execute(text("""
            SELECT l.id FROM launches l WHERE NOT EXISTS
            (SELECT 1 FROM business_order_launches b WHERE b.launch_id=l.id)
            AND NOT EXISTS (SELECT 1 FROM folders f WHERE f.launch_id=l.id AND f.slug=:slug)
        """), {'slug':slug}).scalars().all()
        if missing:
            conn.execute(Folder.__table__.insert(), [
                dict(id=uid(), launch_id=lid, slug=slug, label=label) for lid in missing])

    keys = inspector.get_unique_constraints('partner_order_lines')
    if any(k['column_names'] == ['partner_id', 'order_ref', 'material_ref'] for k in keys):
        table = Base.metadata.tables['partner_order_lines']
        ddl = str(CreateTable(table).compile(dialect=conn.dialect))
        conn.exec_driver_sql(ddl.replace('CREATE TABLE partner_order_lines', 'CREATE TABLE supplier_lines_new', 1))
        columns = ', '.join(c.name for c in table.columns)
        conn.exec_driver_sql(f'INSERT INTO supplier_lines_new ({columns}) SELECT {columns} FROM partner_order_lines')
        conn.exec_driver_sql('DROP TABLE partner_order_lines')
        conn.exec_driver_sql('ALTER TABLE supplier_lines_new RENAME TO partner_order_lines')
        for index in table.indexes:
            index.create(conn)

    if 'obsolete' not in {c['name'] for c in inspector.get_columns('approval_runs')}:
        conn.exec_driver_sql('ALTER TABLE approval_runs ADD COLUMN obsolete BOOLEAN NOT NULL DEFAULT 0')
    for run, target, original in conn.exec_driver_sql("""
            SELECT r.id, d.doc_type, t.document_type FROM approval_runs r
            JOIN approval_templates t ON r.template_id=t.id
            JOIN document_versions v ON r.document_version_id=v.id JOIN documents d ON d.id=v.document_id"""):
        if type_key(target) != type_key(original):
            conn.execute(text('UPDATE approval_runs SET obsolete=1 WHERE id=:id'), {'id':run})
    conn.exec_driver_sql("""
        INSERT INTO document_reviews(id,document_version_id,decision,comment,reviewed_by,reviewed_at)
        SELECT d.id,r.document_version_id,d.decision,d.comment,d.actor_id,d.decided_at
        FROM approval_decisions d JOIN approval_runs r ON r.id=d.run_id
        WHERE d.decision IN ('rejected','changes_requested') AND r.obsolete=0
        AND NOT EXISTS (SELECT 1 FROM document_reviews v WHERE v.id=d.id)
    """)
    _invalidate_legacy_reclassifications(conn)
    # Build immutable balance snapshots once for historical movement streams.
    from sqlalchemy.orm import Session
    from .partner_models import PartnerReceiptHistory, PartnerOrderLine, PartnerDelivery
    from .partner_phase2_models import PartnerMovementCancellation
    from .partner_delivery_routes import discrepancy_history
    PartnerReceiptHistory.__table__.create(conn,checkfirst=True)
    with Session(bind=conn) as session:
        for line in session.scalars(select(PartnerOrderLine)):
            moves=list(session.scalars(select(PartnerDelivery).where(PartnerDelivery.line_id==line.id)))
            cancellations={c.movement_id:c for c in session.scalars(select(PartnerMovementCancellation)
                           .join(PartnerDelivery,PartnerDelivery.id==PartnerMovementCancellation.movement_id)
                           .where(PartnerDelivery.line_id==line.id))}
            for index,event in enumerate(discrepancy_history(line,moves,cancellations),1):
                event['date']=event['date'].isoformat()
                conn.execute(insert(PartnerReceiptHistory).on_conflict_do_nothing(index_elements=["line_id","position"]),dict(line_id=line.id,position=index,event_json=json.dumps(event)))
