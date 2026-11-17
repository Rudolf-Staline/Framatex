# Grille de recette — consolidation du 17 novembre 2026

Ces résultats sont techniques, sur données synthétiques locales. Ils ne valent
pas validation des règles ni recette des collaborateurs Framatex.

| Parcours / règle | Nature | Vérification technique | Décision / recette Framatex |
|---|---|---|---|
| Une commande, un Dossier Jaune, quatre rubriques | Règle fournie | API, migrations et navigateur | Confirmer avec corpus autorisé |
| Plusieurs lancements, document commun sans provenance inventée | Règle fournie | ACL, recherche, dossier et complétude | Vérifier vocabulaire quotidien |
| Accès commande explicite et restrictions de provenance | Choix technique conservateur | Lecteurs, retrait, source restreinte, anciennes versions | Revoir les habilitations matérialisées par 0025 |
| Création, achats, qualité et réception sans administrateur | Mécanisme demandé | Permissions explicites + parcours synthétique | Attribuer les droits selon responsabilités approuvées |
| Document facultatif / futur / exigible / dispensé | États demandés | Noyau partagé, priorités et compteurs | Configurer les obligations officielles |
| Une obligation par commande ou lancement | Mécanisme, pas règle officielle | Scopes et identifiants d'instance distincts | Définir les obligations par livraison/événement si requises ; aucun tel référentiel n'existe encore |
| Délai depuis création commande ou lancement | Paramètre explicite | Pas de substitution silencieuse de référence | Confirmer événement et échéance de chaque règle |
| Validation d'une version puis nouvelle version / réouverture | Règle fournie | Ancienne décision conservée, nouvelle version non approuvée | Faire réaliser la décision par les rôles métier |
| Publication accessible puis retrait ou révocation client | Règle fournie | Téléchargement réel + complétude | Confirmer destinataires, pièces et durées |
| Fournisseur : demande, correction, approbation, intégration | Parcours approuvé | Isolation et intégration unique | Recette fournisseurs habilités à organiser sans contact automatique |
| Réception hors portail | Parcours demandé | Employé réel, canal et source conservés | Confirmer preuves et procédures d'identification expéditeur |
| Réceptions fractionnées, retour et annulation | Mécanisme demandé | Décimales, unité, idempotence et historique | Définir tolérances/dates ; partiel normal par défaut, pas anomalie automatique |
| Fiche identification et ateliers par lancement | Données historiques + proposition évolutive | Clés stables, conflit et décimales | Confirmer libellés et champs utiles, sans obligation inventée |
| Catalogue de types et « À classer » | Proposition technique évolutive | Alias uniques, originaux conservés, classement explicite | Valider le catalogue ; aucun rapprochement ambigu automatique |
| Commentaire interne par version | Parcours demandé | Auteur/date/ACL ; distinct des décisions | Faire tester simplicité par les services |
| Recherche et pagination | Mécanisme technique | SQL borné, pages et historiques à la demande | Tester sur volume autorisé représentatif |
| Quotas et dépôts parallèles | Paramètres techniques | Réservations, crash, scan et reprise | Dimensionner volume/disque/concurrence sur les serveurs retenus |
| Sauvegarde/restauration | Mécanisme technique | Base neuve, empreintes, versions et décisions | Fixer destination, rétention, RPO/RTO et responsabilités |
| Antivirus/extraction | Qualification externe requise | Refus indisponibilité et limites synthétiques | Installer/qualifier scanner, signatures et vrai corpus |
| Emails | Reprise technique testée avec transport simulé | Baux, échec permanent, état incertain, aucun email réel | Configurer relais et procédure de rapprochement des envois incertains |
| Audit et conservation | Mécanisme technique | Export + empreinte, purge explicite synthétique, révocations indépendantes | Définir délais/autorités ; journal non annoncé immuable |
