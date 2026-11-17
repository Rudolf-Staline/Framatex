"""Isolated synthetic search benchmark; never reads a configured application database."""
import argparse
import gc
import json
import os
from pathlib import Path
import statistics
import tempfile
import time
import tracemalloc
import threading
from concurrent.futures import ThreadPoolExecutor


def run(sizes, repeats, actor='reader', concurrency=()):
    with tempfile.TemporaryDirectory(prefix='framatex-search-measure-') as directory:
        os.environ['FRAMATEX_DATA_DIR'] = directory
        os.environ['DATABASE_URL'] = 'sqlite:///' + directory + '/measure.db'
        os.environ['FRAMATEX_SECRET_KEY'] = 'synthetic-measurement-only-' * 3
        from sqlalchemy import event
        from fastapi.encoders import jsonable_encoder
        from app.main import app  # register all model metadata
        from app.core import Base, engine, SessionLocal
        from app.models import User, Role, RolePermission, Document, DocumentVersion, Folder, Launch
        from app.partner_models import Partner
        from app.partner_phase2_models import BusinessOrder, BusinessOrderLaunch
        from app.order_documents import OrderDossier, OrderMember
        from app.document_search_routes import search
        output=[]
        for size in sizes:
            Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
            with SessionLocal() as db:
                user=User(id='benchmark-user', name='Synthetic', email='measure@local.invalid', password_hash='unused', roles=[Role(name='Administrateur' if actor=='admin' else 'Synthetic reader',grants=[] if actor=='admin' else [RolePermission(action='launch.read'),RolePermission(action='document.read')])])
                launch=Launch(id='benchmark-launch', name='Synthetic', created_by=user.id, client_name='Synthetic client')
                db.add(user); db.flush(); db.add(launch); db.flush()
                client=Partner(id='benchmark-client',kind='client',name='Synthetic client');db.add(client);db.flush()
                order=BusinessOrder(id='benchmark-order',client_id=client.id,reference='SYNTHETIC',created_by=user.id);db.add(order);db.flush()
                db.add(BusinessOrderLaunch(launch_id=launch.id,order_id=order.id,linked_by=user.id));db.add(OrderMember(order_id=order.id,user_id=user.id));
                root=OrderDossier(id='benchmark-dossier',order_id=order.id);db.add(root);db.flush()
                folder=Folder(id='benchmark-folder', dossier_id=root.id, slug='jaune', label='Jaune'); db.add(folder); db.flush()
                db.add_all([Document(id=f'doc-{i}',folder_id=folder.id,title=f'Document {i:08}',doc_type='Synthetic',created_by=user.id) for i in range(size)]);db.flush()
                db.add_all([DocumentVersion(id=f'version-{i}-{number}',document_id=f'doc-{i}',number=number,original_name='synthetic.txt',disk_name=f'blob-{i}-{number}',content_type='text/plain',size=1,sha256='a'*64,uploaded_by=user.id) for i in range(size) for number in range(1,4)])
                db.commit()
            samples=[]
            for _ in range(repeats):
                count=[0]
                def statement(*_args):count[0]+=1
                event.listen(engine,'before_cursor_execute',statement)
                gc.collect();tracemalloc.start();started=time.perf_counter()
                with SessionLocal() as db:
                    user=db.get(User,'benchmark-user')
                    result=search(q='',order_ref='',orli_ref='',client='',supplier='',doc_type='',folder=None,author='',status=None,after=None,before=None,version=None,sort='newest',offset=0,limit=25,user=user,db=db)
                    payload=json.dumps(jsonable_encoder(result),ensure_ascii=False).encode()
                elapsed=(time.perf_counter()-started)*1000
                _current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();event.remove(engine,'before_cursor_execute',statement)
                assert len(result['items'])==min(size,25) and result['total']==size
                samples.append({'sql':count[0],'latency_ms':round(elapsed,2),'json_bytes':len(payload),'peak_python_bytes':peak})
            measurement={'documents':size,'versions':size*3,'page_size':25,'samples':samples,'median_latency_ms':round(statistics.median(s['latency_ms'] for s in samples),2)}
            if concurrency:
                concurrent_results=[]
                for workers in concurrency:
                    local=threading.local()
                    def concurrent_statement(*_args):
                        if hasattr(local,'statements'):
                            local.statements+=1
                    event.listen(engine,'before_cursor_execute',concurrent_statement)
                    gc.collect();tracemalloc.start();batch_started=time.perf_counter()
                    concurrent_samples=[]
                    try:
                        with ThreadPoolExecutor(max_workers=workers) as pool:
                            for wave in range(repeats):
                                barrier=threading.Barrier(workers)
                                def request(worker):
                                    local.statements=0
                                    barrier.wait(timeout=30)
                                    started=time.perf_counter()
                                    try:
                                        # Each request owns its Session and connection.
                                        with SessionLocal() as db:
                                            user=db.get(User,'benchmark-user')
                                            result=search(q='',order_ref='',orli_ref='',client='',supplier='',doc_type='',folder=None,author='',status=None,after=None,before=None,version=None,sort='newest',offset=0,limit=25,user=user,db=db)
                                            payload=json.dumps(jsonable_encoder(result),ensure_ascii=False).encode()
                                        assert len(result['items'])==min(size,25) and result['total']==size
                                        return {'wave':wave+1,'worker':worker+1,'sql':local.statements,'latency_ms':round((time.perf_counter()-started)*1000,2),'json_bytes':len(payload)}
                                    except Exception as exc:
                                        return {'wave':wave+1,'worker':worker+1,'sql':local.statements,'latency_ms':round((time.perf_counter()-started)*1000,2),'error':type(exc).__name__}
                                concurrent_samples.extend(pool.map(request,range(workers)))
                    finally:
                        batch_elapsed=time.perf_counter()-batch_started
                        _current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                        event.remove(engine,'before_cursor_execute',concurrent_statement)
                    successful=[sample for sample in concurrent_samples if 'error' not in sample]
                    concurrent_results.append({'concurrency':workers,'waves':repeats,'requests':len(concurrent_samples),'errors':len(concurrent_samples)-len(successful),'samples':concurrent_samples,
                        'batch_elapsed_ms':round(batch_elapsed*1000,2),'requests_per_second':round(len(successful)/batch_elapsed,2),'peak_python_bytes_all_threads':peak,
                        'median_latency_ms':round(statistics.median(sample['latency_ms'] for sample in successful),2) if successful else None})
                measurement['concurrent']=concurrent_results
            output.append(measurement)
        return {'conditions':'Shared development host (no exclusive CPU/RAM isolation); local SQLite temporary DB; '+actor+'; canonical order, shared documents, one linked launch; 3 versions/document; metadata search endpoint function including ORM user lookup; no HTTP/network; tracemalloc enabled; sequential samples plus optional isolated concurrent waves (one Session/thread, fixed first page); concurrent memory is aggregate; no production or p95 claim','results':output}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sizes',type=int,nargs='+',default=[100,1000]);parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--output',type=Path);parser.add_argument('--actor',choices=['admin','reader'],default='reader');parser.add_argument('--concurrency',type=int,nargs='+',default=[],help='Optional isolated waves, e.g. --concurrency 2 4')
    args=parser.parse_args()
    if args.repeats<1 or any(size<1 for size in args.sizes) or any(workers<1 or workers>16 for workers in args.concurrency):
        parser.error('sizes/repeats must be positive; concurrency must be between 1 and 16')
    result=run(args.sizes,args.repeats,args.actor,args.concurrency);value=json.dumps(result,indent=2)
    if args.output:args.output.write_text(value+'\n')
    print(value)
