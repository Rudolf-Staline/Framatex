# Plan de migration — 4 rubriques globales

**Statut : préparé, non exécuté.** Départ : modèle par lancement (`launches → folders → documents → document_versions`). Arrivée : Dossier Jaune unique → quatre catégories communes → documents. L'application actuelle continue de fonctionner sur l'ancien schéma tant que les API et les garde-fous d'accès n'ont pas basculé.

## Objectifs vérifiables

- **Zéro perte** d'ID document, version, validation, commentaire, historique, empreinte ou objet stocké.
- **Zéro élargissement d'accès** sans validation de l'administrateur (règle de non-régression des droits).
- **Zéro fusion** automatique des documents même si leurs noms, empreintes ou références ORLI sont semblables.
- **Zéro dépendance obligatoire à ORLI** pour le dépôt, la consultation ou la modification d'une métadonnée.
- Une reprise **répétable et traçable**, sans suppression de tables historiques à cette étape.

## Phase 0 — Audit, lecture seule

Exécuter `python tools/audit_dossier_jaune.py` **sur une copie de la base** ou sur une connexion de lecture seule appropriée. Le programme n'effectue aucun `UPDATE`, `DELETE`, `INSERT` ou `DDL` et affiche uniquement des agrégats. Il ne suffit pas pour diagnostiquer les relations indirectes ; examiner aussi la matrice de droits.

Inventaire exigé :
- nombre de `launches`, `folders`, `documents`, `document_versions`, `approval_runs` et `approval_decisions` ;
- répartition des anciens dossiers par `slug` et nombre de documents sans référence `launches.orli_ref` ;
- lancements restreints, pièces rattachées, statut des comptes et autorisations existantes ;
- documents orphelins, sous-dossiers de couleur inconnue, doubles catégories à résoudre ;
- toutes les tables et API portant une notion `launch_id`, `folder_id` ou une attribution par lancement ;
- manifeste de stockage : clés objet / noms disque / tailles / SHA-256 (à vérifier sur les fichiers, distinctement des métadonnées).

## Phase 1 — Sauvegarde indépendante et restauration témoin

Sauvegarder la base PostgreSQL de façon cohérente ; capturer une copie chiffrée et vérifiée du stockage privé de versions ; vérifier l'accès aux deux sauvegardes. Restaurer sur un environnement isolé et ouvrir un échantillon de pièces réparties entre les quatre couleurs (dont plusieurs versions d'une pièce et une approbation). Ne pas considérer le backup terminé sans essai de restauration.

## Phase 2 — Schéma additif PostgreSQL, migration versionnée

Le SQL ci-dessous est **une esquisse**, pas un script applicable en production :

```sql
-- À transformer en migration PostgreSQL versionnée après inspection effective du schéma.
CREATE TABLE dossier_jaune (
    id TEXT PRIMARY KEY,
    CHECK (id = 'framat-ex-unique')
);
CREATE TABLE global_folders (
    slug TEXT PRIMARY KEY CHECK (slug IN ('jaune','rose','bleu','vert')),
    label TEXT NOT NULL
);
-- Dans documents, ajouter des colonnes nullable temporairement :
-- global_folder_slug TEXT REFERENCES global_folders(slug)
-- orli_ref TEXT NULL
-- Document d'origine : table document_legacy_origin document_id / launch_id / folder_id / old_orli_ref / batch_id.
-- Ne pas supprimer folder_id, folders, launches, ACL, ni les autres FKs historiques.
```

Le code doit choisir de façon stable l'identité du singleton et insérer exactement les quatre lignes de `global_folders` via une migration idempotente. Une contrainte d'unicité s'applique à la couleur, **pas à la référence ORLI**.

## Phase 3 — Copie des rattachements et identification des ambiguïtés

Pour chaque `documents.id` existant :
1. remonter `documents.folder_id → folders.slug, folders.launch_id → launches.id` ;
2. vérifier que `slug ∈ {jaune, rose, bleu, vert}`, sinon **arrêt/quarantaine** ;
3. écrire un `global_folder_slug` déterministe, conserver l'ancien `folder_id` et `launch_id` dans le registre de provenance ;
4. suggérer la référence `launches.orli_ref` lorsqu'elle existe, **sans écraser** une valeur document plus précise ; en cas de désaccord, demande d'arbitrage ;
5. conserver exactement `documents.id`, `document_versions.id`, `number`, `disk_name` et `sha256`. Pas de déplacement des objets binaires ;
6. journaliser `batch_id`, horodatage, nombre d'enregistrements et anomalies.

Une référence ORLI identique sur plusieurs documents est attendue et **ne constitue pas un doublon**.

## Phase 4 — Sécurité : blocage de l'extension de droits

**Bloquant principal.** Aujourd'hui, les restrictions par lancement sont évaluées dans `app/access.py` et les rôles/sous-dossiers dans `app/main.py`.

- Établir une matrice `user × document` de consultation et téléchargement sur la copie avant migration.
- Maintenir une couche de contrôle d'accès par provenance des documents anciens tant que la politique cible n'est pas formellement validée.
- Pour toute pièce issue d'un lancement `restricted`, ne pas attribuer automatiquement des droits plus larges au motif qu'elle rejoint le sous-dossier commun.
- Rejouer les tests d'accès sur API, URL directe, recherche, téléversement, QR, partage client, exports, assistant et liens de versions.
- Reprendre et auditer les pièces publiées à des clients ; la référence ORLI ne prouve ni propriété ni autorisation.

## Phase 5 — Compatibilité des fonctions existantes

Recenser et modifier séparément :
- `/api/launches`, création, métadonnées et dépôt documentaires ;
- garde `app/access.py` et vérifications `document.folder.launch_id` ;
- complétude (`launch_completeness`, règles et validations), écarts métier, simulations, notifications, validations, ORLI, matière, Excel, historique, partage client/fournisseur ;
- frontend `static/app.js`, `static/approvals.js` et autres fonctions spécialisées, assistants et exports.

Les analyses par référence ORLI doivent être formulées comme **des recherches et vues de regroupement** ; en l'absence d'ORLI, elles doivent fonctionner selon des associations explicites ou indiquer honnêtement qu'un périmètre manque.

## Phase 6 — Contrôles avant/après, sur copie représentative

| Vérification | Acceptation |
|---|---|
| Documents | Ensemble des `documents.id` inchangé |
| Versions | Ensemble des IDs, nombres, métadonnées, empreintes inchangé |
| Validation | Même nombre d'étapes/décisions et mêmes références `document_version_id` |
| Stockage | Manifeste des objets réconcilié ; un échantillon de binaires re-haché |
| Couleurs | 100 % des documents courants rattachés à l'une des quatre couleurs |
| ORLI | Valeur facultative, partagée entre pièces, corrigible et auditée |
| Sécurité | Aucun document précédemment interdit n'est devenu visible |
| Fonctions | Import, recherche, téléchargement, OCR, Excel, notifications et validations testés |
| Retour arrière | Démarrage de l'ancien code sur le jeu restauré, sans perte |

Exiger un relevé des écarts et la signature du responsable métier/sécurité avant la mise en production.

## Phase 7 — Bascule et rollback

1. Prévoir une fenêtre de maintenance avec gel des **écritures documentaires**, validations, imports ORLI, publications et traitements asynchrones.
2. Faire une dernière sauvegarde et relever le watermark d'audit (date/ID).
3. Appliquer le schéma et la reprise contrôlée ; exécuter la recette technique et métier.
4. Promouvoir la nouvelle application seulement après tests et contrôle des permissions.
5. Garder anciens identifiants, schéma, données et objets sauvegardés pour restauration. En cas d'échec, remettre l'ancienne application et sa base/restauration **ensemble**. Une simple promotion Vercel n'annule **pas** une migration de base.
6. Si des écritures ont lieu après la bascule, un rollback nécessite d'abord une stratégie de réconciliation ; ne pas décréter le retour sans tenir compte de ces écritures.

## Points non résolus

1. Correspondance des quatre rubriques avec les documents réels, typologies et exceptions.
2. Politique cible de sécurité des anciennes pièces restreintes par lancement.
3. Référence ORLI provisoire/définitive, ambiguïtés et éventuel cas de références multiples pour un seul document.
4. Politique de conservation et de purge des anciens lancements ; **pas de purge dans ce plan**.
5. Périmètre et conditions de publication externe des documents.

**Interdiction d'exécuter la migration en production à ce stade.** Ce fichier documente la préparation, pas une autorisation de changement de données.
