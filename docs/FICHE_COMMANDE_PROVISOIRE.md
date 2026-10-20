# Fiche commande provisoire

Une commande possède un dossier et quatre sous-dossiers. L'entrée **Commandes** permet de créer, retrouver et modifier ces dossiers. La bibliothèque commune existante reste consultable ; ses documents ne sont pas réattribués automatiquement à une commande.

## Champs

Seul le nom du dossier est requis pour commencer. Numéro de commande, client, atelier, programme / collection, article / modèle, quantité, livraison prévue, ORLI et observations peuvent être complétés plus tard. Ce sont des champs provisoires, pas une liste métier validée par Framatex. Une date manquante n'est pas une anomalie et la fiche ne calcule pas une complétude documentaire.

Le catalogue dans `app/order_fields.py` pilote les formulaires de création, modification et consultation. Les clés restent stables lors des changements de libellés. Les champs supplémentaires sont stockés dans `launches.identification_json` ; un ajout ultérieur au catalogue et au modèle de validation ne demande donc pas de nouvelle colonne. La configuration est actuellement modifiable dans le code, sans écran administrateur.

Les modifications partielles conservent les champs omis ; `null` vide explicitement un champ. Les permissions de lancement et les restrictions existantes s'appliquent aussi à la fiche. Les documents conservent leurs identifiants et versions.

## Mise en service

SQLite : la révision `0006_order_identification` est appliquée par le migrateur existant, avec sauvegarde d'un fichier existant avant l'ajout de la colonne.

PostgreSQL / démo distante : préparer la modification additive avant de déployer ce code sur la base Framatex concernée :

```sh
python -m tools.migrate_order_identification
python -m tools.migrate_order_identification --apply
```

Le premier appel inspecte seulement le schéma. Le second ajoute une colonne `TEXT NOT NULL DEFAULT '{}'` si elle manque. Il est répétable, sans modifier les rôles ni les politiques RLS. Le démarrage PostgreSQL contrôle la présence de la colonne. Aucun changement distant n'est effectué par la préparation de cette branche.

## Suite à préciser

Framatex doit confirmer la liste des champs, leurs valeurs possibles et ceux qui deviennent obligatoires. Le périmètre de l'espace client, son invitation, ses droits et ses informations visibles restent à définir ; la fiche interne ne constitue pas encore un portail client.
