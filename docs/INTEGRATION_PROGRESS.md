# FRAMATEX — progression de l'intégration

Branche : `integration/document-intelligence-access`.

## Sources vérifiées

- Intelligence documentaire : `feat/document-intelligence` à `fa34cf43f468da5021868e1ee8b7184b678a5024`.
- Gestion des accès : `feat/access-management` à `33aae76d3ad73aa55b3d985e28552309b0ed9f18`.

## Travail terminé

- Têtes distantes récupérées directement depuis GitHub.
- Branche d'intégration créée depuis la dernière révision documentaire.
- Fusion Git réelle de `feat/access-management` dans la base `feat/document-intelligence`, publiée à `a277195`.
- Migrations réunies dans l'ordre `0012_document_intelligence`, `0012b_document_search`, `0013_access_management`.
- Le dépôt guidé et le dépôt direct d'une nouvelle version exigent désormais `document.version`.
- Les confirmations OCR et valeurs extraites exigent `value.write`, séparément du dépôt.
- Comparaisons, rapprochements, doublons, cohérence, inspections Excel et alertes exigent `controls.read` sur toutes leurs sources.
- La recherche FTS reste filtrée par commande et sous-dossier avant de restituer titre, référence ou extrait.
- Les notifications documentaires respectent affectations, actions nécessaires et préférences internes.
- L'interface utilise les capacités de la commande courante pour téléchargement, commentaire, version, comparaison et confirmation de valeur.

## Conflits résolus

- `app/migrate.py` : conservation des modèles et migrations des deux branches dans l'ordre attendu.
- `tests/test_business_memory.py` : fixture historique conservée avec une borne explicite avant `0011`.

## Fichiers modifiés depuis le merge

- Backend : contrôle d'accès documentaire, alertes, notifications et capacités de commande.
- Interface : `static/app.js`, `static/internal.js`, `static/intake.js`.
- Tests : `tests/test_access_management.py`.
- Documentation : ce fichier.

## Tests exécutés

- Sécurité ciblée Codex + Claude : **36 réussis**, 1 avertissement, 0 échec.
- Scénarios d'accès dynamiques seuls : **13 réussis**, 1 avertissement, 0 échec.
- JavaScript global : **19 réussis**, 0 échec.
- Couverture ajoutée : dépôt sans version, confirmation sans valeur, contrôle masqué, alerte masquée, téléchargement séparé et recherche FTS confidentielle.

## Erreurs restantes

- Suites Python globales, migrations isolées et recettes API/Chromium intégrées encore à exécuter.

## Prochaine action

Commit/push du lot de sécurité, puis validation des migrations et recettes globales.

## Dernier commit stable

- Merge récupérable distant : `a2771952a9f890f9b8e4c3c16329841fbfc3fddf`.
