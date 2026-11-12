"""Paired guide evaluation. Real calls require an evaluation key and explicit opt-in."""
import argparse
from collections import Counter
from functools import partial
import json
import os
from pathlib import Path
import statistics
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def principal_for(audience):
    from app.guide_core import Principal
    role = SimpleNamespace(name='Administrateur' if audience == 'admin' else 'Employé', grants=[SimpleNamespace(action=a, folder_slug=f) for a, f in [('launch.read', None), ('launch.create', None), ('launch.update', None)] + [(a, s) for a in ('document.read', 'document.write', 'document.review') for s in ('jaune', 'rose', 'bleu', 'vert')]])
    subject = SimpleNamespace(id='evaluation', active=True, roles=[role])
    return Principal('employee' if audience in ('employee', 'admin') else audience, subject, {'read', 'message.write', 'document.write', 'delivery.write'}, audience == 'admin')


def score(row, hits, clarification, who, elapsed):
    from app.guide_core import visible, ACTIONS, resolve, NAV, GuideContext
    ids = [p['id'] for p in hits[:3]]
    correct = not ids if row.get('refuse') else clarification if row.get('clarification') else bool(ids) and ids[0] in row['expected']
    top3 = not ids if row.get('refuse') else clarification if row.get('clarification') else bool(set(ids) & set(row['expected']))
    actions = [ACTIONS[a] for p in hits[:3] for a in p['actions']]
    resolved = [resolve(a['id'], who, GuideContext(), None) for a in actions]
    safe = all(visible(p, who) for p in hits) and all(a['type'] in row['allowed_action_types'] and a['type'] not in row['forbidden_actions'] for a in resolved)
    safe = safe and all(a['navigation'] is None or a['navigation'] in NAV.values() for a in resolved)
    relevant = not resolved if row.get('refuse') else True if row.get('clarification') else bool(hits) and set(hits[0]['actions']) <= set(row['expected_action_ids'])
    return {'chosen': ids, 'correct': bool(correct), 'top3': bool(top3), 'requires_clarification': bool(clarification), 'safe_actions': safe, 'relevant_shortcuts': bool(relevant), 'ms': round(elapsed * 1000, 3)}


def metrics(results):
    denominator = len(results)
    times = sorted(r['ms'] for r in results)
    return {'denominator': denominator, 'correct': sum(r['correct'] for r in results),
            **{name: sum(r[key] for r in results) / denominator if denominator else None for name, key in [('top1_accuracy', 'correct'), ('top3_accuracy', 'top3'), ('safe_actions_rate', 'safe_actions'), ('relevant_shortcuts_rate', 'relevant_shortcuts')]},
            'median_ms': statistics.median(times) if times else None, 'p95_ms': times[min(denominator - 1, int(denominator * .95))] if times else None}


def failure_reason(exc):
    """Fixed categories only: never log a provider response, credential or question."""
    from pydantic import ValidationError
    code = getattr(exc, 'code', None) or getattr(getattr(exc, 'response', None), 'status_code', None)
    if str(code) == '429':
        return 'provider_quota'
    if isinstance(exc, TimeoutError) or 'timeout' in type(exc).__name__.lower():
        return 'timeout'
    if isinstance(exc, (ValueError, ValidationError)):
        return 'invalid_response'
    return 'provider_unavailable'


def real_client():
    if os.getenv('FRAMATEX_GUIDE_REAL_AI_TEST') != '1' or not os.getenv('FRAMATEX_GUIDE_EVAL_API_KEY'):
        raise ValueError('Test réel : FRAMATEX_GUIDE_REAL_AI_TEST=1 et FRAMATEX_GUIDE_EVAL_API_KEY de test requis ; aucun appel effectué.')
    from app.guide_gemini import generate
    return partial(generate, api_key=os.environ['FRAMATEX_GUIDE_EVAL_API_KEY'])


def evaluate(real_ai=False, *, questions=None, ai_budget=30, client=None):
    from app.guide_core import retrieve, GuideContext
    from app.guide_gemini import safe_payload, validate_selection
    if not isinstance(ai_budget, int) or isinstance(ai_budget, bool) or ai_budget < 0:
        raise ValueError('Le budget d’évaluation doit être un entier positif ou nul.')
    if client is not None and not real_ai:
        raise ValueError('Un client simulé exige le mode enrichi explicite.')
    if real_ai and client is None:
        client = real_client()
        client_kind = 'real'
    else:
        client_kind = 'simulated' if client else 'none'
    questions = json.loads((ROOT / 'tests/fixtures/guide_questions.fr.json').read_text()) if questions is None else questions
    results = []
    attempts = 0
    quota_exhausted = False
    for row in questions:
        who = principal_for(row['audience'])
        context = GuideContext()
        start = time.perf_counter()
        hits, denied = retrieve(row['question'], who, context)
        clarification = not hits or len(hits) > 1 and len(row['question'].split()) <= 2
        local = score(row, hits, clarification, who, time.perf_counter() - start)
        eligible = bool(hits) and not denied
        enriched = dict(local)
        outcome, reason, attempted = 'not_requested', 'disabled', False
        if not eligible:
            reason = 'restricted' if denied else 'no_verified_candidates'
        elif real_ai:
            if quota_exhausted:
                outcome, reason = 'local_fallback', 'provider_quota'
            elif attempts >= ai_budget:
                outcome, reason = 'local_fallback', 'evaluation_budget'
            else:
                attempts += 1
                attempted = True
                try:
                    selection = validate_selection(client(safe_payload(row['question'], who, context, hits)), hits)
                    known = {p['id']: p for p in hits}
                    enriched = score(row, [known[pid] for pid in selection.procedure_ids], selection.requires_clarification, who, time.perf_counter() - start)
                    outcome, reason = 'gemini_validated', None
                except Exception as exc:
                    reason = failure_reason(exc)
                    quota_exhausted = reason == 'provider_quota'
                    outcome = 'local_fallback'
                    enriched['ms'] = round((time.perf_counter() - start) * 1000, 3)
        results.append({'id': row['id'], 'audience': row['audience'], 'expected': row['expected'],
                        'eligible': eligible, 'attempted': attempted, 'outcome': outcome, 'reason': reason,
                        'local': local, 'enriched': enriched})
    paired = [r for r in results if r['outcome'] == 'gemini_validated']
    eligible_count = sum(r['eligible'] for r in results)
    validated_count = len(paired)
    fallback = [r for r in results if r['outcome'] == 'local_fallback']
    local_metrics = metrics([r['local'] for r in results])
    enriched_metrics = metrics([r['enriched'] for r in results])
    enriched_metrics['gemini_validated_results'] = validated_count
    enriched_metrics['local_results'] = len(results) - validated_count
    for mode, summary in [('local', local_metrics), ('enriched', enriched_metrics)]:
        refusals = [r[mode] for r, q in zip(results, questions) if q.get('refuse')]
        summary['refusals'] = {'correct': sum(r['correct'] for r in refusals), 'denominator': len(refusals), 'accuracy': sum(r['correct'] for r in refusals) / len(refusals) if refusals else None}
    return {'schema_version': 2, 'questions': len(results), 'mode': 'enriched' if real_ai else 'local', 'client': client_kind,
            'external_calls_allowed': real_ai and client_kind == 'real',
            'budget': {'scope': 'evaluation_process_only', 'limit': ai_budget, 'used': attempts, 'production_quotas_used': False},
            'coverage': {'eligible': eligible_count, 'attempts': attempts, 'validated': validated_count,
                         'validated_denominator': eligible_count, 'validated_rate': validated_count / eligible_count if eligible_count else None,
                         'partial': bool(real_ai and validated_count < eligible_count),
                         'status': 'not_run' if not real_ai else 'complete' if validated_count == eligible_count else 'partial',
                         'not_requested': sum(r['outcome'] == 'not_requested' for r in results),
                         'not_requested_reasons': dict(Counter(r['reason'] for r in results if r['outcome'] == 'not_requested')),
                         'fallbacks': len(fallback), 'attempted_fallbacks': sum(r['attempted'] for r in fallback),
                         'fallback_reasons': dict(Counter(r['reason'] for r in fallback))},
            'local_full': local_metrics, 'enriched_full': enriched_metrics,
            'paired_validated': {'denominator': validated_count, 'local': metrics([r['local'] for r in paired]), 'enriched': metrics([r['enriched'] for r in paired]),
                                 'improved': sum(not r['local']['correct'] and r['enriched']['correct'] for r in paired),
                                 'degraded': sum(r['local']['correct'] and not r['enriched']['correct'] for r in paired),
                                 'unchanged': sum(r['local']['correct'] == r['enriched']['correct'] for r in paired)},
            'comparison_real_pending': client_kind != 'real' or validated_count < eligible_count,
            'navigation': 'Mesurée séparément dans tools/check_guide_browser.py ; pas déduite de la pertinence textuelle.',
            'results': results}


def simulated_client():
    """Reproducible example: success, timeout, invalid JSON, then provider quota."""
    class Quota(Exception):
        code = 429
    calls = 0
    def generate(payload):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TimeoutError()
        if calls == 3:
            return 'invalid-json'
        if calls == 4:
            raise Quota()
        return json.dumps({'procedure_ids': [payload['candidates'][0]['id']], 'action_ids': [], 'confidence': 'high', 'requires_clarification': False})
    return generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--gemini', action='store_true')
    mode.add_argument('--simulate', action='store_true', help='Exemple reproductible avec client simulé ; aucun appel externe.')
    parser.add_argument('--ai-budget', type=int, default=30, help='Nombre maximal de tentatives pour cette évaluation uniquement (défaut : 30).')
    parser.add_argument('--output', default='artifacts/guide-evaluation.json')
    args = parser.parse_args()
    if args.ai_budget < 0:
        parser.error('--ai-budget doit être positif ou nul')
    # No DB migrations, production counters or environment overrides are needed.
    try:
        report = evaluate(args.gemini or args.simulate, ai_budget=args.ai_budget, client=simulated_client() if args.simulate else None)
    except ValueError as exc:
        parser.error(str(exc))
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    main()
