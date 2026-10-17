"""Administrator-controlled per-launch restrictions and explicit memberships."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import Launch, LaunchMember, User
from .access import must_access

router = APIRouter(tags=['0.15 — Portée des autorisations'])


def deps():
    from .main import admin_only, audit
    return admin_only, audit


class SetRestricted(BaseModel):
    restricted: bool


class AssignMember(BaseModel):
    user_id: str


@router.get('/api/launches/{launch_id}/access')
def read_access(launch_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    admin_only, _ = deps(); admin_only(user)
    launch = must_access(db,user,launch_id)
    members = db.scalars(select(LaunchMember).where(LaunchMember.launch_id == launch.id)).all()
    return {'launch_id':launch.id,'restricted':bool(launch.restricted),'creator_id':launch.created_by,
            'members':[{'id':m.id,'user_id':m.user_id,'name':(db.get(User,m.user_id).name if db.get(User,m.user_id) else 'Utilisateur supprimé'),
                        'created_at':m.created_at.isoformat()} for m in members]}


@router.put('/api/launches/{launch_id}/access')
def set_restricted(launch_id: str, payload: SetRestricted, user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    admin_only,audit = deps();admin_only(user)
    launch=must_access(db,user,launch_id)
    launch.restricted=payload.restricted
    audit(db,user,'launch.access.mode','launch',launch.id,{'restricted':payload.restricted})
    db.commit()
    return read_access(launch_id,user,db)


@router.post('/api/launches/{launch_id}/access/members',status_code=201)
def add_member(launch_id:str,payload:AssignMember,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only,audit = deps();admin_only(user)
    launch=must_access(db,user,launch_id)
    target=db.get(User,payload.user_id)
    if not target or not target.active:
        raise HTTPException(422,'Collaborateur introuvable ou désactivé')
    if target.id==launch.created_by:
        raise HTTPException(409,'Le créateur possède déjà un accès implicite')
    exists=db.scalar(select(LaunchMember.id).where(LaunchMember.launch_id==launch.id, LaunchMember.user_id==target.id))
    if exists:
        raise HTTPException(409,'Collaborateur déjà autorisé')
    db.add(LaunchMember(launch_id=launch.id,user_id=target.id,granted_by=user.id))
    audit(db,user,'launch.access.grant','launch',launch.id,{'user_id':target.id})
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Collaborateur déjà autorisé')
    return read_access(launch_id,user,db)


@router.delete('/api/launches/{launch_id}/access/members/{user_id}')
def remove_member(launch_id:str,user_id:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    admin_only,audit=deps();admin_only(user)
    launch=must_access(db,user,launch_id)
    member=db.scalar(select(LaunchMember).where(LaunchMember.launch_id==launch.id,LaunchMember.user_id==user_id))
    if not member:
        raise HTTPException(404,'Autorisation introuvable')
    db.delete(member)
    audit(db,user,'launch.access.revoke','launch',launch.id,{'user_id':user_id})
    db.commit()
    return read_access(launch_id,user,db)
