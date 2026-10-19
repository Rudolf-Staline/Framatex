# Mise en service du Dossier Jaune unique — procédure V2

**Cette procédure est un garde-fou. Ne pas appliquer sur la production sans sauvegarde vérifiée et validation des droits.**  
Implémentation sur la PR #21 ; le domaine `framat-demo.vercel.app` n'a pas été modifié par cette branche.

## Réalisé

- Interface authentifiée principale : un Dossier Jaune et **quatre sous-dossiers permanents**.
- Recherche de documents par nom/type/fichier/référence ORLI ; téléchargement des versions.
- Dépôt direct dans une rubrique sans demander de lancement ni de commande ; référence ORLI facultative et modifiable.
- Backend : `global_folders` (quatre lignes) + `global_document_entries` (documents, références ORLI et provenance) ; `global_library_config` uniquement pour le conteneur technique des anciens modules.
- Aucun ID historique, fichier, numéro de version ou circuit de validation supprimé.
- Consultation sécurisée par **deux conditions cumulatives** : permission de la rubrique et permission d'accès héritée de l'ancien lancement. Les documents anciennement restreints ne sont pas ouverts à tous.
- Les anciens dépôts par API sont également indexés dans la bibliothèque ; une référence ORLI issue d'un lancement est actualisée jusqu'à ce que celle du document ait été modifiée manuellement.
- Inventaire en lecture seule : `python tools/audit_dossier_jaune.py`.
- Migration transactionnelle et idempotente : `python -m tools.migrate_global_library` puis `--apply --backup-confirmed`.
- Pour SQLite (pilote local), révision `0004_global_library` intégrée à `python -m app.migrate upgrade`.

## Déroulement pour une copie réaliste

1. Mettre en pause les écritures, imports et décisions de validation le temps de prendre le snapshot cohérent.
2. Sauvegarder séparément **PostgreSQL et les objets du bucket Supabase**, avec preuve de restauration ; ne pas copier de secrets dans les rapports.
3. Restaurer la base et les objets sur une infrastructure **isolée**, configurée avec un domaine, un bucket et un compte de service distincts.
4. Sur cette copie, lancer le diagnostic `DATABASE_URL=… python tools/audit_dossier_jaune.py`. Résoudre tout document orphelin, couleur inconnue et politique d'accès incertaine.
5. Lancer le précontrôle `DATABASE_URL=… python -m tools.migrate_global_library` ; il n'écrit rien.
6. Après vérification de la copie restaurée, appliquer avec `DATABASE_URL=… python -m tools.migrate_global_library --apply --backup-confirmed`.
7. L'upgrade active les politiques **RLS** des trois nouvelles tables PostgreSQL et révoque l'accès direct des rôles Data API ; le serveur doit se connecter via son rôle autorisé.
8. Vérifier les quatre rubriques, le nombre de documents/versions, la présence du même historique, les SHA-256 et les droits en consultation, téléchargement et partage.
9. Sur l'environnement de test, vérifier les scénarios utilisateur : dépôt sans ORLI, référence facultative puis correction, filtre par ORLI, téléchargement des anciennes versions, utilisateur restreint.
10. Faire valider la recette métier et sécurité **avant** toute demande de changement sur la production.

## À garder en tête

Cette V2 est une **migration additive de compatibilité**. L'ancien modèle `launches/folders` reste en base pour les modules non migrés (complétude par lancement, impacts, imports, suivi), mais **l'utilisateur ne crée plus de Dossier Jaune pour un lancement dans le nouveau parcours**. La suppression physique des anciennes tables ou l'abandon complet du conteneur technique relèvent d'une phase de décommissionnement distincte.

En cas de rollback, redéployer uniquement l'ancien frontend n'est **pas suffisant** si des écritures ont été faites après la bascule ; sauvegardes, schéma, objets et watermark d'audit doivent rester cohérents.

## Point restant non démontré

La migration n'a été validée automatiquement que sur **des bases SQLite synthétiques isolées**. Une restauration de la base Supabase réelle n'a pas été faite depuis la conversation. Aucun test sur le bucket réel, aucune migration PostgreSQL réelle, aucun changement de production n'a été exécuté ici.
