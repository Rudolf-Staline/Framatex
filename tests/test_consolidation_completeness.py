"""Synthetic cross-module regressions: one evaluator, explicit cardinality and ACLs."""
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_partners import app, setup, post, organization, activate, H, PWD
from app.core import SessionLocal, hash_password
from app.models import Role, RolePermission, User
from app.order_documents import OrderMember


def command(c, reference='CMD-COMPLETE'):
    cid = organization(c, 'Client complétude ' + reference, 'client')
    return post(c, '/api/orders', {'client_id': cid, 'reference': reference})['id']


def profile(c, name='Profil de consolidation', validation=False):
    p = post(c, '/api/admin/completeness/profiles', {'name': name})
    r = post(c, f'/api/admin/completeness/profiles/{p["id"]}/rules', {
        'title': 'Fiche technique', 'folder': 'jaune', 'document_type': 'Fiche technique',
        'due_phase': 'preparation', 'requires_validation': validation})
    return p['id'], r['id']


def context(c, oid, pid):
    r = c.put(f'/api/orders/{oid}/completeness/context', json={'profile_id': pid}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def document(c, oid, lid=None):
    r = c.post(f'/api/orders/{oid}/documents', data={
        'folder': 'jaune', 'title': 'Fiche technique', 'doc_type': 'Fiche technique',
        **({'launch_id': lid} if lid else {})}, files={'file': ('fiche.txt', b'Synthetique', 'text/plain')}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()


def report(c, oid):
    r = c.get(f'/api/orders/{oid}/completeness')
    assert r.status_code == 200, r.text
    return r.json()


def policy(c, rid, **data):
    r = c.put(f'/api/admin/completeness/rules/{rid}/policy', json=data, headers=H)
    assert r.status_code == 200, r.text


def test_launchless_optional_future_missing_exception_and_priorities():
    with TestClient(app) as c:
        setup(c); oid = command(c); pid, rid = profile(c)
        initial = context(c, oid, pid)
        assert initial['rows'][0]['status'] == 'missing'
        assert initial['counts']['missing'] == 1
        assert initial['business_rules_confirmed'] is None
        priorities = c.get('/api/workspace/priorities').json()
        action = next(i for i in priorities['items'] if i.get('order_id') == oid)
        assert action['action'] == 'open_order' and action['folder'] == 'jaune' and action['launch_id'] is None
        assert action['url'].endswith('/order/' + oid)
        policy(c, rid, obligation_scope='launch')
        unresolved = report(c, oid)['rows'][0]
        assert unresolved['status'] == 'not_due' and not unresolved['can_review']
        assert c.put(f'/api/orders/{oid}/completeness/rules/{rid}/exception', json={'reason': 'Aucun lancement à dispenser'}, headers=H).status_code == 404
        policy(c, rid, optional=True)
        assert report(c, oid)['rows'][0]['status'] == 'optional'
        assert not any(i.get('order_id') == oid for i in c.get('/api/workspace/priorities').json()['items'])
        policy(c, rid, days_after_launch=30)
        row = report(c, oid)['rows'][0]
        assert row['status'] == 'not_due' and row['deadline_reference_missing']
        assert row['due_date'] is None  # Never silently substitute order creation.
        policy(c, rid, days_after_launch=30, deadline_reference='order_created')
        row = report(c, oid)['rows'][0]
        assert row['status'] == 'not_due' and row['due_date'] and not row['deadline_reference_missing']
        policy(c, rid)
        url = f'/api/orders/{oid}/completeness/rules/{rid}/exception'
        assert c.put(url, json={'reason': 'Dispense synthétique justifiée'}, headers=H).status_code == 200
        result = report(c, oid)
        assert result['rows'][0]['status'] == 'exception'
        assert result['counts']['ready'] == 0 and result['counts']['exception'] == 1
        assert not any(i.get('order_id') == oid for i in c.get('/api/workspace/priorities').json()['items'])
        assert c.put(url, json={'active': False}, headers=H).status_code == 200
        assert report(c, oid)['rows'][0]['status'] == 'missing'


def test_separate_launch_obligations_historical_exception_and_deduplication():
    with TestClient(app) as c:
        setup(c); oid = command(c); pid, rid = profile(c)
        lids = [post(c, '/api/launches', {'name': 'Lancement ' + str(i), 'order_id': oid})['id'] for i in range(2)]
        policy(c, rid, obligation_scope='launch')
        context(c, oid, pid)
        common = document(c, oid)
        rows = report(c, oid)['rows']
        assert len(rows) == 2 and all(r['status'] == 'missing' and not r['documents'] for r in rows)
        own = document(c, oid, lids[0])
        rows = {r['launch_id']: r for r in report(c, oid)['rows']}
        assert rows[lids[0]]['status'] == 'present' and rows[lids[1]]['status'] == 'missing'
        assert rows[lids[0]]['documents'][0]['id'] == own['id']
        # Existing launch exception remains attached to that launch only when
        # projected into the order, and is deduplicated with explicit scope.
        assert c.patch(f'/api/launches/{lids[1]}/completeness/context', json={'profile_id': pid}, headers=H).status_code == 200
        assert c.put(f'/api/launches/{lids[1]}/completeness/rules/{rid}/exception', json={'reason': 'Dérogation historique uniquement lot deux'}, headers=H).status_code == 200
        result = report(c, oid)
        assert len(result['rows']) == 2 and result['counts']['exception'] == 1 and result['counts']['ready'] == 1
        assert not any(i.get('order_id') == oid for i in c.get('/api/workspace/priorities').json()['items'])
        assert c.put(f'/api/orders/{oid}/completeness/rules/{rid}/exception', json={'active': False, 'launch_id': lids[1]}, headers=H).status_code == 200
        actions = [i for i in c.get('/api/workspace/priorities').json()['items'] if i.get('order_id') == oid]
        assert len(actions) == 1 and actions[0]['launch_id'] == lids[1]
        assert common['id'] not in str(report(c, oid)['rows'])


def test_order_and_launch_shared_version_decisions_and_partial_visibility():
    with TestClient(app) as c:
        setup(c); oid = command(c); pid, rid = profile(c, validation=True)
        context(c, oid, pid); doc = document(c, oid)
        assert report(c, oid)['rows'][0]['status'] == 'pending_validation'
        post(c, f'/api/documents/{doc["id"]}/reviews', {'decision': 'approved'})
        assert report(c, oid)['rows'][0]['status'] == 'present'
        assert c.post(f'/api/documents/{doc["id"]}/versions', files={'file': ('v2.txt', b'Nouvelle version', 'text/plain')}, headers=H).status_code == 201
        assert report(c, oid)['rows'][0]['status'] == 'pending_validation'
        hidden_launch = post(c, '/api/launches', {'name': 'Lancement confidentiel', 'order_id': oid})['id']
        with SessionLocal() as db:
            from app.models import Launch
            db.get(Launch, hidden_launch).restricted = True
            role = Role(name='Lecture Rose seulement', grants=[RolePermission(action='launch.read'), RolePermission(action='document.read', folder_slug='rose')])
            reader = User(name='Lecteur', email='limited-completeness@sample.local', password_hash=hash_password(PWD), roles=[role])
            db.add(reader); db.flush(); db.add(OrderMember(order_id=oid, user_id=reader.id)); db.commit()
        post(c, '/api/auth/login', {'email': 'limited-completeness@sample.local', 'password': PWD}, 200)
        limited = report(c, oid)
        assert limited['partial_visibility'] and limited['rows'] == [] and limited['counts']['missing'] == 0
        assert 'Fiche technique' not in str(limited)
        assert c.put(f'/api/orders/{oid}/completeness/rules/{rid}/exception', json={'reason': 'Tentative non habilitée'}, headers=H).status_code == 404
        with SessionLocal() as db:
            role = db.scalar(select(Role).where(Role.name == 'Lecture Rose seulement'))
            role.grants.append(RolePermission(action='document.read', folder_slug='jaune')); db.commit()
        actions = c.get('/api/workspace/priorities').json()['items']
        assert any(i.get('order_id') == oid and i['launch_id'] is None for i in actions)
        assert hidden_launch not in str(actions)  # Hidden source cannot suppress or leak through a common obligation.
        assert c.put(f'/api/orders/{oid}/completeness/rules/{rid}/exception', json={'reason': 'Lecture seule sans droit de dérogation'}, headers=H).status_code == 403


def test_order_projection_uses_actual_portal_publication_availability():
    with TestClient(app) as c, TestClient(app) as external:
        setup(c); oid = command(c); pid, rid = profile(c, validation=True)
        lid = post(c, '/api/launches', {'name': 'Lancement publié', 'order_id': oid})['id']
        # A historical profile is represented in the order with its own scope.
        assert c.patch(f'/api/launches/{lid}/completeness/context', json={'profile_id': pid}, headers=H).status_code == 200
        policy(c, rid, requires_client_publication=True)
        doc = document(c, oid, lid)
        post(c, f'/api/documents/{doc["id"]}/reviews', {'decision': 'approved'})
        assert report(c, oid)['rows'][0]['status'] == 'pending_publication'
        pub = post(c, f'/api/launches/{lid}/client-publications', {'document_version_id': doc['latest']['id'], 'reason': 'Publication synthétique approuvée'})
        from app.partner_phase2_models import BusinessOrder
        with SessionLocal() as db: cid = db.get(BusinessOrder, oid).client_id
        binding = post(c, '/api/partners/publications', {'partner_id': cid, 'publication_id': pub['id']})
        assert report(c, oid)['rows'][0]['status'] == 'pending_publication'
        invite = activate(c, external, cid, 'publication-consolidation@sample.local')
        assert report(c, oid)['rows'][0]['status'] == 'present'
        assert external.get(f'/api/partner/publications/{binding["id"]}/download').status_code == 200
        assert c.patch(f'/api/partners/accounts/{invite["account_id"]}', json={'active': False}, headers=H).status_code == 200
        assert report(c, oid)['rows'][0]['status'] == 'pending_publication'
        assert c.patch(f'/api/partners/accounts/{invite["account_id"]}', json={'active': True}, headers=H).status_code == 200
        post(c, f'/api/client-publications/{pub["id"]}/revoke', {'reason': 'Retrait synthétique de la publication'}, 200)
        assert report(c, oid)['rows'][0]['status'] == 'pending_publication'


def test_completeness_batches_current_versions_and_bounds_evidence_payload():
    """Query growth is independent of document/version count for one rule."""
    from sqlalchemy import event
    from app.core import engine
    from app.models import Document, DocumentVersion, Folder
    from app.order_documents import OrderDossier
    from app.partner_phase2_models import BusinessOrder
    from app.workflow_models import DocumentReview
    with TestClient(app) as c:
        setup(c); oid = command(c); pid, rid = profile(c, validation=True)
        context(c, oid, pid)
        def grow(start, stop):
            with SessionLocal() as db:
                folder_id = db.scalar(select(Folder.id).join(OrderDossier).where(OrderDossier.order_id == oid, Folder.slug == 'jaune'))
                user_id = db.get(BusinessOrder, oid).created_by
                for i in range(start, stop):
                    doc = Document(id=f'complete-doc-{i}', folder_id=folder_id, title=f'Fiche {i}', doc_type='Fiche technique', created_by=user_id)
                    db.add(doc); db.flush()
                    for number in (1, 2):
                        version = DocumentVersion(id=f'complete-version-{i}-{number}', document_id=doc.id, number=number,
                            original_name='synthetic.txt', disk_name=f'complete-{i}-{number}', content_type='text/plain', size=1,
                            sha256='0'*64, uploaded_by=user_id)
                        db.add(version); db.flush()
                        if number == 2: db.add(DocumentReview(document_version_id=version.id, decision='approved', reviewed_by=user_id))
                db.commit()
        def measured():
            statements = []
            def count(conn, cursor, statement, parameters, context, executemany): statements.append(statement)
            event.listen(engine, 'before_cursor_execute', count)
            try: result = report(c, oid)
            finally: event.remove(engine, 'before_cursor_execute', count)
            return result, len(statements)
        grow(0, 10); small, small_count = measured()
        grow(10, 200); large, large_count = measured()
        assert small['counts']['ready'] == large['counts']['ready'] == 1
        assert large['rows'][0]['document_count'] == 200
        assert len(large['rows'][0]['documents']) == 20 and large['rows'][0]['documents_truncated']
        assert all(d['version'] == 2 for d in large['rows'][0]['documents'])
        assert large_count <= small_count + 4, (small_count, large_count)
        assert large_count < 45, large_count
        print(f'Completeness synthetic 10/200 docs, 2 versions each: {small_count}/{large_count} SQL statements; evidence {len(small["rows"][0]["documents"])}/{len(large["rows"][0]["documents"])}')
