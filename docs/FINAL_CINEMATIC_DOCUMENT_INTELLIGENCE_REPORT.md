# Rapport final — intégration cinématique et intelligence documentaire

Date : 24 novembre 2026

## Branche intégrée

`integration/cinematic-document-intelligence` réunit :

- `design/cinematic-experience-final` au commit `88336bbd558a2cf7a6e8fc1cc20279c5fb2d188f` ;
- `feat/advanced-document-extraction` au commit `c2ca8ba8be09c0753c960d87c0da850f3d2d1823`.

Les améliorations Three.js, le Dossier Jaune 3D, le tissu textile animé, les connexions et le carrousel sont conservés tels quels. Aucune refonte graphique n'a été ajoutée.

## Moteur documentaire conservé

- Lecture PDF progressive, texte natif prioritaire et OCR local seulement pour les pages qui en ont besoin.
- Limites configurables de taille, pages, texte, durée, mémoire et rendu OCR.
- Provenance par page/cellule, empreinte SHA-256, champs bruts et normalisés, unités, confiance et statut humain.
- Classification explicable, sans décision métier automatique ni divulgation hors habilitations.
- Diagnostics séparés pour PDF protégé, fichier trop volumineux, délai, page illisible, Tesseract absent ou mal configuré et langue OCR absente.

## Correctif de recette

Le parcours « même email déposé deux fois » détectait correctement le doublon, mais sa recette ne confirmait plus explicitement le type documentaire avant le dépôt. La recette Chromium confirme désormais le type proposé, conserve la protection de confirmation humaine, puis vérifie :

1. le doublon exact est visible dans le Dossier Jaune et au tableau de bord ;
2. une décision motivée le marque comme examiné ;
3. la ligne revient à l'état `Présent` sans fausser la complétude.

Tesseract peut également poursuivre en anglais ou en français lorsqu'une seule des deux données de langue est installée ; la langue absente reste indiquée comme limite de lecture. Sans aucune langue utilisable, la lecture OCR reste refusée explicitement.

## Validation

- Tests ciblés documentaire, espace documentaire et habilitations : `42 passed`.
- Recette API globale : `96/96 vérifications réussies`.
- Recette globale Chromium : `135/135 vérifications réussies`.
- Animations et parcours Chromium contrôlés à 1440, 1024, 820 et 390 px, sans erreur JavaScript bloquante ni défilement horizontal.
- Captures de la recette finale : `/tmp/framatex-cinematic-final/captures` (artefacts de validation non versionnés).
