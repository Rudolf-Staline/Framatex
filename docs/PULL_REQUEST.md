## Problème et comportement livré

Les demandes fournisseurs et publications client du socle étaient limitées à des simulations internes. Cette branche ajoute des comptes partenaires isolés, un portail fournisseur avec dépôts versionnés, refus motivé, nouvelle version, approbation et clôture, et l'accès client aux versions explicitement publiées. Elle conserve les données et contrôles existants.

Les commandes matières distinguent les déclarations fournisseurs des réceptions confirmées et des retours. Une file email persistante, avec préférence utilisateur et transport SMTP désactivé par défaut, expose les états réels. Migrations additives, sauvegarde/restauration vérifiée et garde DEMO accompagnent ces parcours.

## Validation

- 74 tests Python réussis (67 avant modifications).
- Tests JavaScript existants et vérifications de syntaxe réussis.
- Parcours fournisseur complet dans Chromium, y compris correction/version 2 et affichage mobile.
- Tests d'isolation deux clients/deux fournisseurs, révocation et publications obsolètes.
- Tests de migration et restauration DB + fichiers sur données synthétiques.
- Transport email testé par fonction contrôlée, aucun envoi SMTP réel.

## Limites et risques

Travail partiel, non prêt pour pilote externe : 76 exigences vérifiées sur 273 (27,8 %), objectif 90 % non atteint. Portail client complet, intégration documentaire fournisseur, réconciliation commande, extensions ORLI/cohérence, scan malware et durcissement opérationnel restent à faire. Administration nouvelle réservée aux administrateurs. Aucune migration PostgreSQL ni déploiement. Les branches alternatives ont été inspectées sans fusion automatique. Aucun changement IA.

Voir IMPLEMENTATION_STATUS.md pour les résultats, le périmètre restant et la reprise ; SECURITE.md et docs/MIGRATIONS_PARTENAIRES.md avant toute mise en service. Cette PR doit rester en brouillon jusqu'à la validation métier et sécurité requise.
