"""Partner storage budget and optional required scanner, never a format-only AV claim."""
import os
import shlex
import subprocess
from fastapi import HTTPException
from sqlalchemy import select,func,update
from .partner_models import Partner,PartnerRequest,PartnerSubmission
from .partner_phase2_models import PartnerAttachment

def lock_budget(db,org_id):
    # Serializes writes for one organization (SQLite writer lock / SQL row lock).
    db.execute(update(Partner).where(Partner.id==org_id).values(id=org_id))

def verify_budget(db,org_id,new_size):
    quota=int(os.getenv('FRAMATEX_PARTNER_QUOTA_BYTES',str(100*1024*1024)))
    used=db.scalar(select(func.coalesce(func.sum(PartnerSubmission.size),0)).join(PartnerRequest).where(PartnerRequest.partner_id==org_id))
    attached=db.scalar(select(func.coalesce(func.sum(PartnerAttachment.size),0)).where(PartnerAttachment.partner_id==org_id))
    if used+attached+new_size>quota:raise HTTPException(413,'Quota de stockage de cette organisation dépassé')

def scan(path):
    mode=os.getenv('FRAMATEX_UPLOAD_SCAN_MODE','disabled')
    if mode=='disabled':return 'not_scanned'
    if mode!='required':raise HTTPException(503,'Politique antivirus invalide')
    command=os.getenv('FRAMATEX_SCANNER_COMMAND','')
    if not command:raise HTTPException(503,'Scanner obligatoire indisponible : dépôt refusé')
    try:
        result=subprocess.run([*shlex.split(command),str(path)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired,ValueError):raise HTTPException(503,'Scanner indisponible : dépôt refusé')
    if result.returncode==1:raise HTTPException(422,'Fichier refusé par le scanner')
    if result.returncode!=0:raise HTTPException(503,'Échec du scanner : dépôt refusé')
    return 'clean'
