"""Explicit opt-in only. CI never calls Google or uses a real credential."""
import os
import pytest

@pytest.mark.skipif(os.getenv('FRAMATEX_GUIDE_REAL_AI_TEST')!='1' or not os.getenv('GEMINI_API_KEY'),reason='Real Gemini requires an explicit test flag and test key')
def test_optional_live_sdk_selection_on_public_synthetic_procedures(monkeypatch):
    from tools.evaluate_guide import principal_for
    from app.guide_core import GuideContext,PROCEDURES
    from app.guide_gemini import generate,safe_payload,Selection
    monkeypatch.setenv('FRAMATEX_GUIDE_AI_ENABLED','1')
    candidates=[PROCEDURES['create_order'],PROCEDURES['open_dossier']]
    payload=safe_payload('Comment créer une commande ?',principal_for('admin'),GuideContext(),candidates)
    selection=Selection.model_validate_json(generate(payload))
    assert selection.procedure_ids and selection.procedure_ids[0]=='create_order'
    assert set(selection.action_ids)<=set(a for p in candidates for a in p['actions'])
