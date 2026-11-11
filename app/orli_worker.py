"""Isolated, bounded ORLI export parsing (no database or network)."""
import json
import resource
import sys
from pathlib import Path


def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(8,8));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    payload=json.loads(sys.stdin.read(8192))
    from fastapi import HTTPException
    from .orli_import import read_export
    from .file_validation import validate_format
    try:
        path=Path(payload['path'])
        validate_format(path,'.xlsx' if payload['filename'].lower().endswith('.xlsx') else '.txt')
        print(json.dumps({'result':read_export(path.read_bytes(),payload['filename'],payload['mapping'])},ensure_ascii=False))
    except HTTPException as exc:print(json.dumps({'status':exc.status_code,'detail':exc.detail}))
    except Exception:print(json.dumps({'status':422,'detail':'Export corrompu, actif ou incompatible avec son format'}))

if __name__=='__main__':main()
