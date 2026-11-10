# État de livraison — 10 novembre 2026

**Mission partiellement réalisée. Objectif 90 % non atteint. Pas prêt pour pilote externe.**
Branche : `feat/framat-industrialization`, base `845d7de` (main). Aucun déploiement, aucune fusion dans main, aucune donnée réelle, aucun service externe activé, aucun développement IA.

## Avant / après

Avant : socle documentaire, ACL par lancement/rubrique, versions, approbations, complétude, contrôles statiques, imports ORLI, matières et notifications internes. Partages client et demandes fournisseurs limités à des simulations internes.

Ajouts : organisations et comptes partenaires séparés des employés ; invitations et récupération assistée, sessions révocables ; parcours fournisseur dépôt → refus → nouvelle version → approbation → clôture ; messages et preuve de dépôt ; notification interne au créateur ; attribution explicite d'une publication approuvée à un client et téléchargement contrôlé ; commandes matières, déclarations fournisseurs, réceptions partielles confirmées, retours et clés idempotentes ; préférences email, file persistante et worker SMTP désactivé par défaut ; migrations additives 0004–0006 ; sauvegarde DB + fichiers et restauration vérifiée ; garde DEMO ; interface fonctionnelle `/partners` et documentation.

Corrections pendant validation : débordement mobile des empreintes ; format décimal stable des agrégats ; fixture de migration corrigée (la table documents ne possède pas updated_at) ; exclusions explicites des nouvelles tables lors de l'inspection d'un ancien schéma ; noms de sauvegarde automatiques avec microsecondes pour éviter une collision courante.

## Tests réellement exécutés

- État initial : `.venv/bin/python -m pytest -q` → **67 passed**, 1 avertissement Starlette/httpx.
- Régression complète après fonctionnalités : même commande → **74 passed**, 1 avertissement Starlette/httpx, 33,12 s.
- `tests/test_partners.py` : fournisseur, deux organisations fournisseurs, clients isolés, publications retirées/obsolètes, sessions, récupération, expiration, fichiers invalides, commandes avec deux matières, livraisons partielles/retours/idempotence et file email.
- `tests/test_partner_migration_backup.py` : migrations répétables depuis copie synthétique 0003, conservation des comptes/documents/versions/relations, archive vérifiée, restauration vers répertoire neuf, refus d'écrasement et de traversée de chemin, mode DEMO. Dernière exécution ciblée après précision des noms de sauvegarde : **2 passed**.
- Boucle `for file in tests/*.cjs; do node "$file" || exit; done` : réussie.
- Boucle `for file in static/*.js; do node --check "$file" || exit; done` : réussie.
- `.venv/bin/python tools/check_partner_browser.py` : **PASS**, Chromium local, activation/connexion/dépôt/correction/version 2/approbation/clôture, affichage 390 px sans débordement et sans erreur JS fournisseur. Base temporaire et serveur loopback isolés. Capture : `artifacts/partner-browser.png`.
- `git diff --check` : réussi.

Échecs intermédiaires corrigés : assertion mobile du premier passage navigateur ; fixture SQL utilisant updated_at ; assertion décimale 40 contre 40.000. Installation du navigateur Playwright initialement empêchée par le répertoire cache non inscriptible ; Chromium déjà installé a permis le test. Aucun test restant en échec dans les commandes ci-dessus. Aucun test SMTP avec vrai destinataire ni PostgreSQL ni charge/concurrence multi-worker réalisé. Le test de transport email utilise volontairement une fonction contrôlée : il ne constitue pas une preuve d'envoi réel.

## Recette A–H

| Scénario | Résultat |
|---|---|
| A fournisseur | Validé par API et navigateur, y compris correction et clôture |
| B client | Validé par API pour approbation/publication/téléchargement/retrait ; pas de test navigateur client dédié |
| C permissions | Deux clients et deux fournisseurs isolés dans les tests ; pas de certification sécurité globale |
| D commande/réception | Validé API pour plusieurs matières, déclarations distinctes, réceptions fractionnées et retours |
| E changement documentaire | Régressions du socle et invalidation de publication testées ; réévaluation complète des nouvelles pièces partenaires non réalisée |
| F ORLI | Tests existants passent ; extension complète de réimport/conflits et format réel non réalisée |
| G communications | Fil, notification interne et file/reprises vérifiés ; SMTP réel bloqué sans configuration autorisée |
| H restauration | DB + fichiers historiques synthétiques restaurés, empreintes/relations vérifiées ; volume production et toutes familles métiers non certifiés |

## Couverture et restes

`COUVERTURE_FONCTIONNELLE.md` et `docs/requirements.json` : **76 / 273 = 27,8 %**, 158 partiels, 36 absents, 3 bloqués. Décompte conservateur des exigences explicites, sans exclusion des blocages. Aucun résultat accepté formellement par Framatex. La mission ne peut pas être qualifiée d'industrialisation complète à ce stade.

Restent notamment : rôles fournisseurs et domaines emails autorisés ; fiches administratives riches et pièces jointes de messages ; livraison annoncée/prévue avec écarts et annulations plus détaillés ; intégration des pièces fournisseur à la complétude/cohérence internes ; tableau de commandes et clarifications client ; référentiel commande unifié multi-lancements ; recherche avancée/pagination générale ; profils ORLI persistants et gestion complète des conflits ; règles Excel/champs critiques et ressources extraction ; délégations d'approbation ; scan antivirus, quotas, sécurité multi-worker, stockage objet et PostgreSQL. Les demandes historiques et aperçus client du module sharing restent explicitement simulés ; aucune conversion silencieuse.

Autorisations/configurations Framatex nécessaires : organisation documentaire définitive, règles métier/types publiables, fournisseur SMTP et destinataires, format ORLI réel, architecture hébergement/stockage et validation avant exposition externe.

## Reprise précise

1. Installer et tester avec les commandes de `GUIDE_DEPLOIEMENT.md` ; inspecter les derniers commits et la matrice.
2. Priorité P0 : revue indépendante de l'isolation et des uploads, enrichissement des rôles/quotas, suppression des identifiants manuels dans l'UX, tests navigateur client et réceptions.
3. Raccorder les pièces fournisseurs approuvées à des versions documentaires internes sans perdre auteur externe, empreinte, décisions ni historique ; ensuite intégrer complétude et cohérence.
4. Finaliser les commandes/client/clarifications ; résoudre le modèle par commande sur validation métier avant toute migration globale.
5. Compléter ORLI/conflits, contrôles/extraction et approbations, puis exécuter la recette A–H élargie. Actualiser les statuts seulement avec preuve d'acceptation exécutée.
6. SMTP : configurer seulement après autorisation, utiliser d'abord un serveur de test sans vrais contacts ; superviser les états processing ambigus et les cinq échecs maximum.

## Livraison Git

Commits séparés pour audit, portail, restauration/DEMO, livraisons, communications et documentation. Brouillon de description dans `docs/PULL_REQUEST.md`. Résultat de publication Git/PR consigné ci-dessous après tentative.

Résultat Git : branche poussée avec succès sur `origin/feat/framat-industrialization`. Création de PR tentée avec `gh pr create --draft --base main --head feat/framat-industrialization --title 'Portails partenaires : parcours fournisseur, publications contrôlées et réceptions' --body-file docs/PULL_REQUEST.md` ; refus de l'API : `Post "https://api.github.com/graphql": Forbidden`. La PR n'a donc pas été créée. Lien de création : https://github.com/Rudolf-Staline/Framatex/pull/new/feat/framat-industrialization . Description prête dans `docs/PULL_REQUEST.md`. Aucun refus d'auto-approbation, aucun déploiement ou merge tenté.
