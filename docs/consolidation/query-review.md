# Revue indépendante des requêtes et mesures concurrentes

Relecture du code de consolidation : `order_document_queries.py`, `document_search_routes.py`, listes commandes/lancements, résumé dossier et `static/orders.js`. Les constats ci-dessous ont été transmis au responsable central avant toute correction ; ils ne décrivent pas nécessairement l'état final après intégration.

## Vérifications de conception
- Recherche et pages documentaires : prédicat d'accès appliqué avant COUNT et LIMIT ; combinaisons commande/provenance respectées ; tri avec identifiant comme dernier critère, sans ordre indéterminé en cas de dates égales.
- Listes des commandes : accès commande avant pagination, lancements filtrés selon leurs restrictions ; chargement groupé des lancements de la page.
- Recherche : client canonique de commande et repli historique, filtre `client_id` permettant de distinguer les homonymes ; pas de fuite d'identifiant observée dans les sélections relues.
- Pages documentaires : dernière version uniquement ; historique récupéré séparément ; détail d'approbation borné à la page visible.

## Points signalés pour intégration
1. Exiger également `launch.read` pour l'historique, comme pour les autres surfaces documentaires ; la route de téléchargement historique doit suivre cette politique.
2. L'interface de création de commande était encore limitée à `state.me.admin` malgré `order.create` disponible côté serveur. L'annuaire choisi pour cette action doit être accessible au rôle métier habilité.
3. Le traitement d'erreur asynchrone de la liste des commandes pouvait viser un élément DOM absent après navigation ; vérifier le contexte dans le chemin d'erreur aussi.
4. Le compteur de résumé du dossier ignorait les filtres `q` et `launch_id` pourtant appliqués aux documents.
5. Une navigation vers un autre dossier pendant les requêtes initiales peut laisser la réponse précédente remplacer l'écran plus récent ; prévoir un jeton de navigation. Les chargements de page documentaire ont déjà leur propre numéro de requête.
6. Les requêtes d'approbation restent par document de la page (volume borné, mais optimisation par chargement groupé encore possible). Le tableau de bord évalue encore les lancements individuellement ; le coût dépend de leur nombre.
7. Les pages à offset peuvent se décaler en cas d'insertion concurrente. Le tri est déterministe, sans promesse de snapshot persistant entre deux clics.

## Mesures concurrentes synthétiques
Commande exécutée :

```sh
PYTHONPATH=. /tmp/framatex-venv/bin/python tools/measure_document_search.py --sizes 100 1000 --repeats 3 --concurrency 2 4 --output docs/consolidation/search-concurrent.json
```

Données jetables créées dans un répertoire temporaire, variables de base imposées par le script : aucun accès à une base configurée ou distante. Un lecteur interne autorisé, une commande, des pièces communes, un lancement lié, trois versions par document. Appel de la fonction de recherche avec session et connexion SQLAlchemy distinctes par requête, page fixe de 25 pièces. Trois vagues, départ synchronisé de chaque vague. Hôte de développement partagé, sans exclusivité CPU/RAM ; `tracemalloc` activé. Les chiffres sont des observations locales, sans HTTP, charge de production ni p95.

| Documents / versions | Concurrence | Requêtes | Erreurs | SQL par requête | JSON | Médiane locale | Pic Python agrégé |
|---|---:|---:|---:|---:|---:|---:|---:|
| 100 / 300 | 2 | 6 | 0 | 5 | 10 126 octets | 125,55 ms | 2 195 113 octets |
| 100 / 300 | 4 | 12 | 0 | 5 | 10 126 octets | 250,21 ms | 4 822 354 octets |
| 1 000 / 3 000 | 2 | 6 | 0 | 5 | 10 202 octets | 93,12 ms | 2 168 420 octets |
| 1 000 / 3 000 | 4 | 12 | 0 | 5 | 10 202 octets | 215,00 ms | 4 636 381 octets |

La variation de latence entre corpus ne constitue pas une amélioration démontrée : charge partagée, caches, ordonnancement et instrumentation interviennent. Le résultat robuste ici est le nombre constant de cinq instructions SQL pour la page et l'absence d'erreur sur les 36 requêtes concurrentes. Les échantillons bruts, durées par vague et mémoire agrégée restent inspectables dans `search-concurrent.json`.
