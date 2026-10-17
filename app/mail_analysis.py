"""Analyse locale conservatrice des courriels RFC 5322.

Les engagements proposés ne sont ni des obligations prouvées ni des tâches créées
sans consentement. Aucun appel réseau, aucun rendu HTML actif.
"""
from __future__ import annotations
import re
from email import policy
from email.parser import BytesParser

MAX_BODY = 14000
MAX_ATTACHMENTS = 100


def parse_email(data: bytes) -> dict:
    if not data or len(data) > 20 * 1024 * 1024:
        raise ValueError('Email vide ou trop volumineux')
    msg = BytesParser(policy=policy.default).parsebytes(data)
    if not msg.get('From') and not msg.get('Subject') and not msg.get('Date'):
        raise ValueError('En-têtes de courrier absents : fichier .eml non reconnu')
    if msg.defects:
        raise ValueError('Courrier malformé : structure MIME invalide')
    if msg.get('Bcc'):
        # Bcc may contain sensitive recipients. Never surface or persist it.
        pass
    attachments=[]
    bodies=[]
    for part in msg.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        if filename or part.get_content_disposition() == 'attachment':
            if len(attachments) < MAX_ATTACHMENTS:
                attachments.append({'filename': str(filename or 'Pièce jointe sans nom')[:200],
                                    'content_type': str(part.get_content_type())[:100]})
            continue
        if part.get_content_type() == 'text/plain' and len(bodies) < 4:
            try:
                value=part.get_content()
                if isinstance(value, str):
                    bodies.append(value)
            except (UnicodeDecodeError, LookupError, ValueError, TypeError):
                continue
    body='\n'.join(bodies)
    body=re.sub(r'\x00|[\x01-\x08\x0b\x0c\x0e-\x1f]', '', body)
    body=body[:MAX_BODY]
    return {
        'message_id':str(msg.get('Message-ID',''))[:250],
        'subject':str(msg.get('Subject','(sans objet)'))[:300],
        'sender':str(msg.get('From',''))[:300],
        'recipients':str(msg.get('To',''))[:1800],
        'carbon_copy':str(msg.get('Cc',''))[:1800],
        'sent_at_raw':str(msg.get('Date',''))[:180],
        'body_excerpt':body,
        'attachments':attachments,
    }

# Expressions volontairement transparentes et restrictives ; priorité à la précision.
ACTION = re.compile(r'\b(?:nous (?:vous )?(?:transmettrons|enverrons|confirmerons|livrerons|fournirons)|'
                    r'je (?:vous )?(?:transmettrai|enverrai|confirmerai|livrerai|fournirai)|'
                    r'(?:sera|seront) (?:transmis|transmise|livr[ée]s?|envoy[ée]s?)|'
                    r'(?:merci de|veuillez) (?:transmettre|confirmer|envoyer|fournir))\b', re.I)
DATES = re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b')
CONDITION = re.compile(r'\b(sous réserve[^.;\n]{0,180}|si (?:le|la|les|nous|vous)[^.;\n]{0,180})',re.I)


def suggest_commitments(parsed:dict) -> dict:
    body=parsed.get('body_excerpt') or ''
    candidates=[]
    seen=set()
    for line in body.splitlines():
        line=line.strip().lstrip('>-• \t')
        if len(line)<15 or len(line)>650 or line in seen or not ACTION.search(line):
            continue
        seen.add(line)
        date_match = DATES.search(line)
        due_date=None
        if date_match:
            try:
                from datetime import datetime
                due_date=datetime.strptime(date_match.group(1).replace('-','/'),'%d/%m/%Y').date().isoformat()
            except ValueError:
                pass
        cond=CONDITION.search(line)
        candidates.append({'description':line[:650], 'responsible':parsed.get('sender',''),
                           'due_date':due_date, 'condition':cond.group(1)[:500] if cond else '',
                           'source_excerpt':line[:650]})
        if len(candidates)>=10:break
    return {'candidates':candidates,'method':'Règles lexicales locales',
            'human_confirmation_required':True,
            'limits':'Les dates relatives (ex. vendredi) ne sont pas interprétées. Une proposition ne prouve pas qu’un engagement ferme existe.'}
