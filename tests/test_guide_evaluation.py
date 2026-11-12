from tools.evaluate_guide import evaluate

def test_annotated_questions_local_accuracy_refusals_and_safe_shortcuts():
    r=evaluate()
    assert r['questions']>=100
    assert r['top1_accuracy']>=.95 and r['top3_accuracy']>=.95
    assert r['safe_actions_rate']==1 and r['relevant_shortcuts_rate']==1 and r['correct_refusal_rate']==1
    assert not r['external_calls_allowed'] and not r['gemini_improvement_measured']
