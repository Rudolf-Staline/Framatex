# FRAMATEX — progression habilitations et espaces collaborateurs

Branche : `feat/access-ux-refinement`, créée depuis `integration/document-intelligence-access` à `a59d8459905b7e7f4f37d1b5c3fa6b7b7ede2db2`.

## Terminé — lot P0

- Matrice de commande remplacée : chaque cellule collaborateur/sous-dossier possède son sélecteur indépendant `Aucun accès`, `Lecture seule`, `Dépôt sans validation`, `Responsable` ou `Personnalisé`.
- La copie depuis une autre commande est conservée comme proposition secondaire à confirmer par enregistrement.
- Les droits personnalisés réutilisent exclusivement les actions existantes du catalogue central.
- Le préréglage dépôt ne contient plus `document.version` : une nouvelle version reste un droit distinct.
- L'API de détail de commande expose un niveau lisible calculé à partir des droits effectifs de la commande courante.
- L'interface technicien masque téléchargement et actions non autorisées et affiche le niveau de la rubrique, y compris sur les cartes de sous-dossiers.
- La recette Chromium dédiée valide l'administration à 1440 et 390 px : création de comptes, niveaux individuels, dépôt sans validation, refus de validation et de téléchargement, isolation par commande/sous-dossier, recherche filtrée, révocation immédiate et persistance après redémarrage.

## Validation terminée

- `pytest -q` : **208 passed**, 1 avertissement externe Starlette, 95,48 s.
- `node --test tests/*.cjs` : **20/20** réussis.
- `scripts/validate_access_ui.py` : **15 vérifications**, 12 captures (1440 et 390 px), y compris révocation pendant une session et persistance après redémarrage.
- `scripts/qa_platform_review.py` : **96/96** vérifications API et migrations.
- `scripts/demo_browser_full.py` : **135/135** vérifications Chromium, largeurs 1440, 1024, 820 et 390 px, Client A/B et résilience.
- Le scénario Client A/B attend désormais le rendu frais de la fenêtre après changement de statut ; une attente de checklist attend la fermeture réelle de la modale après le PATCH. Ces deux corrections éliminent des courses de recette sans assouplir les contrôles fonctionnels.

## Fichiers modifiés

- `app/access_control.py`, `app/main.py`;
- `static/access-admin.js`, `static/brand/access.css`, `static/app.js`, `static/dossier.js`, `static/brand/dossier.css`;
- `scripts/validate_access_ui.py`, `scripts/validate_client_workflow_ui.py`, `scripts/demo_full_platform.py`, `tests/test_access_management.py`, `tests/test_access_ux_frontend.cjs`;
- ce document.

## Dernier commit stable

- Lot principal publié : `e78f1991c949801402405c0e26acb9caebde81ca`.
- Lot de validation publié : `aa0725ef0709619844e27dcb3c8b7692b890619f`.
- Rapport de livraison et stabilisation finale : commit et push en cours.
