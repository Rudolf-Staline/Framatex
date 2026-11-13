"""Private document blobs: bounded validation, quota, hash, scanner and cleanup.

All HTTP upload surfaces and extraction previews use this single owner. Existing
blob paths and the isolated app.file_validation worker protocol are unchanged.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from .core import DATA_DIR

MAX_UPLOAD = 20 * 1024 * 1024
STORAGE = DATA_DIR / "files"
STORAGE.mkdir(parents=True, exist_ok=True)
EXTS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".txt", ".eml"}
MIMES = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain", ".eml": "message/rfc822"}


def verify_file(file_path: Path, extension: str):
    import subprocess, sys
    try:
        result=subprocess.run([sys.executable,'-m','app.file_validation'],
            input=json.dumps({'path':str(file_path.resolve()),'extension':extension}),
            capture_output=True,text=True,timeout=12,check=False)
        data=json.loads(result.stdout) if result.returncode==0 else {}
        if not data.get('valid'):raise HTTPException(422,data.get('message','Vérification interrompue : fichier illisible ou disproportionné'))
    except (OSError,ValueError,subprocess.TimeoutExpired):
        raise HTTPException(422,'Vérification du fichier impossible dans les limites autorisées')


async def store_upload(file: UploadFile):
    supplied=file.filename or ''
    if len(supplied)>240 or any(c in supplied for c in ('/','\\','\0','\r','\n')) or supplied in ('.','..'):
        raise HTTPException(422,'Nom de fichier invalide')
    original_name = supplied
    suffix = Path(original_name).suffix.lower()
    if not original_name or suffix not in EXTS:
        raise HTTPException(422, "Format non autorisé (PDF, DOCX, XLSX, PNG, JPEG, TXT ou EML)")
    disk_name = secrets.token_hex(24)
    target = STORAGE / disk_name
    sha = hashlib.sha256()
    total = 0
    created = False
    try:
        from .storage_budget import upload_budget
        with upload_budget(STORAGE) as remaining:
            descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            created=True
            with os.fdopen(descriptor,"wb") as out:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > remaining:
                        raise HTTPException(413,'Quota du stockage privé dépassé')
                    if total > MAX_UPLOAD:
                        raise HTTPException(413, "Fichier trop volumineux (20 Mo maximum)")
                    sha.update(chunk)
                    out.write(chunk)
            if total == 0:
                raise HTTPException(422, "Fichier vide")
            await run_in_threadpool(verify_file,target,suffix)
            from .partner_uploads import scan
            await run_in_threadpool(scan,target)
            return original_name, disk_name, total, sha.hexdigest(), MIMES[suffix]
    except FileExistsError:
        raise HTTPException(409,"Conflit de stockage : aucun fichier existant n’a été modifié")
    except Exception:
        if created:target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
