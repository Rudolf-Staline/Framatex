# Migration et restauration phase 3

Migrations SQLite 0021 (dossiers), 0022 (séquences de validation et notifications par commande), 0023 (contexte de complétude par commande). PostgreSQL reste refusé par le migrateur. Ne pas exécuter sur une base de production dans le cadre de cette mission.

1. Arrêter les écritures et prendre une sauvegarde complète indépendante :
   `python -m app.backup backup /chemin/data /chemin/prive/avant-phase3.zip`.
   Cette commande vérifie l'intégrité SQLite, les clés étrangères et chaque fichier/SHA-256 ; elle produit un manifeste vérifiable.
2. Restaurer vers un **nouveau** répertoire :
   `python -m app.backup restore /chemin/prive/avant-phase3.zip /chemin/copie`.
3. Sur la copie seulement, définir `FRAMATEX_DATA_DIR=/chemin/copie`, retirer tout `DATABASE_URL` pointant ailleurs ; inspecter les rattachements avec `python -m app.migrate preflight`. Les rattachements incompatibles bloquent la migration. Les lancements sans rattachement sont conservés, sans inférence.
4. Exécuter `python -m app.migrate upgrade` puis `python -m app.migrate status`. Une archive complète base + fichiers avec manifeste vérifié est créée automatiquement avant conversion du schéma documentaire historique ; une copie SQLite supplémentaire est aussi créée. Le changement de nullabilité de `folders.launch_id` utilise une reconstruction transactionnelle SQLite ; les contraintes étrangères sont désactivées uniquement sur la connexion de migration, puis vérifiées avant commit et réactivées, y compris après erreur.
5. Exécuter les tests et vérifier les fichiers avec `app.backup.validate`. Comparer identifiants, versions et liens métier. Répéter la migration : aucune duplication attendue.
6. En cas d'échec, ne pas tenter une migration inverse destructrice. Restaurer l'archive complète vers un autre nouveau répertoire et redémarrer la version précédente contre cette copie. Les sessions de la copie restaurée sont révoquées ; sa clé de session n'est pas sauvegardée.

La copie `.backup-*` ne remplace pas l'archive complète `.phase3-*.zip`. Les deux restent privées et doivent être conservées hors du dépôt. Aucun fichier n'est déplacé pendant 0021. Un fichier historique absent ou une empreinte incorrecte bloque l'archive et donc la conversion ; corriger la copie à partir d'une sauvegarde fiable, sans fabriquer de pièce de remplacement.

Preuve automatisée : `tests/test_order_documents_phase3.py` utilise le schéma SQL exact du commit de phase 2, deux lancements liés, un lancement non lié, des homonymes, une validation, une sauvegarde, une restauration et deux conversions successives. Compléter la répétition sur une copie des données de déploiement avant toute autorisation de production.

0022 reconstruit transactionnellement `approval_runs` et `internal_notifications` : les anciennes lignes reçoivent la séquence 1 ; identifiants, décisions, délégations et dates restent inchangés. Une réouverture crée une nouvelle ligne et révoque la publication de la version concernée, sans supprimer de validation historique. 0023 est additive.
