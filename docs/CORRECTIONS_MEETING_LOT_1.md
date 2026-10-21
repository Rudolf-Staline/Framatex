# Corrections du meeting — premier lot

## Livré

La sidebar reprend la teinte de l’échantillon fourni le 21 octobre : `#FFF9DF`. Arial, le fond blanc des espaces de travail et le retrait de la colonne Livraison prévue sont conservés.

### Pièces attendues

Le contrôle documentaire existant est désormais visible depuis la liste des commandes : pièces manquantes, pièces en attente de validation ou règles non définies. Il ne modifie pas le statut manuel du dossier. Sans profil, le système ne prétend pas que le dossier est complet.

Dans chaque sous-dossier, une ligne donne accès aux exigences paramétrées. Les comptes ne voient que le bilan autorisé par leurs accès. Les types de documents attendus restent configurés dans un profil et affectés explicitement à la commande.

### Commentaires et repères PDF

Une icône de commentaire ouvre les échanges internes du document. Chaque commentaire conserve son auteur, sa date et la version concernée. Un repère de page est facultatif pour les PDF ; le serveur vérifie que cette page existe. Le remplacement d’un fichier conserve les commentaires sur leur ancienne version.

La lecture exige l’accès au dossier et au sous-dossier. L’ajout exige aussi le droit de modification. Ces commentaires ne sont pas exposés au portail client. Ce lot fournit des commentaires avec repère de page, sans dessin ni surlignage sur le PDF.

### Réceptions partielles

Une comparaison peut être configurée en mode « Commande et cumul des réceptions partielles ». Le document A porte la quantité commandée ; les documents B portent les réceptions. Seules leurs dernières versions sont prises en compte.

- Un cumul inférieur à la commande est présenté comme une réception partielle avec un solde attendu.
- Un dépassement au-delà de la tolérance produit un écart à examiner.
- Une valeur manquante, des unités différentes, une quantité négative ou des fichiers justificatifs identiques empêchent un cumul silencieux.
- Une nouvelle version ou une réception ajoutée renouvelle les preuves : une ancienne décision ne s’applique pas automatiquement au nouveau constat.

Les règles d’égalité déjà configurées conservent leur comportement. Le cumul est réservé aux quantités totales, jamais aux prix ni aux consommations unitaires. Retours et annulations demandent un traitement distinct.

## Migration

Ajouts : table `document_comments` et colonne `cross_document_rules.comparison_mode`, avec défaut `equality` pour les règles existantes. Aucune donnée historique n’est supprimée.

SQLite applique la révision `0008_meeting_corrections`. Pour PostgreSQL :

```sh
python -m tools.migrate_meeting_corrections --apply
```

La table des commentaires reste inaccessible aux rôles publics Supabase : RLS activée, privilèges retirés à `PUBLIC`, `anon` et `authenticated`. Le serveur applique les droits métier existants.

## Vérifications

110 tests Python et 32 vérifications JavaScript réussis. Parcours Chromium : couleur exacte, accès aux exigences, commentaire échappé et persisté, formulaire mobile, configuration du cumul et exemple 100 commandées / 40 reçues / 60 attendues. Les données de démonstration restent locales.

## Suite identifiée

Les autres points des échanges restent à traiter par lots : rapprochement avec le dossier technique client, alertes sur antécédents client/atelier et amélioration de l’OCR avec vérification humaine. Leur présence dans cette liste ne signifie pas qu’ils sont entièrement intégrés. L’espace fournisseur reste reporté ; les règles documentaires réelles restent à valider avec Framatex.
