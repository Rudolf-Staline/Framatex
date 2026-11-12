"""Fail CI when a catalogue, navigation, tour or stable target contract drifts."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def validate():
    data=json.loads((ROOT/'app/guide_data/catalog.fr.json').read_text());nav=json.loads((ROOT/'app/guide_data/navigation.json').read_text());targets=json.loads((ROOT/'app/guide_data/targets.json').read_text())
    assert data['locale']=='fr'
    procedures=data['procedures'];tours=data['tours'];actions=data['actions']
    for values in (procedures,tours):assert len({p['id'] for p in values})==len(values),'Identifiants dupliqués'
    pids={p['id'] for p in procedures};tids={t['id'] for t in tours}
    for p in procedures:
        assert re.fullmatch('[a-z][a-z0-9_]+',p['id'])
        assert p['title'] and p['steps'] and p['prerequisites'] and p['problems']
        assert len({s['id'] for s in p['steps']})==len(p['steps'])
        assert p['destination'] in nav and p['tour_id'] in tids
        assert all((ROOT/f).is_file() for f in p['sources'])
        assert all(actions[a]['procedure_id']==p['id'] for a in p['actions'])
        assert all(s['description'].strip() for s in p['steps'])
        assert set(p['audience'])<= {'admin','employee','supplier','client','public'}
    for a in actions.values():
        assert a['procedure_id'] in pids and a['type'] in ('navigate','start_tour','open_procedure','focus_element','select_context')
        assert a['destination'] in (tids if a['type']=='start_tour' else pids if a['type']=='open_procedure' else nav)
    for t in tours:
        assert t['steps'] and (t['procedure_id'] is None or t['procedure_id'] in pids)
        for s in t['steps']:
            assert s['destination'] in nav and s['target'] in targets
    for d in nav.values():
        assert d['target'] in targets and d['surface'] in ('internal','partner')
        assert (ROOT/d['source']).is_file()
        assert not d.get('route') or d['route'] in ('/search','/partners')
        if d['handler']=='view':assert "'"+d['view']+"'" in (ROOT/'static/app.js').read_text()
    for name,contract in targets.items():
        assert contract['marker'] in (ROOT/contract['file']).read_text(),f'Cible disparue : {name}'
    # Actual routes, not historical README claims.
    import sys
    sys.path.insert(0,str(ROOT))
    from app.main import app
    paths=app.openapi()['paths']
    for d in nav.values():
        if d.get('route'):assert d['route'] in paths,f'Route absente : {d["route"]}'
    return {'procedures':len(procedures),'tours':len(tours),'actions':len(actions),'targets':len(targets)}

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))
