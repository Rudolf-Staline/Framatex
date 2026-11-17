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
    try:quota=int(os.getenv('FRAMATEX_PARTNER_QUOTA_BYTES',str(100*1024*1024)))
    except ValueError:raise HTTPException(503,'Configuration du quota fournisseur invalide')
    if quota<1:raise HTTPException(503,'Quota fournisseur indisponible')
    used=db.scalar(select(func.coalesce(func.sum(PartnerSubmission.size),0)).join(PartnerRequest).where(PartnerRequest.partner_id==org_id))
    attached=db.scalar(select(func.coalesce(func.sum(PartnerAttachment.size),0)).where(PartnerAttachment.partner_id==org_id))
    administrative=db.scalar(select(func.coalesce(func.sum(PartnerAdministrativeDocument.size),0)).where(PartnerAdministrativeDocument.partner_id==org_id))
    if used+attached+administrative+new_size>quota:raise HTTPException(413,'Quota de stockage de cette organisation dépassé')


def verify_actor(db,org_id,actor,action):
    """Recheck revocation after slow file validation, within the short write phase."""
    if actor.startswith('partner:'):
        from .partner_models import PartnerAccount
        from .partner_permissions import require,email_allowed
        account=db.get(PartnerAccount,actor.split(':',1)[1]);db.refresh(account) if account else None
        if not account or not account.active or account.partner_id!=org_id or not email_allowed(db,org_id,account.email):
            raise HTTPException(403,'Compte partenaire révoqué')
        require(db,account,'read');require(db,account,action)
        return account
    else:
        from .models import User
        user=db.get(User,actor.split(':',1)[1]);db.refresh(user) if user else None
        if not user or not user.active:raise HTTPException(403,'Compte collaborateur désactivé')
        db.expire(user,['roles'])
        from .access import admin_only,must
        org=db.get(Partner,org_id)
        if action=='document.write' or org.kind=='client':admin_only(user)
        else:must(user,'supplier.request')
        return user
