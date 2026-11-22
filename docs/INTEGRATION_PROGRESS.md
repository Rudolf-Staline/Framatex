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
- Python global intégré : **207 réussis**, 1 avertissement, 0 échec.
- Recette API/migrations : **96/96** sur base vierge puis copie historique, rejeu et conservation des données.
- Recette Chromium globale : **135/135**, Client A/B, FRAMATEX, documentaire, responsive et runtime T+60.
- Recette Chromium habilitations : **15/15**, trois techniciens, révocation immédiate, URL directes, persistance après redémarrage et 12 captures.

## Erreurs restantes

- Aucune erreur critique connue. Le lanceur Windows natif reste non exécutable depuis cet environnement Linux; ses tests unitaires et le démarrage Uvicorn équivalent sont validés.

## Prochaine action

Créer le rapport final et publier les captures intégrées utiles.

## Dernier commit stable

- Sécurité documentaire intégrée distante : `89a398b2f97efba1d650429b5ecd0c9f037fc013`.
