"""Versioned, repeatable SQLite migrations for Framatex MVP.

Usage: python -m app.migrate status | upgrade
The CLI backs up an existing file before applying schema changes. Production
migration requires a maintenance window and independent backup verification.
"""
from __future__ import annotations
import argparse
import os
from contextlib import contextmanager
import sqlite3
import shutil
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect, text, Table, Column, String
from .core import Base, engine

# Import every registered model before inspecting metadata.
from . import models, completeness_models, workflow_models, quality_models, intake_models  # noqa: F401
from . import spec_models, mail_models, impact_sim_models, orli_models, material_models # noqa: F401
from . import partner_phase2_models
from . import partner_models, order_documents
from . import approval_models, sharing_models, pilot_models # noqa: F401

# Include the migration ledger in SQLAlchemy metadata so test databases that
# reset Base.metadata also reset this ledger; production upgrades remain explicit.
MIGRATION_TABLE = Table('schema_migrations', Base.metadata,
                        Column('version', String(80), primary_key=True),
                        Column('applied_at', String(50), nullable=False), extend_existing=True)

REVISIONS = ('0001_baseline', '0002_launch_scope', '0003_pilot_reports', '0004_partners', '0005_partner_deliveries', '0006_partner_mail', '0007_partner_phase2', '0008_confirmed_sources', '0009_client_conversations', '0010_security_notifications', '0011_delivery_cancellations', '0012_orli_profiles', '0013_excel_policies', '0014_partner_administration', '0015_partner_default_roles', '0016_completeness_policies', '0017_order_registry', '0018_approval_assignments', '0019_partner_notice_center', '0020_audit_session_index', '0021_order_dossiers', '0022_approval_cycles', '0023_order_completeness')


def _versions(conn):
    conn.execute(text('CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(80) PRIMARY KEY, applied_at VARCHAR(50) NOT NULL)'))
    return {v for v, in conn.execute(text('SELECT version FROM schema_migrations'))}


@contextmanager
def migration_connection():
    with engine.connect() as conn:
        conn.exec_driver_sql('PRAGMA foreign_keys=OFF')
        conn.commit()
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.exec_driver_sql('PRAGMA foreign_keys=ON')
            conn.commit()


def migrate():
    if engine.dialect.name != 'sqlite':
        raise RuntimeError('Le migrateur MVP gère SQLite seulement. Ne pas démarrer sur une base PostgreSQL sans migrations spécifiques.')
    # Back up the real SQLite database before any legacy ALTER TABLE.
    with engine.connect() as probe:
        tables = set(inspect(probe).get_table_names())
        legacy = ('launches' in tables and
                  'restricted' not in {c['name'] for c in inspect(probe).get_columns('launches')})
        old_document_layout=('folders' in tables and 'dossier_id' not in {c['name'] for c in inspect(probe).get_columns('folders')})
        has_migrations = 'schema_migrations' in tables
        pending_pilot = has_migrations and REVISIONS[-1] not in {
            v for v, in probe.execute(text('SELECT version FROM schema_migrations'))}
    if old_document_layout and engine.url.database not in (None,':memory:'):
        from .backup import backup as complete_backup
        source=Path(engine.url.database).resolve()
        destination=source.with_name(source.name+'.phase3-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.zip')
        complete_backup(source.parent,destination,database_name=source.name)
        print('Archive complète vérifiée avant conversion :',destination)
    if legacy or pending_pilot:
        saved = backup_sqlite()
        if saved:
            print('Sauvegarde automatique avant migration :', saved)
    with migration_connection() as conn:
        conn.exec_driver_sql("BEGIN IMMEDIATE")  # Serialize concurrent SQLite worker startups.
        done = _versions(conn)
        unknown = done.difference(REVISIONS)
        if unknown:
            raise RuntimeError(f'Révisions non reconnues: {sorted(unknown)}')
        if '0001_baseline' not in done:
            existing = set(inspect(conn).get_table_names())
            if 'launches' in existing:
                expected = {'users','roles','launches','folders','documents','document_versions'}
                if not expected.issubset(existing):
                    raise RuntimeError('Schéma existant partiel : migration interrompue pour éviter une perte de données')
                # Old 0.14 installations must contain the complete pre-0.15 schema.
                missing = (set(Base.metadata.tables) - {'schema_migrations', 'launch_members', 'pilot_reports','security_login_buckets','orli_mapping_profiles','orli_refresh_decisions','document_excel_policies','requirement_policies','launch_order_contexts','business_orders','business_order_launches','approval_stage_policies','approval_stage_assignments','order_dossiers','order_members','order_completeness'} - {t for t in Base.metadata.tables if t.startswith('partner')}) - existing
                if missing:
                    raise RuntimeError('Base antérieure incomplète : tables manquantes : ' + ', '.join(sorted(missing)))
            else:
                # A new installation initializes its full contemporary schema.
                Base.metadata.create_all(bind=conn)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                        {'v':'0001_baseline','d':datetime.now(timezone.utc).isoformat()})
        if '0002_launch_scope' not in done:
            cols = {c['name'] for c in inspect(conn).get_columns('launches')}
            if 'restricted' not in cols:
                conn.execute(text('ALTER TABLE launches ADD COLUMN restricted BOOLEAN NOT NULL DEFAULT 0'))
            conn.execute(text("""CREATE TABLE IF NOT EXISTS launch_members (
              id VARCHAR(36) PRIMARY KEY,
              launch_id VARCHAR(36) NOT NULL REFERENCES launches(id),
              user_id VARCHAR(36) NOT NULL REFERENCES users(id),
              granted_by VARCHAR(36) NOT NULL REFERENCES users(id),
              created_at DATETIME NOT NULL,
              CONSTRAINT uq_launch_member UNIQUE(launch_id,user_id)
            )"""))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_launch_members_launch_id ON launch_members (launch_id)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_launch_members_user_id ON launch_members (user_id)'))
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                        {'v':'0002_launch_scope','d':datetime.now(timezone.utc).isoformat()})
        if '0003_pilot_reports' not in done:
            Base.metadata.tables['pilot_reports'].create(bind=conn, checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0003_pilot_reports','d':datetime.now(timezone.utc).isoformat()})
        if '0004_partners' not in done:
            for table in Base.metadata.sorted_tables:
                if table.name not in {'partner_notices','partner_notice_reads','partner_administrative_documents','partner_client_order_events','partner_movement_cancellations','partner_event_reads','partner_client_orders','partner_threads','partner_messages','partner_attachments','partner_confirmed_datum_sources','partner_profiles','partner_roles','partner_role_assignments','partner_integrations'} and table.name.startswith('partner') and table.name not in ('partner_order_lines','partner_deliveries','partner_mail','partner_mail_preferences'):
                    table.create(bind=conn, checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0004_partners','d':datetime.now(timezone.utc).isoformat()})
        if '0005_partner_deliveries' not in done:
            for name in ('partner_order_lines','partner_deliveries'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0005_partner_deliveries','d':datetime.now(timezone.utc).isoformat()})
        if '0006_partner_mail' not in done:
            for name in ('partner_mail','partner_mail_preferences'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0006_partner_mail','d':datetime.now(timezone.utc).isoformat()})
        if '0007_partner_phase2' not in done:
            for table in Base.metadata.sorted_tables:
                if table.name in {'partner_profiles','partner_roles','partner_role_assignments','partner_integrations'}:
                    table.create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0007_partner_phase2','d':datetime.now(timezone.utc).isoformat()})
        if '0008_confirmed_sources' not in done:
            Base.metadata.tables['partner_confirmed_datum_sources'].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0008_confirmed_sources','d':datetime.now(timezone.utc).isoformat()})
        if '0009_client_conversations' not in done:
            for name in ('partner_client_orders','partner_threads','partner_messages','partner_attachments'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0009_client_conversations','d':datetime.now(timezone.utc).isoformat()})
        if '0010_security_notifications' not in done:
            for name in ('partner_event_reads','security_login_buckets'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0010_security_notifications','d':datetime.now(timezone.utc).isoformat()})
        if '0011_delivery_cancellations' not in done:
            Base.metadata.tables['partner_movement_cancellations'].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0011_delivery_cancellations','d':datetime.now(timezone.utc).isoformat()})
        if '0012_orli_profiles' not in done:
            for name in ('orli_mapping_profiles','orli_refresh_decisions'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0012_orli_profiles','d':datetime.now(timezone.utc).isoformat()})
        if '0013_excel_policies' not in done:
            Base.metadata.tables['document_excel_policies'].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0013_excel_policies','d':datetime.now(timezone.utc).isoformat()})
        if '0014_partner_administration' not in done:
            for name in ('partner_administrative_documents','partner_client_order_events'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0014_partner_administration','d':datetime.now(timezone.utc).isoformat()})
        if '0015_partner_default_roles' not in done:
            # Preserve existing accounts, while new unassigned invitations default to read-only.
            import json
            from .models import uid
            for partner_id, in conn.execute(text('SELECT DISTINCT partner_id FROM partner_accounts')):
                role_id=uid()
                conn.execute(text('INSERT INTO partner_roles(id,partner_id,name,permissions_json) VALUES (:id,:org,:name,:permissions)'),
                    {'id':role_id,'org':partner_id,'name':'Contributeur historique','permissions':json.dumps(['read','document.write','message.write','delivery.write'])})
                for account_id, in conn.execute(text('SELECT id FROM partner_accounts WHERE partner_id=:org AND id NOT IN (SELECT account_id FROM partner_role_assignments)'),{'org':partner_id}):
                    conn.execute(text('INSERT INTO partner_role_assignments(account_id,role_id) VALUES (:a,:r)'),{'a':account_id,'r':role_id})
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0015_partner_default_roles','d':datetime.now(timezone.utc).isoformat()})
        if '0016_completeness_policies' not in done:
            for name in ('requirement_policies','launch_order_contexts'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0016_completeness_policies','d':datetime.now(timezone.utc).isoformat()})
        if '0017_order_registry' not in done:
            for name in ('business_orders','business_order_launches'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0017_order_registry','d':datetime.now(timezone.utc).isoformat()})
        if '0018_approval_assignments' not in done:
            for name in ('approval_stage_policies','approval_stage_assignments'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0018_approval_assignments','d':datetime.now(timezone.utc).isoformat()})
        if '0019_partner_notice_center' not in done:
            for name in ('partner_notices','partner_notice_reads'):
                Base.metadata.tables[name].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0019_partner_notice_center','d':datetime.now(timezone.utc).isoformat()})
        if REVISIONS[-1] not in done:
            for index in Base.metadata.tables['audit_events'].indexes:
                index.create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0020_audit_session_index','d':datetime.now(timezone.utc).isoformat()})
        if '0021_order_dossiers' not in done:
            from .order_migration import upgrade
            upgrade(conn)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0021_order_dossiers','d':datetime.now(timezone.utc).isoformat()})
        if '0022_approval_cycles' not in done:
            from .approval_migration import upgrade as approval_upgrade
            approval_upgrade(conn)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0022_approval_cycles','d':datetime.now(timezone.utc).isoformat()})
        if '0023_order_completeness' not in done:
            Base.metadata.tables['order_completeness'].create(bind=conn,checkfirst=True)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0023_order_completeness','d':datetime.now(timezone.utc).isoformat()})
        if conn.exec_driver_sql('PRAGMA foreign_key_check').first():
            raise RuntimeError('Relations historiques invalides : migration annulée, corriger la copie de travail avant reprise')
        # Defensive consistency check: pre-0.15 historical tables stay untouched.
        cols = {c['name'] for c in inspect(conn).get_columns('launches')}
        if 'restricted' not in cols or 'launch_members' not in inspect(conn).get_table_names():
            raise RuntimeError('Schéma de portée incohérent')
    return REVISIONS


def backup_sqlite():
    url = engine.url
    if url.database in (None, ':memory:'):
        return None
    src = Path(url.database)
    if not src.exists() or src.stat().st_size == 0:
        return None
    dest = src.with_name(f'{src.name}.backup-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}')
    descriptor=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(descriptor)
    with sqlite3.connect(str(src)) as origin, sqlite3.connect(str(dest)) as backup:
        if origin.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or origin.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Intégrité de la base source invalide : migration refusée')
        origin.backup(backup)
        if backup.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise RuntimeError('Sauvegarde SQLite invalide : migration refusée')
    dest.chmod(0o600)
    return dest


def main():
    p = argparse.ArgumentParser(description='Migrations SQLite Framatex')
    p.add_argument('command', choices=('status','preflight','upgrade'), nargs='?', default='status')
    args = p.parse_args()
    if args.command == 'preflight':
        import json
        from .order_migration import preflight
        with engine.connect() as conn:
            if 'business_order_launches' not in inspect(conn).get_table_names():
                print('Référentiel commandes absent : appliquer les migrations antérieures sur une copie')
            else:print(json.dumps(preflight(conn),ensure_ascii=False,indent=2))
        return
    if args.command == 'status':
        with engine.connect() as conn:
            if 'schema_migrations' not in inspect(conn).get_table_names():
                print('Base sans version : migration nécessaire')
            else:
                print('Révisions appliquées :',', '.join(r for r, in conn.execute(text('SELECT version FROM schema_migrations ORDER BY version'))))
        return
    print('Schéma à jour :', ', '.join(migrate()))


if __name__ == '__main__':
    main()
