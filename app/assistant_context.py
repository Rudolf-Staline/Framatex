"""Contextual assistant over authorized Framatex metadata, with no fabricated file contents."""
from __future__ import annotations

import re
from sqlalchemy import select
from .models import Launch
from .access import visible
from .experience_search import normalized as _normalize

FOLDERS = {
    "jaune": ("jaune", "technique"), "rose": ("rose", "reception"),
    "bleu": ("bleu", "douane"), "vert": ("vert", "facturation", "facture"),
}
STOPWORDS = {
    "un", "une", "le", "la", "les", "des", "de", "du", "dans", "mes", "mon", "ma",
    "moi", "nos", "pour", "dossier", "dossiers", "document", "documents", "piece",
    "pieces", "client", "fichier", "fichiers", "commande", "commandes", "framat",
}


def reply(title, answer, destination=None, results=None, launch=None, folder=None, area=None):
    return {
        "title": title, "answer": answer, "destination": destination,
        "results": results or [], "launch_id": launch.id if launch else None,
        "folder": folder, "area": area, "requires_human_action": True,
        "source": "Framatex · informations accessibles en temps réel",
    }


def launch_result(launch, folder="jaune"):
    return {
        "label": launch.name, "description": launch.order_ref or launch.status,
        "launch_id": launch.id, "folder": folder,
    }


def requested_folder(phrase):
    for slug, aliases in FOLDERS.items():
        if any(re.search(r"\b" + re.escape(alias) + r"\b", phrase) for alias in aliases):
            return slug
    return None


def find_mentioned_launch(rows, question):
    """Select only a unique named/referenced dossier, not an ambiguous substring."""
    question = _normalize(question)
    candidates = []
    for launch in rows:
        terms = (launch.order_ref, launch.orli_ref, launch.name)
        if any(len(_normalize(t.strip())) >= 4 and _normalize(t.strip()) in question
               for t in terms if t):
            candidates.append(launch)
    return candidates[0] if len(candidates) == 1 else None


def contextual_answer(db, user, question, launch, permitted):
    phrase = _normalize(question)
    from .main import is_admin
    if any(term in phrase for term in (
        "inscrire un client", "creer un client", "espace client",
        "portail client", "associer un client", "rattacher un client",
    )):
        if is_admin(user):
            return reply(
                "Clients et espace client",
                "Dans Clients, inscrivez la société et créez ses contacts. "
                "Rattachez ensuite la commande à cette société. Le contact voit "
                "le dossier associé et les versions explicitement approuvées et publiées. "
                "Pour publier : ouvrez la commande, puis Contrôles et outils → Partage externe.",
                "clients",
            )
        return reply(
            "Accès client", "Un administrateur doit créer l’accès du contact et rattacher "
            "la commande à la société. L’accès au dossier ne publie pas automatiquement "
            "les fichiers internes.", "launches",
        )

    # Never select a launch that the caller cannot access.
    rows = [launch] if launch else visible(
        db, user, db.scalars(select(Launch).order_by(Launch.updated_at.desc())).all()
    )
    selected = launch or find_mentioned_launch(rows, question)
    folder = requested_folder(phrase)

    wants_missing = any(term in phrase for term in (
        "manquant", "manque", "absent", "pieces attendues", "completude", "incomplet",
    ))
    if wants_missing:
        if not selected:
            return reply(
                "De quel dossier s’agit-il ?",
                "Indiquez une référence de commande ou ouvrez un dossier. "
                "Je pourrai alors consulter ses exigences documentaires configurées.",
                results=[launch_result(l) for l in rows[:6]],
            )
        from .completeness import evaluate
        report = evaluate(db, selected, user, permitted)
        if not report["configured"]:
            return reply(
                "Aucune règle de complétude configurée",
                "Ce dossier ne possède pas encore de profil documentaire actif. "
                "Je ne peux pas déduire des documents manquants sans règles métier.",
                "detail", launch=selected, area="completude", folder=folder,
            )
        missing = [r for r in report["rows"]
                   if r["status"] in ("missing", "pending_validation")
                   and (not folder or r["folder"] == folder)]
        text = "; ".join(
            f'{r["title"]} ({r["folder"]} : '
            f'{"absente" if r["status"] == "missing" else "à valider"})'
            for r in missing[:10]
        )
        suffix = (" D’autres éléments existent ; consultez les vérifications."
                  if len(missing) > 10 else "")
        caveat = (" Certaines règles restent masquées par vos habilitations."
                  if report["partial_visibility"] else "")
        answer = ((f'{len(missing)} point(s) à vérifier : {text}.' + suffix)
                  if missing else "Aucune pièce manquante ou à valider parmi les règles visibles.")
        return reply(
            "Complétude du dossier", answer + caveat, "detail",
            launch=selected, folder=folder, area="completude",
        )

    wants_publication = any(term in phrase for term in (
        "publie", "publication", "partage", "visible par le client",
        "client ne voit", "client voit", "documents du client",
    ))
    if wants_publication:
        if not selected:
            return reply(
                "Publication vers l’espace client",
                "Ouvrez une commande et choisissez Contrôles et outils → Partage externe. "
                "Une commande rattachée à un client n’autorise pas automatiquement ses pièces.",
                "launches",
            )
        from .client_routes import portal_publications
        publications = portal_publications(db, selected) if is_admin(user) else []
        answer = (
            f'{len(publications)} version(s) actuellement visible(s) par le client. '
            if is_admin(user) else
            "La consultation des publications est réservée aux comptes habilités. "
        )
        answer += (
            "Le dossier doit être rattaché à une société active. Pour qu’un fichier apparaisse, "
            "la dernière version doit être admissible, approuvée puis publiée dans Partage externe. "
            "La simple présence du fichier dans le dossier jaune ne suffit pas."
        )
        return reply(
            "Visibilité client", answer, "detail", launch=selected, area="partage",
        )

    wants_contents = any(term in phrase for term in (
        "contenu du dossier", "contenu de la commande", "documents dans",
        "fichiers dans", "liste des documents", "liste les documents",
        "quels documents", "quels fichiers", "montre les documents",
        "montre les fichiers", "documents disponibles", "pieces disponibles",
    ))
    if wants_contents:
        if not selected:
            return reply(
                "Choisissez une commande",
                "Donnez sa référence ou ouvrez-la avant de demander la liste des fichiers.",
                results=[launch_result(l) for l in rows[:6]],
            )
        documents = [
            (doc, f) for f in selected.folders
            if (not folder or f.slug == folder) and permitted(user, "document.read", f.slug)
            for doc in f.documents
        ]
        results = [{
            "label": doc.title,
            "description": f"{selected.name} · {f.label} · "
                           f"{len(doc.versions)} version(s)",
            "launch_id": selected.id, "folder": f.slug,
        } for doc, f in documents[:8]]
        if not documents:
            answer = (
                "Aucun document accessible dans ce sous-dossier."
                if folder else "Aucun document accessible dans les sous-dossiers autorisés."
            )
        else:
            answer = (
                f"{len(documents)} document(s) accessibles"
                + (f" dans le sous-dossier {folder}" if folder else "")
                + ". Les huit premiers sont proposés ci-dessous."
            )
        return reply(
            "Documents accessibles", answer, "detail", results=results,
            launch=selected, folder=folder,
        )

    wants_status = any(term in phrase for term in (
        "statut", "resume", "resumer", "avancement", "ou en est",
        "combien de document", "combien de fichier",
    ))
    if wants_status:
        if not selected:
            return reply(
                "Quel dossier souhaitez-vous examiner ?",
                "Choisissez une commande ou indiquez sa référence pour connaître "
                "son statut et ses documents accessibles.",
                results=[launch_result(l) for l in rows[:6]],
            )
        docs = [doc for f in selected.folders
                if permitted(user, "document.read", f.slug)
                for doc in f.documents]
        answer = (
            f"{selected.name} : {selected.status}. {len(docs)} document(s), "
            f"{sum(len(d.versions) for d in docs)} version(s) accessibles."
        )
        if selected.order_ref:
            answer += f" Référence : {selected.order_ref}."
        answer += " Le statut est saisi par l’équipe, sans validation automatique."
        return reply("État de la commande", answer, "detail", launch=selected)

    search_match = re.search(
        r"\b(?:rechercher?|cherche[rz]?|trouve[rz]?|retrouve[rz]?)\s+(.+)",
        phrase,
    )
    if not search_match or phrase.startswith(("ou ", "comment ")):
        return None
    query = search_match.group(1).strip(' «»"\'?.!')
    quoted = re.search(r'[«"“]([^»"”]+)[»"”]', question)
    if quoted:
        query = _normalize(quoted.group(1))
    tokens = [t for t in re.findall(r"[\w-]+", query) if t not in STOPWORDS]
    if not tokens:
        return reply(
            "Précisez votre recherche",
            "Indiquez un titre, une société ou une référence, par exemple CMD-2026-001.",
            "launches",
        )
    results = []
    for item in rows:
        haystack = _normalize(" ".join(
            (item.name, item.client_name or "", item.order_ref or "", item.orli_ref or "")
        ))
        if all(t in haystack for t in tokens):
            results.append(launch_result(item))
        for f in item.folders:
            if not permitted(user, "document.read", f.slug):
                continue
            for doc in f.documents:
                if all(t in _normalize(f"{doc.title} {doc.doc_type}") for t in tokens):
                    results.append({
                        "label": doc.title,
                        "description": f"{item.name} · {f.label}",
                        "launch_id": item.id, "folder": f.slug,
                    })
    count = len(results)
    return reply(
        "Résultats de recherche" if count else "Aucun résultat accessible",
        (f"{count} résultat(s) dans les titres et références autorisés."
         if count else "Aucun résultat dans les informations auxquelles vous avez accès. "
                       "Essayez une expression plus courte."),
        results=results[:8],
    )
