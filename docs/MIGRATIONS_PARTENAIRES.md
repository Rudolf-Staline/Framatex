# Migrations et reprise

- 0004_partners : organisations, comptes, jetons, demandes, versions, événements, attribution des publications.
- 0005_partner_deliveries : lignes matières et mouvements partenaires.
- 0006_partner_mail : file email et préférences.

Migrations SQLite additives, répétables, conservant les tables, identifiants, fichiers et ACL historiques. Les anciens fournisseurs/clients nommés en texte ne sont pas automatiquement convertis en comptes. Aucune migration du Dossier Jaune global n'est appliquée. Le migrateur refuse PostgreSQL et les révisions inconnues.

Mettre l'application en maintenance sans écrivains avant sauvegarde et migration. Le migrateur produit une sauvegarde SQLite avant mise à niveau d'une base versionnée ; cela ne remplace pas une copie des fichiers.

```bash
.venv/bin/python -m app.backup backup /chemin/donnees /chemin/sauvegardes/framat-unique.zip
.venv/bin/python -m app.migrate upgrade
.venv/bin/python -m app.backup restore /chemin/sauvegardes/framat-unique.zip /chemin/nouvelle-installation
```

Le script de sauvegarde attend `framat.db` et `files/` dans le répertoire source. Un DATABASE_URL SQLite personnalisé avec autre emplacement doit être traité séparément. L'archive possède un manifeste SHA256 ; intégrité SQLite, relations et empreintes des documents sont vérifiées. La restauration refuse une destination existante et les chemins dangereux. Les sessions/invitations partenaires restaurées sont invalidées. Le secret de session employé n'est pas exporté ; configurer le secret de la nouvelle installation selon la politique de reprise.

Retour arrière : maintenir l'archive pré-migration et restaurer dans une nouvelle installation avec le code correspondant. Ne pas supprimer les nouvelles tables contenant des échanges réels. Pas de downgrade destructif automatique. Les tests utilisent une base synthétique 0003 avec compte, lancement restreint, dossier, document et version ; ils vérifient la conservation et la restauration.
