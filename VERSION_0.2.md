# Framatex MVP 0.2 · Complétude documentaire contextuelle

## Ce qui a changé depuis 0.1

- Profils documentaires configurables par l'administrateur, avec règles par type, sous-dossier, étape d'exigibilité et nécessité éventuelle d'une validation explicite.
- Contexte par lancement : association d'un profil et choix de l'étape (indépendante du statut général du dossier).
- Évaluation dynamique : `present`, `missing`, `pending_validation`, `not_due`, `exception`.
- Confirmation humaine d'une version documentaire. Une nouvelle version **ne conserve pas automatiquement** la validation antérieure.
- Dérogation/exception documentée avec justification et levée possible, historisée dans le journal d'audit. Elle ne vaut jamais preuve de présence.
- Tableau de bord : points documentaires à vérifier et dossiers sans règles actives.
- Contrôle de droits appliqué côté API, y compris les règles invisibles d'un sous-dossier inaccessible et la validation des versions.
- Interface d'administration des profils et règles + panneau de complétude par lancement.
- Script de données fictives : `python -m app.seed_completeness_demo`.

## Tester une démo propre

Depuis la racine, après `pip install -r requirements.txt` :

1. `python -m app.bootstrap_admin --email admin@exemple.local` et choisir un mot de passe solide.
2. `python -m app.seed_demo`.
3. `python -m app.seed_completeness_demo` (règles **inventées**, pour essais seulement).
4. `uvicorn app.main:app --host 127.0.0.1 --port 8000`.
5. Se connecter, ouvrir un dossier de démonstration et consulter « Complétude documentaire ».
6. Dans le dossier de chemises, observer une fiche d'emploi non encore validée ; ouvrir « Valider » pour approuver la version actuelle. Déposer une nouvelle version, puis constater que la validation est à refaire.
7. Dans un autre dossier, justifier l'absence d'une pièce exigible puis lever l'exception.
8. Dans « Administration », ajouter un profil métier et une règle personnalisée ; modifier un lancement pour utiliser ce profil.

Le script de démonstration ne doit pas être utilisé avec de vraies données. Aucun document ou processus réel de Framatex n'est pris comme acquis.

## Vérifications

`python -m pytest -q` : tests fonctionnels et de permissions, couvrant notamment l'absence de profil, les étapes d'exigibilité, les droits, les exceptions, l'invalidation des approbations après mise à jour et les réponses aux cas incohérents.

## Limites

- Les cinq étapes et les règles affichées dans la démo sont des **hypothèses de prototypage** ; à faire approuver par Framatex.
- Le classement des documents est fondé sur la correspondance **exacte du type documentaire**, renseigné par l'utilisateur. Aucun OCR ni détection sémantique ne se fait pour ce module.
- Les validations enregistrent une approbation de version, pas une signature électronique légalement qualifiée ni un contrôle qualité physique.
- Les règles ne bloquent pas les opérations. La complétude ne signifie pas conformité.
- Le module n'a pas encore : règles conditionnelles complexes, workflow de relance, gestion des délais réels, historisation immuable, gestion des migrations, habilitations par lancement, moteur de notification.
- Application **locale de prototypage** : ne pas importer de dossiers ou données réels sans approbation et mesures de sécurité adaptées.
