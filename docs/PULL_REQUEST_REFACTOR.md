## Problème et résultat

Les routeurs, les démonstrations et les services empruntaient leurs fonctions partagées à `app.main`, alors que celui-ci importait ces mêmes routeurs. Le chargement dépendait de l’ordre d’initialisation de l’application. Ce changement donne un propriétaire aux fonctions partagées et réserve `app.main:app` à l’assemblage et aux protections HTTP.

`app/main.py` passe de 842 à 211 lignes. Les 35 modules qui importaient ses helpers n’en dépendent plus. L’authentification employé, les permissions, l’audit, le stockage et les quatre groupes de routes métier sont séparés. Le scanner commun quitte le module partenaire ; les quotas d’organisation y restent. Les routeurs se chargent dans un interpréteur frais sans charger `app.main`.

Le stockage garde les formats, MIME, limites, chemins, hash, messages et contrôles existants. Les tests nouveaux vérifient aussi le retrait des blobs après rollback sans altérer les fichiers historiques. Les anciennes démonstrations utilisent le migrateur existant pour enregistrer le schéma et sont vérifiées deux fois pour leur idempotence.

Le frontend extrait la complétude dans une vue sans appels API et un contrôleur d’interactions. Les noms des callbacks, les sélecteurs du guide et l’ordre relatif des scripts sont conservés. Aucun framework ni abstraction générique de services n’est ajouté.

## Commits à lire

| Commit | Lot |
|---|---|
| `99b2a23` | Authentification employé, permissions et audit |
| `5a95645` | Stockage documentaire et fonctions partagées des ressources |
| `e2d2b62` | Assemblage des routeurs métier et tests de frontières |
| `f53d83d` | Séparation des vues et interactions de complétude |
| `f4e7db9` | Suppression des relais d’import inutiles, imports morts et découplage du scanner |

Le commit local `d61d2e2` et la branche `refactor/backend-boundaries` n’étaient pas accessibles ; les extractions absentes ont été reproduites depuis `main` (`dffb33e`).

## Contrats et vérification

- OpenAPI avant/après strictement identique : 204 chemins, 235 opérations et même SHA-256 ; 88 tables enregistrées avec les mêmes colonnes.
- Aucune modification de modèle ou de migration. Conservation des URL, permissions, sessions, frontières partenaires et du Dossier Jaune unique par commande.
- Suite Python finale : **156 réussites, un test réel Gemini ignoré et un avertissement SQLite préexistant**. Les 14 scripts JavaScript, la syntaxe, les trois recettes Chromium, le catalogue, le manuel et les évaluations locale/simulée passent. Le guide local obtient 122/122 sur le corpus existant. La modification des accès passe aussi dans la recette partenaires finale.
- Tests ajoutés : imports des routeurs sans application, deux ordres de chargement, rollback des fichiers sur trois surfaces, anciens scripts de démonstration et échappement du rendu administratif.

Commandes principales exécutées séquentiellement :

```bash
FRAMATEX_GUIDE_AI_ENABLED=0 FRAMATEX_GUIDE_REAL_AI_TEST=0 PYTHONPATH=. python -m pytest -q
for file in tests/*.cjs; do node "$file"; done
for file in static/*.js; do node --check "$file"; done
python tools/check_guide_catalog.py
python tools/build_guide_manual.py --check
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_phase3_browser.py
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_partner_browser.py
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_guide_browser.py
```

La référence Python sur le code initial avait expiré dans le test de création concurrente du secret (20 secondes), exécuté avec une recette navigateur ; ce test a passé seul sans modification. La recette partenaires initiale a passé : l’expiration connue en CI sur « Modifier les accès » n’y a pas été reproduite. Deux tentatives intermédiaires ont expiré avant le navigateur, sur l’authentification HTTP ; une mesure isolée donne 389 ms. Aucun délai de test ou contrôle fonctionnel n’a été assoupli. Les résultats locaux ne sont pas présentés comme une validation du runner GitHub ni du Chromium Playwright exact.

Aucun appel réel Gemini, déploiement ou fusion automatique. Cette PR reste destinée à la revue.

Voir le [rapport complet](https://github.com/Rudolf-Staline/Framatex/blob/refactor/application-boundaries/docs/REFACTOR_APPLICATION_BOUNDARIES.md) et les [comparaisons de contrats](https://github.com/Rudolf-Staline/Framatex/blob/refactor/application-boundaries/artifacts/refactor-contracts.json).
