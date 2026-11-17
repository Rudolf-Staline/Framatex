"""Explicit local audit export and verified purge; no retention period is assumed.

Use only in an operator-approved maintenance window. Security revocation tables
are never exported or purged by this command. This is not an immutable journal.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from sqlalchemy import select, delete
from .core import SessionLocal
from .models import AuditEvent

COLUMNS=('id','action','actor_id','target_type','target_id','detail','occurred_at')


def record(row):
    return {key:(getattr(row,key).isoformat() if key=='occurred_at' else getattr(row,key)) for key in COLUMNS}


def export_audit(before, destination, factory=SessionLocal):
    destination=Path(destination)
    descriptor=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    digest=hashlib.sha256();count=0
    try:
        with factory() as db,os.fdopen(descriptor,'wb') as out:
            for row in db.scalars(select(AuditEvent).where(AuditEvent.occurred_at<before).order_by(AuditEvent.occurred_at,AuditEvent.id).execution_options(yield_per=500)):
                line=(json.dumps(record(row),ensure_ascii=False,sort_keys=True)+'\n').encode()
                out.write(line);digest.update(line);count+=1
            out.flush();os.fsync(out.fileno())
        manifest=destination.with_name(destination.name+'.manifest.json')
        descriptor=os.open(manifest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(descriptor,'w') as out:
            json.dump({'sha256':digest.hexdigest(),'rows':count,'before':before.isoformat()},out,sort_keys=True)
    except BaseException:
        destination.unlink(missing_ok=True);raise
    return {'rows':count,'sha256':digest.hexdigest()}


def purge_export(destination, *, apply=False, factory=SessionLocal):
    destination=Path(destination);data=destination.read_bytes()
    manifest=json.loads(destination.with_name(destination.name+'.manifest.json').read_text())
    if hashlib.sha256(data).hexdigest()!=manifest['sha256']:raise ValueError('Archive modifiée : purge refusée')
    records=[json.loads(line) for line in data.splitlines()]
    if len(records)!=manifest['rows'] or len({row['id'] for row in records})!=len(records):raise ValueError('Archive incohérente')
    with factory() as db:
        # Stop concurrent mutation until the exact archived rows have been checked.
        from sqlalchemy import text
        db.execute(text('BEGIN IMMEDIATE'))
        for row in records:
            current=db.get(AuditEvent,row['id'])
            if not current or record(current)!=row:raise ValueError('Historique modifié depuis export : purge refusée')
        if apply:
            ids=[row['id'] for row in records]
            for start in range(0,len(ids),500):db.execute(delete(AuditEvent).where(AuditEvent.id.in_(ids[start:start+500])))
            db.commit()
        else:db.rollback()
    return {'rows':len(records),'applied':apply}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='operation',required=True)
    export=sub.add_parser('export');export.add_argument('destination',type=Path);export.add_argument('--before',type=datetime.fromisoformat,required=True)
    purge=sub.add_parser('purge-export');purge.add_argument('destination',type=Path);purge.add_argument('--apply',action='store_true')
    args=p.parse_args()
    print(export_audit(args.before,args.destination) if args.operation=='export' else purge_export(args.destination,apply=args.apply))

if __name__=='__main__':main()
