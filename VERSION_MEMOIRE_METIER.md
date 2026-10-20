# Mémoire métier et vérifications du Dossier Jaune unique

Une équipe peut consigner un incident dans **Mémoire métier**, décrire sa cause,
sa solution et ce qu'il faut retenir, puis retrouver des cas en posant une question.
Les fiches sont classées par sous-dossier ; ORLI et document source sont facultatifs.
La version du document source reste celle observée lors de l'enregistrement.
Un incident résolu doit comporter une solution. Les modifications concurrentes
sont refusées avec une demande de rechargement.

L'assistant flottant ouvre les rubriques et recherche dans les retours d'expérience.
Ses réponses reprennent les textes enregistrés et présentent jusqu'à trois fiches
sources. La recherche est locale, par mots-clés et synonymes : elle ne constitue
pas un chatbot génératif ni une compréhension sémantique exhaustive.
Une question sans résultat reçoit une réponse explicite sans solution inventée.

**Vérifications** regroupe les pièces manquantes et la cohérence :

- Définir une pièce attendue par type documentaire, sous-dossier et éventuellement
  référence ORLI. Sans ORLI, l'attente porte sur toute la rubrique, pas sur chaque lancement.
- Relever des valeurs numériques sur les versions courantes des documents.
- Configurer une règle de cohérence (types, sous-dossiers, champ et tolérance).
  Le rapprochement compare uniquement une même référence ORLI. Il conserve les
  incertitudes quand une pièce ou une valeur manque, quand plusieurs documents
  sont candidats ou quand les unités diffèrent.
- À partir d'un écart, « Consigner le problème » préremplit un retour d'expérience.

Les listes, compteurs et réponses ne portent que sur les documents accessibles.
Une fiche liée à une pièce d'un ancien lancement restreint reste soumise à son ACL.
Les droits `rex.read` et `rex.write` sont configurables par sous-dossier ; les rôles
existants ne reçoivent aucun nouveau droit automatiquement. L'administrateur y a accès.
Les attentes utilisent `completeness.review`, la saisie de valeurs `document.write`.
Les règles de cohérence restent administrées dans les autorisations existantes.

## Migration additive

SQLite : `python -m app.migrate upgrade` applique `0005_experience_controls`.

PostgreSQL : `python -m tools.migrate_document_intelligence --apply` ajoute
uniquement `experience_records` et `document_expectations`, active RLS et révoque
les accès directs Data API aux rôles `PUBLIC`, `anon` et `authenticated`.
Les documents et les rôles existants ne sont ni réécrits ni supprimés.
Exécuter cette étape avant de déployer la nouvelle version.

Les nouvelles pages suivent les couleurs et la typographie existantes.
Les propositions de refonte visuelle sont séparées de cette livraison fonctionnelle.

## Validation

`python -m pytest -q` ; tests JavaScript de `tests/*.cjs` ; `node --check static/*.js`.

Les cas couvrent résolution, citations, ACL par sous-dossier et document,
révocation d'accès, contrôle des versions, concurrence, ORLI, décimaux, tolérance,
unités, sources ambiguës et répétition de la migration.
Le démarrage attend la fin du chargement des scripts différés avant de demander
la session, pour éviter un écran de chargement bloqué.
