"""Routes 0.10 — graphe des dépendances et scénarios d'impact, sans mutation métier."""
from __future__ import annotations
import json
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .core import get_db, get_current_user
from .models import User
from .impact_sim_models import ImpactSimulation
from .impact_simulation import INPUTS, calculate, dependency_graph
from .main import audit, get_launch, must, permitted

router = APIRouter()

class ScenarioInput(BaseModel):
    title: str = Field(default='Simulation indicative', min_length=3, max_length=160)
    changes: Dict[str, str] = Field(min_length=1, max_length=3)
    save: bool = False


def require_technical(user: User):
    must(user, 'launch.read')
    must(user, 'document.read', 'jaune')

@router.get('/api/launches/{launch_id}/dependency-graph')
def graph(launch_id: str, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    must(user, 'launch.read')
    get_launch(db, launch_id)
    return dependency_graph(db, launch_id, lambda folder: permitted(user, 'document.read', folder))

@router.post('/api/launches/{launch_id}/impact-simulations')
def simulate(launch_id: str, payload: ScenarioInput, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    require_technical(user)
    get_launch(db, launch_id)
    result = calculate(db, launch_id, payload.changes)
    scenario_id = None
    if payload.save:
        must(user, 'value.write', 'jaune')
        entry = ImpactSimulation(launch_id=launch_id, title=payload.title.strip(),
                                 payload_json=json.dumps(payload.changes, ensure_ascii=False),
                                 result_json=json.dumps(result, ensure_ascii=False), created_by=user.id)
        db.add(entry); db.flush()
        scenario_id = entry.id
        audit(db, user, 'impact.simulation.save', 'impact_simulation', entry.id,
              {'launch': launch_id, 'changed_fields': sorted(payload.changes)})
        db.commit()
    return {'saved_id': scenario_id, 'title': payload.title, 'result': result,
            'saved': scenario_id is not None}

@router.get('/api/launches/{launch_id}/impact-simulations')
def history(launch_id: str, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    require_technical(user)
    get_launch(db, launch_id)
    rows = db.scalars(select(ImpactSimulation).where(ImpactSimulation.launch_id == launch_id)
                       .order_by(ImpactSimulation.created_at.desc()).limit(30)).all()
    return [{'id': r.id, 'title': r.title, 'created_at': r.created_at.isoformat(),
             'created_by': r.created_by, 'result': json.loads(r.result_json)} for r in rows]
