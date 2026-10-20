"""Local contextual answers over authorized metadata; never reads document contents."""
import re
from sqlalchemy import select
from .models import Launch
from .access import visible
from .experience_search import normalized as _normalize


def reply(title, answer, destination=None, results=None, launch=None):
    return {'title':title,'answer':answer,'destination':destination,
            'results':results or [], 'launch_id':launch.id if launch else None,
            'folder':None,'area':None,'requires_human_action':True,
            'source':'Framatex · métadonnées autorisées à la date de la demande'}


def launch_result(launch):
    return {'label':launch.name,'description':launch.order_ref or launch.status,
            'launch_id':launch.id,'folder':'jaune'}


def contextual_answer(db, user, question, launch, permitted):
    phrase = _normalize(question)
    if any(term in phrase for term in ('inscrire un client','creer un client','espace client','portail client','associer un client','rattacher un client')):
        from .main import is_admin
        if is_admin(user):
            return reply('Clients et espace client',
                'Dans Clients, inscrivez la société puis créez un accès pour chaque contact. Dans Nouveau dossier ou Modifier le dossier, choisissez ce client du répertoire. Le contact voit ses dossiers et uniquement les versions approuvées puis publiées dans Échanges documentaires.', 'clients')
        return reply('Rattacher un dossier à un client',
            'Choisissez le client du répertoire dans Nouveau dossier ou Modifier le dossier si vos droits le permettent. Un administrateur peut inscrire une société et créer les accès à son espace client.', 'launches')
    status_query = any(term in phrase for term in ('statut','resume','resumer','avancement','ou en est','combien de document'))
    search_match = re.search(r'\b(?:recherche[r]?|cherche[r]?|trouve[r]?|retrouve[r]?)\s+(.+)', phrase)
    if phrase.startswith(('ou ', 'comment ')) and not status_query:
        return None
    if not status_query and not search_match:
        return None
    rows = [launch] if launch else visible(db, user, db.scalars(select(Launch).order_by(Launch.updated_at.desc())).all())
    if status_query:
        if not launch:
            return reply('Quel dossier souhaitez-vous examiner ?',
                'Choisissez un dossier dans le sélecteur de contexte pour connaître son statut et son nombre de documents accessibles.',
                results=[launch_result(l) for l in rows[:6]])
        docs = [doc for folder in launch.folders if permitted(user,'document.read',folder.slug) for doc in folder.documents]
        answer = f'{launch.name} : {launch.status}. {len(docs)} document(s) et {sum(len(d.versions) for d in docs)} version(s) accessibles.'
        if launch.order_ref:
            answer += f' Commande : {launch.order_ref}.'
        answer += ' Ce statut est celui enregistré par votre équipe ; il ne constitue pas une validation automatique.'
        return reply('Votre dossier en bref', answer, 'detail', launch=launch)
    query = search_match.group(1).strip(' «»"\'?.!')
    quoted = re.search(r'[«"“]([^»"”]+)[»"”]', question)
    if quoted:
        query = _normalize(quoted.group(1))
    stop = {'un','une','le','la','les','des','de','du','dans','mes','mon','ma','moi','nos','pour','dossier','dossiers','document','documents','piece','pieces','client'}
    tokens = [t for t in re.findall(r'[\w-]+',query) if t not in stop]
    if not tokens:
        return reply('Précisez votre recherche',
            'Indiquez un titre, une société ou une référence. Par exemple : « Recherche fiche technique » ou « Cherche CMD-2026-001 ».', 'launches')
    results = []
    for l in rows:
        haystack = _normalize(' '.join((l.name,l.client_name or '',l.order_ref or '',l.orli_ref or '')))
        if all(t in haystack for t in tokens):
            results.append(launch_result(l))
        for folder in l.folders:
            if not permitted(user,'document.read',folder.slug):
                continue
            for doc in folder.documents:
                text = _normalize(f'{doc.title} {doc.doc_type}')
                if all(t in text for t in tokens):
                    results.append({'label':doc.title,'description':f'{l.name} · {folder.label}',
                                    'launch_id':l.id,'folder':folder.slug})
    count = len(results)
    return reply('Résultats de recherche' if count else 'Aucun résultat accessible',
        (f'{count} résultat(s) dans les titres, types documentaires et références accessibles.' + (' Les six premiers sont affichés.' if count>6 else '')) if count else
        'Aucun résultat dans les informations auxquelles vous avez accès. Essayez un titre plus court ou une référence de commande.',
        results=results[:6])
