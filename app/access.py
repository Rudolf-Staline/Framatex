"""Per-launch access checks for all API entrypoints, including indirect object routes.

A launch is unrestricted until an administrator explicitly enables restricted
mode, to preserve the original MVP's existing data and collaborators on upgrade.
In restricted mode: admin OR creator OR an explicitly assigned member.
Existing role / folder permissions remain mandatory independently.
"""
from __future__ import annotations
import jwt
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.routing import request_response
from starlette.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import COOKIE, SECRET_KEY, SessionLocal
from .models import User, Launch, LaunchMember, Document, DocumentVersion


def accessible(db: Session, user: User, launch: Launch | None) -> bool:
    if launch is None or not user.active:
        return False
    if any(r.name == "Administrateur" for r in user.roles):
        return True
    if not launch.restricted or launch.created_by == user.id:
        return True
    return db.scalar(select(LaunchMember.id).where(
        LaunchMember.launch_id == launch.id, LaunchMember.user_id == user.id)) is not None


def visible(db: Session, user: User, launches: list[Launch]) -> list[Launch]:
    return [l for l in launches if accessible(db, user, l)]


def must_access(db: Session, user: User, launch_id: str) -> Launch:
    launch = db.get(Launch, launch_id)
    if not accessible(db, user, launch):
        # Prevent user enumeration of confidential launch identifiers.
        raise HTTPException(404, "Lancement introuvable")
    return launch


def version_launch(db: Session, version_id: str) -> str | None:
    version = db.get(DocumentVersion, version_id)
    return version.document.folder.launch_id if version else None


def document_launch(db: Session, document_id: str) -> str | None:
    document = db.get(Document, document_id)
    return document.folder.launch_id if document else None


def indirect_launch(db: Session, params: dict) -> str | None:
    if params.get('launch_id'):
        return params['launch_id']
    if params.get('doc_id'):
        return document_launch(db,params['doc_id'])
    if params.get('version_id'):
        return version_launch(db,params['version_id'])
    if params.get('run_id'):
        from .approval_models import ApprovalRun
        row = db.get(ApprovalRun,params['run_id'])
        return version_launch(db,row.document_version_id) if row else None
    if params.get('alert_id'):
        from .workflow_models import ImpactAlert
        row = db.get(ImpactAlert,params['alert_id'])
        return row.launch_id if row else None
    if params.get('notification_id'):
        from .approval_models import InternalNotification
        row = db.get(InternalNotification,params['notification_id'])
        return row.launch_id if row else None
    if params.get('publication_id'):
        from .sharing_models import ClientPublication
        row = db.get(ClientPublication,params['publication_id'])
        return row.launch_id if row else None
    if params.get('request_id'):
        from .sharing_models import SupplierDocumentRequest
        row = db.get(SupplierDocumentRequest,params['request_id'])
        return row.launch_id if row else None
    return None


GUARDED_PARAMS = {'launch_id', 'doc_id', 'version_id', 'run_id', 'alert_id',
                  'notification_id', 'publication_id', 'request_id'}


def install_scope_guard(app):
    """Protect all existing and future parameterized routes, not only the UI.

    Wrapping FastAPI's registered request handlers ensures the checks precede
    endpoint execution for old module endpoints without bypassing their own
    standard role and folder permission dependencies.
    """
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path_format.startswith('/api/'):
            continue
        if not GUARDED_PARAMS.intersection(route.param_convertors):
            continue
        original = route.get_route_handler()
        async def secured(request: Request, handler=original):
            params = request.path_params
            with SessionLocal() as db:
                launch_id = indirect_launch(db, params)
                if launch_id:
                    token = request.cookies.get(COOKIE)
                    try:
                        sub = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])['sub'] if token else None
                        user = db.get(User, sub) if sub else None
                    except (jwt.InvalidTokenError, KeyError):
                        user = None
                    if not user or not user.active:
                        return JSONResponse({'detail':'Connexion nécessaire'},status_code=401)
                    if not accessible(db,user,db.get(Launch,launch_id)):
                        return JSONResponse({'detail':'Lancement introuvable'},status_code=404)
            return await handler(request)
        route.app = request_response(secured)
