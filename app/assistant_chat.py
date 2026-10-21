"""Guide global et consultation sourcée de la mémoire métier."""
from __future__ import annotations
import re
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


def conversational_response(question: str):
    """Handle direct conversational turns before domain search, without inventing data."""
    phrase = " ".join(re.findall(r"[a-z0-9]+", normalized(question)))
    greetings = {
        "salut", "bonjour", "bonsoir", "coucou", "hello", "hey", "hi", "yo",
        "bjr", "slt", "salut jauno", "bonjour jauno", "bonsoir jauno",
        "salut assistant", "bonjour assistant", "bonsoir assistant",
    }
    how_are_you = {
        "ca va", "comment ca va", "comment vas tu", "tu vas bien",
        "comment allez vous", "salut ca va", "bonjour ca va",
    }
    thanks = {
        "merci", "merci beaucoup", "merci jauno", "super merci",
        "ok merci", "parfait merci", "thanks", "thank you",
    }
    who = {
        "qui es tu", "qui etes vous", "tu es qui", "c est quoi jauno",
        "c est qui jauno", "presente toi", "ton nom", "comment tu t appelles",
    }
    help_requests = {
        "aide", "aide moi", "help", "je suis perdu", "que sais tu faire",
        "que peux tu faire", "tu peux faire quoi", "comment tu peux m aider",
        "quelles sont tes fonctionnalites",
    }
    goodbyes = {"au revoir", "a bientot", "bye", "bonne journee", "bonne soiree", "a plus"}
    if phrase in greetings:
        title, answer = ("Salut !" if phrase.startswith(("salut", "slt", "coucou", "hey", "yo", "hi")) else "Bonjour !"), (
            "Je suis l’assistant JAUNO. Je peux retrouver un dossier jaune, chercher "
            "un document, vérifier les pièces manquantes ou expliquer le partage client. "
            "De quoi avez-vous besoin ?"
        )
    elif phrase in how_are_you:
        title, answer = "Tout va bien, merci !", (
            "Je suis prêt à vous aider dans JAUNO. Vous cherchez un dossier, "
            "un fichier ou une information sur l’avancement d’une commande ?"
        )
    elif phrase in thanks:
        title, answer = "Avec plaisir !", (
            "Je peux aussi vous aider à retrouver un document ou à vérifier "
            "la complétude de votre dossier."
        )
    elif phrase in who:
        title, answer = "Je suis l’assistant JAUNO.", (
            "Je suis un guide documentaire connecté aux informations auxquelles "
            "votre compte a accès. Je peux retrouver des références, lister les fichiers "
            "et signaler les exigences documentaires non satisfaites. "
            "Je ne valide pas les pièces à la place des collaborateurs."
        )
    elif phrase in help_requests:
        title, answer = "Comment puis-je vous aider ?", (
            "Essayez par exemple : « Recherche CMD-2026-001 », "
            "« Quels documents sont dans le sous-dossier rose ? », "
            "« Quelles pièces manquent dans ce dossier ? » ou "
            "« Pourquoi mon client ne voit-il pas un fichier ? ». "
            "Ouvrez un dossier jaune pour poser une question directement à son sujet."
        )
    elif phrase in goodbyes:
        title, answer = "À bientôt !", "Bonne continuation dans JAUNO."
    else:
        return None
    return {
        "title": title, "answer": answer, "source": "Assistant JAUNO",
        "destination": None, "results": [], "requires_human_action": False,
        "sources": [],
    }


@router.post("/api/assistant/chat")
def chat(payload: ChatInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .main import permitted
    phrase = normalized(payload.question)
    from .access import must_access
    from .assistant_context import contextual_answer
    context = must_access(db,user,payload.launch_id) if payload.launch_id else None
    conversational = conversational_response(payload.question)
    if conversational is not None:
        return conversational
    result = contextual_answer(db,user,payload.question,context,permitted)
    if result is not None:
        return result
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
        (("facture", "deposer", "document", "rubrique", "sous-dossier", "dossier jaune"), "Dossier Jaune", "dossier",
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
                    "sources": [], "source": "Guide de navigation JAUNO", "requires_human_action": True}
    if permitted(user, "launch.read"):
        from .workspace_routes import guide, GuideRequest
        result = guide(GuideRequest(question=payload.question, launch_id=payload.launch_id), user, db)
        if result.get("destination"):
            return result
    return answer_question(db, user, Question(question=payload.question, folder=payload.folder))
