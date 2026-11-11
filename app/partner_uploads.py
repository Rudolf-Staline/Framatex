"""Partner storage budget and optional required scanner, never a format-only AV claim."""
import logging
import time
import os
import shlex
import subprocess
from fastapi import HTTPException
from sqlalchemy import select,func,update
from .partner_models import Partner,PartnerRequest,PartnerSubmission
from .partner_phase2_models import PartnerAttachment,PartnerAdministrativeDocument

def lock_budget(db,org_id):
    # Serializes writes for one organization (SQLite writer lock / SQL row lock).
    db.execute(update(Partner).where(Partner.id==org_id).values(id=org_id))
    if not db.scalar(select(Partner.active).where(Partner.id==org_id)):
        raise HTTPException(403,'Organisation suspendue')

def verify_budget(db,org_id,new_size):
    quota=int(os.getenv('FRAMATEX_PARTNER_QUOTA_BYTES',str(100*1024*1024)))
    used=db.scalar(select(func.coalesce(func.sum(PartnerSubmission.size),0)).join(PartnerRequest).where(PartnerRequest.partner_id==org_id))
    attached=db.scalar(select(func.coalesce(func.sum(PartnerAttachment.size),0)).where(PartnerAttachment.partner_id==org_id))
    administrative=db.scalar(select(func.coalesce(func.sum(PartnerAdministrativeDocument.size),0)).where(PartnerAdministrativeDocument.partner_id==org_id))
    if used+attached+administrative+new_size>quota:raise HTTPException(413,'Quota de stockage de cette organisation dépassé')

def scan(path):
    mode=os.getenv('FRAMATEX_UPLOAD_SCAN_MODE','disabled')
    if mode=='disabled':return 'not_scanned'
    if mode!='required':raise HTTPException(503,'Politique antivirus invalide')
    backend=os.getenv('FRAMATEX_SCANNER_BACKEND','command')
    if backend not in {'command','clamav'}:raise HTTPException(503,'Adaptateur antivirus invalide')
    command=os.getenv('FRAMATEX_SCANNER_COMMAND','clamscan --no-summary --alert-encrypted=yes' if backend=='clamav' else '')
    if not command:raise HTTPException(503,'Scanner obligatoire indisponible : dépôt refusé')
    started=time.monotonic()
    log=logging.getLogger('framat.upload_scan')
    try:
        timeout=int(os.getenv('FRAMATEX_SCANNER_TIMEOUT_SECONDS','30'))
        if not 1<=timeout<=120:raise ValueError('timeout')
        result=subprocess.run([*shlex.split(command),str(path)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=timeout,check=False)
    except (OSError,subprocess.TimeoutExpired,ValueError):
        log.warning('upload_scan result=unavailable')
        raise HTTPException(503,'Scanner indisponible : dépôt refusé')
    log.info('upload_scan result=%s elapsed_ms=%d', 'clean' if result.returncode==0 else 'detected' if result.returncode==1 else 'error',int((time.monotonic()-started)*1000))
    if result.returncode==1:raise HTTPException(422,'Fichier refusé par le scanner')
    if result.returncode!=0:raise HTTPException(503,'Échec du scanner : dépôt refusé')
    return 'clean'
