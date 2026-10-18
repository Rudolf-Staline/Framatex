"""Offline contract checks: secrets and payloads never need a real Supabase project."""
from __future__ import annotations

import httpx
import pytest
from app import cloud_storage as cs


@pytest.fixture
def fake_config(monkeypatch):
    monkeypatch.setenv("FRAMATEX_STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://fake-demo.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "private-test-secret")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "framat-documents")
    return monkeypatch


def test_supabase_rejects_path_traversal(fake_config):
    with pytest.raises(ValueError):
        cs._endpoint("../../private")


def test_upload_and_private_download(fake_config, tmp_path, monkeypatch):
    payload = b"demo bytes only"
    key = "a" * 48
    source = tmp_path / "source"
    source.write_bytes(payload)
    traces = []

    def handler(request):
        traces.append((request.method, request.url.path, request.headers.get("authorization")))
        if request.method == "POST":
            assert request.content == payload
            assert request.headers.get("x-upsert") == "false"
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET":
            return httpx.Response(200, content=payload)
        if request.method == "DELETE":
            return httpx.Response(200, json={})
        return httpx.Response(404)

    original_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(cs.httpx, "Client", lambda **kw: original_client(transport=transport, **kw))
    cs.upload_local(key, source)
    found = cs.ensure_local(key, tmp_path / "cache")
    assert found.read_bytes() == payload
    cs.remove(key, found.parent)
    assert not found.exists()
    assert [method for method, _, _ in traces] == ["POST", "GET", "DELETE"]
    assert all(path.endswith("/framat-documents/" + key) for _, path, _ in traces)
    assert all(authorization == "Bearer private-test-secret" for _, _, authorization in traces)


def test_missing_secret_refuses_cloud_access(fake_config, monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_SECRET_KEY")
    with pytest.raises(RuntimeError, match="SUPABASE_SECRET_KEY"):
        cs.upload_local("b" * 48, tmp_path / "missing")


def test_file_not_found_is_not_silently_created(fake_config, monkeypatch, tmp_path):
    original_client = httpx.Client
    monkeypatch.setattr(cs.httpx, "Client", lambda **kw: original_client(transport=httpx.MockTransport(lambda request: httpx.Response(404)), **kw))
    # A stale key should remain unavailable; no zero-byte fake document is generated.
    key = "c" * 48
    path = cs.ensure_local(key, tmp_path)
    assert not path.exists()
