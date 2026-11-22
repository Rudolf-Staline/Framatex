# DOCUMENT INTELLIGENCE — progression

Branche : `feat/document-intelligence`, créée depuis `feat/smart-business-memory-ux` à `6b0eafe3713e16f607aadfb3a91724218f4467ca`.

## Livraison implémentée

- PDF hybride traité page par page : le texte natif est conservé et les pages sans texte passent par OCR. Les résultats d’extraction comprennent page, méthode et extrait source. Prétraitement d’image et tentative de correction d’orientation avec fallback.
- Comparaison d’une version documentaire avec sa précédente : champs structurés analysés et constats Excel, endpoint protégé et accès depuis l’historique de document. Aucune fusion automatique.
- Pas de migration nouvelle; les données d’analyse existantes sont réutilisées.

## Résultats vérifiés sur `096c5887e2e5df841dfe38cb38191462da49acf0`

- Python : 188 réussis, 1 avertissement de dépréciation Starlette/httpx.
- JavaScript : 19 suites réussies (`node --test tests/*.cjs`).
- Recette API/plateforme : 94/94.
- Recette Chromium : 133/133, incluant Client A/B, OCR, responsive et stabilité runtime.
- Rapport détaillé et captures : `docs/DOCUMENT_INTELLIGENCE_REPORT.md` et `docs/document-intelligence-captures/`.

## Limites de périmètre

Voir le rapport final pour les fonctionnalités avancées restantes : dédoublonnage sémantique, recherche plein texte indexée, comparaison complète de contenu, suivi persistant d’anomalies, analyse périodique d’empreintes, provenance exhaustive cellule/page et calibration de confiance. La livraison est partielle par rapport à une intelligence documentaire avancée complète; les tests verts ne valident pas ces fonctionnalités non implémentées.

## Commits

- `1e08c0e` PDF hybride, OCR et provenance.
- `096c588` comparaison des versions analysées.
- Le commit du rapport et des captures, puis le SHA de la branche publiée, sont communiqués dans la réponse finale.
