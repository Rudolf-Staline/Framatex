# Gestion des collaborateurs et des habilitations — suivi

Branche : `feat/access-management` (base `feat/smart-business-memory-ux`, `6b0eafe`).
Périmètre : comptes, habilitations, administration, personnalisation. Aucune
modification des algorithmes documentaires (OCR, SHA-256, Excel, doublons,
versions, cohérence) dont Codex a la charge sur `feat/document-intelligence`.

## Conception retenue (en cours)

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

## En cours

## Problèmes rencontrés

## Tests exécutés

## Limitations

## Prochaines tâches
