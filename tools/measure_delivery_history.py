"""Reproducible synthetic before/after function benchmark; no databases or SMTP."""
import ast
from datetime import datetime,timedelta
from decimal import Decimal
import json
from pathlib import Path
import statistics
import subprocess
import time
from types import SimpleNamespace as Row
from app.partner_delivery_routes import discrepancy_history


def main():
    source=subprocess.check_output(['git','show','origin/main:app/partner_delivery_routes.py'],text=True)
    old=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='discrepancy_history')
    namespace={'Decimal':Decimal}
    exec(compile(ast.Module(body=[old],type_ignores=[]),'<historical-function>','exec'),namespace)
    reference=namespace['discrepancy_history'];results=[]
    for size in (500,2000):
        movements=[];cancellations={};start=datetime(2026,1,1)
        for i in range(size):
            mid=f'{i:08}';kind=('planned','declared','received','returned')[i%4]
            movements.append(Row(id=mid,kind=kind,quantity=Decimal(i%13+1)/1000,created_at=start+timedelta(seconds=i),source_id='synthetic-source',note='Synthetic measurement'))
            cancellations[mid]=Row(created_at=start+timedelta(seconds=size+i),reason='Synthetic cancellation') if i%10==0 else None
        row=Row(ordered=Decimal('100.125'));assert reference(row,movements,cancellations)==discrepancy_history(row,movements,cancellations)
        timings={}
        for name,fn in [('before',reference),('after',discrepancy_history)]:
            samples=[]
            for _ in range(3):
                t=time.perf_counter();fn(row,movements,cancellations);samples.append((time.perf_counter()-t)*1000)
            timings[name]={'milliseconds':samples,'median_ms':statistics.median(samples)}
        results.append({'movements':size,'cancellations':sum(c is not None for c in cancellations.values()),**timings})
    output={'conditions':'Local isolated CPU function benchmark; synthetic Decimal data; 3 serial repetitions; results equivalent; no production/p95 claim','results':results}
    target=Path('artifacts/consolidation-delivery-history.json');target.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))

if __name__=='__main__':main()
