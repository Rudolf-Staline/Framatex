"""Annotated local evaluation; --gemini is explicit, optional and never used by CI."""
import argparse,json,os,statistics,tempfile,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]


def principal_for(audience):
    from app.guide_core import Principal
    role=SimpleNamespace(name='Administrateur' if audience=='admin' else 'Employé',grants=[SimpleNamespace(action=a,folder_slug=f) for a,f in [('launch.read',None),('launch.create',None),('launch.update',None)]+[(a,s) for a in ('document.read','document.write','document.review') for s in ('jaune','rose','bleu','vert')]])
    subject=SimpleNamespace(id='evaluation',active=True,roles=[role])
    return Principal('employee' if audience in ('employee','admin') else audience,subject,{'read','message.write','document.write','delivery.write'},audience=='admin')


def evaluate(real_ai=False):
    from app.guide_core import retrieve,GuideContext,visible,ACTIONS,resolve,NAV
    questions=json.loads((ROOT/'tests/fixtures/guide_questions.fr.json').read_text());results=[]
    for row in questions:
        who=principal_for(row['audience']);start=time.perf_counter();hits,denied=retrieve(row['question'],who,GuideContext())
        clarification=(not hits) or (len(hits)>1 and len(row['question'].split())<=2);mode='local';fallback=None
        if real_ai and hits and not denied:
            from app.guide_gemini import choose
            selected,fallback=choose(row['question'],who,GuideContext(),hits)
            if selected:
                allowed={p['id']:p for p in hits};hits=[allowed[pid] for pid in selected.procedure_ids];clarification=selected.requires_clarification;mode='gemini'
        ids=[p['id'] for p in hits]
        correct=(not ids) if row.get('refuse') else clarification if row.get('clarification') else bool(ids) and ids[0] in row['expected']
        top3=(not ids) if row.get('refuse') else clarification if row.get('clarification') else bool(set(ids[:3])&set(row['expected']))
        actions=[ACTIONS[a] for p in hits[:3] for a in p['actions']]
        resolved=[resolve(a['id'],who,GuideContext(),None) for a in actions]
        safe=all(visible(p,who) for p in hits) and all(a['type'] in row['allowed_action_types'] and a['type'] not in row['forbidden_actions'] for a in resolved)
        safe=safe and all(a['navigation'] is None or a['navigation'] in NAV.values() for a in resolved)
        relevant=(not resolved) if row.get('refuse') else True if row.get('clarification') else bool(hits) and set(hits[0]['actions'])<=set(row['expected_action_ids'])
        results.append({'id':row['id'],'expected':row['expected'],'chosen':ids[:3],'correct':correct,'top3':top3,'safe_actions':safe,'relevant_shortcuts':relevant,'mode':mode,'fallback':fallback,'ms':round((time.perf_counter()-start)*1000,3)})
    times=sorted(r['ms'] for r in results);refusals=[r for r,q in zip(results,questions) if q.get('refuse')]
    report={'dataset':'122 questions synthétiques annotées, dont titres canoniques, paraphrases, fautes, ambiguïtés et refus','questions':len(results),
            'top1_accuracy':sum(r['correct'] for r in results)/len(results),'top3_accuracy':sum(r['top3'] for r in results)/len(results),
            'relevant_shortcuts_rate':sum(r['relevant_shortcuts'] for r in results)/len(results),
            'safe_actions_rate':sum(r['safe_actions'] for r in results)/len(results),'correct_refusal_rate':sum(r['correct'] for r in refusals)/len(refusals),
            'median_ms':statistics.median(times),'p95_ms':times[int(len(times)*.95)],'external_calls_allowed':real_ai,
            'gemini_improvement_measured':real_ai and any(r['mode']=='gemini' for r in results),
            'navigation':'Mesurée séparément dans tools/check_guide_browser.py ; pas déduite de la pertinence textuelle.',
            'results':results}
    if real_ai:
        baseline=evaluate(False);report['local_baseline_top1']=baseline['top1_accuracy'];report['top1_delta']=report['top1_accuracy']-baseline['top1_accuracy'];report['gemini_improvement_observed']=report['gemini_improvement_measured'] and report['top1_delta']>0
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--gemini',action='store_true');parser.add_argument('--output',default='artifacts/guide-evaluation.json');args=parser.parse_args()
    if args.gemini and (os.getenv('FRAMATEX_GUIDE_REAL_AI_TEST')!='1' or not os.getenv('GEMINI_API_KEY')):raise SystemExit('Test réel explicitement autorisé et clé de test nécessaires ; aucun appel effectué.')
    with tempfile.TemporaryDirectory(prefix='guide-evaluation-') as directory:
        os.environ['FRAMATEX_DATA_DIR']=directory;os.environ.pop('DATABASE_URL',None)
        import sys;sys.path.insert(0,str(ROOT))
        if args.gemini:
            from app.migrate import migrate
            migrate()
        result=evaluate(args.gemini);path=ROOT/args.output;path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False,indent=2))
