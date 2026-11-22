# DOCUMENT INTELLIGENCE — progression

Branche : `feat/document-intelligence`.

## Terminé

- OCR PDF hybride page par page, OCR image et provenance source avec fallback lorsque Tesseract est indisponible.
- Classification explicable alignée sur les 22 exigences du catalogue, avec états clair, probable, multiple, incompatible et impossible, sans score probabiliste inventé et avec confirmation humaine.
- Extraction structurée PDF, Word, Excel et OCR : références, dates, unités, prix, montant et quantités métier distinctes.
- Détection de doublon exact SHA-256, doublon potentiel, nouvelle version et document indépendant; choix humain obligatoire et décision persistée.
- Lecture Excel statique sûre : cellules, en-têtes, feuilles, formules et références invalides, sans macro, lien externe ni recalcul.
- Cohérence interdocuments pour les règles configurées, avec sources, versions, unités, écart, limites et résultat explicite.
- Décisions persistantes `justified`, `to_correct` et `deferred`; une acceptation justifiée n'est pas reproposée tant que la signature de preuve reste identique.
- Comparaison de versions : champs proposés et confirmés, texte significatif, constats/formules Excel et contrôles potentiellement impactés.
- Revérification et notifications internes ciblées à la suite d'une nouvelle version; aucune validation automatiquement transférée.
- Recherche FTS5 dans le contenu analysé, mise à jour à la publication et filtrage final par commande et sous-dossier.
- Parcours navigateur corrigé pour exiger les choix de relation explicites; intention « nouvelle version » préservée depuis le bouton dédié.

## Partiellement terminé / limites déclarées

- Pas de revérification SHA-256 périodique hors dépôt.
- Similarité déterministe texte/références/champs, sans comparaison visuelle perceptuelle des scans.
- OCR et différences textuelles volontairement bornés par les limites de ressources.
- Pas de backfill automatique de l'index FTS pour toutes les anciennes versions antérieures à la migration.
- `non applicable` existe pour les impacts; il n'est pas une décision proposée sur une règle de cohérence chiffrée.
- Adaptation aux permissions `controls.read` et `document.version` à effectuer seulement lors de l'intégration de `feat/access-management`.

## Non commencé car hors périmètre

- Agent IA, chatbot, Ollama, RAG et intégration e-mail.
- Fusion de `feat/access-management` ou modification de `main`.

## Tests exécutés

- Python global : **194 réussis**, 1 avertissement, 0 échec.
- JavaScript global : **19 réussis**, 0 échec.
- Recette API/plateforme : **94/94**, migrations et conservation des données comprises.
- Recette Chromium complète : **133/133**, dont Client A/B, PDF/OCR, Word/Excel, doublons, versions, cohérence, recherche, responsive et stabilité T+60.

## Migrations et reprise

- `0012_document_intelligence` : décisions de rapprochement documentaire.
- `0012b_document_search` : index local SQLite FTS5.
- Ordre d'intégration documenté : ces deux migrations précèdent `0013_access_management` de Claude Code.

## Commits récupérables

- `ec68e65` — doublons et versions guidés;
- `e29d83b` — classification et extraction enrichies;
- `d55da26` — décisions humaines et revérification;
- `cedbad7` — recherche plein texte FTS5;
- `0dbb8ce` — stabilité Chromium et fixture de migration;
- `d8b4aa9` — recette exigeant les choix explicites;
- `7866613` — intention explicite de nouvelle version préservée.

Dernière révision fonctionnelle entièrement couverte par Chromium : `78666136e1da69ad5e084ccfaa8bee3f0cd58f7d`.

## Prochaine tâche précise

Aucune tâche P0/P1 bloquante restante. Après intégration de la branche d'accès, mapper les routes documentaires vers `controls.read` et `document.version`, puis lancer le backfill FTS optionnel des documents historiques si FRAMATEX souhaite les rendre immédiatement recherchables.
