"""Guide global et consultation sourcée de la mémoire métier."""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .core import get_current_user, get_db
from .models import User
from .experience_routes import Question, answer_question
from .experience_search import normalized

router = APIRouter(tags=["Assistant"])


class ChatInput(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    launch_id: str | None = Field(default=None, max_length=36)
    folder: Literal["jaune", "rose", "bleu", "vert"] | None = None
    mode: Literal["auto", "memory"] = "auto"


@router.post("/api/assistant/chat")
def chat(payload: ChatInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import permitted
    phrase = normalized(payload.question)
    memory = payload.mode == "memory" or any(word in phrase for word in
        ("resolu", "resoudre", "rencontre", "solution", "cause", "deja", "incident", "probleme", "eviter", "pourquoi"))
    if memory:
        return answer_question(db, user, Question(question=payload.question, folder=payload.folder))
    routes = (
        (("manquant", "completude", "piece attendue"), "Pièces manquantes", "controls",
         "Dans Vérifications, définissez les pièces attendues par sous-dossier et référence ORLI. La liste distingue les pièces accessibles présentes et manquantes. Sans attente configurée, aucun manque n’est déduit."),
        (("coherence", "incoherence", "anomalie", "comparer", "ecart"), "Cohérence documentaire", "controls",
         "Dans Vérifications, relevez les valeurs sur les documents puis appliquez une règle de comparaison. Seules les pièces de la même référence ORLI sont rapprochées ; une source ambiguë ou une unité différente reste à examiner."),
        (("experience", "memoire", "enregistrer un probleme"), "Mémoire métier", "rex",
         "Dans Mémoire métier, enregistrez le problème, son contexte et la solution. Vous pourrez ensuite poser une question pour retrouver les fiches sources et leurs enseignements."),
        (("facture", "deposer", "document", "rubrique", "sous-dossier", "dossier jaune", "bonjour"), "Dossier Jaune", "dossier",
         "Choisissez le sous-dossier dans Dossier Jaune : Jaune pour la technique, Rose pour la réception, Bleu pour la douane et Vert pour la facturation. Le bouton Déposer un document ouvre le formulaire de dépôt."),
    )
    for words, title, destination, answer in routes:
        if any(word in phrase for word in words):
            if not any(permitted(user, "document.read", s) for s in ("jaune", "rose", "bleu", "vert")):
                continue
            folder = "vert" if "facture" in phrase else None
            if folder and not permitted(user, "document.read", folder):
                continue
            return {"title": title, "answer": answer, "destination": destination, "folder": folder,
                    "sources": [], "source": "Guide de navigation Framatex", "requires_human_action": True}
    if permitted(user, "launch.read"):
        from .workspace_routes import guide, GuideRequest
        result = guide(GuideRequest(question=payload.question, launch_id=payload.launch_id), user, db)
        if result.get("destination"):
            return result
    return answer_question(db, user, Question(question=payload.question, folder=payload.folder))
