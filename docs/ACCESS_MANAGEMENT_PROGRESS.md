# Gestion des collaborateurs et des habilitations — suivi

Branche : `feat/access-management` (base `feat/smart-business-memory-ux`, `6b0eafe`).
Périmètre : comptes, habilitations, administration, personnalisation. Aucune
modification des algorithmes documentaires (OCR, SHA-256, Excel, doublons,
versions, cohérence) dont Codex a la charge sur `feat/document-intelligence`.
Rapport détaillé : [`ACCESS_MANAGEMENT_REPORT.md`](ACCESS_MANAGEMENT_REPORT.md).

## Conception retenue

- Point de contrôle central : `app/access_control.py`
  `can(user, action, folder, launch_id)` — « cet utilisateur peut-il réaliser
  cette action sur ce sous-dossier de cette commande ? ».
- Affectations individuelles : `launch_assignments` (collaborateur × commande ×
  sous-dossier × actions), refus par défaut pour les non-administrateurs.
- Profil collaborateur : `collaborator_profiles` (fonction, mot de passe
  temporaire, révocation des sessions, préférences de notification).
- Migration `0013_access_management` : comptes existants passés en mode
  « affectations », droits hérités présentés au chef comme propositions.

## Terminé

- P0 comptes : création, modification, activation/désactivation, réinitialisation
  (mot de passe temporaire affiché une fois), révocation des sessions, historique.
- P0 mots de passe : Argon2, changement imposé à la première connexion (y compris
  pour un mot de passe saisi par le chef dans l'écran Administration historique),
  changement depuis « Mon compte », sessions antérieures invalidées.
- P0 affectations dynamiques par commande et sous-dossier, 10 actions détaillées,
  préréglages proposés (jamais appliqués sans confirmation), copie depuis une autre
  commande (proposition), affectation groupée.
- P0 isolation : commandes, documents, versions, téléchargements, passeports, QR,
  recherche, tableaux de bord, activité, priorités, notifications, mémoire métier,
  contrôles croisés (Consulter contrôles exigé sur les deux sous-dossiers).
- P0 écrans chef (liste, matrice depuis l'en-tête de commande, habilitations par
  collaborateur, vue globale, droits hérités à vérifier) et écrans technicien
  (Mon tableau de bord, Mes commandes, Mes sous-dossiers, Mon compte, état vide).
- P1 vue globale filtrable ; préférences de notification ; service des destinataires
  autorisés (`app/access_notifications.py`) ; notification interne « nouvelle affectation ».
- Comptes de démonstration : `scripts/seed_access_demo.py` (base isolée uniquement).
- Recette navigateur : `scripts/validate_access_ui.py` (Chromium, 1440 et 390 px).

## En cours

- Rien d'inachevé dans le périmètre P0/P1 livré. Voir « Prochaines tâches » (P2).

## Problèmes rencontrés

- ~200 appels `permitted()` sans commande : résolus par une portée de commande
  (`ContextVar`) posée par le middleware et par `launch_scope()` dans les boucles
  multi-commandes ; sans portée, une action de sous-dossier est refusée.
- Tests historiques reposant sur des comptes « rôle seul » : conservés grâce au
  mode hérité (comptes sans profil, uniquement dans des bases de test anciennes).
- `qa_platform_review.py` créait un collaborateur à droits de rôle : mis à jour
  pour affecter explicitement la commande, et pour vérifier qu'un « membre » sans
  affectation n'a aucun accès (même intention de sécurité, modèle 0013).
- Tesseract absent du conteneur : 2 contrôles OCR de la recette globale échouaient
  (environnement, hors périmètre) ; installé ensuite pour la recette finale.

## Tests exécutés

- `pytest` : 198 réussis (186 existants + 12 habilitations).
- Tests JS (`node tests/*.cjs`) : 19/19 réussis.
- `scripts/validate_access_ui.py` : 15 vérifications, 12 captures, aucune erreur JS.
- Recettes globales : qa_platform_review 96/96, demo_full_platform 135/135,
  validate_internal_ui, validate_client_workflow_ui, business_memory 11/11, document_workspace 9/9.

## Limitations

- Pas d'envoi d'email : préférences et destinataires seulement (pas de SMTP, M365, n8n).
- Pas de lien de réinitialisation par email (le chef réinitialise).
- Le téléchargement est contrôlé ; la copie d'écran ou de texte affiché ne l'est pas.
- Le drapeau « commande restreinte / membres » ne concerne plus que les comptes
  hérités : pour un compte en mode affectations, seule l'affectation ouvre l'accès.

## Prochaines tâches

- P2 : modèles de fonction réutilisables, expiration programmée d'une affectation,
  délégation d'administration limitée, envoi effectif des emails (après choix du canal).
- Intégration Codex : ajouter sa révision à `REVISIONS` et appeler `can()` /
  `recipients()` dans ses nouvelles routes (voir le rapport).
