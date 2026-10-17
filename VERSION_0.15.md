# Version 0.15 — Migrations SQLite et accès par lancement

Deux chantiers de sécurisation du MVP local (pas encore une homologation de sécurité ni un déploiement Framatex).

## 1. Migrations du schéma versionnées

- `python -m app.migrate status` affiche les révisions enregistrées.
- `python -m app.migrate upgrade` crée ou met à jour le schéma SQLite. Les révisions `0001_baseline` et `0002_launch_scope` sont rejouables et stockées dans `schema_migrations`.
- Sur une base 0.14 existante, les données et historiques antérieurs sont conservés. Lorsqu'une nouvelle colonne est nécessaire, une sauvegarde SQLite datée (`framat.db.backup-YYYY...`) est créée automatiquement avant modification, y compris au démarrage.
- Si un ancien schéma est incomplet ou inconnu, la migration s'arrête au lieu d'ajouter des tables incohérentes. Le prototype ne propose pas encore de migrateur PostgreSQL ni de mécanisme Alembic : **SQLite uniquement**.
- Les nouvelles installations et les installations existantes peuvent démarrer avec la même commande `uvicorn app.main:app` ; la migration s'exécute avant l'ouverture du service.

**Procédure de mise à niveau conseillée :** arrêter le serveur ; copier entièrement le dossier `data/` dans un emplacement de sauvegarde indépendant ; conserver sa clé de session ; remplacer le code ; lancer `python -m app.migrate upgrade` ; vérifier `status` ; exécuter les tests ; puis démarrer le serveur. Conserver également la sauvegarde automatique. Aucun retour arrière automatisé n'est prévu : restaurer le dossier `data/` complet en cas d'échec et remettre la version de code correspondante.

## 2. Autorisations par lancement

- Par défaut, les dossiers existants conservent leur accessibilité par rôle/sous-dossier afin de ne pas couper les utilisateurs lors de la mise à jour.
- Un administrateur peut activer le **mode restreint** pour un dossier de fabrication, depuis le bouton « Gérer les accès » situé dans sa fiche.
- Lorsque ce mode est actif, seuls l'administrateur, le créateur du lancement et les membres nommément autorisés peuvent accéder à ce lancement. Les habilitations habituelles `launch.read`, `document.read`, `document.write` et les droits par sous-dossier continuent à s'appliquer : un membre ne gagne **aucun droit documentaire** du seul fait de son inscription.
- L'administrateur peut accorder ou retirer les accès nominativement. La liste des autorisations et les modifications de statut sont consignées dans le journal d'audit.
- Les vérifications portent aussi sur les téléchargements et les URL indirectes (`doc_id`, `version_id`, `run_id`, `alert_id`, `publication_id`, `request_id`, `notification_id`), sans exposer l'existence d'un lancement auquel un utilisateur n'a pas accès (réponse 404).
- Les dossiers restreints ne figurent pas dans les résultats de recherche, les indicateurs globaux, les actions prioritaires ou les notifications des non-membres.
- Pour que **les nouveaux dossiers soient restreints dès leur création**, configurer `FRAMATEX_RESTRICT_NEW_LAUNCHES=1` dans l'environnement du serveur. Le mode rétrocompatible vaut `0`. Les autres droits restent attribués via les rôles.

### Endpoints administrateur

- `GET /api/launches/{id}/access` — voir mode et membres.
- `PUT /api/launches/{id}/access` — définir `{"restricted":true}` ou `false`.
- `POST /api/launches/{id}/access/members` — ajouter un utilisateur actif (`{"user_id":"..."}`).
- `DELETE /api/launches/{id}/access/members/{user_id}` — retirer son accès.

### Limites explicites

- Les contrôles globaux s'appuient sur la version actuelle de FastAPI et doivent être rejoués après une montée de version du framework.
- L'accès du créateur est implicite en mode restreint et ne peut pas être retiré individuellement dans cette version. Un traitement du départ d'un collaborateur ou du transfert de propriété devra être ajouté.
- Le mode **ouvert** préserve le comportement ancien : il convient d'activer le mode restreint avant d'utiliser des dossiers confidentiels dans un pilote.
- Les permissions ne sont pas encore définies par *type documentaire*, et il n'existe pas de chiffrement au repos, de MFA, de système de quotas ni d'audit de sécurité indépendant. Le contrôle serveur ne remplace pas ces mesures.

## Vérification

`PYTHONPATH=. python -m pytest -q` : 59 tests Python, dont tests des restrictions, des suppressions d'accès, des téléchargements, des anciennes migrations et des sauvegardes. Tous les tests JavaScript du projet ont été exécutés et leur syntaxe vérifiée.
