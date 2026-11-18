"""Readiness reports the correct migration family for PostgreSQL and SQLite."""
import json
import sys
import types
from types import SimpleNamespace

from app import operations_routes
from app.migrate import REVISIONS


class FakeConnection:
    def __init__(self, revisions):
        self.revisions = revisions
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query):
        statement = str(query)
        self.queries.append(statement)
        if 'SELECT version FROM schema_migrations' in statement:
            return [(value,) for value in self.revisions]
        if 'SELECT 1 FROM users LIMIT 1' in statement or statement == 'SELECT 1':
            return []
        raise AssertionError(f'Unexpected query: {statement}')


def invoke(monkeypatch, tmp_path, dialect, revisions):
    connection = FakeConnection(revisions)
    engine = SimpleNamespace(dialect=SimpleNamespace(name=dialect), connect=lambda: connection)
    monkeypatch.setattr(operations_routes, 'engine', engine)
    monkeypatch.setattr(operations_routes, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(operations_routes, 'scanner_readiness', lambda: {'ready': True, 'state': 'test'})
    monkeypatch.setattr(operations_routes, 'build_identity', lambda: {'version': 'test', 'commit': 'test'})
    monkeypatch.setenv('FRAMATEX_MIN_FREE_BYTES', '0')
    if dialect == 'postgresql':
        # Tests only the readiness contract; there is no live PostgreSQL connection.
        monkeypatch.setitem(sys.modules, 'app.postgres_schema', types.SimpleNamespace(REVISION='pg_0001_initial'))
    response = operations_routes.readiness()
    return response.status_code, json.loads(response.body), connection.queries


def test_postgres_schema_is_ready(monkeypatch, tmp_path):
    status, payload, queries = invoke(monkeypatch, tmp_path, 'postgresql', ['pg_0001_initial'])
    assert status == 200
    assert payload['checks']['database'] is True
    assert 'SELECT 1 FROM users LIMIT 1' in queries


def test_postgres_rejects_sqlite_revision(monkeypatch, tmp_path):
    status, payload, _ = invoke(monkeypatch, tmp_path, 'postgresql', list(REVISIONS))
    assert status == 503
    assert payload['checks']['database'] is False


def test_sqlite_still_uses_legacy_revisions(monkeypatch, tmp_path):
    status, payload, queries = invoke(monkeypatch, tmp_path, 'sqlite', list(REVISIONS))
    assert status == 200
    assert payload['checks']['database'] is True
    assert 'SELECT 1 FROM users LIMIT 1' not in queries
