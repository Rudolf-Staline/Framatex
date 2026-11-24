# Suppression documentaire et justification facultative

## Livraison

- Branche : `feat/document-deletion-validation`
- Base effective : `design/landing-final-premium`, qui contient l'historique de
  `integration/document-intelligence-access`. La branche nommée
  `integration/final-premium-design` indiquée dans la demande n'existait ni
  localement ni sur `origin` ; aucune branche `main` n'a été modifiée.
- Migration additive : `0015_document_soft_deletion`, après `0014`.

## Fonctionnalités livrées

| Fonctionnalité | État | Vérification |
|---|---|---|
| Suppression logique de document et version | Terminée | Test API ciblé |
| Motif de suppression facultatif | Terminée | Motif vide et motif renseigné testés |
| Permissions de suppression | Terminée | Administrateur, responsable, déposant propriétaire et lecteur testés |
| Corbeille/restauration administrateur | Terminée | Suppression, liste, restauration et téléchargement testés |
| Masquage des éléments supprimés | Terminée | Téléchargement, complétude, recherche et sources de partage filtrés |
| Confirmation manuelle du type sans minimum de justification | Terminée | Vide et un caractère acceptés, confirmation explicite conservée |
| Recette interface Chromium | Terminée | 4 largeurs, parcours interne et Client, 52 captures |

## API

- `DELETE /api/documents/{document_id}`
- `DELETE /api/document-versions/{version_id}`
- `GET /api/admin/document-trash`
- `POST /api/admin/document-trash/documents/{document_id}/restore`
- `POST /api/admin/document-trash/versions/{version_id}/restore`
- `POST /api/document-versions/{version_id}/identification/confirm`
  accepte désormais une justification vide ou courte. L'action reste une
  confirmation humaine explicite.

## Sécurité et comportement

- La suppression exige toujours `document.read` dans le sous-dossier visé.
  L'administrateur et un responsable ayant `document.review` peuvent supprimer ;
  le déposant doit être l'auteur de la version, disposer de `document.write` et
  ne peut retirer qu'une version non validée.
- La restauration et la corbeille sont réservées à l'administrateur. Les champs
  `deleted_at`, `deleted_by` et `deletion_reason` conservent la trace, complétée
  par l'audit `document.delete`, `document.version.delete`,
  `document.restore` et `document.version.restore`.
- Une source supprimée ne peut plus être téléchargée, affichée dans les listes,
  recherchée, comptée par la complétude, utilisée par les contrôles actifs ni
  servie au Client via une publication historique. Une restauration rend le
  contenu à nouveau consultable sans fabriquer de validation métier.
- Les actions proposées dans la modale suivent les autorisations calculées par
  le backend ; le contrôle serveur reste l'autorité lors d'un appel direct.

## Interface

La modale documentaire présente les actions autorisées seulement, avec l'icône
corbeille. La confirmation contient le nom du document, la version concernée,
un champ « Motif de suppression (facultatif) », Annuler et Confirmer. La
corbeille documentaire est accessible au seul administrateur depuis la
navigation interne.

Capture inspectée :
`/workspace/artifacts/document-deletion-validation/1440-fiche-document.png`
(la modale avec l'action de suppression). Les 52 captures et le résultat
machine sont dans `/workspace/artifacts/document-deletion-validation/` pour la
recette locale.

## Fichiers principaux

- `app/models.py`, `app/migrate.py`, `app/document_deletion_routes.py`
- `app/main.py`, `app/completeness.py`, `app/quality.py`,
  `app/internal_routes.py`, `app/sharing_routes.py`, `app/paper_routes.py`,
  `app/intake_routes.py`, `app/document_intake_routes.py`
- `static/app.js`, `static/document-upload.js`, `static/internal.js`
- `tests/test_document_workspace.py`

## Tests exécutés

| Commande | Résultat |
|---|---|
| `python -m app.migrate upgrade` puis `status` sur une base temporaire | Toutes les révisions, dont 0012, 0012b, 0013 et 0015, appliquées ; rejeu stable |
| `pytest -q` | **211 passed**, 1 avertissement de dépréciation tiers, 56,29 s |
| `node --test tests/*.cjs` | **21 passed**, 0 échec |
| `python scripts/validate_internal_ui.py --output /workspace/artifacts/document-deletion-validation` | **passed**, 1440/1024/820/390, 7 contrôles, 52 captures, 0 erreur JS/API |

## Limites

La recette Chromium couvre le dépôt, la nouvelle version, les contrôles, le
parcours Client et la présence de l'action de suppression dans la modale. Les
autorisations de suppression/restauration et les cas de refus sont validés par
les tests API isolés, sur base temporaire. Aucune base opérationnelle n'a été
utilisée ou modifiée.
