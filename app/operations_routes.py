"""Liveness and dependency readiness, with no credentials in public responses."""
import logging
import os
from pathlib import Path
import re
from .scanner_config import operational, scanner_command
import shutil
import subprocess
import tempfile
import time
from functools import lru_cache
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .core import engine, DATA_DIR, ROOT

router=APIRouter()


@lru_cache(maxsize=1)
def build_identity():
    commit=os.getenv('FRAMATEX_BUILD_COMMIT','')
    if not commit:
        # git archive substitutes the SHA, including in packages without .git.
        commit = '$Format:%H$'
    if not re.fullmatch(r'[0-9a-fA-F]{7,40}', commit) and (ROOT / '.git').exists() and not os.getenv('FRAMATEX_BUILD_COMMIT'):
        try:
            commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,timeout=2,check=True).stdout.strip()
        except (OSError,subprocess.SubprocessError):commit='unknown'
    if not re.fullmatch(r'[0-9a-fA-F]{7,40}',commit):commit='unknown'
    return {'version':os.getenv('FRAMATEX_BUILD_VERSION','consolidation-2026.11'),'commit':commit}


def scanner_readiness():
    mode=os.getenv('FRAMATEX_UPLOAD_SCAN_MODE','disabled')
    if mode=='disabled':return {'ready':not operational(),'state':'disabled'}
    if mode!='required':return {'ready':False,'state':'invalid_configuration'}
    backend=os.getenv('FRAMATEX_SCANNER_BACKEND','command')
    if backend not in {'command','clamav'}:return {'ready':False,'state':'invalid_configuration'}
    try:program=scanner_command(backend)[0]
    except (ValueError,IndexError):return {'ready':False,'state':'unconfigured'}
    if not shutil.which(program):return {'ready':False,'state':'unavailable'}
    if backend=='clamav':
        directory=Path(os.getenv('FRAMATEX_CLAMAV_DATABASE_DIR','/var/lib/clamav'))
        try:
            definitions=[p for p in directory.glob('daily.*') if p.suffix in {'.cld','.cvd'}]
            max_hours=float(os.getenv('FRAMATEX_SCANNER_MAX_SIGNATURE_AGE_HOURS','48'))
            age=max(0,time.time()-max(p.stat().st_mtime for p in definitions))/3600
            if max_hours<=0:raise ValueError()
        except (ValueError,OSError):return {'ready':False,'state':'signature_status_unknown'}
        if age>max_hours:return {'ready':False,'state':'signatures_stale','signature_age_hours':round(age,1)}
        return {'ready':True,'state':'available','signature_age_hours':round(age,1)}
    return {'ready':True,'state':'executable_available'}


@router.get('/api/ready')
def readiness():
    from .migrate import REVISIONS
    checks={}
    try:
        with engine.connect() as db:
            done={r[0] for r in db.execute(text('SELECT version FROM schema_migrations'))}
            db.execute(text('SELECT 1'))
            checks['database']=done==set(REVISIONS)
    except Exception:checks['database']=False
    try:
        minimum=int(os.getenv('FRAMATEX_MIN_FREE_BYTES',str(100*1024*1024)))
        with tempfile.TemporaryFile(dir=DATA_DIR) as probe:probe.write(b'probe');probe.flush()
        checks['storage']=minimum>=0 and shutil.disk_usage(DATA_DIR).free>=minimum
    except (OSError,ValueError):checks['storage']=False
    scanner=scanner_readiness();checks['scanner']=scanner['ready']
    ready=all(checks.values())
    return JSONResponse({'status':'ready' if ready else 'not_ready',**build_identity(),'checks':checks,'scanner':scanner},status_code=200 if ready else 503)
