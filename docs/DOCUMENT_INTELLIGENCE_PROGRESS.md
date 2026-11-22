# DOCUMENT INTELLIGENCE — progression

Branche : `feat/document-intelligence`, créée depuis `feat/smart-business-memory-ux` à `6b0eafe3713e16f607aadfb3a91724218f4467ca`.

## Livraison implémentée

- PDF hybride traité page par page : le texte natif est conservé et les pages sans texte passent par OCR. Les résultats d’extraction comprennent page, méthode et extrait source. Prétraitement d’image et tentative de correction d’orientation avec fallback.
- Comparaison d’une version documentaire avec sa précédente : champs structurés analysés et constats Excel, endpoint protégé et accès depuis l’historique de document. Aucune fusion automatique.
- Les analyses OCR et comparaisons de versions continuent de réutiliser les données existantes.
- Rapprochement guidé au dépôt : doublon exact par SHA-256, nouvelle version par références et type compatibles, doublon potentiel par texte normalisé et champs communs. Les références contradictoires empêchent un faux rapprochement de deux documents du même type.
- Choix humain obligatoire lorsqu’un rapprochement est proposé : nouvelle version, nouveau document indépendant, conservation justifiée ou annulation du transfert. La décision, les versions et la preuve sont persistées sans suppression ni fusion automatique.
- Migration additive `0012_document_intelligence`, à appliquer avant la migration `0013_access_management` de la branche Claude.
- Classification alignée sur le catalogue standard, avec états `identified`, `probable`, `multiple` et `impossible`; le nom de fichier reste un indice non décisif et les preuves de contenu restent visibles.
- Extraction distincte des quantités commandée, produite et livrée, ainsi que référence client et montant total. Les localisateurs page PDF, feuille/plage Excel et paragraphe Word sont associés aux propositions et aux valeurs confirmées.
- Lecture Excel bornée : les formules restent exclues de l’extraction de valeurs et sont inspectées séparément, sans macro, lien externe ni recalcul.
- Cohérence enrichie sans remplacer le moteur existant : identité stable par règle/versions/valeurs, résultat technique distinct de la décision humaine, états API explicites (`coherent`, `deviation`, `missing_data`, `ambiguous_sources`, `incompatible_units`, `control_impossible`).
- Décisions persistantes : accepter avec justification, demander une correction ou reporter. Un écart accepté ne peut pas être accepté une seconde fois pour la même signature; une nouvelle version change la signature et réouvre la vérification.
- Revérification ciblée : une nouvelle version ne notifie que les règles de cohérence configurées qui utilisent ce type et ce sous-dossier. Les notifications internes existantes restent filtrées par les droits.
- Comparateur enrichi : valeurs proposées/confirmées avant-après, texte significatif ajouté/retiré, constats Excel et liste des contrôles configurés à revérifier.
- Recherche plein texte FTS5 sur le contenu effectivement analysé et les références extraites. L’index est actualisé à chaque version analysée; les résultats et extraits passent ensuite par les contrôles existants de visibilité de commande et de sous-dossier.
- Migration additive `0012b_document_search`, ordonnée après `0012_document_intelligence` et avant `0013_access_management` lors de l’intégration.

## Résultats vérifiés sur `096c5887e2e5df841dfe38cb38191462da49acf0`

- Python : 188 réussis, 1 avertissement de dépréciation Starlette/httpx.
- JavaScript : 19 suites réussies (`node --test tests/*.cjs`).
- Recette API/plateforme : 94/94.
- Recette Chromium : 133/133, incluant Client A/B, OCR, responsive et stabilité runtime.
- Rapport détaillé et captures : `docs/DOCUMENT_INTELLIGENCE_REPORT.md` et `docs/document-intelligence-captures/`.

## Tests du lot doublons et versions

- `tests/test_document_workspace.py` : 8 réussis.
- `tests/test_intake.py` : 7 réussis.
- Syntaxe `static/document-upload.js` vérifiée par Node.
- Couverture ajoutée : doublon exact renommé, choix manquant refusé, conservation justifiée persistée, version proposée, document indépendant de même type et doublon potentiel conservé séparément.

## Tests du lot classification et extraction

- `tests/test_intake.py` + `tests/test_document_workspace.py` : 17 réussis.
- `tests/test_quality.py` + `tests/test_intake.py` : 14 réussis.
- Syntaxe des interfaces intake et dépôt vérifiée par Node.
- Couverture ajoutée : états de classification, quantités distinctes, provenance Word et Excel, extraction ambiguë préservée.

## Tests du lot cohérence, décisions et revérification

- `tests/test_quality.py` + `tests/test_document_workspace.py` + `tests/test_intake.py` : 23 réussis.
- Syntaxe `static/quality.js` et `static/internal.js` vérifiée par Node.
- Couverture ajoutée : résultat technique maintenu après décision, acceptation non répétable, traitement reporté, invalidation sur nouvelle version, notification ciblée et diff textuel.

## Tests du lot recherche plein texte

- `tests/test_internal_operations.py` + `tests/test_document_workspace.py` : 37 réussis.
- FTS5 disponible dans le runtime SQLite; syntaxe de l’interface vérifiée par Node.
- Couverture ajoutée : recherche d’une expression absente des métadonnées, extrait source, mise à jour à la publication et refus de restitution à un rôle sans lecture du sous-dossier.
- Suite globale : 194 tests Python réussis, 1 avertissement de dépréciation; 19 tests JavaScript réussis.
- Correctif de stabilité Chromium : le mouvement 3D d’une carte s’arrête immédiatement lorsque le pointeur atteint un lien ou un contrôle, afin que la cible du clic ne se déplace plus.

## Partiellement terminé

- Contrôles `not_applicable` : disponibles au niveau des alertes d’impact existantes; pas encore proposés comme décision d’une règle de cohérence chiffrée.
- Comparaison : champs et formules disponibles; diff textuel encore absent.

## Limites de périmètre

Voir le rapport final pour les fonctionnalités avancées restantes : dédoublonnage sémantique, recherche plein texte indexée, comparaison complète de contenu, suivi persistant d’anomalies, analyse périodique d’empreintes, provenance exhaustive cellule/page et calibration de confiance. La livraison est partielle par rapport à une intelligence documentaire avancée complète; les tests verts ne valident pas ces fonctionnalités non implémentées.

## Commits

- `1e08c0e` PDF hybride, OCR et provenance.
- `096c588` comparaison des versions analysées.
- `b64b9bd` rapport du premier état partiel.
- Prochain jalon : classification des 22 catégories et extraction structurée avec provenance.
