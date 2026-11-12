import json
from collections import Counter
from pathlib import Path

import pytest

from app import guide_core, guide_gemini
from tools.evaluate_guide import evaluate, principal_for


def selection(pid):
    return json.dumps({'procedure_ids': [pid], 'action_ids': [], 'confidence': 'high', 'requires_clarification': False})


def annotated(qid, expected='create_order', refuse=False):
    return {'id': qid, 'question': qid, 'audience': 'admin', 'expected': [] if refuse else [expected],
            'refuse': refuse, 'clarification': False, 'forbidden_actions': ['business_write', 'download_file'],
            'allowed_action_types': ['navigate', 'start_tour', 'open_procedure'],
            'expected_action_ids': [prefix + expected for prefix in ('open_', 'show_', 'read_')]}


def controlled_search(monkeypatch):
    def retrieve(question, *_):
        if question == 'no_candidate':
            return [], False
        return [guide_core.PROCEDURES['create_order'], guide_core.PROCEDURES['open_dossier']], False
    monkeypatch.setattr(guide_core, 'retrieve', retrieve)


def test_annotated_questions_local_accuracy_refusals_and_safe_shortcuts(monkeypatch):
    monkeypatch.setattr(guide_gemini, 'generate', lambda *_: pytest.fail('Local evaluation cannot call Google'))
    r = evaluate()
    assert r['questions'] == 122 and r['coverage']['eligible'] == 112
    local = r['local_full']
    assert local['denominator'] == 122 and local['top1_accuracy'] >= .95 and local['top3_accuracy'] >= .95
    assert local['safe_actions_rate'] == local['relevant_shortcuts_rate'] == local['refusals']['accuracy'] == 1
    assert r['coverage']['attempts'] == r['paired_validated']['denominator'] == 0
    assert r['paired_validated']['local']['top1_accuracy'] is None
    assert not r['external_calls_allowed'] and r['comparison_real_pending']
    assert r['coverage']['status'] == 'not_run'
    assert all(row['local'] == row['enriched'] for row in r['results'])


def test_paired_report_separates_validated_not_requested_and_fallbacks(monkeypatch):
    controlled_search(monkeypatch)
    class Quota(Exception):
        code = 429
    replies = iter([selection('create_order'), selection('open_dossier'), selection('open_dossier'), TimeoutError(), 'not-json', Quota()])
    calls = []
    def fake(payload):
        calls.append(payload)
        result = next(replies)
        if isinstance(result, Exception):
            raise result
        return result
    rows = [annotated('unchanged'), annotated('improved', 'open_dossier'), annotated('degraded'),
            annotated('no_candidate', refuse=True), annotated('timeout'), annotated('invalid'), annotated('quota'), annotated('after_quota')]
    report = evaluate(True, questions=rows, client=fake, ai_budget=8)
    assert len(calls) == 6
    assert report['coverage'] == {'eligible': 7, 'attempts': 6, 'validated': 3, 'validated_denominator': 7,
                                   'validated_rate': 3 / 7, 'partial': True, 'status': 'partial',
                                   'not_requested': 1, 'not_requested_reasons': {'no_verified_candidates': 1},
                                   'fallbacks': 4, 'attempted_fallbacks': 3,
                                   'fallback_reasons': {'timeout': 1, 'invalid_response': 1, 'provider_quota': 2}}
    assert report['local_full']['correct'] == report['enriched_full']['correct'] == 7
    assert report['local_full']['denominator'] == report['enriched_full']['denominator'] == 8
    paired = report['paired_validated']
    assert paired['denominator'] == 3
    assert paired['local']['correct'] == paired['enriched']['correct'] == 2
    assert paired['improved'] == paired['degraded'] == paired['unchanged'] == 1
    assert report['enriched_full']['gemini_validated_results'] == 3 and report['enriched_full']['local_results'] == 5
    assert report['client'] == 'simulated' and not report['external_calls_allowed'] and report['comparison_real_pending']
    outcomes = {r['id']: r for r in report['results']}
    assert outcomes['no_candidate']['outcome'] == 'not_requested'
    assert not outcomes['no_candidate']['attempted'] and not outcomes['after_quota']['attempted']
    for qid in ('timeout', 'invalid', 'quota', 'after_quota'):
        assert outcomes[qid]['outcome'] == 'local_fallback'
        assert outcomes[qid]['local']['chosen'] == outcomes[qid]['enriched']['chosen']


def test_evaluation_budget_is_independent_and_covers_all_eligible_questions(monkeypatch):
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_ENABLED', '0')
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_USER_DAILY_LIMIT', '1')
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_DAILY_LIMIT', '1')
    monkeypatch.setattr(guide_gemini, 'reserve', lambda *_: pytest.fail('Evaluation cannot consume production budgets'))
    calls = []
    def fake(payload):
        calls.append(payload)
        return selection(payload['candidates'][0]['id'])
    report = evaluate(True, client=fake, ai_budget=112)
    assert len(calls) == report['coverage']['eligible'] == report['coverage']['validated'] == 112
    assert report['coverage']['status'] == 'complete' and not report['coverage']['partial']
    assert report['budget'] == {'scope': 'evaluation_process_only', 'limit': 112, 'used': 112, 'production_quotas_used': False}
    assert report['local_full']['denominator'] == report['enriched_full']['denominator'] == 122
    assert report['paired_validated']['denominator'] == 112
    assert guide_core.setting('FRAMATEX_GUIDE_AI_USER_DAILY_LIMIT', 30) == 1


def test_budget_exhaustion_keeps_local_results_out_of_validated_score(monkeypatch):
    controlled_search(monkeypatch)
    calls = []
    def fake(payload):
        calls.append(payload)
        return selection('create_order')
    report = evaluate(True, questions=[annotated(str(i)) for i in range(4)], client=fake, ai_budget=2)
    assert len(calls) == report['coverage']['attempts'] == report['paired_validated']['denominator'] == 2
    assert report['coverage']['fallback_reasons'] == {'evaluation_budget': 2}
    assert report['coverage']['partial'] and report['enriched_full']['denominator'] == 4
    assert all(not r['attempted'] for r in report['results'][2:])


@pytest.mark.parametrize('raw', ['{}', selection('invented'), json.dumps({'procedure_ids': ['create_order'], 'action_ids': ['delete_all'], 'confidence': 'high', 'requires_clarification': False})])
def test_evaluation_reuses_production_response_validation(monkeypatch, raw):
    controlled_search(monkeypatch)
    r = evaluate(True, questions=[annotated('invalid')], client=lambda _: raw, ai_budget=1)
    assert r['coverage']['fallback_reasons'] == {'invalid_response': 1}
    assert r['paired_validated']['denominator'] == 0 and r['coverage']['attempts'] == 1


def test_real_evaluation_requires_explicit_flag_and_dedicated_test_key(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'production-key-must-not-be-used')
    monkeypatch.delenv('FRAMATEX_GUIDE_EVAL_API_KEY', raising=False)
    monkeypatch.setenv('FRAMATEX_GUIDE_REAL_AI_TEST', '1')
    with pytest.raises(ValueError, match='EVAL_API_KEY'):
        evaluate(True)
    monkeypatch.setenv('FRAMATEX_GUIDE_EVAL_API_KEY', 'test-only-key')
    monkeypatch.setenv('FRAMATEX_GUIDE_REAL_AI_TEST', '0')
    with pytest.raises(ValueError, match='REAL_AI_TEST'):
        evaluate(True)


def test_main_production_defaults_allow_57_of_112_candidates(monkeypatch):
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_ENABLED', '1')
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic')
    monkeypatch.delenv('FRAMATEX_GUIDE_AI_USER_DAILY_LIMIT', raising=False)
    monkeypatch.delenv('FRAMATEX_GUIDE_AI_DAILY_LIMIT', raising=False)
    counters = Counter()
    def reserve(key, limit, _):
        if counters[key] >= limit:
            return False
        counters[key] += 1
        return True
    monkeypatch.setattr(guide_gemini, 'reserve', reserve)
    monkeypatch.setattr(guide_gemini, 'generate', lambda payload: selection(payload['candidates'][0]['id']))
    rows = json.loads((Path(__file__).parent / 'fixtures/guide_questions.fr.json').read_text())
    counts = Counter()
    for row in rows:
        who = principal_for(row['audience'])
        hits, denied = guide_core.retrieve(row['question'], who, guide_core.GuideContext())
        if hits and not denied:
            answer, reason = guide_gemini.choose(row['question'], who, guide_core.GuideContext(), hits)
            counts['eligible'] += 1
            counts['validated' if answer else reason] += 1
    assert counts == {'eligible': 112, 'validated': 57, 'user_budget': 55}


def test_reproducible_simulated_example_has_explicit_partial_denominators():
    from tools.evaluate_guide import simulated_client
    r = evaluate(True, client=simulated_client(), ai_budget=112)
    assert r['coverage']['eligible'] == 112 and r['coverage']['attempts'] == 4
    assert r['coverage']['validated'] == r['paired_validated']['denominator'] == 1
    assert r['coverage']['not_requested'] == 10 and r['coverage']['fallbacks'] == 111
    assert r['coverage']['fallback_reasons'] == {'timeout': 1, 'invalid_response': 1, 'provider_quota': 109}
    assert r['coverage']['partial'] and not r['external_calls_allowed']
    assert r['paired_validated']['improved'] == r['paired_validated']['degraded'] == 0
    assert r['paired_validated']['unchanged'] == 1


def test_explicit_real_client_uses_test_key_without_changing_production(monkeypatch):
    controlled_search(monkeypatch)
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_ENABLED', '0')
    monkeypatch.setenv('FRAMATEX_GUIDE_REAL_AI_TEST', '1')
    monkeypatch.setenv('GEMINI_API_KEY', 'production-key-must-not-be-used')
    monkeypatch.setenv('FRAMATEX_GUIDE_EVAL_API_KEY', 'dedicated-test-key')
    keys = []
    def fake(payload, *, api_key):
        keys.append(api_key)
        return selection('create_order')
    monkeypatch.setattr(guide_gemini, 'generate', fake)
    r = evaluate(True, questions=[annotated('key_selection')], ai_budget=1)
    assert keys == ['dedicated-test-key'] and r['client'] == 'real'
    assert r['coverage']['validated'] == 1
    import os
    assert os.environ['FRAMATEX_GUIDE_AI_ENABLED'] == '0'
    assert os.environ['GEMINI_API_KEY'] == 'production-key-must-not-be-used'
