"""Employee access changes revoke existing sessions and preserve an active administrator."""
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select,update
from sqlalchemy.orm import Session
from .core import get_current_user,get_db,hash_password
from .models import User,Role
from .main import admin_only,audit,user_out

router=APIRouter(tags=['Accès employés'])
class AccessInput(BaseModel):
    active:bool
    role_ids:list[str]=Field(min_length=1,max_length=50)
    password:str|None=Field(default=None,min_length=12,max_length=256)
    reason:str=Field(min_length=12,max_length=1800)

@router.patch('/api/admin/users/{uid}/access')
def change(uid:str,payload:AccessInput,user=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only(user)
    db.execute(update(User).where(User.id==uid).values(active=User.active),execution_options={'synchronize_session':False})
    row=db.get(User,uid)
    if not row:raise HTTPException(404,'Collaborateur introuvable')
    db.refresh(row)
    roles=[db.get(Role,rid) for rid in set(payload.role_ids)]
    if any(r is None for r in roles):raise HTTPException(422,'Rôle inconnu')
    will_admin=payload.active and any(r.name=='Administrateur' for r in roles)
    if row.active and any(r.name=='Administrateur' for r in row.roles) and not will_admin:
        others=db.scalar(select(User.id).join(User.roles).where(User.id!=uid,User.active.is_(True),Role.name=='Administrateur').limit(1))
        if not others:raise HTTPException(409,'Conserver au moins un administrateur actif')
    before={'active':row.active,'roles':[r.id for r in row.roles]}
    row.active=payload.active;row.roles=roles
    if payload.password:row.password_hash=hash_password(payload.password)
    audit(db,user,'user.access','user',uid,{'before':before,'active':payload.active,'roles':[r.id for r in roles],'password_changed':bool(payload.password),'reason':payload.reason})
    audit(db,user,'session.revoke_all','user',uid)
    db.commit();return user_out(row)
