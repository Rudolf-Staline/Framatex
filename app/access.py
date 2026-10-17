"""Per-launch access checks for all API entrypoints, including indirect object routes.

A launch is unrestricted until an administrator explicitly enables restricted
mode, to preserve the original MVP's existing data and collaborators on upgrade.
In restricted mode: admin OR creator OR an explicitly assigned member.
Existing role / folder permissions remain mandatory independently.
"""
from __future__ import annotations
from fastapi import Depends, HTTPException, Request
from fastapi.routing import APIRoute, request_response
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
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


def enforce_route_scope(request: Request, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """FastAPI dependency applied to each scoped endpoint, including old routers."""
    launch_id = indirect_launch(db, request.path_params)
    if launch_id:
        must_access(db, user, launch_id)


def install_scope_guard(app):
    """Add a FastAPI dependency to every route containing a scoped identifier.

    Using the request dependency tree, not route internals such as
    `param_convertors`, makes the protection independent of Starlette's
    implementation of path converters. This also protects old routers
    registered before v0.15 and preserves existing endpoint dependencies.
    """
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path_format.startswith('/api/'):
            continue
        if not any('{' + param + '}' in route.path_format for param in GUARDED_PARAMS):
            continue
        guard = get_parameterless_sub_dependant(
            depends=Depends(enforce_route_scope), path=route.path_format)
        route.dependant.dependencies.insert(0, guard)
        # Recompile the handler once with the additional dependency.
        route.app = request_response(route.get_route_handler())
