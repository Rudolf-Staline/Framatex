"""Database configuration for the isolated PostgreSQL demonstration.

This module performs no network or filesystem I/O, so it is safe to validate
configuration before the application starts.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


PG_SCHEMA_DEFAULT = 'framatex_demo_v2'
_IDENT = re.compile(r'^[a-z][a-z0-9_]{0,62}$')


def data_dir(root: Path) -> Path:
    configured = os.getenv('FRAMATEX_DATA_DIR')
    if os.getenv('VERCEL'):
        # Vercel application source (/var/task) is read-only. /tmp is volatile.
        result = Path(configured if configured else '/tmp/framatex').resolve()
        if not result.is_relative_to('/tmp'):
            raise RuntimeError('Sur Vercel, FRAMATEX_DATA_DIR doit se trouver sous /tmp')
        return result
    return Path(configured if configured else str(root / 'data')).resolve()


def database_configuration(root: Path, data: Path):
    url_str = os.getenv('DATABASE_URL')
    if not url_str:
        if os.getenv('VERCEL'):
            raise RuntimeError('DATABASE_URL persistent est obligatoire sur Vercel; SQLite /tmp est interdit')
        url_str = f'sqlite:///{data / "framat.db"}'
    url = make_url(url_str)
    if url.get_backend_name() == 'sqlite':
        if os.getenv('VERCEL'):
            raise RuntimeError('SQLite persistant est impossible sur Vercel : configurer PostgreSQL')
        return url_str, {'connect_args': {'check_same_thread': False}}, None
    if url.get_backend_name() != 'postgresql':
        raise RuntimeError('SGBD inconnu : utiliser SQLite local ou PostgreSQL')
    schema = os.getenv('FRAMATEX_DB_SCHEMA', PG_SCHEMA_DEFAULT)
    if not _IDENT.fullmatch(schema) or schema in ('public', 'auth', 'storage', 'pg_catalog'):
        raise RuntimeError('FRAMATEX_DB_SCHEMA doit être un schéma privé dédié, non public')
    if url.drivername != 'postgresql+psycopg':
        url_str = url.set(drivername='postgresql+psycopg').render_as_string(hide_password=False)
    kwargs = {
        'connect_args': {'connect_timeout': 10, 'prepare_threshold': None, 'sslmode': 'require'},
        'poolclass': NullPool,
        'execution_options': {'schema_translate_map': {None: schema}},
    }
    return url_str, kwargs, schema
