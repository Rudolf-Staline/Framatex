# FRAMATEX — progression habilitations et espaces collaborateurs

Branche : `feat/access-ux-refinement`, créée depuis `integration/document-intelligence-access` à `a59d8459905b7e7f4f37d1b5c3fa6b7b7ede2db2`.

## Terminé — lot P0 en cours de validation

- Matrice de commande remplacée : chaque cellule collaborateur/sous-dossier possède son sélecteur indépendant `Aucun accès`, `Lecture seule`, `Dépôt sans validation`, `Responsable` ou `Personnalisé`.
- La copie depuis une autre commande est conservée comme proposition secondaire à confirmer par enregistrement.
- Les droits personnalisés réutilisent exclusivement les actions existantes du catalogue central.
- Le préréglage dépôt ne contient plus `document.version` : une nouvelle version reste un droit distinct.
- L'API de détail de commande expose un niveau lisible calculé à partir des droits effectifs de la commande courante.
- L'interface technicien masque téléchargement et actions non autorisées et affiche le niveau de la rubrique.

## À vérifier avant livraison

- Tests ciblés des quatre niveaux, modifications immédiates et droits personnalisés.
- Recettes Python, JavaScript et Chromium sur la branche.
- Rapport final et captures de la nouvelle matrice.

## Fichiers modifiés

- `app/access_control.py`, `app/main.py`;
- `static/access-admin.js`, `static/brand/access.css`, `static/app.js`;
- ce document.

## Dernier commit stable

- Base intégrée publiée : `a59d8459905b7e7f4f37d1b5c3fa6b7b7ede2db2`.
