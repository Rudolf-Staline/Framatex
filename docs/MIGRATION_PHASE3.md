# Migration et restauration phase 3

Migration SQLite 0021. PostgreSQL reste refusé par le migrateur. Ne pas exécuter sur une base de production dans le cadre de cette mission.

1. Arrêter les écritures et prendre une sauvegarde complète indépendante :
   `python -m app.backup backup /chemin/data /chemin/prive/avant-phase3.zip`.
   Cette commande vérifie l'intégrité SQLite, les clés étrangères et chaque fichier/SHA-256 ; elle produit un manifeste vérifiable.
2. Restaurer vers un **nouveau** répertoire :
   `python -m app.backup restore /chemin/prive/avant-phase3.zip /chemin/copie`.
3. Sur la copie seulement, définir `FRAMATEX_DATA_DIR=/chemin/copie`, retirer tout `DATABASE_URL` pointant ailleurs ; inspecter les rattachements avec `app.order_migration.preflight` sur une connexion SQLAlchemy. Les rattachements incompatibles bloquent la migration. Les lancements sans rattachement sont conservés, sans inférence.
4. Exécuter `python -m app.migrate upgrade` puis `python -m app.migrate status`. Une sauvegarde SQLite supplémentaire est faite par le migrateur. Le changement de nullabilité de `folders.launch_id` utilise une reconstruction transactionnelle SQLite ; les contraintes étrangères sont désactivées uniquement sur la connexion de migration, puis vérifiées avant commit et réactivées, y compris après erreur.
5. Exécuter les tests et vérifier les fichiers avec `app.backup.validate`. Comparer identifiants, versions et liens métier. Répéter la migration : aucune duplication attendue.
6. En cas d'échec, ne pas tenter une migration inverse destructrice. Restaurer l'archive complète vers un autre nouveau répertoire et redémarrer la version précédente contre cette copie. Les sessions de la copie restaurée sont révoquées ; sa clé de session n'est pas sauvegardée.

La sauvegarde automatique du migrateur est uniquement une copie cohérente de la base ; elle ne remplace pas l'archive complète base + fichiers. Aucun fichier n'est déplacé pendant 0021.

Preuve automatisée : `tests/test_order_documents_phase3.py` utilise le schéma SQL exact du commit de phase 2, deux lancements liés, un lancement non lié, des homonymes, une validation, une sauvegarde, une restauration et deux conversions successives. Compléter la répétition sur une copie des données de déploiement avant toute autorisation de production.
