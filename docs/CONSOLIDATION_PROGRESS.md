# Consolidation Framatex — 17 novembre 2026

## Point de reprise
- Départ : `33e7836c1999db1b63331b626f5fa69d50bf193f` (origin/main récupéré le 17 novembre 2026).
- Branche : `consolidation/framatex-2026-11-17` ; arbre initial propre, aucune instruction AGENTS.md trouvée dans /workspace.
- Périmètre : lots 1 à 7 de la mission jointe ; données synthétiques locales uniquement, aucun déploiement, aucune fusion ni contact externe.
- Environnement : Python isolé dans `/tmp/framatex-venv`, dépendances en installation ; capacités serveur réelles inconnues.

## Dépendances et plan
1. Droits commande et contexte documentaire → requêtes, publications, complétude et priorités.
2. Migrations conservatrices → nouveaux contrats et exploitation.
3. Noyau de complétude → priorités et interface.
4. Parcours partenaires/réceptions et permissions → intégration et recette non administrateur.
5. Identification/types/commentaires → gestion quotidienne et guide.
6. Pagination/requêtes, dépôts et exploitation → mesures et restauration.
7. Intégration, suite globale, recette synthétique, documentation et PR.

Chaque responsable tient un compte rendu séparé dans docs/consolidation/ pour éviter les éditions concurrentes. Le présent fichier sera consolidé après vérification centrale.

## État initial
| Lot | État | Preuves / prochaine action |
|---|---|---|
| 1 Modèle, migrations, droits | En investigation | order_accessible dépend encore de tous les lancements ; vérifier scénarios de retrait |
| 2 Complétude/priorités/recherche | En investigation | Deux moteurs présents ; contrats à comparer |
| 3 Fournisseurs/réceptions | En investigation | Modules existants à réutiliser |
| 4 Gestion documentaire | En investigation | Inspecter identification, types et commentaires existants |
| 5 Volumétrie/concurrence | En investigation | Mesurer un corpus synthétique avant correction |
| 6 Exploitation | En investigation | Vérifier sauvegarde, emails, disponibilité et configuration |
| 7 Validation/livraison | À faire | Suite initiale puis régressions ciblées et validation globale |

## Décisions / hypothèses
- Aucun rôle métier sensible accordé implicitement aux comptes existants.
- Les règles et délais officiels ne sont pas supposés validés ; les mécanismes restent configurables.
- Conserver FastAPI, SQLAlchemy, SQLite et l'interface existante ; ne pas annoncer de support PostgreSQL sans preuve.

## Tests et limites
- Pas encore exécutés : installation des dépendances en cours.
- Corpus réel, dimensionnement serveurs, règles officielles et recette Framatex restent des dépendances externes.

## Point de contrôle — implémentation et intégration
- Commits contrôlés : `6d8f7ea` stockage, `43dd687` ACL/contexte, `bcb3979` identification/types/commentaires, `0dcfe31` mesures concurrentes, `bd8f00f` interruption dépôt, `df0a0c7` exploitation, `bf96907` parcours documentaire.
- Référence isolée initiale : **156 passed, 2 skipped** (352,38 s). Le premier essai dans l'arbre partagé avait été contaminé par les modifications de migration pendant exécution ; il ne sert pas de référence.
- Mesure recherche comparable avant/après, lecteur non administrateur, page 25, 3 versions/pièce : **379 → 5 SQL à 100 documents ; 3 079 → 5 à 1 000**, fichiers JSON bruts conservés. Concurrence 2/4 sessions : 36 requêtes, zéro erreur.
- Tests root recherche/commandes/documents : **13 passed**, 47,36 s après isolation de la fixture synthétique MVP. L'ancien fixture module ne réinitialisait pas les rôles et échouait si exécuté après d'autres modules : couverture conservée, base de test réinitialisée.
- Parcours navigateur fournisseur/client complet et Framatex Guide réussis sous Chromium local ; parcours dossier complet réussi après correction d'un import de la nouvelle file et d'une course modal/historique.
- Vérification indépendante exploitation a trouvé une course sur la reprise simultanée des baux email ; correction et tests dédiés en cours avant gel final.
- Pagination annuaires/réceptions/validation et calcul incrémental mouvements implémentés ; mesures et vérification finale partenaires en cours.
- Noyau de complétude partagé et priorités sans lancement implémentés ; tests des budgets et agrégats en cours.

Prochaine étape : réunir les commits restants, figer le code, exécuter la suite globale avec un répertoire temporaire explicite, finaliser rapport/recette, pousser la branche et tenter la PR. `gh auth status` signale actuellement un token GitHub invalide ; aucune PR n'est annoncée.
