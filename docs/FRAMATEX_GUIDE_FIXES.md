# Correction clavier et évaluation appariée de Framatex Guide

Base : `main` au commit `07e246d`, après fusion de la PR #35. Branche : `fix/guide-keyboard-evaluation`. Le correctif porte sur le guide, son client Gemini partagé, son banc d’essai et leur documentation. Les limites de production restent inchangées. Aucun déploiement ni fusion automatique.

## Cause du retour clavier

Le scénario de référence est [l’étape Chromium du run 43253569099](https://github.com/Rudolf-Staline/Framatex/actions/runs/43253569099/job/131305651770#step:11:1). Son journal API n’est pas accessible dans cet environnement (`api.github.com` refusé).

La commande de CI est `python tools/check_guide_browser.py`. Son premier lancement local a échoué avant le parcours : le Chromium Playwright n’était pas installé, et son téléchargement sur `cdn.playwright.dev` a reçu `403 Domain forbidden`. Le même script a donc été exécuté avec `FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium`, version système 156.0.8078.79. Le navigateur demandé par Playwright est 158.0.8127.18 ; l’identité exacte avec le runner CI reste à vérifier lorsque le téléchargement est autorisé.

Avant toute modification du scénario, le défaut a été reproduit avec le script de `main` en retardant les callbacks `requestAnimationFrame` de 200 ms par une instrumentation Playwright. Le titre affichait « Ajouter une fiche technique · 3/4 », la cible était `order-section-jaune` et le focus se trouvait sur `.driver-popover-close-btn`. L’assertion attendait 2/4 après Flèche gauche, mais obtenait encore 3/4. Aucun champ de saisie ne capturait la touche. L’[extrait de reproduction](../artifacts/guide-keyboard-main-reproduction.txt) conserve ces observations et l’assertion en échec.

Driver.js 1.12.1 crée le titre et le popover dans `drive()` avant le callback de frame qui termine sa transition. Son gestionnaire de Flèche gauche ignore la touche tant que son état de transition est actif, même avec les animations réduites. Le titre visible ne garantit donc pas que ce gestionnaire accepte une touche. Le guide possédait aussi un verrou qui abandonnait une commande reçue pendant un changement d’écran ; une répétition de la recette a exposé la même perte avec deux clics Suivant rapprochés.

Le guide prend maintenant en charge ses raccourcis et utilise une file commune aux boutons et aux flèches. Chaque commande est liée à la visite active et attend la précédente ; elle ne réutilise pas un ancien profil ou une visite terminée. Échap attend la transition en cours avant d’enregistrer la pause. Les champs natifs et éditables gardent leurs flèches, les événements déjà traités et les combinaisons de touches ne sont pas détournés. Le clavier intégré de Driver est désactivé pour éviter une double exécution ; ses ressources livrées restent inchangées.

La recette conserve l’entrée normale par recherche, procédure et « Me montrer comment faire ». Elle vérifie 3/4 → 2/4, la cible surlignée, Retour, la poursuite jusqu’à 4/4, la saisie et le sélecteur, Échap depuis un champ, la pause, la reprise et la fin sans dépôt. Elle répète cette visite dans trois sessions dont deux avec des frames retardées. Les attentes portent sur l’interface et la progression, sans temporisation ajoutée devant une assertion.

## Quotas confirmés sur main

Le corpus inchangé contient 122 questions, dont **112 éligibles** : 81 administrateur, 4 publiques, 15 fournisseur et 12 client. Les principaux synthétiques historiques partagent deux propriétaires : `employee:evaluation` reçoit 85 questions éligibles et `partner:evaluation` en reçoit 27. Avec 30 requêtes par propriétaire et 100 globales par jour, **57 questions** peuvent effectivement atteindre le client, et 55 basculent à cause du budget utilisateur. La borne théorique de 60 ne peut pas être atteinte avec cette répartition.

Ce résultat a été reproduit avec un client simulé et les limites de production ; aucune requête Google n’a été effectuée. L’ancien rapport attribuait au score enrichi des résultats locaux après repli, sans fournir la comparaison appariée qui permettrait d’isoler le modèle.

## Nouveau rapport

Chaque question possède `local`, `enriched`, `eligible`, `attempted`, `outcome` et `reason`. Les issues sont `gemini_validated`, `not_requested` ou `local_fallback`. Les résultats attendus et le profil sont partagés ; le même validateur fermé est utilisé en production et dans le banc.

- `local_full` : score local sur toutes les questions.
- `enriched_full` : score du mode enrichi sur toutes les questions, avec nombres de résultats validés et locaux explicités.
- `paired_validated` : uniquement les questions ayant une réponse du client validée ; scores locaux/enrichis avec dénominateur, améliorations, dégradations et résultats inchangés selon la justesse du choix.
- `coverage` : éligibles, tentatives réelles du client, réponses validées, questions non sollicitées et replis par raison. Un repli empêché par le budget ou un quota indique `attempted=false`, contrairement à un appel échoué.

Le drapeau `--ai-budget` limite seulement les tentatives du processus d’évaluation. Il ne relève pas les quotas de production et ne modifie pas l’environnement serveur ni sa base. Le défaut est 30 ; 112 couvre tous les candidats actuels, sous réserve du fournisseur. Les délais, quotas et réponses invalides restent des replis locaux identifiés et la couverture est marquée partielle. Sans réponse validée, les scores appariés sont `null`, avec un dénominateur de zéro.

### Exemple reproductible, sans réseau

```bash
python tools/evaluate_guide.py --simulate --ai-budget 112 --output artifacts/guide-evaluation-simulated.json
```

Ce client simulé retourne une réponse valide, puis un timeout, un JSON invalide et un quota fournisseur. Le rapport [guide-evaluation-simulated.json](../artifacts/guide-evaluation-simulated.json) donne :

| Mesure | Résultat |
|---|---:|
| Questions / éligibles | 122 / 112 |
| Tentatives / réponses validées | 4 / 1 |
| Non sollicitées, sans candidat ou interdites | 10 |
| Replis locaux / dont après tentative | 111 / 3 |
| Motifs de repli | 1 timeout, 1 réponse invalide, 109 quota |
| Score local complet | 122 / 122 |
| Score enrichi complet | 122 / 122, dont 121 résultats locaux |
| Comparaison appariée | local 1 / 1, enrichi 1 / 1 |
| Améliorées / dégradées / inchangées | 0 / 0 / 1 |
| Couverture validée | 1 / 112, partielle |

Les 109 replis quota comprennent l’appel ayant reçu le quota et les 108 appels suivants évités. Ce rapport ne démontre aucun gain Gemini. Un autre test contrôlé vérifie une amélioration, une dégradation et un résultat inchangé sur trois réponses validées, afin de tester les compteurs appariés.

### Comparaison réelle restant à exécuter

Aucune clé de test n’a été fournie pour cette correction. Aucun appel réel n’est exécuté. Configurer la clé dédiée `FRAMATEX_GUIDE_EVAL_API_KEY` dans les paramètres secrets, puis lancer exactement :

```bash
FRAMATEX_GUIDE_REAL_AI_TEST=1 python tools/evaluate_guide.py --gemini --ai-budget 112 --output artifacts/guide-evaluation-gemini.json
```

L’IA de production reste désactivée par défaut. Une clé de production seule ne permet pas cette évaluation. La CI conserve ses drapeaux à zéro et ne lance que l’évaluation locale et le client simulé. La disponibilité du modèle et les limites réelles du fournisseur restent à qualifier.

## Vérification et livraison

Les captures et les rapports ne contiennent que des données synthétiques. Les commandes de recette exécutées sont :

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

Les exécutables Python provenaient du virtualenv `.venv`. La suite complète utilise ClamAV réel installé dans cet environnement, avec ses chemins de binaire et de bibliothèques ajoutés au processus de test.

La suite globale finale donne **149 tests réussis, un test réel Gemini ignoré et un avertissement de dépréciation SQLite préexistant**. Le groupe d’évaluation de 11 tests passe également. Les trois recettes Guide complètes passent, soit neuf visites de dépôt dont six avec frames retardées. Les parcours existants des commandes/dossiers et des partenaires passent également. Les tests JavaScript, les contrôles du catalogue et du manuel et les dépendances passent ; axe ne signale aucune violation dans les quatre tailles exercées. Voir [guide-browser.json](../artifacts/guide-browser.json).

La branche est poussée sur GitHub. Le domaine `api.github.com` reste refusé par la politique réseau active à l’heure de la vérification. Après autorisation de l’utilisateur, `api.github.com` et `cdn.playwright.dev` ont été ajoutés au brouillon réseau par l’outil de configuration, qui renvoie `requires_publish: true`. Cet outil ne peut pas appliquer le brouillon à la session active. Aucun appel réel Google, déploiement d’application ou fusion n’a été effectué.
