"""Explicitly enabled SMTP worker; no send from HTTP requests.
SMTP acceptance is not delivery/read proof. Failed messages are retried; a crash
between SMTP acceptance and database commit requires operator reconciliation.
"""
from datetime import timedelta
from email.message import EmailMessage
import os
import smtplib
import ssl
from sqlalchemy import select, update, text
from .core import SessionLocal, utcnow
from .partner_models import PartnerMail, PartnerMailPreference, PartnerAccount, Partner, PartnerEvent, PartnerRequest


def enqueue(db, event):
    row=db.get(PartnerRequest,event.request_id)
    for account in db.scalars(select(PartnerAccount).where(PartnerAccount.partner_id==row.partner_id,PartnerAccount.active.is_(True))):
        preference=db.get(PartnerMailPreference,account.id)
        if preference and preference.enabled:
            db.add(PartnerMail(event_id=event.id,account_id=account.id))


def smtp_send(recipient, event_id):
    # An operator must provide approved configuration and explicitly run the worker.
    if os.getenv('FRAMATEX_EMAIL_ENABLED')!='1':
        raise RuntimeError('SMTP désactivé')
    host=os.environ['FRAMATEX_SMTP_HOST'];sender=os.environ['FRAMATEX_SMTP_FROM']
    message=EmailMessage()
    message['From']=sender;message['To']=recipient
    message['Subject']='Framatex : mise à jour de votre espace fournisseur'
    message['Message-ID']=f'<{event_id}@framatex.local>'
    message.set_content('Une mise à jour est disponible dans votre espace fournisseur Framatex. Connectez-vous via votre adresse habituelle pour la consulter. Ce message ne contient aucune pièce jointe.')
    accepted=False
    try:
        with smtplib.SMTP(host,int(os.getenv('FRAMATEX_SMTP_PORT','587')),timeout=20) as smtp:
            smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            if os.getenv('FRAMATEX_SMTP_USER'):
                smtp.login(os.environ['FRAMATEX_SMTP_USER'],os.environ['FRAMATEX_SMTP_PASSWORD'])
            refused=smtp.send_message(message)
            if refused:raise smtplib.SMTPRecipientsRefused(refused)
            accepted=True
    except (smtplib.SMTPException,OSError):
        # send_message returned a definitive successful DATA response. A failed
        # QUIT/connection close cannot turn that acceptance into a retry.
        if not accepted:raise
        import logging
        logging.getLogger('framat.smtp').warning('smtp_cleanup_failed_after_acceptance')


def recover_expired(db):
    """Retry abandoned reservations; never replay a possibly accepted SMTP send."""
    from .operations_models import PartnerMailLease
    # Serialize the read/modify/delete cycle: a stale reader must never delete
    # a replacement lease with the same mail_id but a different owner token.
    db.execute(text('BEGIN IMMEDIATE'))
    now=utcnow()
    leases=list(db.scalars(select(PartnerMailLease).where(PartnerMailLease.expires_at<=now)))
    for lease in leases:
        row=db.get(PartnerMail,lease.mail_id)
        if row and row.status=='processing':
            row.status='pending' if lease.phase=='reserved' else 'uncertain'
            row.last_error='LeaseExpiredBeforeSend' if lease.phase=='reserved' else 'SMTPOutcomeUnknown'
            row.next_at=now
        db.delete(lease)
    # Historical processing rows have no proof whether SMTP accepted them.
    for row in db.scalars(select(PartnerMail).where(PartnerMail.status=='processing',
            ~select(PartnerMailLease.mail_id).where(PartnerMailLease.mail_id==PartnerMail.id).exists())):
        row.status='uncertain';row.last_error='HistoricalSMTPOutcomeUnknown'
    db.commit()


def _failure_status(exc):
    if isinstance(exc,smtplib.SMTPRecipientsRefused):
        codes=[value[0] for value in exc.recipients.values()]
        return 'permanent_failed' if codes and all(500<=c<600 for c in codes) else 'failed'
    if isinstance(exc,smtplib.SMTPResponseException):
        return 'permanent_failed' if 500<=exc.smtp_code<600 else 'failed'
    if isinstance(exc,(smtplib.SMTPServerDisconnected,OSError)):
        return 'uncertain'
    return 'failed'


def process_batch(factory=SessionLocal, transport=None, limit=50, checkpoint=None):
    """Bounded worker. checkpoint exists for crash-window tests, never SMTP calls."""
    from uuid import uuid4
    from .operations_models import PartnerMailLease
    if transport is None and os.getenv('FRAMATEX_EMAIL_ENABLED')!='1':
        return {'processed':0,'status':'disabled'}
    send=transport or smtp_send
    lease_seconds=int(os.getenv('FRAMATEX_MAIL_LEASE_SECONDS','120'))
    if not 30<=lease_seconds<=3600:raise ValueError('Bail SMTP invalide (30–3600 secondes)')
    limit=max(1,min(limit,500));processed=0
    with factory() as db:
        recover_expired(db)
        ids=list(db.scalars(select(PartnerMail.id).where(PartnerMail.status.in_(['pending','failed']),
            PartnerMail.next_at<=utcnow(),PartnerMail.attempts<5).order_by(PartnerMail.next_at,PartnerMail.id).limit(limit)))
    for mid in ids:
        token=str(uuid4())
        with factory() as db:
            claimed=db.execute(update(PartnerMail).where(PartnerMail.id==mid,PartnerMail.status.in_(['pending','failed']),
                PartnerMail.next_at<=utcnow(),PartnerMail.attempts<5).values(status='processing'))
            if claimed.rowcount!=1:db.rollback();continue
            db.add(PartnerMailLease(mail_id=mid,token=token,expires_at=utcnow()+timedelta(seconds=lease_seconds),phase='reserved'))
            db.commit()
        if checkpoint:checkpoint('reserved',mid)
        with factory() as db:
            db.execute(text('BEGIN IMMEDIATE'))
            row=db.get(PartnerMail,mid)
            lease=db.scalar(select(PartnerMailLease).where(PartnerMailLease.mail_id==mid,
                PartnerMailLease.token==token,PartnerMailLease.expires_at>utcnow()))
            if not lease or not row or row.status!='processing':db.rollback();continue
            account=db.get(PartnerAccount,row.account_id)
            org=db.get(Partner,account.partner_id);preference=db.get(PartnerMailPreference,account.id)
            if not account.active or not org.active or not preference or not preference.enabled:
                row.status='cancelled';db.delete(lease);db.commit();continue
            # Commit uncertainty boundary BEFORE invoking any external transport.
            # No SQL transaction or session is held while waiting for SMTP.
            lease.phase='sending';row.attempts+=1
            recipient=account.email;attempts=row.attempts
            db.commit()
        if checkpoint:checkpoint('sending',mid)
        status='accepted';last_error=''
        try:
            send(recipient,mid)
            if checkpoint:checkpoint('accepted_before_commit',mid)
        except Exception as exc:
            status=_failure_status(exc)
            if status=='failed' and attempts>=5:status='exhausted'
            last_error=type(exc).__name__[:100]
        processed+=1
        with factory() as db:
            db.execute(text('BEGIN IMMEDIATE'))
            row=db.get(PartnerMail,mid);lease=db.get(PartnerMailLease,mid)
            # Expiration/reconciliation or a replacement owner wins. Finishing
            # an obsolete attempt cannot erase its lease or overwrite a decision.
            if not lease or lease.token!=token or not row or row.status!='processing':
                db.rollback();continue
            row.status=status;row.last_error=last_error
            if status=='accepted':row.accepted_at=utcnow()
            else:row.next_at=utcnow()+timedelta(minutes=2**attempts)
            db.delete(lease);db.commit()
    return {'processed':processed,'status':'completed'}


def reconcile_uncertain(mail_id, decision, reason, factory=SessionLocal):
    """Explicit operator decision after examining the mail relay log.

    Retrying may duplicate a message; no transport provides exactly-once SMTP.
    """
    if decision not in {'retry','accepted','cancelled'} or len(reason.strip())<8:
        raise ValueError('Décision et justification opérateur requises')
    with factory() as db:
        db.execute(text('BEGIN IMMEDIATE'))
        row=db.get(PartnerMail,mail_id)
        if not row or row.status!='uncertain':raise ValueError('Envoi incertain introuvable')
        row.status={'retry':'pending','accepted':'accepted','cancelled':'cancelled'}[decision]
        row.next_at=utcnow()
        if decision=='retry' and row.attempts>=5:raise ValueError('Budget de cinq tentatives épuisé')
        if decision=='accepted':row.accepted_at=utcnow()
        from .audit import audit
        audit(db,None,'partner.mail_reconcile','partner_mail',mail_id,{'decision':decision,'reason':reason})
        db.commit()


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reconcile');p.add_argument('--decision',choices=['retry','accepted','cancelled']);p.add_argument('--reason')
    args=p.parse_args()
    if args.reconcile:
        reconcile_uncertain(args.reconcile,args.decision,args.reason or '')
        print({'status':'reconciled'})
    else:print(process_batch())
