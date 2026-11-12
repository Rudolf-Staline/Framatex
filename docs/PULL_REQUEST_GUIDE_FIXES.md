## Retour clavier et synchronisation

Dans la visite « Ajouter une fiche technique », Flèche gauche pouvait laisser l’utilisateur à 3/4. Driver.js affiche le titre avant la frame qui termine sa transition, puis ignore les flèches tant que cette transition est active. Le défaut a été reproduit avant modification du scénario avec une frame retardée de 200 ms : le focus était sur le bouton de fermeture, la cible était la rubrique Jaune, et l’assertion 2/4 obtenait encore 3/4.

Le guide gère ses raccourcis dans la même file de commandes que les boutons. Les commandes reçues pendant un chargement ne sont plus abandonnées ; une commande d’une ancienne visite ne s’applique pas à la suivante. Échap enregistre la pause après la transition en cours. Les champs de texte, sélecteurs et éléments éditables gardent leurs flèches. Le clavier intégré de Driver est désactivé pour éviter la double exécution ; les fichiers du fournisseur restent inchangés.

La recette conserve l’entrée par recherche → procédure → « Me montrer comment faire ». Elle vérifie 3/4 → 2/4, la cible réellement surlignée, Retour, la poursuite jusqu’à la fin, la saisie, Échap depuis un champ, la pause et la reprise sans dépôt. Trois recettes complètes ont passé : neuf visites de dépôt dont six dans des sessions aux frames retardées. Les assertions portent sur l’interface et la progression.

## Comparaison local/Gemini

Sur main, 112 des 122 questions ont des candidats. Les identités synthétiques regroupent 85 questions éligibles sous un propriétaire employé et 27 sous un propriétaire partenaire. Avec les quotas de production par défaut, 57 questions atteignent effectivement le client et 55 basculent en local ; la borne de 60 n’est pas atteinte avec cette répartition.

Le nouveau rapport conserve, pour chaque question, le résultat local et le résultat enrichi, l’éligibilité, la tentative effective, l’issue et la raison du repli. Il donne les deux scores sur le corpus complet et une comparaison appariée limitée aux réponses Gemini validées, avec dénominateurs et nombres améliorés/dégradés/inchangés. Les replis ne figurent jamais dans le score apparié du modèle.

`--ai-budget` borne les tentatives du processus d’évaluation, sans modifier ni consommer les limites de production. Le même validateur fermé est partagé avec la production. Une clé distincte `FRAMATEX_GUIDE_EVAL_API_KEY` et `FRAMATEX_GUIDE_REAL_AI_TEST=1` sont nécessaires pour un appel réel ; la clé de production seule ne suffit pas. La CI utilise uniquement les modes local et simulé.

Exemple reproductible du client simulé, avec un succès, un timeout, un JSON invalide puis un quota :

| Mesure | Valeur |
|---|---:|
| Corpus / éligibles | 122 / 112 |
| Tentatives / réponses validées | 4 / 1 |
| Non sollicitées / replis locaux | 10 / 111 |
| Replis après tentative | 3 |
| Score local complet / enrichi complet | 122/122 / 122/122 |
| Résultats locaux inclus dans l’enrichi complet | 121 |
| Apparié : local / enrichi | 1/1 / 1/1 |
| Améliorées / dégradées / inchangées | 0 / 0 / 1 |
| Couverture | 1/112, partielle |

Les replis sont 1 timeout, 1 réponse invalide et 109 quotas, dont 108 appels évités après le premier quota. Cet exemple ne mesure aucun gain réel. Un test contrôlé supplémentaire vérifie les compteurs avec une amélioration, une dégradation et un résultat inchangé parmi trois réponses validées.

## Vérification

```bash
FRAMATEX_GUIDE_AI_ENABLED=0 FRAMATEX_GUIDE_REAL_AI_TEST=0 PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m pytest -q tests/test_guide_evaluation.py
for file in tests/*.cjs; do node "$file"; done
for file in static/*.js; do node --check "$file"; done
python tools/check_guide_catalog.py
python tools/build_guide_manual.py --check
python tools/evaluate_guide.py
python tools/evaluate_guide.py --simulate --ai-budget 112 --output artifacts/guide-evaluation-simulated.json
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_guide_browser.py
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_phase3_browser.py
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium python tools/check_partner_browser.py
python -m pip check
git diff origin/main --check
```

La suite globale finale donne **149 tests réussis, un test réel Gemini ignoré et un avertissement SQLite préexistant**. Les 11 tests d’évaluation passent, ainsi que les tests JavaScript, les contrôles catalogue/manuel et les trois recettes Guide complètes. Les deux parcours Chromium existants passent aussi ; axe ne signale aucune violation aux quatre tailles vérifiées. L’état de GitHub Actions est consigné dans le rapport lié ci-dessous.

## Vérifications externes restantes

Aucune clé de test n’a été fournie ; aucun appel Google réel n’a été effectué. Après configuration de `FRAMATEX_GUIDE_EVAL_API_KEY`, la commande exacte est :

```bash
FRAMATEX_GUIDE_REAL_AI_TEST=1 python tools/evaluate_guide.py --gemini --ai-budget 112 --output artifacts/guide-evaluation-gemini.json
```

La reproduction locale utilise Chromium système 156.0.8078.79. Le Chromium Playwright 158.0.8127.18 n’a pas pu être téléchargé tant que `cdn.playwright.dev` est interdit. Le journal du run de référence et l’accès à GitHub Actions sont également bloqués par l’interdiction active de `api.github.com`. Les domaines ont été sauvegardés dans le brouillon réseau après autorisation de l’utilisateur ; l’outil indique qu’une publication de configuration est requise pour les activer. Aucun résultat distant n’est présumé.

Voir le [rapport de correction](https://github.com/Rudolf-Staline/Framatex/blob/fix/guide-keyboard-evaluation/docs/FRAMATEX_GUIDE_FIXES.md), la [reproduction sur main](https://github.com/Rudolf-Staline/Framatex/blob/fix/guide-keyboard-evaluation/artifacts/guide-keyboard-main-reproduction.txt) et l’[exemple JSON](https://github.com/Rudolf-Staline/Framatex/blob/fix/guide-keyboard-evaluation/artifacts/guide-evaluation-simulated.json). Aucun déploiement ni fusion automatique.
