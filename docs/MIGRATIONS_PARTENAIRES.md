# Migrations et reprise — phase 2

Migrations SQLite additives, répétables, sans réécriture des tables métier historiques. Le migrateur refuse les révisions inconnues, PostgreSQL et les relations invalides. Les démarrages concurrents sont sérialisés ; les clés étrangères sont activées sur les connexions applicatives.

| Révisions | Ajout |
|---|---|
| 0001–0003 | Socle, portée des lancements, rapports pilote |
| 0004–0006 | Partenaires, livraisons, file email |
| 0007–0008 | Profils/rôles/intégration fournisseur, provenance des champs confirmés |
| 0009–0011 | Commandes client, conversations/pièces jointes, lectures, limiteur partagé, annulations |
| 0012–0013 | Mappings ORLI, décisions de rapprochement, cellules critiques Excel |
| 0014–0015 | Pièces administratives, historique client, rôles historiques conservés |
| 0016–0017 | Conditions de complétude, contexte commande, référentiel multi-lancements |
| 0018–0019 | Délégations/échéances des étapes, centre de notifications partenaires |
| 0020 | Index des événements d'audit pour révocations et génération de sessions |

La migration 0015 attribue un rôle contributeur aux anciens comptes sans affectation afin de préserver les usages existants. Les nouvelles invitations sans rôle explicite sont en lecture seule. Vérifier les habilitations historiques lors de la recette, sans transformation silencieuse des fournisseurs nommés en texte en comptes externes.

Mettre l'application en maintenance sans écrivains avant sauvegarde/migration. La sauvegarde SQLite automatique du migrateur ne remplace pas une archive des fichiers privés.

```bash
.venv/bin/python -m app.backup backup /chemin/donnees /chemin/sauvegardes/framat-unique.zip
.venv/bin/python -m app.migrate upgrade
.venv/bin/python -m app.backup restore /chemin/sauvegardes/framat-unique.zip /chemin/nouvelle-installation
```

L'outil attend `framat.db` et `files/` dans le répertoire source. Un DATABASE_URL SQLite situé ailleurs nécessite une procédure adaptée. L'archive contient un manifeste SHA256 et possède des permissions privées. Intégrité SQLite, relations et empreintes des documents internes, soumissions, pièces jointes et pièces administratives sont vérifiées. La destination de restauration doit être neuve ; les entrées dupliquées, chemins dangereux et empreintes différentes sont refusés.

La restauration invalide les invitations/sessions partenaires et ajoute une nouvelle génération de sessions employés. Même une clé d'environnement inchangée ne réactive pas les JWT précédents. Le secret de session local n'est pas exporté.

Les tests couvrent la copie synthétique d'un schéma 0003 avec compte, lancement restreint, document et version ; migration répétée et concurrente ; absence de perte d'identifiants et d'empreintes ; sauvegarde/restauration des nouvelles familles de fichiers. Ils ne qualifient pas les volumes de production.

Retour arrière : restaurer l'archive pré-migration dans une nouvelle installation avec le code correspondant. Aucun downgrade destructif ni suppression de tables contenant des échanges réels.
