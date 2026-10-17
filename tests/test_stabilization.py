"""MVP 0.16: HTTP protections and login brute-force safeguards."""
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core import clear_login_failures, login_limit_key

H = {'X-Framatex-Request': '1'}


def test_headers_also_protect_denials_and_authenticated_pages():
    with TestClient(app) as client:
        home = client.get('/')
        assert home.status_code == 200
        assert home.headers['cache-control'] == 'no-store'
        assert home.headers['x-frame-options'] == 'DENY'
        assert home.headers['x-content-type-options'] == 'nosniff'
        assert "frame-ancestors 'none'" in home.headers['content-security-policy']
        assert "script-src 'self'" in home.headers['content-security-policy']
        denied = client.get('/api/launches/not-authorized')
        assert denied.status_code == 401
        assert denied.headers['cache-control'] == 'no-store'
        assert denied.headers['x-frame-options'] == 'DENY'
        assert denied.headers['referrer-policy'] == 'same-origin'
        assert denied.headers['permissions-policy'].startswith('camera=()')


def test_rate_limit_blocks_repeated_failed_logins_without_affecting_other_accounts():
    email='nobody-recipe-016@pilot.invalid'
    key=login_limit_key('testclient',email)
    clear_login_failures(key)
    try:
        with TestClient(app) as client:
            for _ in range(5):
                r=client.post('/api/auth/login',headers=H,json={'email': email,'password':'WrongPassword2026'})
                assert r.status_code==401
            blocked=client.post('/api/auth/login',headers=H,json={'email': email,'password':'WrongPassword2026'})
            assert blocked.status_code==429
            assert blocked.headers['cache-control']=='no-store'
            another=client.post('/api/auth/login',headers=H,json={'email':'another-pilot@pilot.invalid','password':'WrongPassword2026'})
            assert another.status_code==401
    finally:
        clear_login_failures(key)
        clear_login_failures(login_limit_key('testclient','another-pilot@pilot.invalid'))


def test_mobile_logout_and_detail_navigation_are_present():
    root = Path(__file__).resolve().parents[1]
    css=(root/'static/styles.css').read_text()
    js=(root/'static/app.js').read_text()
    assert '.sidebar-bottom{display:flex' in css
    assert 'installDetailNavigation();' in js
    assert 'detail-section-select' in js
    assert 'detail-go-top' in js
