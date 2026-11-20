"""Explicit, non-destructive PostgreSQL bootstrap for an EMPTY, private schema.

Never run this during a Vercel request. Existing Supabase `public` tables are
not touched and are never considered the schema of the current application.
"""
from __future__ import annotations

import argparse
import os

from sqlalchemy import inspect, text
from datetime import datetime, timezone

from .core import Base, PG_SCHEMA, engine
from . import migrate as _register_all_models  # noqa: F401

REVISION = 'pg_0001_initial'


def verify_schema(bind, schema):
    if not schema or bind.dialect.name != 'postgresql':
        raise RuntimeError('Vérification PostgreSQL attendue')
    with bind.connect() as conn:
        inspector = inspect(conn)
        if schema not in inspector.get_schema_names():
            raise RuntimeError('Schéma PostgreSQL absent : initialisation explicite requise')
        current = set(inspector.get_table_names(schema=schema))
        expected = set(Base.metadata.tables)
        # Allow the preceding schema during rollout of the additive experience table.
        expected -= {'order_experiences'} - current
        if current != expected:
            raise RuntimeError(f'Schéma PostgreSQL incomplet : absentes={sorted(expected-current)}, inconnues={sorted(current-expected)}')
        revisions = set(conn.execute(text(f'SELECT version FROM "{schema}".schema_migrations')).scalars())
        if revisions != {REVISION}:
            raise RuntimeError('Version PostgreSQL non reconnue ; migration contrôlée requise')
        # Single PostgreSQL reflection for all tables, instead of 94 sequential
        # queries during cold start on Vercel.
        columns = inspector.get_multi_columns(schema=schema)
        for table in Base.metadata.sorted_tables:
            if table.name not in expected:
                continue
            actual = {c['name'] for c in columns.get((schema, table.name), [])}
            expected_columns = set(table.columns.keys())
            if not expected_columns.issubset(actual):
                raise RuntimeError(f'Colonnes manquantes dans {table.name}: {sorted(expected_columns-actual)}')


def bootstrap_schema(bind, schema):
    if not schema or bind.dialect.name != 'postgresql':
        raise RuntimeError('Bootstrap réservé à PostgreSQL')
    if os.getenv('FRAMATEX_ALLOW_PG_BOOTSTRAP') != '1':
        raise RuntimeError('Activation explicite requise : FRAMATEX_ALLOW_PG_BOOTSTRAP=1')
    with bind.begin() as conn:
        # Advisory transaction lock coordinates concurrent administrative runs.
        conn.execute(text('SELECT pg_advisory_xact_lock(hashtext(:name))'), {'name': 'framatex-bootstrap-'+schema})
        if schema in inspect(conn).get_schema_names():
            if inspect(conn).get_table_names(schema=schema):
                raise RuntimeError('Le schéma cible contient déjà des tables : aucune modification appliquée')
        else:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        # Keep schema out of Supabase's public REST API; no browser DB access.
        conn.execute(text(f'REVOKE ALL ON SCHEMA "{schema}" FROM PUBLIC, anon, authenticated'))
        Base.metadata.create_all(bind=conn)
        conn.execute(text(f'INSERT INTO "{schema}".schema_migrations(version, applied_at) VALUES (:version, :at)'),
                     {'version': REVISION, 'at': datetime.now(timezone.utc).isoformat()})
    verify_schema(bind, schema)


def upgrade_schema(bind, schema):
    """Add the order experience table to an existing private schema."""
    verify_schema(bind, schema)
    from .order_experience import OrderExperience
    with bind.begin() as conn:
        if conn.scalar(text('SELECT current_schema()')) != schema:
            raise RuntimeError('Le schéma actif ne correspond pas au schéma Framatex')
        conn.execute(text('SELECT pg_advisory_xact_lock(hashtext(:name))'), {'name': 'framatex-upgrade-'+schema})
        OrderExperience.__table__.create(conn, checkfirst=True)
    verify_schema(bind, schema)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('verify', 'bootstrap', 'upgrade'))
    args = parser.parse_args()
    if engine.dialect.name != 'postgresql':
        parser.error('DATABASE_URL PostgreSQL requis')
    if args.operation == 'verify':
        verify_schema(engine, PG_SCHEMA)
    elif args.operation == 'bootstrap':
        bootstrap_schema(engine, PG_SCHEMA)
    else:
        upgrade_schema(engine, PG_SCHEMA)
    print(f'{args.operation}: schéma {PG_SCHEMA} valide')


if __name__ == '__main__':
    main()
