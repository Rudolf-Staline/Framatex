"""Partner organization quotas, independent of shared file validation and scanning."""
import os
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
