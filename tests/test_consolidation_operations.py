"""Synthetic historical schemas and simulated SMTP crash windows only."""
import os, tempfile
os.environ.setdefault('FRAMATEX_DATA_DIR',tempfile.mkdtemp(prefix='framat-operations-tests-'))
import gzip
from pathlib import Path
import sqlite3
from datetime import timedelta
import smtplib
import pytest
from sqlalchemy import create_engine, text, select, delete
from fastapi.testclient import TestClient
from app import migrate
from app.core import SessionLocal, utcnow, COOKIE
from app.models import AuditEvent
from app.operations_models import PartnerMailLease
from app.partner_models import PartnerMail
from app.partner_mail import process_batch, reconcile_uncertain
from test_partners import app, setup, post, organization, activate, H


@pytest.mark.parametrize('revision',[20,21,22,23])
def test_real_historical_intermediate_schemas_upgrade_twice_without_loss(tmp_path,monkeypatch,revision):
    source=tmp_path/'source';source.mkdir();(source/'files').mkdir()
    database=source/'framat.db'
    script=gzip.decompress((Path(__file__).parent/'fixtures'/f'schema_{revision:04}.sql.gz').read_bytes()).decode()
    with sqlite3.connect(database) as db:
        db.executescript(script)
        db.execute("INSERT INTO users(id,email,name,password_hash,active,created_at) VALUES ('historic','historical@sample.local','Historical synthetic','hash',1,'2026-01-01')")
        db.execute("INSERT INTO audit_events(id,action,target_type,target_id,detail,occurred_at) VALUES ('logout-history','session.logout','session','0123456789abcdef0123456789abcdef','{}','2026-01-01')")
        db.execute("INSERT INTO audit_events(id,action,target_type,target_id,detail,occurred_at) VALUES ('generation-history','session.revoke_all','user','historic','{}','2026-01-01')")
    engine=create_engine('sqlite:///'+str(database))
    monkeypatch.setattr(migrate,'engine',engine)
    migrate.migrate();migrate.migrate()
    with engine.connect() as db:
        assert set(db.execute(text('SELECT version FROM schema_migrations')).scalars())==set(migrate.REVISIONS)
        assert db.execute(text("SELECT name FROM users WHERE id='historic'")).scalar_one()=='Historical synthetic'
        assert db.execute(text('SELECT count(*) FROM audit_events')).scalar_one()==2
        assert db.execute(text("SELECT generation FROM session_generations WHERE scope='user:historic'")).scalar_one()=='generation-history'
        assert db.execute(text('SELECT count(*) FROM session_revocations')).scalar_one()==1
        assert not db.exec_driver_sql('PRAGMA foreign_key_check').all()
    assert list(source.glob('framat.db.backup-*'))
    engine.dispose()


class SimulatedPowerLoss(BaseException):pass


def mail_fixture(staff,supplier):
    lid=setup(staff);org=organization(staff,'Synthetic mail supplier')
    activate(staff,supplier,org,'crash-mail@sample.local')
    assert supplier.put('/api/partner/mail-preference',json={'active':True},headers=H).status_code==200
    post(staff,'/api/partners/requests',{'partner_id':org,'launch_id':lid,'order_ref':'SMTP','title':'Certificat','doc_type':'Certificat'})


@pytest.mark.parametrize('phase,expected',[('reserved','accepted'),('sending','uncertain'),('accepted_before_commit','uncertain')])
def test_smtp_crash_reservation_retry_and_uncertain_acceptance(phase,expected):
    with TestClient(app) as staff,TestClient(app) as supplier:
        mail_fixture(staff,supplier);sent=[]
        def checkpoint(at,mid):
            if at==phase:raise SimulatedPowerLoss()
        with pytest.raises(SimulatedPowerLoss):
            process_batch(transport=lambda *args:sent.append(args),checkpoint=checkpoint)
        with SessionLocal() as db:
            lease=db.scalar(select(PartnerMailLease));lease.expires_at=utcnow()-timedelta(seconds=1);db.commit()
        process_batch(transport=lambda *args:sent.append(args))
        with SessionLocal() as db:
            row=db.scalar(select(PartnerMail));assert row.status==expected;mid=row.id
        assert len(sent)==(0 if phase=='sending' else 1)
        if expected=='uncertain':
            process_batch(transport=lambda *args:sent.append(args))
            assert len(sent)==(0 if phase=='sending' else 1)
            reconcile_uncertain(mid,'cancelled','Vérification synthétique du relais')
            with SessionLocal() as db:assert db.get(PartnerMail,mid).status=='cancelled'


def test_smtp_permanent_failure_does_not_retry_and_errors_are_redacted():
    with TestClient(app) as staff,TestClient(app) as supplier:
        mail_fixture(staff,supplier)
        def failure(*args):raise smtplib.SMTPDataError(550,b'secret SMTP response')
        process_batch(transport=failure)
        with SessionLocal() as db:
            row=db.scalar(select(PartnerMail))
            assert row.status=='permanent_failed' and row.last_error=='SMTPDataError'
        assert process_batch(transport=lambda *args:pytest.fail('Permanent failure retried'))['processed']==0


def test_verified_audit_export_and_purge_cannot_revive_revoked_session(tmp_path):
    with TestClient(app) as staff:
        setup(staff);cookie=staff.cookies.get(COOKIE)
        assert staff.post('/api/auth/logout',headers=H).status_code==200
        from app.audit_maintenance import export_audit,purge_export
        archive=tmp_path/'audit.jsonl'
        exported=export_audit(utcnow()+timedelta(days=1),archive)
        assert exported['rows']>0
        assert purge_export(archive)=={'rows':exported['rows'],'applied':False}
        with SessionLocal() as db:assert db.scalar(select(AuditEvent)) is not None
        assert purge_export(archive,apply=True)['applied']
        with SessionLocal() as db:assert db.scalar(select(AuditEvent)) is None
        archive.write_bytes(archive.read_bytes()+b'altered')
        with pytest.raises(ValueError,match='Archive modifiée'):purge_export(archive,apply=True)
        staff.cookies.set(COOKIE,cookie)
        assert staff.get('/api/auth/me').status_code==401


def test_health_and_readiness_have_actual_build_identity_and_safe_checks(monkeypatch):
    with TestClient(app) as staff:
        setup(staff)
        migrate.migrate()  # setup resets metadata and ledger after lifespan.
        response=staff.get('/api/health');assert response.status_code==200
        assert response.json()['version']==app.version
        assert response.json()['commit']!='unknown' and len(response.headers['X-Request-ID'])==32
        monkeypatch.setenv('FRAMATEX_MODE','OPERATIONAL');monkeypatch.setenv('FRAMATEX_UPLOAD_SCAN_MODE','required')
        monkeypatch.setenv('FRAMATEX_SCANNER_COMMAND','missing-framat-scanner')
        response=staff.get('/api/ready');assert response.status_code==503
        assert response.json()['checks']['database'] and not response.json()['checks']['scanner']
        assert 'missing-framat-scanner' not in response.text


def test_unknown_socket_failure_stays_uncertain_instead_of_automatic_retry():
    with TestClient(app) as staff,TestClient(app) as supplier:
        mail_fixture(staff,supplier)
        def failure(*args):raise ConnectionError('Synthetic ambiguous socket failure')
        process_batch(transport=failure)
        with SessionLocal() as db:assert db.scalar(select(PartnerMail)).status=='uncertain'
        assert process_batch(transport=lambda *args:pytest.fail('Ambiguous send retried'))['processed']==0


def test_snapshot_barrier_excludes_sqlite_writers(tmp_path):
    from app.backup import write_barrier
    path=tmp_path/'synthetic.db'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE records(value TEXT)')
    with write_barrier(path):
        with sqlite3.connect(path,timeout=0.01) as writer:
            with pytest.raises(sqlite3.OperationalError,match='locked'):
                writer.execute("INSERT INTO records VALUES ('concurrent')")
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO records VALUES ('resumed')")
        assert db.execute('SELECT value FROM records').fetchall()==[('resumed',)]


def test_missing_0020_with_later_ledger_and_unknown_revision_rejection(tmp_path,monkeypatch):
    database=tmp_path/'framat.db';engine=create_engine('sqlite:///'+str(database))
    monkeypatch.setattr(migrate,'engine',engine)
    migrate.migrate()
    with engine.begin() as db:
        db.execute(text("DELETE FROM schema_migrations WHERE version='0020_audit_session_index'"))
    migrate.migrate()
    with engine.begin() as db:
        assert db.execute(text('SELECT count(*) FROM schema_migrations')).scalar_one()==len(migrate.REVISIONS)
        db.execute(text("INSERT INTO schema_migrations VALUES ('9999_unknown','2026-01-01')"))
    with pytest.raises(RuntimeError,match='Révisions non reconnues'):migrate.migrate()
    with engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM schema_migrations WHERE version='9999_unknown'")).scalar_one()==1
    engine.dispose()


def test_expired_reservation_is_not_sent_by_original_worker():
    with TestClient(app) as staff,TestClient(app) as supplier:
        mail_fixture(staff,supplier);sent=[]
        def expire(at,mid):
            if at=='reserved':
                with SessionLocal() as db:
                    lease=db.get(PartnerMailLease,mid);lease.expires_at=utcnow()-timedelta(seconds=1);db.commit()
        process_batch(transport=lambda *args:sent.append(args),checkpoint=expire)
        assert sent==[]
        process_batch(transport=lambda *args:sent.append(args))
        assert len(sent)==1


def test_obsolete_smtp_attempt_cannot_erase_replacement_lease_or_decision():
    with TestClient(app) as staff,TestClient(app) as supplier:
        mail_fixture(staff,supplier)
        def replace(at,mid):
            if at=='accepted_before_commit':
                with SessionLocal() as db:
                    lease=db.get(PartnerMailLease,mid)
                    lease.token='replacement-owner';lease.phase='reserved'
                    row=db.get(PartnerMail,mid);row.status='cancelled';db.commit()
        process_batch(transport=lambda *args:None,checkpoint=replace)
        with SessionLocal() as db:
            assert db.scalar(select(PartnerMail)).status=='cancelled'
            assert db.scalar(select(PartnerMailLease)).token=='replacement-owner'


def test_two_workers_recover_one_expired_reservation_without_duplicate_transport():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    with TestClient(app) as staff,TestClient(app) as supplier:
        mail_fixture(staff,supplier)
        def crash(at,mid):
            if at=='reserved':raise SimulatedPowerLoss()
        with pytest.raises(SimulatedPowerLoss):process_batch(transport=lambda *args:None,checkpoint=crash)
        with SessionLocal() as db:
            lease=db.scalar(select(PartnerMailLease));lease.expires_at=utcnow()-timedelta(seconds=1);db.commit()
        sent=[];lock=Lock()
        def send(*args):
            with lock:sent.append(args)
        with ThreadPoolExecutor(max_workers=2) as workers:
            results=list(workers.map(lambda _:process_batch(transport=send),range(2)))
        assert len(sent)==1 and sum(r['processed'] for r in results)==1


def test_smtp_quit_failure_does_not_reclassify_known_acceptance(monkeypatch):
    import app.partner_mail as mail
    accepted=[]
    class MockSMTP:
        def __init__(self,*args,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):raise smtplib.SMTPResponseException(500,b'Synthetic QUIT failure after DATA success')
        def ehlo(self):pass
        def starttls(self,**kwargs):pass
        def send_message(self,message):accepted.append(message['Message-ID']);return {}
    monkeypatch.setattr(mail.smtplib,'SMTP',MockSMTP)
    monkeypatch.setenv('FRAMATEX_EMAIL_ENABLED','1')
    monkeypatch.setenv('FRAMATEX_SMTP_HOST','mock.invalid')
    monkeypatch.setenv('FRAMATEX_SMTP_FROM','mock@sample.local')
    monkeypatch.delenv('FRAMATEX_SMTP_USER',raising=False)
    mail.smtp_send('synthetic@sample.local','event-mock')
    assert accepted==['<event-mock@framatex.local>']
