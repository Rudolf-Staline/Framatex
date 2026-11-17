# Recherche, pagination et navigation documentaire

## Corrections
- Recherche : autorisation SQL et droits de rubrique appliqués avant COUNT/OFFSET/LIMIT, tri avec identifiant de départage ; plus de chargement complet pour filtrer en Python.
- Client : `BusinessOrder.client_id` et nom canonique prioritaires, repli sur `Launch.client_name` pour les documents historiques. Filtre `client_id` pour distinguer les homonymes ; les pièces communes sans lancement sont conservées.
- Types : recherche par identifiant, libellés et alias non ambigus, affectation canonique conservée sans fusion des originaux.
- Commandes/lancements : filtres SQL, pages de 1 à 100, tri déterministe, compter uniquement les objets accessibles. `/api/orders?page=true` et `/api/launches?page=true` renvoient `{items,total,offset,limit}` ; sans page, la forme liste historique reste disponible, désormais bornée à 100 par défaut et `X-Total-Count` signale le total. Les intégrateurs doivent utiliser offset/limit pour parcourir le tout.
- Interface commandes : recherche/tri/page côté serveur, réponse tardive écartée lors d'un changement de recherche, état de chargement et erreur récupérable.
- Dossier canonique : `?summary=true` ne charge pas les collections documentaires ; `/document-page` renvoie 25 pièces avec dernière version et validation courante. L'historique utilise `/api/documents/{id}/history?offset=&limit=` ; les originaux restent téléchargables.
- Clients pour création : `/api/order-clients` nécessite `order.create`, retourne uniquement identité et nom des clients actifs, paginés ; l'annuaire d'administration reste réservé à l'administration. Aucune permission ajoutée aux rôles existants.
- Télécharger une version ne charge plus toutes les versions du document.
- Tableau de bord : dénombrement documentaire et versions en SQL ; listes lancements filtrées en SQL. Le calcul de complétude reste proportionnel au nombre d'obligations visibles.

## Mesures locales
Voir `search-before.json`, `search-after.json`, `search-concurrent.json` et `query-review.md`.
Copie du commit initial dans `/tmp/framatex-baseline`, mêmes données synthétiques, SQLite local, lecteur non administrateur, une commande, un lancement, trois versions par pièce commune, page de 25. Mesure de la fonction API avec session SQLAlchemy, sans HTTP ; trois échantillons séquentiels, tracemalloc activé. L'hôte est partagé avec d'autres vérifications : ne pas interpréter la latence comme une capacité serveur.

| Documents / versions | SQL avant → après | Médiane locale avant → après | JSON avant → après | Mémoire Python après (échantillons hors premier échauffement) |
|---|---:|---:|---:|---:|
| 100 / 300 | 379 → 5 | 556,05 → 83,69 ms | 9 776 → 10 126 octets | 693 582 à 794 381 octets |
| 1 000 / 3 000 | 3 079 → 5 | 5 782,29 → 83,86 ms | 9 852 → 10 202 octets | 690 048 à 695 853 octets |

36 recherches concurrentes (2 puis 4 threads, sessions distinctes, corpus 100/1000) : zéro erreur, cinq instructions SQL par recherche. Les médianes et chaque échantillon sont conservés dans le JSON. Aucun p95 ni mesure de production n'est revendiqué.

## Vérifications et limites
`tests/test_consolidation_queries.py` couvre pièces sans lancement, clients homonymes, accès avant comptage/pagination, budget SQL stable sur corpus croissant, résumés sans versions et historique paginé. Les tests API existants de recherche et commande sont conservés.

Les anciennes routes de détail et d'aperçu complet restent compatibles et peuvent retourner de gros historiques ; les nouvelles pages de commande ne les utilisent plus pour charger les documents. Les séquences d'approbation complexes produisent encore des requêtes par circuit, bornées à la page. La pagination offset peut se décaler si une insertion intervient entre deux requêtes ; il faut actualiser pour retrouver une vue courante (pas de promesse de snapshot multi-requêtes). Une pagination par curseur et la matérialisation incrémentale des priorités/complétudes restent des optimisations distinctes à dimensionner après mesure réelle.
