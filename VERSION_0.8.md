# Framatex MVP 0.8 — Emails et engagements

Date : 17 octobre 2026

## Innovation 1 — archivage sans impression

- Import volontaire d’un fichier `.eml` de 20 Mo maximum.
- Conservation du fichier intégral comme document versionné du sous-dossier Rose.
- Métadonnées conservées : objet, expéditeur, destinataires, copie, date brute et identifiant Message-ID.
- Aperçu du corps `text/plain` uniquement, avec taille maximale ; pièces jointes conservées dans le fichier source et répertoriées sans extraction automatique.
- Respect des droits sur le dossier Rose et traçabilité du dépôt.

## Innovation 2 — registre des engagements

- Propositions lexicales locales à partir d’un email archivé ; aucune création automatique.
- Confirmation de la formulation, du responsable, de la date et des conditions par un utilisateur disposant du droit `commitment.review`.
- Statuts : en attente, réalisé, reporté, annulé ; mises à jour accompagnées d’une justification et historisées.
- Liaison permanente de chaque engagement au courriel d’origine et au lancement concerné.
- Les dates relatives ne sont pas interprétées automatiquement.

## Sécurité et limites

- Accès aux courriels et engagements réservé aux lecteurs du sous-dossier Rose.
- La lecture d'une boîte Gmail/Outlook, l'envoi automatique et l'extraction en masse restent hors périmètre.
- Les pièces jointes ne sont pas ouvertes/exécutées côté serveur, et le HTML n'est pas rendu comme contenu actif.
- Les en-têtes des emails et les promesses peuvent être falsifiés ; validation humaine nécessaire.
- Le prototype local n'est pas homologué pour des communications réelles de Framatex.

## Validation

Les tests de cette tranche couvrent l'import, le rattachement au lancement, les pièces jointes, les propositions, les actions humaines, les permissions et la protection des endpoints de mutation.
