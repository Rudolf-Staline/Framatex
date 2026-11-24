"""Landing publique : « / » sert l'accueil, l'espace FRAMATEX reste accessible."""
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def _assert_security_headers(response):
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-frame-options'] == 'DENY'
    csp = response.headers['content-security-policy']
    assert "frame-ancestors 'none'" in csp and "script-src 'self'" in csp


def test_root_serves_public_landing_with_both_spaces():
    with TestClient(app) as client:
        home = client.get('/')
        assert home.status_code == 200
        _assert_security_headers(home)
        html = home.text
        assert 'Choisissez votre espace' in html
        assert 'href="/espace-framatex"' in html
        assert 'href="/espace-client"' in html
        assert '/assets/landing/landing-redirect.js' in html
        assert 'app.js' not in html


def test_framatex_space_serves_existing_internal_app():
    with TestClient(app) as client:
        page = client.get('/espace-framatex')
        assert page.status_code == 200
        _assert_security_headers(page)
        assert page.content == (ROOT / 'static/index.html').read_bytes()
        assert '/assets/app.js' in page.text


def test_client_space_entry_and_landing_assets_are_served():
    with TestClient(app) as client:
        page = client.get('/espace-client')
        assert page.status_code == 200
        _assert_security_headers(page)
        assert 'Espace Client' in page.text
        # Portail Client (static/client/), relié à /api/client/*.
        assert page.content == (ROOT / 'static/client/index.html').read_bytes()
        assert client.get('/assets/client/client.js').status_code == 200
        for asset in ('landing.css', 'landing.js', 'landing-redirect.js'):
            assert client.get(f'/assets/landing/{asset}').status_code == 200


def test_printed_qr_links_are_forwarded_to_framatex_space():
    script = (ROOT / 'static/landing/landing-redirect.js').read_text()
    assert "'/espace-framatex' + hash" in script
    assert '#\\/launch\\/' in script


def test_landing_motion_assets_are_versioned_and_not_cached():
    with TestClient(app) as client:
        html = client.get('/').text
        for name in ('landing.css', 'motion.css', 'landing.js'):
            path = f'/assets/landing/{name}?v=landing-premium-1'
            assert path in html
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'no-store'
            assert response.headers['content-type'].split(';')[0] == ('text/javascript' if name.endswith('.js') else 'text/css')
        assert 'class="hero-weave" aria-hidden="true"' in html


def test_landing_premium_navigation_and_real_team_photo():
    with TestClient(app) as client:
        html = client.get('/').text
        assert 'class="site-header" data-header' in html
        # Partenariat : les trois photographies officielles de la signature (11 février 2026), locales.
        assert 'data-carousel' in html and '11 février 2026' in html and 'partnership-carousel.js' in html
        for n in (1, 2, 3):
            for ext in ('avif', 'webp', 'jpg'):
                assert f'/assets/landing/partenariat-{n}.{ext}' in html
                assert client.get(f'/assets/landing/partenariat-{n}.{ext}').status_code == 200
        # « Notre solution » : photographie officielle de l'équipe (banner-17.jpg), hébergée localement.
        for name in ('notre-solution-equipe.avif', 'notre-solution-equipe.webp', 'notre-solution-equipe.jpg'):
            assert f'/assets/landing/{name}' in html
            served = client.get(f'/assets/landing/{name}')
            assert served.status_code == 200 and served.headers['content-type'].startswith('image/'), name
        assert 'Équipe réunie autour d’une table de travail' in html
        assert 'btn btn-primary hero-cta' in html
        css = client.get('/assets/landing/landing.css?v=landing-premium-1').text
        assert '--landing-serif' in css
        assert '.site-header {\n  position: sticky; top: 0; z-index: 50;\n  background: var(--navy);' in css
