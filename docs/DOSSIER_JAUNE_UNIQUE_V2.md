# Framatex — cadrage V2 : Dossier Jaune unique

**État : validé comme principe de conception, à faire valider formellement par Framatex avant une reprise en production.**  
**Date : 19 octobre 2026.**  
**Périmètre : spécification et préparation seulement ; aucun schéma ou fichier de production modifié.**

## 1. Organisation et vocabulaire

```text
Framatex
└── Dossier Jaune (unique)
    ├── Jaune — Technique
    ├── Rose  — Réception
    ├── Bleu  — Douane
    └── Vert  — Facturation
```

- Il existe exactement **un** Dossier Jaune et **quatre sous-dossiers**, permanents, à l'échelle de l'entreprise.
- Les documents d'une couleur sont **déposés ensemble**, sans arborescence par lancement, commande ou client.
- Les lancements et commandes restent des objets **métier** et des **critères de recherche** ; ils n'engendrent aucun répertoire.
- Un document porte un identifiant stable, un titre, un type et **une référence de lancement / ORLI facultative et éditable**. Plusieurs documents peuvent partager la même référence et une référence vide est légitime.
- La mise à jour de ORLI ne déplace aucun fichier, ne modifie ni son empreinte ni ses versions et déclenche un événement d'audit.
- Ne pas fusionner des pièces qui ont le même nom ou la même référence : l'identité documentaire est indépendante d'ORLI.
- Une validation s'applique à **une version précise** ; toutes les étapes et décisions restent consultables.
- Le dossier unique ne signifie **pas** que chaque utilisateur lit toutes les pièces. Les permissions par rubrique, type et opération sont contrôlées côté API et au téléchargement.

Les dénominations Jaune/Technique, Rose/Réception, Bleu/Douane et Vert/Facturation sont celles du projet en cours ; elles restent à confirmer sur des exemples métier de Framatex.

## 2. Exigences fonctionnelles modifiées

| Code | Comportement cible |
|---|---|
| DJ-01 | Un seul point d'entrée « Dossier Jaune » ; aucune création libre de dossier principal |
| DJ-02 | Quatre sous-dossiers immuables ; dépôt direct dans l'un d'eux |
| DJ-03 | Recherche globale par nom, type, date, catégorie, référence ORLI et état de validation |
| DJ-04 | ORLI facultatif à la création, ajout et correction après coup avec audit |
| DJ-05 | Une même valeur ORLI peut servir de filtre transverse à plusieurs sous-dossiers, sans constituer un dossier |
| DJ-06 | Versions, originaux, empreintes, décisions de validation et liens de téléchargement intacts |
| DJ-07 | Droits effectifs par utilisateur, rôle, sous-dossier, type et opération, y compris par URL directe |
| DJ-08 | Les modules OCR, Excel, incohérences, complétude, notifications, impact, partage et assistant sont adaptés au modèle global |
| DJ-09 | Les tableaux de bord montrent des situations réelles ; leur « complétude » n'est calculée que pour un périmètre documentaire explicite |
| DJ-10 | Aucune exposition automatique de documents anciennement soumis à restriction par lancement |

### Écrans

Accueil : quatre rubriques réelles, recherche et documents récents/actionnables.  
Dans une rubrique : tableau des documents (nom, type, date, référence ORLI, version, validation, action).  
Détail d'un document : versions et historique de métadonnées, ORLI facultatif, circuits de validation, provenance de migration masquée aux utilisateurs courants.  
Le filtre ORLI est une **vue** transversale et jamais un cinquième sous-dossier.

## 3. Données cibles proposées

- `dossier_jaune` : singleton logique de l'entreprise, pas une collection par lancement.
- `global_folders` : 4 lignes uniques, identifiées par `jaune`, `rose`, `bleu`, `vert`.
- `documents` : ID historique conservé, nouveau `global_folder_id` pendant la transition, ORLI nullable et non unique.
- `document_versions` : IDs, numéros, `disk_name`, `sha256`, métadonnées et liens de validation inchangés.
- `document_legacy_origin` : `document_id`, ancien `folder_id`, ancien `launch_id`, ORLI précédent, lot/date de migration.
- `launches`, `folders` et toutes les tables `*_launch_id` historiques **conservées** pendant la transition. Les références de lancement restent consultables dans un registre métier/archives si nécessaire.

**Attention :** la migration proposée est additive ; le code existant ne sait pas encore utiliser ce nouveau modèle. Ne pas appliquer seulement le changement de schéma et considérer la fonctionnalité livrée.

## 4. Portée et arbitrages

Le rôle « Administrateur » reste initial ; les autres rôles sont configurés. Les anciennes restrictions par lancement ont un sens plus étroit que la nouvelle bibliothèque commune : la transition **ne peut pas** les remplacer par un droit de lecture global sans arbitrage. Les pièces provenant de lancements restreints restent non exposées jusqu'à mise en place d'une protection équivalente et validation explicite.

ORLI : on ne déduit pas silencieusement une référence certaine d'un lien ambigu. En cas d'absence ou de conflit, conserver l'origine et laisser le champ vide ou proposer une résolution humaine documentée. La liaison ORLI ne crée pas de sous-dossier.

Le portail client, s'il est validé ultérieurement, ne voit que les documents explicitement publiés pour son périmètre ; la présence d'une valeur ORLI ne vaut jamais autorisation de publication.

## 5. Écarts techniques constatés

Au commit production examiné `add439954d494cc189d886fc32dcf56de79ca1a4` :

- `app/models.py` : `folders.launch_id → launches.id` (unicité `launch_id, slug`) ; `documents.folder_id → folders.id` ; `document_versions.document_id → documents.id`.
- `app/main.py` : création d'un lancement et de **quatre dossiers associés**, dépôt `POST /api/launches/{launch_id}/documents`, détail et validation par lancement.
- `app/access.py` : restrictions par lancement, résolution d'identité via chemin API et jointures documentaire.
- Plusieurs modèles (`completeness`, `workflow`, `approval`, `orli`, `sharing`, `material`, etc.) portent `launch_id` ou utilisent indirectement la hiérarchie. Il faut auditer l'ensemble des tables et des routes.
- `app/migrate.py` implémente **uniquement les migrations SQLite** et refuse explicitement PostgreSQL.
- Vercel utilise PostgreSQL/Supabase et un stockage privé persistant ; il faut écrire et tester une migration PostgreSQL indépendante.

Voir [PLAN_MIGRATION_DOSSIER_UNIQUE.md](PLAN_MIGRATION_DOSSIER_UNIQUE.md).

## 6. Recette minimale

1. Il n'est pas possible de créer deux Dossiers Jaunes, ni de détruire/dupliquer les quatre rubriques.
2. Une pièce est déposée dans Rose sans créer ni choisir un lancement.
3. Deux documents de rubriques différentes avec la même référence ORLI apparaissent dans le même résultat de filtre.
4. Un document sans ORLI est valide ; le renseigner n'affecte ni sa catégorie ni ses versions.
5. À l'issue de la migration : mêmes ensembles d'IDs de documents, versions, validations ; fichiers et empreintes identiques.
6. Aucun accès auparavant interdit n'est devenu autorisé par erreur (API, téléchargement, partage, assistant, export).
7. Historique, recherche et rapprochement ORLI fonctionnent sur plusieurs anciens lancements.
8. La sauvegarde est restaurée sur une copie test avant autorisation de bascule.

## 7. Portée de ce changement Git

Cette branche ne déploie **aucune migration**. Elle fixe les règles documentaires et le protocole de préparation. Les décisions d'autorisation, de conservation historique et de rattachements ORLI ambigus restent à valider avec Framatex.
