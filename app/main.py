from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from .core import ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .migrate import migrate
    migrate()
    yield

app = FastAPI(title="Framatex · Dossier jaune", version="0.17.0", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=ROOT / "static"), name="assets")

@app.middleware("http")
async def request_header_guard(request: Request, call_next):
    if request.url.path.startswith("/api/") and len(request.url.path)>512:
        return JSONResponse({"detail":"Identifiant ou chemin trop long"},status_code=422)
    if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if request.headers.get("X-Framatex-Request") != "1":
            return Response("En-tête de protection manquant", status_code=403)
    if request.url.path.startswith('/api/'):
        from .access import guard_http_request
        denied = guard_http_request(request)
        if denied is not None:
            return denied
    return await call_next(request)


@app.middleware("http")
async def response_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path == "/" or request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if request.url.path == "/":
        response.headers.setdefault("Content-Security-Policy",
            "default-src 'self'; base-uri 'none'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'; "
            "script-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'")
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.17.0"}


from .auth_routes import router as auth_router
app.include_router(auth_router)

from .launch_routes import router as launch_router
app.include_router(launch_router)


from .document_routes import router as document_router
app.include_router(document_router)


from .employee_admin_routes import router as employee_admin_router
app.include_router(employee_admin_router)


# ─── Complétude documentaire contextuelle (MVP 0.2) ───────────────


from .completeness_routes import router as completeness_router
app.include_router(completeness_router)


# Modules 0.3 : enregistrés après les dépendances partagées de main.py.
from .workflow_routes import router as workflow_router
app.include_router(workflow_router)

# Module 0.4 — contrôles à partir des valeurs et fichiers réellement enregistrés.
from .quality_routes import router as quality_router
app.include_router(quality_router)

# Module 0.5 — suggestions sans classement automatique ni intégration ORLI.
from .intake_routes import router as intake_router
app.include_router(intake_router)

# Module 0.6 — QR et passeports, sans contournement des habilitations.
from .paper_routes import router as paper_router
app.include_router(paper_router)

# Module 0.7 — couverture des exigences et registre des ambiguïtés.
from .spec_routes import router as spec_router
app.include_router(spec_router)

# Module 0.8 — Emails .eml et engagements confirmés après lecture.
from .mail_routes import router as mail_router
app.include_router(mail_router)

from .workspace_routes import router as workspace_router
app.include_router(workspace_router)

# 0.10 — graphe métier et estimations non destructives.
from .impact_sim_routes import router as impact_sim_router
app.include_router(impact_sim_router)

# 0.11 — import ORLI read-only, décision de rapprochement explicite.
from .orli_routes import router as orli_router
app.include_router(orli_router)

# 0.12 — matières documentées et rapprochements non destructifs.
from .material_routes import router as material_router
app.include_router(material_router)

# 0.13 — circuits séquentiels de validation et notifications internes.
from .approval_routes import router as approval_router
app.include_router(approval_router)

# 0.14 — Publications client et demandes fournisseurs simulées (accès uniquement interne).
from .sharing_routes import router as sharing_router
app.include_router(sharing_router)


# 0.15 — Gestion des accès d'un lancement par l'administrateur.
from .access_routes import router as access_router
app.include_router(access_router)

# 0.17 — Signalements pilotes anonymisés vis-à-vis des autres collaborateurs.
from .pilot_routes import router as pilot_router
app.include_router(pilot_router)

# Le contrôle global de portée est effectué dans request_header_guard, avant
# le dispatch FastAPI. Aucun routeur historique ne peut l'éviter.

from .partner_routes import router as partner_router
app.include_router(partner_router)

from .partner_delivery_routes import router as partner_delivery_router
app.include_router(partner_delivery_router)

from .partner_profile_routes import router as partner_profile_router
app.include_router(partner_profile_router)

from .partner_integration_routes import router as integration_router
app.include_router(integration_router)

from .partner_client_routes import router as partner_client_router
app.include_router(partner_client_router)
from .partner_attachment_routes import router as partner_attachment_router
app.include_router(partner_attachment_router)

from .orli_phase2_routes import router as orli_phase2_router
app.include_router(orli_phase2_router)

from .document_search_routes import router as document_search_router
app.include_router(document_search_router)

from .partner_administrative_routes import router as partner_administrative_router
app.include_router(partner_administrative_router)

from .completeness_policy_routes import router as completeness_policy_router
app.include_router(completeness_policy_router)

from .order_registry_routes import router as order_registry_router
app.include_router(order_registry_router)

from .partner_notice_routes import router as partner_notice_router
app.include_router(partner_notice_router)

from .admin_access_routes import router as admin_access_router
app.include_router(admin_access_router)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
@app.exception_handler(RequestValidationError)
async def safe_validation_errors(request,exception):
    return JSONResponse(status_code=422,content={'detail':[
        {'loc':list(error['loc']),'msg':error['msg'],'type':error['type']} for error in exception.errors()
    ]})

from .order_document_routes import router as order_document_router
app.include_router(order_document_router)

from .orli_resolution_routes import router as orli_resolution_router
app.include_router(orli_resolution_router)

from .business_directory_routes import router as business_directory_router
app.include_router(business_directory_router)


from sqlalchemy.exc import OperationalError
@app.exception_handler(OperationalError)
async def safe_database_errors(request,exception):
    return JSONResponse(status_code=503,content={'detail':'Stockage temporairement indisponible ou occupé. Actualisez avant de réessayer.'})

@app.exception_handler(IntegrityError)
async def safe_integrity_errors(request,exception):
    return JSONResponse(status_code=409,content={'detail':'Une opération concurrente ou une relation incompatible empêche cette modification. Actualisez les données.'})

from .guide_routes import router as guide_router
app.include_router(guide_router)
