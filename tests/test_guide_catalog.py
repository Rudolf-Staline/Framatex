"""Catalog contracts are checked independently from generated manuals."""
from pathlib import Path
import json
_DATA=Path(__file__).resolve().parents[1]/'app/guide_data'
_catalog=json.loads((_DATA/'catalog.fr.json').read_text())
PROCEDURES={p['id']:p for p in _catalog['procedures']}
TOURS={t['id']:t for t in _catalog['tours']}
ACTIONS=_catalog['actions'];NAV=json.loads((_DATA/'navigation.json').read_text())


def test_all_major_functions_have_structured_verified_procedures():
    assert len(PROCEDURES)>=50
    assert {'commandes','documents','controles','validations','fournisseurs','clients','orli','administration'} <= {p['category'] for p in PROCEDURES.values()}
    for p in PROCEDURES.values():
        assert len(p['steps'])>=2 and p['prerequisites'] and p['problems'] and p['result']
        assert p['locale']=='fr' and p['version']>=1
        assert p['destination'] in NAV and p['tour_id'] in TOURS
        assert len({s['id'] for s in p['steps']})==len(p['steps'])
        assert all(s['description'].strip() for s in p['steps'])
        for key in p['actions']:
            assert ACTIONS[key]['procedure_id']==p['id']
            assert ACTIONS[key]['type'] in ('navigate','start_tour','open_procedure','focus_element','select_context')
        assert all((Path(__file__).resolve().parents[1]/source).is_file() for source in p['sources'])
    assert len(PROCEDURES)==len({p['id'] for p in PROCEDURES.values()})


def test_destinations_and_tours_are_closed_registries():
    for d in NAV.values():
        assert d['handler'] in ('view','order','order_upload','launch','page','partner','partner_request','partner_order','partner_admin')
        assert d['surface'] in ('internal','partner')
        assert not d.get('route') or d['route'] in ('/search','/partners')
        assert d['target'] and Path(d['source']).is_file()
    for t in TOURS.values():
        assert t['steps']
        for step in t['steps']:assert step['destination'] in NAV and step['target']
