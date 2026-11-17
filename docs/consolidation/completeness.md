# Lot 2 — complétude et priorités

## Constats confirmés et corrections

À partir de `33e7836`, le moteur commande réimplémentait partiellement le moteur lancement : absence des dérogations historiques, test de publication réduit à `status=published`, facultatif/futur affiché manquant, et conversion silencieuse d'un délai `days_after_launch` en délai après création de commande. Les priorités parcouraient uniquement les lancements et produisaient des identifiants identiques pour plusieurs obligations de la même règle.

`app/completeness.py` constitue désormais le noyau commun ; `order_completeness.py` est un adaptateur qui ajoute les profils historiques des lancements et déduplique par `obligation_key`. Les huit états sont : non applicable, facultatif, non encore exigible, manquant exigible, validation en attente, publication en attente, satisfait et dérogation. Les noms API historiques `present/rows` et `ready/items` restent disponibles.

Les dérogations historiques restent limitées à leur lancement. La nouvelle table `order_requirement_exceptions` permet une dérogation de commande sans lancement ; aucune ancienne dérogation n'est élargie par migration. Les décisions restent liées à la version courante ; les circuits d'approbation priment sur une simple validation d'exigence. Une dérogation conserve auteur, date et justification ; son retrait est audité. Elle ne compte jamais comme présence d'un document.

La publication réutilise `partner_routes.visible_publication` avec un compte client actif, doté de `read`, autorisé par le domaine de son organisation, une publication effective et un fichier présent. Statut nominal, publication obsolète, compte désactivé, retrait et destinataire inaccessible ne suffisent pas. Les titres des publications internes sont aussi filtrés par le droit documentaire de provenance.

## Contrats et migration

La révision `0029_requirement_scope` ajoute :
- `RequirementPolicy.obligation_scope` : `context` par défaut, `order`, `launch` ;
- `RequirementPolicy.deadline_reference` : `launch_created` par défaut historique, `order_created` uniquement sur choix explicite ;
- `order_requirement_exceptions`, sans conversion ni suppression de décisions existantes.

Le défaut `context` suit l'attachement du profil : commande ou lancement. Une obligation de commande utilise une pièce commune sans lancement de provenance. Une obligation de lancement utilise uniquement les pièces de ce lancement. Ainsi une pièce commune ne satisfait pas plusieurs obligations propres à des lancements différents. Le choix est une mécanique conservatrice et configurable, pas une règle officielle imposée à Framatex. Les profils déjà attachés aux lancements conservent leur portée dans la vue commande.

`days_after_launch` conserve son nom API pour compatibilité ; l'événement est maintenant explicite dans la configuration et la réponse. Sans lancement de référence, un délai historique reste non exigible avec `deadline_reference_missing=true`. Il faut choisir explicitement `order_created` pour un délai lié à la création de commande. Les formulaires et le guide expliquent ce choix.

`business_rules_confirmed` vaut désormais `null` et `business_rules_status=not_recorded` : l'application ne dispose d'aucune attestation officielle vérifiable. Ce n'est ni une validation inventée ni une affirmation que Framatex aurait rejeté les règles. Une confirmation métier reste externe.

Les preuves de chaque obligation sont limitées à 20 références dans la réponse ; `document_count` et `documents_truncated` explicitent cette limite. Les originaux et historiques complets restent conservés dans les routes documentaires. Le noyau joint seulement la version courante et charge les revues/circuits/intégrations en groupe, sans parcourir toutes les versions.

## Priorités et droits

Les commandes sans lancement participent au calcul. Les obligations communes sont dédupliquées et les actions propres aux lancements sont conservées. Seules les obligations exigibles non dispensées apparaissent ; les destinations comprennent commande et rubrique sans créer de lancement fictif. La fermeture des lancements est respectée ; un lancement inaccessible ne supprime pas une obligation commune accessible. Les sources, preuves et clarifications des exigences, alertes et engagements sont contrôlées avant toute projection. Le tableau de bord utilise les mêmes clés et filtres d'exigibilité.

## Vérification exécutée

Avec `/tmp/framatex-venv/bin/python`, uniquement données synthétiques locales :

```
PYTHONPATH=. python -m pytest -q tests/test_consolidation_completeness.py tests/test_completeness.py tests/test_completeness_phase2.py tests/test_workspace.py tests/test_order_documents_phase3.py tests/test_approvals.py tests/test_approval_phase2.py tests/test_sharing.py
```

27 tests passés avant ajout du test de budget. Le test supplémentaire de budget a ensuite passé séparément. Contrôle guide : 34 tests passés, 1 ignoré (guide réel optionnel), avant le dernier ajustement d'agrégat/chargement groupé. JavaScript : syntaxe orders/workspace/partners contrôlée ; tests workspace historique et navigation commande sans lancement passés.

Mesure isolée `test_completeness_batches_current_versions_and_bounds_evidence_payload` : même commande, même règle avec validation, 10 puis 200 documents, 2 versions par document et approbation de la version 2. Requête HTTP complète de complétude : **18 instructions SQL dans les deux cas**, références de preuve renvoyées **10 puis 20**. TestClient local/SQLite ; un passage par taille, aucune revendication de p95 ou de capacité serveur réelle. Avant correction, inspection du moteur confirmait chargement de toutes les versions et contrôles par candidat ; aucun chiffre avant strictement comparable n'est revendiqué.

## Limites explicites

- Cardinalités implémentées : commande et lancement, qui existent dans le référentiel. Aucune obligation documentaire de livraison/événement n'a été inventée ; la définition et le rattachement de ces obligations restent à valider avant extension.
- Une commande n'a pas de statut de clôture autonome dans le schéma actuel ; le filtre d'actions considère les lancements tous clôturés, sans assimiler arbitrairement la phase « clôture » à une décision de fermeture.
- Le calcul d'un rapport de complétude lit les métadonnées courantes des candidats ; il n'est pas une preuve de dimensionnement pour un nombre illimité de règles/commandes. Les références JSON sont bornées et le budget SQL n'augmente plus par document dans le scénario mesuré.
- Le corpus réel et la validation officielle des règles restent externes.

Dernier contrôle après les ajustements de verrou de dérogation, de source d'engagement et de publication groupée : `tests/test_consolidation_completeness.py tests/test_completeness_phase2.py` → **6 passés**. Les cinq nouvelles régressions passent aussi ensemble, dont le contrôle de budget SQL. Les pièces du corpus de budget sont des métadonnées synthétiques, sans extraction ni scan réel.
