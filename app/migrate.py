"""Versioned, repeatable SQLite migrations for Framatex MVP.

Usage: python -m app.migrate status | upgrade
The CLI backs up an existing file before applying schema changes. Production
migration requires a maintenance window and independent backup verification.
"""
from __future__ import annotations
import argparse
import sqlite3
import shutil
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect, text, Table, Column, String
from .core import Base, engine

# Import every registered model before inspecting metadata.
from . import models, completeness_models, workflow_models, quality_models, intake_models  # noqa: F401
from . import spec_models, mail_models, impact_sim_models, orli_models, material_models # noqa: F401
from . import approval_models, sharing_models, pilot_models, global_library_models  # noqa: F401
from . import experience_models  # noqa: F401

# Include the migration ledger in SQLAlchemy metadata so test databases that
# reset Base.metadata also reset this ledger; production upgrades remain explicit.
MIGRATION_TABLE = Table('schema_migrations', Base.metadata,
                        Column('version', String(80), primary_key=True),
                        Column('applied_at', String(50), nullable=False), extend_existing=True)

REVISIONS = ('0001_baseline', '0002_launch_scope', '0003_pilot_reports', '0004_global_library', '0005_experience_controls', '0006_order_identification')


def _versions(conn):
    conn.execute(text('CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(80) PRIMARY KEY, applied_at VARCHAR(50) NOT NULL)'))
    return {v for v, in conn.execute(text('SELECT version FROM schema_migrations'))}


def migrate():
    if engine.dialect.name != 'sqlite':
        raise RuntimeError('Le migrateur MVP gère SQLite seulement. Ne pas démarrer sur une base PostgreSQL sans migrations spécifiques.')
    # Back up the real SQLite database before any legacy ALTER TABLE.
    with engine.connect() as probe:
        tables = set(inspect(probe).get_table_names())
        legacy = ('launches' in tables and
                  'restricted' not in {c['name'] for c in inspect(probe).get_columns('launches')})
        has_migrations = 'schema_migrations' in tables
        pending_pilot = has_migrations and ('0003_pilot_reports' not in {
            v for v, in probe.execute(text('SELECT version FROM schema_migrations'))} or
            '0004_global_library' not in {v for v, in probe.execute(text('SELECT version FROM schema_migrations'))})
    with engine.connect() as probe:
        pending_identification = 'launches' in tables and 'identification_json' not in {c['name'] for c in inspect(probe).get_columns('launches')}
    if legacy or pending_pilot or pending_identification:
        saved = backup_sqlite()
        if saved:
            print('Sauvegarde automatique avant migration :', saved)
    with engine.begin() as conn:
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
                missing = (set(Base.metadata.tables) - {'schema_migrations', 'launch_members', 'global_folders', 'global_document_entries', 'global_library_config', 'experience_records', 'document_expectations'}) - existing
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
        if '0004_global_library' not in done:
            from tools.migrate_global_library import apply_to_connection
            apply_to_connection(conn)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0004_global_library','d':datetime.now(timezone.utc).isoformat()})
        if '0005_experience_controls' not in done:
            from tools.migrate_document_intelligence import apply_to_connection
            apply_to_connection(conn)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0005_experience_controls','d':datetime.now(timezone.utc).isoformat()})
        if '0006_order_identification' not in done:
            from tools.migrate_order_identification import apply_to_connection
            apply_to_connection(conn)
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v, :d)'),
                         {'v':'0006_order_identification','d':datetime.now(timezone.utc).isoformat()})
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
    dest = src.with_name(f'{src.name}.backup-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}')
    with sqlite3.connect(str(src)) as origin, sqlite3.connect(str(dest)) as backup:
        origin.backup(backup)
    return dest


def main():
    p = argparse.ArgumentParser(description='Migrations SQLite Framatex')
    p.add_argument('command', choices=('status','upgrade'), nargs='?', default='status')
    args = p.parse_args()
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
