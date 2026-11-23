# FRAMATEX — habilitations et espaces collaborateurs

Branche de livraison : `feat/access-ux-refinement`, issue de `integration/document-intelligence-access` (`a59d8459905b7e7f4f37d1b5c3fa6b7b7ede2db2`). Le SHA distant de livraison est vérifié après le push ; la commande de référence est `git ls-remote origin refs/heads/feat/access-ux-refinement`.

## Livré

| Fonctionnalité | État | Validation |
|---|---|---|
| Matrice par collaborateur, commande et sous-dossier | Terminée | Chromium et tests unitaires |
| Niveaux Aucun accès, Lecture seule, Dépôt sans validation, Responsable, Personnalisé | Terminée | Python, JS, Chromium |
| Droits personnalisés et réouverture des droits enregistrés | Terminée | Python, JS, Chromium |
| Téléchargement et nouvelle version distincts | Terminée | Python, API et Chromium |
| Interface collaborateur adaptée aux droits courants | Terminée | Chromium 1440/390 et suite globale |
| Isolation commande/sous-dossier, recherche, QR et passeport | Préservée | API, Chromium et recette d’accès |
| Dépôt uniquement sans lecture | Non réalisé | Le backend impose actuellement `document.read` ; aucun faux masquage visuel n’a été ajouté |
| Confidentialité par document dans un sous-dossier | Non réalisée | Hors modèle de permissions actuel |

## Choix d’ergonomie et de sécurité

- Chaque cellule de la matrice possède son propre sélecteur ; le préréglage global « Droits des nouvelles cases » a disparu.
- Les préréglages utilisent exclusivement les actions existantes : `document.read`, `document.download`, `document.write`, `document.version`, `document.comment`, `controls.read`, `impact.review`, `value.write`, `quality.review` et `document.review`.
- « Dépôt sans validation » donne uniquement lecture et dépôt. Il ne confère ni téléchargement, ni ajout de version, ni validation, ni contrôles.
- Les cartes des quatre sous-dossiers affichent le niveau effectif de la commande ouverte. Les rubriques interdites n’exposent pas leurs titres de documents, compteurs ni actions.
- Le masquage des boutons complète, sans le remplacer, le contrôle central côté serveur. Les droits retirés sont appliqués dès la requête suivante.

## Fichiers principaux

- `app/access_control.py`, `app/main.py`
- `static/access-admin.js`, `static/brand/access.css`
- `static/app.js`, `static/dossier.js`, `static/brand/dossier.css`
- `tests/test_access_management.py`, `tests/test_access_ux_frontend.cjs`
- `scripts/validate_access_ui.py`, `scripts/validate_client_workflow_ui.py`, `scripts/demo_full_platform.py`

Aucune migration n’a été ajoutée : le modèle d’affectations et les migrations `0012`, `0012b`, `0013` existants sont réutilisés et ont été rejoués sur base temporaire par la recette API et Chromium.

## Résultats réellement exécutés

| Commande | Résultat |
|---|---|
| `PYTHONPATH=. .venv/bin/pytest -q` | 208 réussis, 1 avertissement Starlette externe |
| `node --test tests/*.cjs` | 20/20 réussis |
| `PYTHONPATH=. .venv/bin/python scripts/validate_access_ui.py --output …` | 15 vérifications, 12 captures |
| `PYTHONPATH=. .venv/bin/python scripts/qa_platform_review.py --output …` | 96/96 vérifications |
| `PYTHONPATH=. .venv/bin/python scripts/demo_browser_full.py --output …` | 135/135 vérifications Chromium |

La recette Chromium couvre les largeurs 1440, 1024, 820 et 390 px. Les captures utiles de la matrice sont produites dans `artifacts/access-ux-refinement/access-ui/`, notamment `acces-06-matrice-commande.png` et `acces-12-mobile-matrice.png`.

## Stabilisation de recette

Deux attentes de recette ont été corrigées sans amoindrir les assertions : le scénario Client A/B attend le rendu reconstruit après le changement de statut, et la checklist attend la fermeture de la modale après la réponse du PATCH. La recette complète finale est verte.

## Lancer sous Windows

```powershell
git fetch origin
git switch feat/access-ux-refinement
git pull --ff-only origin feat/access-ux-refinement
.\scripts\start_windows.cmd
```

Le lanceur Windows n’a pas été exécuté dans cet environnement Linux ; les parcours FastAPI et Chromium ont été exécutés sur une base temporaire, sans toucher aux données opérationnelles.
