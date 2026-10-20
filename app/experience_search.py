"""Recherche locale explicable. Les réponses citent les fiches, sans générer de faits."""
from __future__ import annotations
import json
import re
import unicodedata

STOP = set("a au aux avec ce ces cet cette comment dans de des du elle elles en est et ete etre eux fait faire faut il ils je la le les leur leurs lui ma mais me mes mon ne nos notre nous on ont ou par pas peut peux plus pour pourquoi qu que quel quelle quelles quels qui sa se ses si son sont sur ta te tes ton tu un une vos votre vous y deja probleme problemes rencontre rencontres resoudre resolu resolus solution solutions eviter lors avoir avons avait cela ceci cas experience retour retours".split())
SYNONYMS = (
    {"quantite", "nombre", "volume", "quantitatif"},
    {"ecart", "difference", "divergence", "incoherence", "discordance"},
    {"retard", "delai", "retarde", "tardive"},
    {"metrage", "consommation", "metre"},
    {"livraison", "reception", "livre", "recu"},
    {"manquant", "absent", "absence", "introuvable"},
    {"facture", "facturation"},
    {"tissu", "textile", "matiere"},
)


def normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalized(text))
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w
            for w in words if len(w) > 2 and w not in STOP}


def rank_records(records, question: str):
    query = tokens(question)
    groups = [next((s for s in SYNONYMS if w in s), {w}) for w in sorted(query)]
    if not groups:
        return []
    ranked = []
    for record in records:
        fields = ((record.title, 4), (" ".join(json.loads(record.tags_json)), 4),
                  (record.problem, 3), (record.cause, 2), (record.solution, 2),
                  (record.lesson, 2), (record.context, 1), (record.orli_ref or "", 4))
        field_tokens = [(tokens(value), weight) for value, weight in fields]
        matched = sum(any(words & group for words, _ in field_tokens) for group in groups)
        if not matched:
            continue
        # Require at least half the meaningful query concepts. A shared generic
        # word cannot turn an unrelated record into a documented answer.
        if matched * 2 < len(groups):
            continue
        score = sum(weight for words, weight in field_tokens for group in groups if words & group)
        ranked.append((score, record))
    ranked.sort(key=lambda row: (-row[0], row[1].status != "resolu", row[1].id))
    return [record for _, record in ranked]
