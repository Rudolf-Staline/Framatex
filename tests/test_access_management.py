"""Collaborateurs et habilitations : comptes, affectations par commande / sous-dossier, isolation.

Chaque scénario est vérifié positivement et négativement, par l'API réelle.
Les comptes fictifs (example.test) et leurs mots de passe sont créés pendant le
test, sur la base temporaire des tests ; aucun secret réel n'est utilisé.
"""
import importlib
import json
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text

from app.core import Base, SessionLocal, check_password, hash_password
from app.main import app
from app.models import AuditEvent, Role, RolePermission, User

H = {'X-Framatex-Request': '1'}
CHEF_PW = secrets.token_urlsafe(18) + 'Aa1!'
DEPOT = ['document.read', 'document.download', 'document.write', 'document.version', 'document.comment', 'controls.read']


@pytest.fixture(scope='module')
def env():
    with TestClient(app) as chef:          # démarrage : migrations, dont 0013
        email = f'chef-{uuid.uuid4().hex[:8]}@example.test'
        with SessionLocal() as db:
            role = db.scalar(select(Role).where(Role.name == 'Administrateur')) or Role(name='Administrateur')
            db.add(User(name='Chef recette', email=email, password_hash=hash_password(CHEF_PW), roles=[role]))
            db.commit()
        assert chef.post('/api/auth/login', headers=H, json={'email': email, 'password': CHEF_PW}).status_code == 200
        tag = uuid.uuid4().hex[:6]
        launches = {}
        for key in ('001', '002', '003', '004'):
            r = chef.post('/api/launches', headers=H, json={'name': f'Commande {key} {tag}', 'order_ref': f'CMD-{key}-{tag}',
                                                            'client_name': 'Client fictif', 'standard_profile': True})
            assert r.status_code == 201, r.text
            launches[key] = r.json()['id']
        docs = {}
        for key, folder, title in (('001', 'jaune', 'FICHE-JAUNE-001'), ('001', 'bleu', 'DOUANE-BLEU-001'),
                                   ('002', 'rose', 'LIVRAISON-ROSE-002'), ('003', 'vert', 'FACTURE-VERT-003')):
            r = chef.post(f"/api/launches/{launches[key]}/documents", headers=H,
                          data={'folder': folder, 'title': f'{title}-{tag}', 'doc_type': 'Autre'},
                          files={'file': (f'{title}.txt', f'{title} {tag}'.encode(), 'text/plain')})
            assert r.status_code == 201, r.text
            docs[title] = r.json()
        techs = {}
        for name in ('a', 'b', 'c', 'd'):
            r = chef.post('/api/admin/collaborators', headers=H, json={
                'name': f'Technicien {name.upper()}', 'email': f'technicien.{name}.{tag}@example.test', 'job_title': 'Technicien'})
            assert r.status_code == 201, r.text
            techs[name] = {'id': r.json()['collaborator']['id'], 'email': f'technicien.{name}.{tag}@example.test',
                           'temp': r.json()['temporary_password'], 'password': secrets.token_urlsafe(16) + 'Bb2?'}
        yield {'chef': chef, 'launches': launches, 'docs': docs, 'techs': techs, 'tag': tag}


def login(env, key, first=False):
    tech = env['techs'][key]
    client = TestClient(app)
    password = tech['temp'] if first else tech['password']
    r = client.post('/api/auth/login', headers=H, json={'email': tech['email'], 'password': password})
    assert r.status_code == 200, r.text
    return client


def assign(env, key, launch, folders):
    r = env['chef'].put(f"/api/admin/collaborators/{env['techs'][key]['id']}/assignments/{env['launches'][launch]}",
                        headers=H, json={'folders': folders})
    assert r.status_code == 200, r.text
    return r.json()


def visible_ids(client):
    return {row['id'] for row in client.get('/api/workspace/launches').json()}


def test_01_04_accounts_temporary_password_and_no_default_access(env):
    chef, techs = env['chef'], env['techs']
    # 1. Le chef garde toute l'administration.
    listing = chef.get('/api/admin/collaborators')
    assert listing.status_code == 200 and {t['id'] for t in techs.values()} <= {c['id'] for c in listing.json()}
    # Aucun mot de passe en clair dans le journal ni dans la base.
    with SessionLocal() as db:
        for tech in techs.values():
            user = db.get(User, tech['id'])
            assert user.password_hash != tech['temp'] and check_password(user.password_hash, tech['temp'])
        details = ' '.join(e.detail or '' for e in db.scalars(select(AuditEvent).where(AuditEvent.action.like('user.%'))))
        assert not any(t['temp'] in details for t in techs.values())
    # 2–3. Première connexion : seul le changement du mot de passe temporaire est possible.
    for key, tech in techs.items():
        client = login(env, key, first=True)
        me = client.get('/api/auth/me').json()
        assert me['must_change_password'] is True and me['admin'] is False and me['access_mode'] == 'assignments'
        assert client.get('/api/workspace/launches').status_code == 403
        assert client.post('/api/account/password', headers=H, json={'current_password': 'faux-mot-de-passe',
                                                                     'new_password': tech['password']}).status_code == 422
        assert client.post('/api/account/password', headers=H, json={'current_password': tech['temp'],
                                                                     'new_password': tech['temp']}).status_code == 422
        assert client.post('/api/account/password', headers=H, json={'current_password': tech['temp'],
                                                                     'new_password': tech['password']}).status_code == 200
        assert client.get('/api/workspace/launches').status_code == 200
    # Le mot de passe temporaire ne fonctionne plus.
    assert TestClient(app).post('/api/auth/login', headers=H, json={'email': techs['a']['email'],
                                                                    'password': techs['a']['temp']}).status_code == 401
    # 4. Nouveau technicien : aucune commande, tableau de bord vide, URL directe refusée.
    a = login(env, 'a')
    assert visible_ids(a) == set() and a.get('/api/launches').json() == []
    board = a.get('/api/workspace/dashboard')
    assert board.status_code == 200 and env['tag'] not in board.text
    assert a.get(f"/api/launches/{env['launches']['001']}").status_code == 404
    # Un technicien n'administre rien.
    for path in ('/api/admin/collaborators', '/api/admin/users', '/api/admin/access/overview'):
        assert a.get(path).status_code == 403


def test_password_chosen_by_chef_in_legacy_screen_is_temporary(env):
    """Écran Administration historique : le chef ne connaît jamais un mot de passe permanent."""
    chef = env['chef']
    role = chef.post('/api/admin/roles', headers=H, json={'name': f'Lecture {env["tag"]}', 'permissions': [{'action': 'launch.read'}]})
    chosen = secrets.token_urlsafe(16) + 'Cc3!'
    email = f'historique.{env["tag"]}@example.test'
    r = chef.post('/api/admin/users', headers=H, json={'name': 'Compte historique', 'email': email, 'password': chosen,
                                                         'role_ids': [role.json()['id']]})
    assert r.status_code == 201, r.text
    user = TestClient(app)
    assert user.post('/api/auth/login', headers=H, json={'email': email, 'password': chosen}).status_code == 200
    assert user.get('/api/workspace/launches', headers=H).status_code == 403
    assert user.get('/api/auth/me', headers=H).json()['must_change_password'] is True
    own = secrets.token_urlsafe(16) + 'Dd4!'
    assert user.post('/api/account/password', headers=H, json={'current_password': chosen, 'new_password': own}).status_code == 200
    assert user.get('/api/workspace/launches', headers=H).json() == []      # aucune commande sans affectation
    with SessionLocal() as db:
        stored = db.scalar(select(User).where(User.email == email)).password_hash
        assert stored.startswith('$argon2') and own not in stored and not check_password(stored, chosen)


def test_05_11_dynamic_assignments_example(env):
    L, docs, tag = env['launches'], env['docs'], env['tag']
    # Exemple : A → 001 Jaune+Rose, 003 Bleu+Vert ; B → 001 Bleu, 002 les quatre ; C → aucune.
    assign(env, 'a', '001', {'jaune': DEPOT, 'rose': ['document.read']})
    assign(env, 'a', '003', {'bleu': ['document.read'], 'vert': ['document.read', 'document.download']})
    assign(env, 'b', '001', {'bleu': ['document.read']})
    assign(env, 'b', '002', {s: ['document.read', 'document.download'] for s in ('jaune', 'rose', 'bleu', 'vert')})
    a, b, c = login(env, 'a'), login(env, 'b'), login(env, 'c')
    assert visible_ids(a) == {L['001'], L['003']}
    assert visible_ids(b) == {L['001'], L['002']}
    assert visible_ids(c) == set()
    # 6. Aucun accès aux commandes non attribuées, y compris par URL directe.
    assert a.get(f"/api/launches/{L['002']}").status_code == 404
    assert c.get(f"/api/launches/{L['001']}").status_code == 404
    # 7–8. Sous-dossiers différents selon la commande : contenu et titres masqués ailleurs.
    detail = a.get(f"/api/launches/{L['001']}").json()
    folders = {f['slug']: f for f in detail['folders']}
    assert folders['jaune']['can_read'] and folders['rose']['can_read']
    assert not folders['bleu']['can_read'] and folders['bleu']['documents'] == []
    assert 'DOUANE-BLEU-001' not in json.dumps(detail)
    b_detail = b.get(f"/api/launches/{L['001']}").json()
    assert 'DOUANE-BLEU-001' in json.dumps(b_detail) and 'FICHE-JAUNE-001' not in json.dumps(b_detail)
    # 9. Un seul technicien sur toute la commande 002.
    assert all(f['can_read'] for f in b.get(f"/api/launches/{L['002']}").json()['folders'])
    # 10. Commande 004 gérée uniquement par le chef.
    overview = env['chef'].get('/api/admin/access/overview').json()
    row = next(r for r in overview['launches'] if r['launch']['id'] == L['004'])
    assert row['chef_only'] and len(row['unassigned_folders']) == 4
    assert all(L['004'] not in visible_ids(x) for x in (a, b, c))
    # 11. Plusieurs techniciens dans le même sous-dossier (lecture seule pour D).
    assign(env, 'd', '001', {'jaune': ['document.read']})
    matrix = env['chef'].get(f"/api/admin/launches/{L['001']}/assignments").json()
    assert set(matrix['coverage']['jaune']) == {env['techs']['a']['id'], env['techs']['d']['id']}
    # Un compte, plusieurs commandes : aucun doublon de compte.
    assert sum(1 for x in env['chef'].get('/api/admin/collaborators').json() if x['email'] == env['techs']['a']['email']) == 1
    assert next(x for x in env['chef'].get('/api/admin/collaborators').json() if x['id'] == env['techs']['a']['id'])['launches_count'] == 2


def test_12_16_actions_upload_validate_download_and_direct_urls(env):
    L, docs = env['launches'], env['docs']
    a, d, c = login(env, 'a'), login(env, 'd'), login(env, 'c')
    jaune_doc = docs['FICHE-JAUNE-001']
    # 12. A dépose et dépose une nouvelle version, mais ne valide pas.
    up = a.post(f"/api/launches/{L['001']}/documents", headers=H, data={'folder': 'jaune', 'title': 'Fiche de prix A', 'doc_type': 'Fiche de prix'},
                files={'file': ('prix.txt', b'prix technicien A', 'text/plain')})
    assert up.status_code == 201, up.text
    assert a.post(f"/api/documents/{up.json()['id']}/versions", headers=H, files={'file': ('prix2.txt', b'prix V2', 'text/plain')}).status_code == 201
    rows = a.get(f"/api/launches/{L['001']}/completeness").json()['rows']
    rule = next(r for r in rows if r['title'] == 'Fiche de prix')
    assert rule['status'] == 'pending_validation' and rule['can_review'] is False
    assert a.post(f"/api/launches/{L['001']}/completeness/rules/{rule['id']}/validate", headers=H,
                  json={'document_id': up.json()['id']}).status_code == 403
    # Rose en lecture seule : pas de dépôt.
    assert a.post(f"/api/launches/{L['001']}/documents", headers=H, data={'folder': 'rose', 'title': 'x', 'doc_type': 'Autre'},
                  files={'file': ('x.txt', b'x', 'text/plain')}).status_code == 403
    # D : lecture sans téléchargement, sans dépôt, sans commentaire.
    assert d.get(f"/api/documents/{jaune_doc['id']}/versions/1/download").status_code == 403
    assert a.get(f"/api/documents/{jaune_doc['id']}/versions/1/download").status_code == 200
    assert d.post(f"/api/document-versions/{jaune_doc['latest']['id']}/comments", headers=H, json={'body': 'commentaire D'}).status_code == 403
    assert a.post(f"/api/document-versions/{jaune_doc['latest']['id']}/comments", headers=H, json={'body': 'commentaire A'}).status_code == 201
    # 15–16. URL directe et accès indirects (document, version, passeport, QR) refusés à C.
    bleu_doc = docs['DOUANE-BLEU-001']
    for path in (f"/api/launches/{L['001']}", f"/api/documents/{jaune_doc['id']}/versions/1/download",
                 f"/api/document-versions/{jaune_doc['latest']['id']}/passport", f"/api/launches/{L['001']}/paper-link",
                 f"/api/document-versions/{jaune_doc['latest']['id']}/comments", f"/api/launches/{L['001']}/completeness"):
        assert c.get(path).status_code == 404, path
    # A, affecté à 001 sans Bleu : le passeport et le téléchargement du Bleu restent refusés.
    assert a.get(f"/api/documents/{bleu_doc['id']}/versions/1/download").status_code == 403
    assert a.get(f"/api/document-versions/{bleu_doc['latest']['id']}/passport").status_code in (403, 404)
    assert a.get(f"/api/document-versions/{jaune_doc['latest']['id']}/passport").status_code == 200


def test_17_search_dashboard_activity_and_controls_stay_scoped(env):
    a, tag = login(env, 'a'), env['tag']
    found = a.get('/api/workspace/search', params={'q': f'FICHE-JAUNE-001-{tag}'}).json()
    assert found['total'] == 1
    for hidden in ('DOUANE-BLEU-001', 'LIVRAISON-ROSE-002'):
        assert a.get('/api/workspace/search', params={'q': f'{hidden}-{tag}'}).json()['total'] == 0
    board = a.get('/api/workspace/dashboard').text
    assert f'CMD-002-{tag}' not in board and f'DOUANE-BLEU-001-{tag}' not in board
    assert f'CMD-001-{tag}' in board
    activity = a.get('/api/workspace/activity', params={'limit': 200}).text
    assert f'DOUANE-BLEU-001-{tag}' not in activity and f'LIVRAISON-ROSE-002-{tag}' not in activity
    priorities = a.get('/api/workspace/priorities').json()
    assert {item['launch_id'] for item in priorities['items']} <= {env['launches']['001'], env['launches']['003']}
    assert all(item.get('folder') in (None, 'jaune', 'rose', 'bleu', 'vert') for item in priorities['items'])
    assert not any(item['launch_id'] == env['launches']['001'] and item.get('folder') in ('bleu', 'vert')
                   for item in priorities['items'])
    # Assistant : indication de rubrique seulement sur un sous-dossier affecté (Vert : A sur 003, pas sur 001).
    ask = lambda client, **extra: client.post('/api/assistant/guide', headers=H, json={'question': 'où classer une facture', **extra}).json()
    assert ask(a)['folder'] == 'vert'
    assert ask(a, launch_id=env['launches']['001'])['folder'] is None
    assert ask(a, launch_id=env['launches']['003'])['folder'] == 'vert'
    assert ask(login(env, 'c'))['folder'] is None
    assert login(env, 'c').post('/api/assistant/guide', headers=H, json={'question': 'facture', 'launch_id': env['launches']['001']}).status_code == 404


def test_controls_require_controls_read_on_both_folders(env):
    """Consulter contrôles : distinct de la lecture, et sans fuite d'un sous-dossier non attribué."""
    chef, L = env['chef'], env['launches']
    rules = []
    for left, right in (('jaune', 'jaune'), ('jaune', 'bleu')):
        r = chef.post('/api/admin/quality-rules', headers=H, json={
            'name': f'Contrôle {left}/{right} {env["tag"]}', 'field_key': 'reference_commande',
            'left_doc_type': 'Fiche d’emploi', 'right_doc_type': 'Lancement définitif', 'left_folder': left, 'right_folder': right})
        assert r.status_code == 201, r.text
        rules.append(r.json()['id'])
    def seen(client):
        return {row['rule_id'] for row in client.get(f"/api/launches/{L['001']}/quality").json()['rows']} & set(rules)
    a, d = login(env, 'a'), login(env, 'd')
    assert seen(chef) == set(rules)
    # A : Jaune avec « Consulter contrôles », pas de Bleu → seul le contrôle Jaune/Jaune.
    assert seen(a) == {rules[0]}
    # D : Jaune en lecture seule, sans « Consulter contrôles » → aucun contrôle.
    assert seen(d) == set()
    assert d.get(f"/api/launches/{L['001']}/excel-inspections").status_code == 200


def test_13_14_revocation_and_deactivation_take_effect_immediately(env):
    L, docs = env['launches'], env['docs']
    a, b = login(env, 'a'), login(env, 'b')
    jaune_doc = docs['FICHE-JAUNE-001']
    assert a.get(f"/api/documents/{jaune_doc['id']}/versions/1/download").status_code == 200
    # 13. Retrait de Jaune pendant la session ouverte de A : effet à la requête suivante.
    assign(env, 'a', '001', {'rose': ['document.read', 'document.download']})
    assert a.get(f"/api/documents/{jaune_doc['id']}/versions/1/download").status_code == 403
    assert 'FICHE-JAUNE-001' not in a.get(f"/api/launches/{L['001']}").text
    assign(env, 'a', '001', {})
    assert a.get(f"/api/launches/{L['001']}").status_code == 404
    assign(env, 'a', '001', {'jaune': DEPOT, 'rose': ['document.read']})
    # 14. Désactivation : la session ouverte de B est refusée immédiatement, la connexion aussi.
    assert b.get('/api/workspace/launches').status_code == 200
    assert env['chef'].patch(f"/api/admin/collaborators/{env['techs']['b']['id']}", headers=H, json={'active': False}).status_code == 200
    assert b.get('/api/workspace/launches').status_code == 401
    assert TestClient(app).post('/api/auth/login', headers=H, json={'email': env['techs']['b']['email'],
                                                                    'password': env['techs']['b']['password']}).status_code == 401
    assert env['chef'].patch(f"/api/admin/collaborators/{env['techs']['b']['id']}", headers=H, json={'active': True}).status_code == 200
    # Réinitialisation : sessions révoquées, nouveau mot de passe temporaire obligatoire.
    reset = env['chef'].post(f"/api/admin/collaborators/{env['techs']['b']['id']}/reset-password", headers=H)
    assert reset.status_code == 200 and reset.json()['temporary_password']
    env['techs']['b']['temp'] = reset.json()['temporary_password']
    b2 = login(env, 'b', first=True)
    assert b2.get('/api/workspace/launches').status_code == 403
    assert b2.post('/api/account/password', headers=H, json={'current_password': env['techs']['b']['temp'],
                                                             'new_password': env['techs']['b']['password']}).status_code == 200
    # Protections du chef : pas d'affectation d'administrateur, pas d'auto-désactivation.
    chef_id = env['chef'].get('/api/auth/me').json()['id']
    assert env['chef'].put(f"/api/admin/collaborators/{chef_id}/assignments/{L['001']}", headers=H,
                           json={'folders': {'jaune': ['document.read']}}).status_code == 422
    assert env['chef'].patch(f"/api/admin/collaborators/{chef_id}", headers=H, json={'active': False}).status_code == 422
    assert env['chef'].get('/api/admin/collaborators').status_code == 200
    # Historique : auteur, cible et changements, sans secret.
    history = env['chef'].get(f"/api/admin/collaborators/{env['techs']['a']['id']}/history").json()
    actions = {h['action'] for h in history}
    assert {'access.assignment.grant', 'access.assignment.revoke', 'access.assignment.update'} <= actions
    assert all(h['actor'] for h in history)


def test_18_business_memory_confidentiality(env):
    chef, L = env['chef'], env['launches']
    partner = chef.post('/api/workspace/partners', headers=H, json={'party_type': 'fournisseur', 'name': f"Fournisseur {env['tag']}"}).json()
    general = chef.post('/api/workspace/business-memory', headers=H, json={
        'partner_id': partner['id'], 'category': 'retard', 'event_date': '2026-11-01', 'body': 'Note generale fournisseur visible'}).json()
    secret = chef.post('/api/workspace/business-memory', headers=H, json={
        'partner_id': partner['id'], 'launch_id': L['002'], 'category': 'qualite', 'event_date': '2026-11-02',
        'body': 'Note confidentielle commande 002'}).json()
    assert general['id'] and secret['id']
    a, c = login(env, 'a'), login(env, 'c')
    items = a.get('/api/workspace/business-memory').json()['items']
    ids = {i['id'] for i in items}
    assert general['id'] in ids and secret['id'] not in ids          # A : Technique de 001, pas 002
    assert a.get(f"/api/workspace/business-memory/{secret['id']}").status_code in (403, 404)
    assert c.get('/api/workspace/business-memory').status_code == 403   # C : aucune commande


def test_19_notification_recipients(env):
    from app.access_notifications import recipients
    L, techs = env['launches'], env['techs']
    with SessionLocal() as db:
        mine = {t['id'] for t in techs.values()}
        rows = recipients(db, launch_id=L['001'], folders=['jaune'], event_type='document.new_version')
        assert {r['user_id'] for r in rows} & mine == {techs['a']['id'], techs['d']['id']}
        validators = recipients(db, launch_id=L['001'], folders=['jaune'], event_type='document.validation_requested')
        assert not {r['user_id'] for r in validators} & mine             # ni A ni D ne valident
        mine = {t['id'] for t in techs.values()}
        assert not {r['user_id'] for r in recipients(db, launch_id=L['004'], folders=['jaune', 'rose', 'bleu', 'vert'],
                                                     event_type='document.new_version')} & mine
    d = login(env, 'd')
    assert d.put('/api/account/preferences', headers=H, json={'preferences': {'important_changes': False}}).status_code == 200
    with SessionLocal() as db:
        rows = [r for r in recipients(db, launch_id=L['001'], folders=['jaune'], event_type='document.new_version') if r['user_id'] in mine]
        assert {r['user_id'] for r in rows} == {techs['a']['id']}
        assert rows[0]['channels'] == {'internal': True, 'email': False}
    preview = env['chef'].get('/api/admin/access/recipients', params={'launch_id': L['001'], 'event': 'document.new_version', 'folders': ['jaune']})
    assert preview.status_code == 200 and [r['user_id'] for r in preview.json() if r['user_id'] in mine] == [techs['a']['id']]


def test_20_assignments_persist_after_restart(env):
    with TestClient(app) as restarted:       # nouveau démarrage de l'application, même base
        r = restarted.post('/api/auth/login', headers=H, json={'email': env['techs']['a']['email'], 'password': env['techs']['a']['password']})
        assert r.status_code == 200
        assert {row['id'] for row in restarted.get('/api/workspace/launches').json()} == {env['launches']['001'], env['launches']['003']}


def test_bulk_copy_and_legacy_proposals_require_confirmation(env):
    chef, L, techs = env['chef'], env['launches'], env['techs']
    proposal = chef.get(f"/api/admin/launches/{L['004']}/assignments/copy-from/{L['001']}").json()
    assert proposal['proposal'] and chef.get(f"/api/admin/launches/{L['004']}/assignments").json()['managed_by_chef_only']
    bulk = chef.post('/api/admin/assignments/bulk', headers=H, json={'user_ids': [techs['c']['id']], 'launch_ids': [L['003'], L['004']],
                                                                    'folders': {'vert': ['document.read']}})
    assert bulk.status_code == 200 and bulk.json()['changes'] == 2
    assert {row['id'] for row in login(env, 'c').get('/api/workspace/launches').json()} == {L['003'], L['004']}


def test_migration_0013_converts_accounts_without_opening_rights(tmp_path, monkeypatch):
    migration = importlib.import_module('app.migrate')
    engine = create_engine('sqlite:///' + str(tmp_path / 'before-0013.db'))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for name in ('collaborator_profiles', 'launch_assignments', 'legacy_access_proposals'):
            conn.execute(text(f'DROP TABLE {name}'))
        for revision in migration.REVISIONS[:migration.REVISIONS.index('0013_access_management')]:
            conn.execute(text('INSERT INTO schema_migrations VALUES (:v,:d)'), {'v': revision, 'd': '2026-11-01'})
        conn.execute(text("INSERT INTO roles (id,name) VALUES ('ra','Administrateur'),('rt','Technique')"))
        conn.execute(text("INSERT INTO role_permissions (id,role_id,action,folder_slug) VALUES "
                          "('p1','rt','launch.read',NULL),('p2','rt','document.read','jaune'),('p3','rt','document.write','jaune')"))
        for uid, email, digest in (('chef', 'admin.test@framatex.com', 'hash-chef'), ('tech', 'tech@example.test', 'hash-tech')):
            conn.execute(text("INSERT INTO users (id,email,name,password_hash,active,created_at) VALUES (:i,:e,:i,:h,1,'2026-01-01')"),
                         {'i': uid, 'e': email, 'h': digest})
        conn.execute(text("INSERT INTO user_roles (user_id,role_id) VALUES ('chef','ra'),('tech','rt')"))
        conn.execute(text("INSERT INTO launches (id,name,status,created_by,created_at,updated_at,restricted) VALUES "
                          "('open','Ouverte','À compléter','chef','2026-01-01','2026-01-01',0),"
                          "('closed','Restreinte','À compléter','chef','2026-01-01','2026-01-01',1)"))
    monkeypatch.setattr(migration, 'engine', engine)
    migration.migrate(); migration.migrate()
    with engine.connect() as conn:
        assert set(inspect(engine).get_table_names()) >= {'collaborator_profiles', 'launch_assignments', 'legacy_access_proposals'}
        assert conn.execute(text("SELECT password_hash FROM users WHERE id='chef'")).scalar() == 'hash-chef'   # chef intact
        assert dict(conn.execute(text('SELECT user_id, access_scope FROM collaborator_profiles')).all()) == {'chef': 'assignments', 'tech': 'assignments'}
        assert conn.execute(text('SELECT COUNT(*) FROM launch_assignments')).scalar() == 0                    # aucun droit ouvert
        proposals = conn.execute(text("SELECT launch_id, origin, folders, status FROM legacy_access_proposals WHERE user_id='tech'")).all()
        assert [(p[0], p[1], p[3]) for p in proposals] == [('open', 'role', 'pending')]                      # restreinte non proposée
        assert set(json.loads(proposals[0][2])) == {'jaune'}
    engine.dispose()
