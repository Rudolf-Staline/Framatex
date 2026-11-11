# Dossier Jaune unique par commande — décision phase 3

Décision R6-02 : « Dossier Jaune global » devient **Dossier Jaune unique par commande**. La décision remplace la représentation historique par lancement, sans supprimer son historique Git.

`BusinessOrder → OrderDossier (UNIQUE order_id) → Folder (UNIQUE dossier_id, slug) → Document → DocumentVersion`.

Les quatre lignes `Folder` canoniques représentent Jaune (technique et commercial), Rose (réception), Bleu (douane), Vert (facturation Framatex). Leurs identifiants sont stables. Les types et exigences restent configurés via les profils de complétude et les circuits existants ; leur validation métier Framatex demeure nécessaire.

`Document.launch_id` est une provenance facultative. Plusieurs documents homonymes et du même type sont indépendants. Chaque lancement lié voit les mêmes rubriques canoniques. Les API `/api/orders/{id}/dossier` et `/api/orders/{id}/documents` permettent le dépôt et le filtre d'origine, sans lancement obligatoire.

Les anciens `Folder` par lancement sont conservés comme identifiants d'archives : `canonical_id` désigne la rubrique cible et ils ne contiennent plus de documents après conversion. Ils ne constituent pas un deuxième dossier. Les documents, versions, signatures SHA-256, dates, auteurs, validations, liens fournisseurs, publications et audits conservent leurs identifiants ; seul `Document.folder_id` change et la provenance est renseignée.

Les lancements non rattachés restent dans un espace historique isolé. Aucune commande n'est déduite d'un nom ou d'une référence. Leur rattachement explicite, par l'administration, transfère les documents vers les rubriques de la commande. Un lancement portant des documents ne peut pas être détaché implicitement : une opération de migration justifiée serait nécessaire.

## Permissions

Les droits de rubrique s'appliquent indépendamment des droits de commande. Pour une commande avec lancements, tous les droits historiques de lancement doivent être satisfaits ; un lancement restreint ne devient pas public par rattachement. Une commande sans lancement est accessible à son créateur, aux membres explicitement enregistrés et aux administrateurs. Les portails externes continuent de n'exposer que les publications et demandes expressément autorisées, jamais le dossier interne.

Un verrou d'écriture sur la commande et les contraintes uniques empêchent les créations concurrentes. Les triggers de migration refusent les dépôts dans une ancienne rubrique convertie et les couples lancement/commande incompatibles.
