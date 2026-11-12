# Vérification de Framatex Guide

Les tests utilisent des comptes, commandes et documents synthétiques sur des bases SQLite temporaires. La CI désactive les appels réels à Google. Les preuves ne constituent pas une recette de production, une mesure sur les utilisateurs Framatex ou une certification d’accessibilité.

## Installation reproductible

```bash
python -m pip install -r requirements-test.txt
npm ci
python -m playwright install --with-deps chromium
```

Installer également ClamAV pour la suite complète, selon le workflow `.github/workflows/tests.yml`. Dans cet environnement, Chromium système a été utilisé avec `FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium` ; le téléchargement Playwright était interdit par la politique réseau. Le SDK officiel et Driver.js sont épinglés, avec leurs dépendances verrouillées.

## Commandes

```bash
FRAMATEX_GUIDE_AI_ENABLED=0 FRAMATEX_GUIDE_REAL_AI_TEST=0 PYTHONPATH=. python -m pytest -q
python tools/check_guide_catalog.py
python tools/build_guide_manual.py --check
python tools/evaluate_guide.py
python tools/evaluate_guide.py --simulate --ai-budget 112 --output artifacts/guide-evaluation-simulated.json
for file in tests/*.cjs; do node "$file"; done
for file in static/*.js; do node --check "$file"; done
python tools/check_partner_browser.py
python tools/check_phase3_browser.py
python tools/check_guide_browser.py
python -m pip check
git diff --check
```

Les trois scripts navigateur démarrent leur propre serveur et arrêtent celui-ci à la fin. Ils n’utilisent pas la base de l’environnement courant. Le parcours Guide remplace le fournisseur par une erreur de délai simulée : sa clé factice ne quitte jamais le serveur de test.

## Couverture et preuves

| Contrôle | Preuve | Portée |
|---|---|---|
| Migration additive | `tests/test_partner_migration_backup.py` | Création des six tables absentes, double exécution, données et empreintes préservées, restauration complète |
| Identité, profil, droits et révocation | `tests/test_guide_api.py` | Employés, partenaires distincts, droits modifiés, contexte étranger ou incohérent, compte sans permission, actions inconnues |
| Apprentissage personnel | Même fichier | Progression isolée par propriétaire/version, fin prématurée refusée, préférences, récents, retours minimaux, statistiques admin |
| Défaillances Gemini | Même fichier | IA désactivée, clé absente, fournisseur inconnu, quota, réseau, délai, JSON invalide, action inventée, sortie ambiguë et budget partagé |
| Confidentialité | Même fichier | Aucune question brute ni identifiant de ressource dans le payload Google, aucun texte de question enregistré, champs additionnels rejetés |
| Recherche et raccourcis | `tests/test_guide_evaluation.py`, `tests/fixtures/guide_questions.fr.json` | 122 questions annotées indépendamment des réponses du moteur ; procédures attendues, actions attendues, types permis, refus et clarifications |
| Catalogue et manuel | `tools/check_guide_catalog.py`, `tools/build_guide_manual.py --check` | Identifiants, sources, routes FastAPI, destinations, étapes, marqueurs de composants et synchronisation exacte du manuel |
| Interface partagée | `tests/test_guide_frontend.cjs` et tests existants adaptés | Rendu texte, délégation unique, résolution fermée, ressources locales ; empreinte des fichiers Driver identique au paquet épinglé |
| Navigation réelle | `tools/check_guide_browser.py` | Première connexion, quatre profils, sélecteur d’objet, dossier canonique, cible absente, reprise, passage application/recherche et aide pleine page/application |
| Clavier et affichage | Même script | Flèches avant/arrière, fermeture par bouton et Échap avec pause enregistrée, réduction des animations, absence de débordement et axe sur le panneau à 360, 390, 768 et 1440 px |
| Aucun envoi par la visite | Même script | Aucun document déposé, aucune version fournisseur transmise, aucun fil de discussion client créé par le guidage |
| Non-régression | Suite Python, tests JS, deux anciens parcours Chromium | Commandes, dossiers, versions, fournisseurs, clients, sécurité et migrations existantes |

L’évaluation mesure la procédure en tête, sa présence parmi les trois premières, la pertinence des raccourcis principaux et la validité de toutes les actions résolues. Un refus attendu exige une liste vide. Une demande annotée ambiguë exige une clarification. Chaque question conserve séparément son résultat local et son résultat enrichi, avec profil, résultat attendu, éligibilité, tentative effective, issue et motif de repli. Les latences du mode enrichi comprennent la recherche locale et, lorsqu’il est sollicité, le client ; elles ne mesurent ni HTTP Framatex ni la navigation. Le premier chargement est inclus dans le détail.

Le rapport de schéma 2 fournit `local_full` et `enriched_full` sur le corpus entier, puis `paired_validated` sur les seules réponses du client validées par le même validateur que la production. Les dénominateurs, améliorations, dégradations et résultats inchangés sont explicites. Les questions non sollicitées et les replis locaux ne figurent jamais dans ce sous-ensemble apparié. La couverture compte séparément candidats éligibles, tentatives, réponses validées et replis. `coverage.status=partial` signale notamment une limite du budget d’évaluation, un quota du fournisseur, un délai ou une sortie invalide.

La visite de dépôt entre par les boutons du guide et conserve le scénario 3/4 → Flèche gauche → 2/4. Elle vérifie aussi la cible réellement surlignée, Retour, les flèches dans le champ de titre et le sélecteur, Échap, la pause, la reprise et la fin sans dépôt. Trois sessions sont exécutées par recette, dont deux avec des callbacks de frames retardés de 200 ms pour reproduire la fenêtre de concurrence. Les attentes portent sur le titre, la cible visible et la progression, sans sommeil ajouté pour faire passer une assertion.

Les résultats locaux sont dans `artifacts/guide-evaluation.json` et `artifacts/guide-browser.json`. Les captures `guide-internal.png`, `guide-supplier.png`, `guide-client.png`, `guide-tour.png` et `guide-help.png` montrent uniquement des données synthétiques. La CI collecte ces fichiers et les preuves des anciens parcours.

## Test réel facultatif

Pour le banc d’essai, configurer une **clé réservée à l’évaluation** dans `FRAMATEX_GUIDE_EVAL_API_KEY`, via les paramètres secrets de l’environnement. La clé de production `GEMINI_API_KEY` n’est pas utilisée par cette commande. L’IA de production peut rester désactivée. La commande exacte pour couvrir les 112 questions éligibles du corpus courant est :

```bash
FRAMATEX_GUIDE_REAL_AI_TEST=1 python tools/evaluate_guide.py --gemini --ai-budget 112 --output artifacts/guide-evaluation-gemini.json
```

`--ai-budget` borne le nombre de tentatives dans ce processus d’évaluation uniquement (défaut : 30). Il ne modifie ni ne consomme les compteurs utilisateur/globaux de production. Un quota fournisseur interrompt les tentatives suivantes et reste visible dans les issues des questions restantes. Un budget de 112 permet de solliciter tous les candidats, sous réserve du fournisseur ; il ne garantit pas 112 réponses valides. Aucun appel réel ni gain Gemini n’a été observé pendant cette correction. Le score local de 100 % sur ce jeu fini ne prouve pas une généralisation à des questions nouvelles.

Le test opt-in historique `tests/test_guide_live.py` utilise séparément `GEMINI_API_KEY` et le drapeau réel ; il reste ignoré en CI. Le mode `--simulate` fournit un exemple sans clé ni réseau et reste clairement identifié comme simulé. Voir [cause du défaut et exemple de rapport](FRAMATEX_GUIDE_FIXES.md).

Les contrats de source contrôlent les 43 cibles, mais seuls les parcours critiques sont exercés dans Chromium. Ils ne prouvent pas que toutes les combinaisons de formulaires, états et permissions de chaque visite sont rendues. Le comportement prévu pour une cible conditionnelle absente est une suspension explicite avec reprise et procédure disponible.
