# Dossier Jaune unique par commande et consolidation phase 3

La documentation et les documents étaient encore organisés par lancement, malgré le référentiel de commandes. Cette branche introduit un dossier canonique unique avec quatre rubriques par commande : plusieurs lancements partagent les mêmes rubriques, les documents gardent leur origine facultative et plusieurs pièces homonymes restent indépendantes.

## Modifications

- Modèle `OrderDossier`, rubriques canoniques, provenance documentaire, alias d'archives et droits de commande conservateurs ; routes historiques compatibles sans élargissement des ACL.
- Dépôt, versions, intégration fournisseur, recherche, contrôles, complétude, notifications, partage client et QR adaptés au propriétaire commande.
- Réouverture motivée en nouvelle séquence par version, décisions historiques conservées, invalidation contrôlée des approbations et publications, concurrence testée.
- Résolution ORLI avec candidats, critères, divergences, décision motivée, empreinte de snapshot et audit ; aucune écriture vers ORLI.
- Vérification/extraction en processus bornés, quota privé et verrou interworkers, collisions sans perte de fichier, nettoyage en erreur ; adaptateur ClamAV réel testé sur EICAR.
- Navigation métier, recherche/tri/pagination, états et confirmations, erreurs réseau et doubles soumissions, focus clavier et contrastes. Parcours navigateur et axe intégrés à GitHub Actions sur PR et `main`, avec dépendances verrouillées.

## Migrations et restauration

0021 reconstruit les rubriques SQLite pour leur propriétaire commande, conserve les anciens identifiants en alias et change uniquement les références documentaires nécessaires. Aucune association de commande n'est inférée d'un texte similaire. Les rattachements incompatibles bloquent la conversion et les lancements non liés restent isolés.

0022 préserve les circuits/décisions existants en séquence 1 et permet de nouvelles séquences. 0023 ajoute le contexte de complétude par commande. Une archive complète vérifiée précède la conversion documentaire historique. Répétition sur le schéma exact de phase 2 et restauration vérifiées. Procédure détaillée : [MIGRATION_PHASE3.md](MIGRATION_PHASE3.md).

## Validation et limites

Les commandes et résultats définitifs sont dans [RAPPORT_PHASE3.md](RAPPORT_PHASE3.md), avec les preuves JSON navigateur et les rapports de tests. Corpus synthétique et bases temporaires uniquement ; pas de modification de base de production, de déploiement ni de fusion automatique.

Couverture honnête : **264/273 (96,7 %)**. Les quatre rubriques restent partielles pour leur validation métier Framatex ; l'extraction attend un corpus réel ; N-09 reste partiel, car le moteur ClamAV a été testé avec une base EICAR synthétique et non une base complète maintenue. N-05, N-06 et N-07 restent bloquées. Voir [SECURITE_PHASE3.md](SECURITE_PHASE3.md).

## Risques à examiner

- Migration SQLite en maintenance, sauvegarde indépendante et répétition sur une copie des données de déploiement avant toute autorisation.
- Une commande comportant un lancement restreint exige l'accès à tous ses lancements : certains accès précédemment publics peuvent devenir plus stricts.
- Le détachement d'un lancement portant des documents est refusé pour éviter un déplacement documentaire implicite.
- Budget privé par défaut de 1 Gio ; antivirus désactivé explicitement dans la configuration de démonstration, à configurer `required` avec signatures à jour en exploitation.
- La CI est configurée pour PR/main ; son exécution distante n'est pas présentée comme observée sans retour de GitHub.
