"""Linux parser worker; intentionally independent from application DB/auth imports."""
import json,resource,sys
from pathlib import Path

def main():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(25,25))
    resource.setrlimit(resource.RLIMIT_FSIZE,(30*1024*1024,30*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    payload=json.loads(sys.stdin.read(8192))
    from .intake import _read_document
    print(json.dumps(_read_document(Path(payload['path']),payload['filename']),ensure_ascii=False))

if __name__=='__main__':main()
