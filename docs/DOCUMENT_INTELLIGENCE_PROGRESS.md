# DOCUMENT INTELLIGENCE — progression

Branche de travail : `feat/document-intelligence`, créée depuis `feat/smart-business-memory-ux` (`6b0eafe3713e16f607aadfb3a91724218f4467ca`).

## Terminé
- Analyse initiale des limites : OCR PDF renvoyait uniquement le texte natif dès qu’une page en contenait, ce qui ignorait les pages scannées du même PDF; prétraitement/rotation OCR absent; provenance page absente.
- Architecture actuelle utilise analyse isolée en sous-processus borné, upload hashé, staging et confirmation humaine; ne pas remplacer ces garde-fous.

## En cours
- Renforcer extraction page par page du PDF, OCR et provenance tout en gardant les limites temporelles et de taille.
- Ajouter vérifications ciblées avant les lots suivants.

## Tests effectués
- Inspection statique des modules intake, document intake, quality, routes d’intake, passeport et tests liés.
- Aucun test de cette nouvelle branche encore exécuté.

## Problèmes rencontrés
- Moteur PDF natif/OCR actuel est tout-ou-rien au niveau du document; une seule page avec texte empêche OCR des pages muettes.
- OCR orientation/preprocessing indisponibles dans le chemin image actuel.

## Prochaines étapes
1. OCR multi-page et images avec orientation/prétraitement bornés.
2. Tests synthétiques PDF hybride, multi-page et OCR indisponible.
3. Services de comparaison/version et propositions de doublons exacts/similaires avec choix utilisateur, sans fusion automatique.
4. Résultats cohérence/décisions et ergonomie ciblée, recherche plein texte si réalisable.
5. Recettes navigateur/globales, rapport, commits et push vérifié.

Dernier état récupérable : commit initial de branche `6b0eafe3713e16f607aadfb3a91724218f4467ca`.
