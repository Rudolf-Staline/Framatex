"""Explicitly enabled SMTP worker; no send from HTTP requests.
SMTP acceptance is not delivery/read proof. Failed messages are retried; a crash
between SMTP acceptance and database commit requires operator reconciliation.
"""
from datetime import timedelta
from email.message import EmailMessage
import os
import smtplib
import ssl
from sqlalchemy import select, update
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
    with smtplib.SMTP(host,int(os.getenv('FRAMATEX_SMTP_PORT','587')),timeout=20) as smtp:
        smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
        if os.getenv('FRAMATEX_SMTP_USER'):
            smtp.login(os.environ['FRAMATEX_SMTP_USER'],os.environ['FRAMATEX_SMTP_PASSWORD'])
        refused=smtp.send_message(message)
        if refused:raise smtplib.SMTPRecipientsRefused(refused)


def process_batch(factory=SessionLocal, transport=None, limit=50):
    if transport is None and os.getenv('FRAMATEX_EMAIL_ENABLED')!='1':
        return {'processed':0,'status':'disabled'}
    send=transport or smtp_send
    processed=0
    with factory() as db:
        ids=list(db.scalars(select(PartnerMail.id).where(PartnerMail.status.in_(['pending','failed']),
            PartnerMail.next_at<=utcnow(),PartnerMail.attempts<5).order_by(PartnerMail.next_at).limit(limit)))
    for mid in ids:
        with factory() as db:
            claimed=db.execute(update(PartnerMail).where(PartnerMail.id==mid,PartnerMail.status.in_(['pending','failed']),
                PartnerMail.next_at<=utcnow(),PartnerMail.attempts<5).values(status='processing',attempts=PartnerMail.attempts+1))
            db.commit()
            if claimed.rowcount!=1:continue
            row=db.get(PartnerMail,mid);account=db.get(PartnerAccount,row.account_id)
            org=db.get(Partner,account.partner_id);preference=db.get(PartnerMailPreference,account.id)
            if not account.active or not org.active or not preference or not preference.enabled:
                row.status='cancelled';db.commit();continue
            try:
                send(account.email,row.id)
            except Exception as exc:
                # Never log SMTP credentials, server responses, message bodies or recipients.
                row.status='failed';row.last_error=type(exc).__name__[:100]
                row.next_at=utcnow()+timedelta(minutes=2**row.attempts)
            else:
                row.status='accepted';row.accepted_at=utcnow();row.last_error=''
            db.commit();processed+=1
    return {'processed':processed,'status':'completed'}

if __name__=='__main__':
    print(process_batch())
