# Landing finale premium — progression

Branche : `design/landing-final-premium` (depuis `feat/folder-color-naming`).

## Terminé

- Audit ciblé des fichiers de landing, des assets locaux, des tests et du comportement animé existant.
- Navigation institutionnelle bleu FRAMATEX, avec menu mobile cohérent.
- Direction typographique éditoriale limitée à la landing : serif système à fort contraste pour les titres, DM Sans conservée pour le texte fonctionnel.
- Section « Notre solution » raccordée à la photographie réelle d’équipe disponible localement, en AVIF/WebP/JPEG, sans génération d’image.

## En cours

- Vérification Chromium aux largeurs 1920, 1440, 1024, 820 et 390 px.
- Ajustements visuels et tests de non-régression.

## Limites connues

- L’environnement bloque l’accès public à `framatex.net` et à Motives International (erreur de tunnel 403) : aucune police ni ressource externe n’a été copiée.
- Aucun fichier distinct correspondant à `banner-17.jpg` n’était joint. La photographie d’équipe déjà présente dans les assets FRAMATEX est utilisée à la place.
