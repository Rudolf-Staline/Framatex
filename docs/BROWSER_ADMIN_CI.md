# Administration : diagnostic et validation navigateur

Branche issue de `main` **5d237c98413a6961bc221274783ce3a59fd19ceb** (fusion de la PR nº 37). Vérification publique du 14 novembre 2026, avant modification : les runs [main #235](https://github.com/Rudolf-Staline/Framatex/actions/runs/43402417703/job/131808286484) et [PR #37 #234](https://github.com/Rudolf-Staline/Framatex/actions/runs/43402385001/job/131808173170) sont toujours en échec dans la recette partenaires ; aucun run plus récent n’apparaît. Les journaux détaillés exigent une connexion. Les lignes et sélecteurs historiques proviennent du signalement ; les traces ci-dessous proviennent des reproductions locales.

## Deux défauts de l’application

### Entrée `[data-view=admin]` absente au démarrage

`app.js` est un script `defer`, suivi notamment de `paper.js`. Son initialisation asynchrone démarrait immédiatement : si `/api/auth/me` terminait avant l’évaluation de `paper.js`, l’appel de `paperOpenDeepLink()` échouait. Le `catch` affichait le formulaire de connexion, sans invalider la session.

La reproduction retient la ressource `paper.js`, puis observe le formulaire de connexion. La page est `/`, le compte en mémoire est l’administrateur synthétique et une vérification indépendante de `/api/auth/me` retourne **200**, administrateur actif. Libérer le script ne relance pas l’initialisation ; le clic sur Administration expire après 30 secondes. Le sélecteur est correctement absent de cette vue de connexion.

Preuves : [états et réseau](../artifacts/repro-startup.json), [trace Playwright nettoyée](../artifacts/repro-startup.zip). Le correctif attend `DOMContentLoaded`, après l’évaluation de tous les scripts différés. La recette retient désormais ce même script et vérifie qu’aucune initialisation n’a commencé avant sa libération, puis attend l’accueil réellement monté et vérifie le compte avant le clic.

### Collaborateur `[data-user-access="<id>"]` introuvable après navigation

La confirmation du classement ferme le formulaire, puis recharge le lancement avec `openLaunch()`. La fermeture du formulaire et la persistance API ne garantissent pas la fin de ce rechargement. Un clic sur Administration pendant cette fenêtre ouvre correctement la liste des collaborateurs. Lorsque le rechargement antérieur termine, il remonte le détail du lancement et efface cette liste.

La reproduction retient la réponse finale `/api/launches/<id>/supplier-requests`, clique sur Administration et observe **deux collaborateurs**, dont le suppléant ciblé. Les appels `/api/admin/users`, `/roles`, `/completeness/profiles`, `/impact-rules` et `/approval-templates` répondent **200**. Après libération de la réponse antérieure, la vue passe de `admin` à `detail`, sans perte de session ni échec des API d’administration. Le clic sur le collaborateur expire alors. Le chargement sans protection existait déjà avant la PR nº 37.

Preuves : [états et réseau](../artifacts/repro-navigation.json), [trace Playwright nettoyée](../artifacts/repro-navigation.zip). `openLaunch()` conserve désormais la génération de navigation qui l’a démarré et vérifie qu’elle est toujours courante après chacune de ses deux phases réseau, avant de modifier l’état partagé ou l’écran. Une navigation plus récente invalide les résultats anciens. Le test JavaScript couvre les deux phases et vérifie qu’une ouverture volontaire ultérieure fonctionne toujours.

La recette reproduit aussi cette réponse tardive : elle attend la liste et le collaborateur, libère la réponse, attend sa consommation et vérifie que l’administration reste affichée. Elle ouvre ensuite « Modifier les accès », désactive le suppléant avec le motif prévu, puis confirme via l’API la désactivation, les rôles conservés et le motif dans l’audit. Les parcours fournisseur/client et leurs contrôles existants sont conservés ; aucune permission, route ni frontière de session n’est modifiée.

Les traces contiennent aussi deux refus 422 attendus pour le fichier `.exe` du lot et un refus CSP préexistant de police Google. Ils n’expliquent pas les deux symptômes.

## Validation locale

[Résultats des trois sessions et états observés](../artifacts/admin-browser-validation.json).

| Contrôle | Résultat |
|---|---|
| Référence non modifiée, Chromium système | Deux recettes partenaires complètes réussies ; défauts intermittents sans ordonnancement contrôlé |
| Régressions provoquées avant correction | Entrée Administration absente ; administration remplacée par le lancement ; deux traces d’échec collectées |
| Partenaires après correction, bases/serveurs/contextes neufs | **3/3 réussites**, y compris les deux ordonnancements contrôlés et la désactivation persistée |
| Commandes / Dossier Jaune | Réussite, contrôles métier, mobile et axe conservés |
| Guide | Réussite, profils internes/fournisseur/client/restreint, visites, clavier, reprise et axe |
| Suite Python existante | **156 réussis**, 1 test Gemini réel ignoré, 1 avertissement SQLite préexistant ; ClamAV réel et base EICAR synthétique |
| Nouveau test de nettoyage des traces | **1 réussi** |
| JavaScript | **15 scripts réussis**, syntaxe des scripts statiques valide |
| Catalogue, manuel, évaluations locale/simulée | Réussite, corpus local 122/122, aucun appel réel Gemini |
| Dépendances, espaces Git | `pip check` et `git diff --check` réussis |

La première exécution de Commandes a révélé une autre synchronisation trop faible : immédiatement après le clic Lancements, « Page suivante » pouvait encore appartenir au tableau du journal d’audit. La recette attend maintenant `aria-current="page"` sur Lancements avant de paginer. Elle passe ensuite sans modifier la pagination de l’application.

Commandes principales, dans un environnement avec les dépendances de CI :

```bash
python -m pip install -r requirements-test.txt
npm ci
python -m playwright install --with-deps chromium
python tools/check_partner_browser.py  # répéter dans trois processus neufs
python tools/check_phase3_browser.py
python tools/check_guide_browser.py
FRAMATEX_GUIDE_AI_ENABLED=0 FRAMATEX_GUIDE_REAL_AI_TEST=0 PYTHONPATH=. python -m pytest -q
for file in tests/*.cjs; do node "$file"; done
for file in static/*.js; do node --check "$file"; done
```

## Preuves en CI et limites

Le workflow exécute trois sessions partenaires distinctes et conserve le résultat de chaque échec : une réussite suivante ne remet jamais le statut à zéro. Commandes et Guide s’exécutent aussi après un échec précédent, sauf annulation du run. Il n’y a ni pause fixe ajoutée, ni clic forcé, ni relèvement global des délais. Les retenues réseau sont des vérifications de régression déterministes, libérées selon l’état de l’interface.

Chaque session produit `partner-admin.json` (vue, compte, session publique, erreurs JavaScript, requêtes échouées, statuts HTTP) et `partner-admin.zip`. Le workflow les copie dans `partner-attempt-1/`, `-2/`, `-3/` et les publie dans `browser-evidence`, même en cas d’échec. La collecte commence après les activations et connexions. Aucune sauvegarde de cookies ou de storage state n’est publiée. Les cookies, en-têtes d’authentification, corps réseau, ressources, paramètres d’URL et JWT sont retirés des traces ; captures et sources sont désactivées. Les traces gardent les actions, le DOM et les métadonnées réseau ; l’absence des ressources peut limiter leur rendu visuel. Le test Python vérifie la suppression effective des secrets synthétiques.

Playwright **1.65.0**, Python **3.12.14**, dépendances verrouillées : identiques aux spécifications du workflow. Le navigateur demandé est **Chromium 158.0.8127.18, révision 1254**. La commande d’installation a été tentée, mais `cdn.playwright.dev` répond **403 Domain forbidden**. Les exécutions locales utilisent donc explicitement `FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium`, version **156.0.8078.79**, sur Debian, et Node **24.22.1** au lieu du Node 22 du workflow. Elles établissent les courses et les correctifs, mais ne constituent pas une validation du binaire exact sur le runner GitHub.

L’API `api.github.com` est également refusée par la politique réseau active. La création de PR brouillon et le suivi du nouveau run doivent être confirmés à distance avant fusion. Aucune réussite GitHub Actions sur cette branche n’est revendiquée. Fusion et déploiement restent à la revue.
