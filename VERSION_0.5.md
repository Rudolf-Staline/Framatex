# Framatex MVP 0.5

## Module A — OCR et extraction structurée
- Lecture locale de texte PDF, Word, Excel, TXT, EML ; OCR de scans/images et PDF scannés quand le moteur est installé.
- Champs candidats : numéro de lancement, référence matière, quantité, date, montant.
- Extrait de preuve et correction humaine avant confirmation.
- Bornes : 20 Mo par fichier, 3 pages PDF analysées, 16 000 caractères, analyse OCR limitée dans le temps.

## Module B — classement documentaire assisté
- Propositions de catégorie et sous-dossier à partir d'indices, sans classement automatique.
- Suggestions restreintes aux sous-dossiers où le collaborateur peut déposer.
- Prévisualisation temporaire effacée après usage ; confirmation explicite du dépôt.

## Vérification
22 tests Python, vérification syntaxique JavaScript. Tests sur données fictives exclusivement.
