"""Offline checks: no Supabase secret, network or production data required."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app import blob_backend
from app.core_pg_config import data_dir, database_configuration, PG_SCHEMA_DEFAULT


def test_serverless_writes_only_under_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.delenv('FRAMATEX_DATA_DIR', raising=False)
    assert str(data_dir(tmp_path)).startswith('/tmp/')
    monkeypatch.setenv('FRAMATEX_DATA_DIR', str(tmp_path / 'other'))
    if not str(tmp_path).startswith('/tmp/'):
        with pytest.raises(RuntimeError, match='/tmp'):
            data_dir(tmp_path)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        database_configuration(tmp_path, tmp_path)


def test_pg_config_is_isolated_no_persistent_client_pool(monkeypatch, tmp_path):
    monkeypatch.delenv('VERCEL', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://postgres:pw@pooler.example.org:6543/postgres')
    monkeypatch.setenv('FRAMATEX_DB_SCHEMA', 'framatex_demo_v2')
    url, settings, schema = database_configuration(tmp_path, tmp_path)
    assert url.startswith('postgresql+psycopg://')
    assert schema == PG_SCHEMA_DEFAULT
    assert settings['connect_args']['prepare_threshold'] is None
    assert settings['execution_options']['schema_translate_map'] == {None: schema}
    monkeypatch.setenv('FRAMATEX_DB_SCHEMA', 'public')
    with pytest.raises(RuntimeError, match='privé'):
        database_configuration(tmp_path, tmp_path)


def test_private_storage_server_auth_and_paths(monkeypatch, tmp_path):
    monkeypatch.setenv('SUPABASE_URL', 'https://qwutrmdghvqntzruscvl.supabase.co')
    monkeypatch.setenv('SUPABASE_STORAGE_BUCKET', 'framat-documents')
    monkeypatch.setenv('SUPABASE_SECRET_KEY', 'sb_secret_sample_test_only')
    key = 'ab' * 24
    url, headers = blob_backend._endpoint(key)
    assert url == ('https://qwutrmdghvqntzruscvl.supabase.co/storage/v1/object/'
                   'framat-documents/' + key)
    assert headers == {'apikey': 'sb_secret_sample_test_only'}
    for invalid in ('../secret', 'f/../../../secret', 'invalid', 'A' * 48):
        with pytest.raises(ValueError):
            blob_backend._endpoint(invalid)
    monkeypatch.setenv('SUPABASE_URL', 'http://untrusted.invalid')
    with pytest.raises(RuntimeError, match='HTTPS'):
        blob_backend._endpoint(key)


def test_private_remote_storage_roundtrip_without_network(monkeypatch, tmp_path):
    monkeypatch.setenv('SUPABASE_URL', 'https://qwutrmdghvqntzruscvl.supabase.co')
    monkeypatch.setenv('SUPABASE_STORAGE_BUCKET', 'framat-documents')
    monkeypatch.setenv('SUPABASE_SECRET_KEY', 'sb_secret_sample_test_only')
    name = 'fe' * 24
    blob = b'private document contents'
    stored = {}

    class Result:
        status_code = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def iter_content(self, size):
            yield blob

    def post(url, headers, data, **kwargs):
        assert headers['x-upsert'] == 'false'
        assert 'Authorization' not in headers
        assert kwargs['allow_redirects'] is False
        stored[name] = data.read()
        return Result()

    def get(url, headers, **kwargs):
        assert name in stored
        assert headers['apikey'].startswith('sb_secret_')
        assert kwargs['allow_redirects'] is False
        return Result()

    def delete(url, headers, **kwargs):
        stored.pop(name)
        return Result()

    monkeypatch.setattr(blob_backend.requests, 'post', post)
    monkeypatch.setattr(blob_backend.requests, 'get', get)
    monkeypatch.setattr(blob_backend.requests, 'delete', delete)
    path = tmp_path / 'source'
    path.write_bytes(blob)
    blob_backend.upload(path, name, 'text/plain')
    assert stored[name] == blob
    cached = blob_backend.download(tmp_path / 'cache', name)
    assert cached.read_bytes() == blob
    blob_backend.delete(name)
    assert name not in stored


def test_remote_download_enforces_size(monkeypatch, tmp_path):
    monkeypatch.setenv('SUPABASE_URL', 'https://qwutrmdghvqntzruscvl.supabase.co')
    monkeypatch.setenv('SUPABASE_STORAGE_BUCKET', 'framat-documents')
    monkeypatch.setenv('SUPABASE_SECRET_KEY', 'sb_secret_sample_test_only')
    class Result:
        status_code = 200
        def __enter__(self):return self
        def __exit__(self, *args):return False
        def iter_content(self, size):yield b'abcdef'
    monkeypatch.setattr(blob_backend.requests, 'get', lambda *a, **kw: Result())
    with pytest.raises(HTTPException) as exc:
        blob_backend.download(tmp_path / 'cache', 'ef' * 24, maximum_size=5)
    assert exc.value.status_code == 503
    assert not list((tmp_path / 'cache').glob('*'))
