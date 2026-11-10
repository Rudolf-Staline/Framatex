import json
from fastapi import HTTPException
from .partner_phase2_models import PartnerProfile, PartnerRole, PartnerRoleAssignment

PERMISSIONS={'read','document.write','message.write','delivery.write'}
# Existing accounts retain their original contributor rights until explicitly assigned.
# Only Framatex administrators can create roles and assign them.
def permissions(db,account):
    assignment=db.get(PartnerRoleAssignment,account.id)
    if not assignment:return set(PERMISSIONS)
    role=db.get(PartnerRole,assignment.role_id)
    if not role or role.partner_id!=account.partner_id:return set()
    return set(json.loads(role.permissions_json)) & PERMISSIONS

def require(db,account,action):
    if action not in permissions(db,account):raise HTTPException(403,'Habilitation partenaire insuffisante')

def email_allowed(db,org_id,email):
    profile=db.get(PartnerProfile,org_id)
    domains=json.loads(profile.domains_json) if profile else []
    return not domains or email.rsplit('@',1)[-1].lower() in domains
