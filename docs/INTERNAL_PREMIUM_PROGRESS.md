# Refonte premium de l'espace interne — suivi

Branche : `design/internal-premium-ux` (base `feat/folder-color-naming`, `f0b064b`), worktree séparé.
Hors périmètre : landing publique (Codex), Espace Client, `main`.
Rapport final : [`INTERNAL_PREMIUM_DESIGN_REPORT.md`](INTERNAL_PREMIUM_DESIGN_REPORT.md).

## Terminé
- Audit de l'identité officielle (framatex.net, Chromium + `getComputedStyle`) : Open Sans, `#003B70`, `#2DAAE1`, `#232323`.
- Skills consultés et installés (Frontend Design, UI UX Pro Max, Impeccable, Taste Skill) ; REA non installé (justification dans le rapport).
- Captures « avant » : `docs/internal-premium-captures/avant/`.
- P0 : Open Sans auto-hébergée (OFL) ; couche `internal-premium.css` / `internal-premium.js` ; menu latéral bleu réductible ;
  barre supérieure en français ; accueil administrateur et accueil technicien sans statistiques ; commandes (filtres repliables,
  tableau) ; fiche commande (actions secondaires regroupées) ; sous-dossiers (en-tête coloré, sélecteur coloré).
- P1 : documents (modales, checklist, dépôt harmonisés par la couche), mémoire métier (repères en ligne, chronologie, filtres
  repliables), habilitations (tableaux et matrice harmonisés), anciens en-têtes alignés (Notifications, Mes actions…).
- Recettes adaptées à l'accueil sans statistiques (mêmes vérifications fonctionnelles, KPI attendus à zéro).

## En cours
- Rien d’inachevé dans P0 et P1 ; restes P3 listés dans le rapport (§ 6 et § 10).

## Problèmes
- framatex.net bloqué par la politique réseau : environnement personnel « Framatex » créé (domaine autorisé, approuvé).
- `validate_document_workspace.py` : 3 échecs déjà présents sur la base `f0b064b` (vérifiés en worktree). Le libellé
  « Sous-dossier Jaune » a été aligné sur le nom officiel « Sous-dossier jaune » ; les 2 autres échecs proviennent de la
  décision « doublon potentiel » désormais exigée au dépôt (comportement métier de la base, hors design).

## Tests
- pytest 209 ; JS 21/21 ; validate_internal_ui, access 15/15, client workflow, business memory 11/11, qa 96/96, demo 135/135 ; document_workspace 7/9 (2 échecs antérieurs). Détail : rapport § 8.

## Limites
- Voir le rapport, § 10.
