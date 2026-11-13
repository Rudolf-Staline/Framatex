# Séparation de l’assemblage et des fonctions métier

Base : `main`, commit `dffb33ec452a1ed596c44aaf740a3112c304b822` après fusion de la PR nº 36. Branche : `refactor/application-boundaries`.

Le commit `d61d2e2` n’est pas présent dans les objets Git locaux. La branche `refactor/backend-boundaries` n’est présente ni localement ni parmi les références distantes accessibles. L’inspection de `main` a confirmé que les extractions d’authentification employé, de permissions et d’audit restaient à effectuer ; elles constituent le premier lot.

## État de référence

- OpenAPI : 204 chemins, 235 opérations ; capture réalisée avant les modifications.
- Suite Python sur le code initial : 148 réussites, une expiration et un test réel Gemini ignoré. L’expiration concerne `test_secret_creation_is_atomic_across_processes_and_private` et sa limite de sous-processus de 20 secondes. Cette exécution était concurrente avec la recette navigateur. Le même test passe seul, sans changement de code, en 8,61 secondes.
- Les 14 scripts de tests JavaScript et les contrôles syntaxiques passent sur le code initial.
- La recette partenaires passe sur le code initial avec Chromium système. L’expiration connue en CI sur « Modifier les accès » n’est pas reproduite dans cette référence. Le binaire Playwright de CI n’est pas disponible dans la session ; Chromium système est la version 156.0.8078.79.

Deux essais intermédiaires de recette ont ensuite expiré sur le premier appel HTTP `/api/auth/login`, avant le démarrage du navigateur. Une mesure isolée de ce chemin donne 389 ms, dont 121 ms pour la vérification du mot de passe. Le code d’authentification et les délais du banc n’ont pas été assouplis. Ces observations sont distinguées des erreurs fonctionnelles ; les vérifications finales sont séquentielles.

## Responsabilités

| Propriétaire | Responsabilité |
|---|---|
| `app/main.py` | Entrée ASGI, cycle de vie, protections et erreurs HTTP, assemblage des routeurs |
| `app/auth_routes.py` | Connexion, déconnexion et session courante des employés |
| `app/access.py` | Permissions par rôle et rubrique, administration et accès aux lancements |
| `app/audit.py` | Ajout d’un événement à la transaction du demandeur, sans commit autonome |
| `app/employees.py` | Représentation publique des comptes employés |
| `app/document_storage.py` | Chemin privé, formats/MIME, limites, quota disque, hash, validation isolée, antivirus et nettoyage |
| `app/file_validation.py` | Worker de validation de formats, avec ses limites de ressources existantes |
| `app/partner_uploads.py` | Verrouillage et quotas propres à une organisation partenaire |
| `app/launches.py` | Recherche d’un lancement, représentation et libellés historiques de rubriques |
| `app/order_documents.py` | Dossier canonique, accès documentaire, recherche et représentation des documents et versions |
| `app/launch_routes.py` | Tableau de bord et routes des lancements |
| `app/document_routes.py` | Dépôt, nouvelles versions et téléchargement |
| `app/employee_admin_routes.py` | Rôles, comptes employés et consultation de l’audit |
| `app/completeness_routes.py` | Profils, exigences et décisions de complétude |
| `static/completeness-view.js` | HTML de complétude et des profils, échappement des valeurs, sans appel API |
| `static/completeness.js` | Interactions, appels API et rafraîchissement des vues de complétude |

`app/main.py` passe de **842 à 211 lignes** ; `static/app.js`, de **228 à 165 lignes**. Les fichiers JavaScript contiennent des lignes denses : ces nombres décrivent une extraction de responsabilités, pas une mesure de complexité.

Avant le changement, 35 modules importaient des fonctions ou constantes de `app.main`, via 47 instructions et 131 symboles importés. Il n’en reste aucun dans le package `app`. Les tests et outils qui chargent réellement l’application conservent `from app.main import app`.

Les six relais `deps`, `_deps`, `_base`, `_context` ou `functions` servant aux réimports circulaires sont remplacés par des imports explicites. Le normaliseur privé inutilisé de `workspace_routes.py` est supprimé après vérification de ses références. Les fonctions JavaScript appelées par les événements conservent leurs noms. Aucun framework, conteneur de dépendances ou mécanisme générique de services n’est ajouté.

Le scanner partagé quitte le module partenaire. Les dépôts et l’import ORLI l’utilisent depuis le stockage documentaire ; les budgets d’organisation restent distincts. Les anciennes démonstrations enregistrent le schéma par le migrateur existant, au lieu de dépendre de l’import de l’application pour enregistrer les modèles. Elles sont exécutées deux fois pour vérifier leur idempotence, leurs clés étrangères et les empreintes des fichiers.

## Contrats conservés

Les schémas OpenAPI avant et après sont strictement égaux, avec la même empreinte SHA-256 après tri des clés :

```text
ee8b68e95fcca6ebfe75ca3baaa2d20f49317b1ccdffc5ed0c2b2eb88c633288
```

Les 88 tables du registre de modèles et leurs colonnes restent identiques. Aucune définition de modèle ni migration n’est modifiée. Les résultats de comparaison sont conservés dans [refactor-contracts.json](../artifacts/refactor-contracts.json).

Les formats acceptés, MIME, limite de 20 Mio, noms de fichiers, chemin `DATA_DIR/files`, empreintes, mode privé, verrou de quota, scanner, messages d’erreur et protocole du worker sont conservés. Les fonctions de validation et de scan sont copiées sans changer leur logique. Les routes utilisent le propriétaire du stockage aussi pour leurs téléchargements et annulations. Trois tests nouveaux provoquent un échec après stockage et vérifient l’absence de nouveau blob, la conservation des anciens octets et le rollback des versions pour les parcours lancement, commande et nouvelle version.

Les cookies, la révocation, les permissions, les frontières entre employés et partenaires et les règles d’accès aux objets restent vérifiés par leurs mécanismes existants. La règle **une commande = un Dossier Jaune unique** et ses quatre rubriques ne change pas. Les libellés historiques des lancements restent distincts des libellés canoniques ; ils ne sont pas fusionnés lors du nettoyage.

Les deux nouveaux scripts de complétude suivent `app.js`. L’ordre relatif de tous les scripts précédents est conservé. Le démarrage, la navigation, les noms de fonctions utilisés par les événements et les sélecteurs du guide sont préservés. Les tests existants de rendu et d’échappement sont conservés et chargent les nouveaux fichiers ; un test vérifie également l’échappement dans le rendu administratif pur.

## Lots et commits

| Commit | Changement | Vérification du lot |
|---|---|---|
| `99b2a23` | Authentification employé, permissions et audit hors de l’assemblage | 29 tests ciblés réussis, OpenAPI inchangé |
| `5a95645` | Stockage partagé, représentation/recherche des ressources, imports des routes et démonstrations | 46 tests ciblés et nouveau test des anciens scripts réussis ; trois tests de rollback inclus ; OpenAPI inchangé |
| `e2d2b62` | Extraction des quatre groupes de routes métier | 24 tests réussis ; expiration du secret déjà observée en référence, puis réussite isolée ; trois tests de frontières/imports réussis ; OpenAPI et registre inchangés |
| `f53d83d` | Vues et interactions de complétude séparées | 14 scripts JavaScript, syntaxe, catalogue et manuel réussis |
| `f4e7db9` | Retrait des relais inutiles, imports morts et scanner découplé des modèles partenaires | 29 tests de parcours et 14 tests supplémentaires, dont antivirus réel et imports indépendants, réussis |

## Vérifications finales

Les commandes sont exécutées dans le virtualenv du projet. Les recettes utilisent des serveurs et bases temporaires et des données synthétiques. Aucun appel réel Gemini n’est autorisé :

```bash
FRAMATEX_GUIDE_AI_ENABLED=0 FRAMATEX_GUIDE_REAL_AI_TEST=0 PYTHONPATH=. python -m pytest -q
for file in tests/*.cjs; do node "$file"; done
for file in static/*.js; do node --check "$file"; done
python tools/check_guide_catalog.py
python tools/build_guide_manual.py --check
python tools/evaluate_guide.py --output /tmp/refactor-local-evaluation.json
python tools/evaluate_guide.py --simulate --ai-budget 112 --output /tmp/refactor-simulated-evaluation.json
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_phase3_browser.py
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_partner_browser.py
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_guide_browser.py
python -m pip check
git diff origin/main --check
```

ClamAV réel est utilisé par les tests dédiés, avec les chemins de son installation locale dans l’environnement de test. Les tests d’import créent deux interpréteurs frais, dans les deux ordres de chargement des routeurs, et vérifient qu’aucun routeur ne charge `app.main`. Les douze vérifications finales passent : **156 tests Python réussis, un test réel Gemini ignoré et un avertissement SQLite préexistant**, les 14 scripts de tests JavaScript et la syntaxe, OpenAPI, catalogue, manuel, évaluations locale/simulée, trois recettes Chromium, dépendances et contrôle des espaces. La recherche locale du guide obtient 122/122 sur le corpus synthétique existant. La recette partenaires finale vérifie notamment le bouton de modification des accès. Les états et durées sont conservés dans [refactor-verification.json](../artifacts/refactor-verification.json).

La disponibilité de l’API GitHub et du téléchargement Playwright reste limitée par la politique réseau active de cette session. Aucun déploiement ni fusion n’est effectué.

## Publication et vérifications restantes

La branche `refactor/application-boundaries` est poussée sur GitHub. La tentative `gh pr create --draft --base main --head refactor/application-boundaries --body-file docs/PULL_REQUEST_REFACTOR.md` a reçu `Post "https://api.github.com/graphql": Forbidden`. Aucune PR brouillon créée ni validation GitHub Actions n’est revendiquée. La [description prête à relire](PULL_REQUEST_REFACTOR.md) et le [lien de création](https://github.com/Rudolf-Staline/Framatex/pull/new/refactor/application-boundaries) sont disponibles ; le mode brouillon reste à sélectionner si la création est effectuée manuellement.

Il reste à vérifier les checks distants et la recette avec le Chromium Playwright exact lorsque ces accès sont disponibles. Le délai d’attente connu sur « Modifier les accès » n’a été reproduit ni dans la référence locale ni dans la recette finale ; aucun changement du banc ne prétend le corriger. Le test réel Gemini reste facultatif et ignoré ; le fonctionnement local et le fournisseur simulé sont vérifiés.

Des services partagés entre certains routeurs, par exemple l’inspection Excel utilisée par les dépôts, restent dans leurs modules historiques. Ils ne dépendent plus de `app.main` et les imports à froid passent ; leur extraction peut constituer un prochain lot distinct. Ce refactoring ne prétend pas supprimer toutes les dépendances entre domaines du projet.
