# Framatex MVP 0.7 — Exigences client et détection des ambiguïtés

Deux innovations complémentaires sont ajoutées au dossier jaune numérique.

## 1. Couverture des exigences client

- Depuis le détail du lancement, sélectionner un dossier technique enregistré et **analyser les spécifications** : les phrases normatives détectées deviennent des **suggestions**, pas des décisions.
- Confirmer manuellement une exigence avec son intitulé, sa catégorie, sa description, son extrait et sa **version source exacte**.
- Associer une **version de preuve** du même lancement (un essai, un document de contrôle, une fiche technique, etc.). Un document présent n'est pas une conformité démontrée.
- Un responsable doté du droit `requirement.review` peut saisir une **vérification motivée** : la matrice indique « vérifiée », « sans preuve », « à vérifier », « source remplacée » ou « preuve remplacée ».
- Lorsque la source change, l'utilisateur autorisé peut **relire la nouvelle version et actualiser l'exigence**, sans reprendre automatiquement les vérifications passées. L'audit conserve l'identité des deux versions.

## 2. Détection des ambiguïtés documentaires

- Analyse lexicale explicable de formulations telles que « légèrement », « modèle précédent », « à confirmer » ou « dès que possible ».
- Extrait et question de clarification proposés, puis **confirmation explicite** par l'utilisateur avant création du point.
- Statut « à clarifier », « clarifiée », « écartée avec justification » ou « source remplacée ».
- Clôture par une personne dotée du droit `ambiguity.review`, avec une justification et un document de clarification facultatif.
- Une version source remplacée nécessite un réexamen du passage avant de rouvrir le suivi.

## Fonctionnement et limites

Le moteur réutilise `app/intake.py`. La lecture est **locale** : PDF texte, DOCX, TXT, EML, XLSX et OCR via Tesseract pour images ou PDF scannés, si installé. L'analyse de PDF est limitée aux **trois premières pages** ; les textes sont bornés à 16 000 caractères, les propositions à 30 par catégorie. Le résultat est une aide au repérage, pas une analyse linguistique exhaustive ni une attestation de conformité.

La liste et ses compteurs sont filtrés par les droits de lecture **à la fois de la source et de sa preuve** : un lecteur sans autorisation pour un document de preuve ne voit pas l'exigence qui lui est liée. Les permissions de contrôle métier sont distinctes des permissions de lecture et de modification : `requirement.review` et `ambiguity.review`. Un rôle préexistant n'obtient **aucune permission supplémentaire** lors de la mise à jour. L'administrateur possède les autorisations système.

Les données sont stockées dans deux nouvelles tables, `client_requirements` et `specification_ambiguities`. Le processus conserve les documents originaux et ne modifie ni ORLI ni les fichiers sources.

## Routes principales

- `GET /api/document-versions/{version_id}/spec-suggestions` : propositions en lecture seule ;
- `GET /api/launches/{launch_id}/specifications` : liste et compteurs filtrés ;
- `POST /api/launches/{launch_id}/requirements` : confirmer une exigence ;
- `POST /api/launches/{launch_id}/requirements/{id}/evidence` : attacher une preuve ;
- `POST /api/launches/{launch_id}/requirements/{id}/verify` : vérifier humainement ;
- `POST /api/launches/{launch_id}/requirements/{id}/refresh-source` : relire une version source remplacée ;
- `POST /api/launches/{launch_id}/ambiguities` : enregistrer un point confirmé ;
- `POST /api/launches/{launch_id}/ambiguities/{id}/resolve` : documenter sa clôture ;
- `POST /api/launches/{launch_id}/ambiguities/{id}/refresh-source` : réexaminer une source modifiée.

Toutes les routes mutatives exigent la session et l'en-tête `X-Framatex-Request: 1`, ainsi que les permissions adaptées.

## Essais

```bash
python -m pip install -r requirements.txt pytest httpx
PYTHONPATH=. python -m pytest -q
for f in tests/*.cjs; do node "$f"; done
```

33 tests Python couvrent les versions 0.1–0.7. Les nouveaux tests incluent la création humaine, la traçabilité, les preuves de versions, le contrôle des permissions, les sources remplacées, la réouverture et la non-divulgation inter-rubriques. Le test de fragment d'interface est dans `tests/test_spec_frontend.cjs`.

## Mise à jour depuis 0.6

Sauvegarder le dossier `data/` **avant** de copier le code. Ne jamais écraser les données utilisateurs avec un dossier de démonstration. Les nouvelles tables sont créées à l'initialisation ; il n'existe pas encore de migration versionnée Alembic ni de stratégie validée de restauration — usage local de démonstration uniquement.

À confirmer avec Framatex avant pilote réel : corpus représentatif de cahiers techniques autorisés, critères métier de conformité, catégories d'exigences, responsabilités de vérification, stockage et confidentialité, protection des fichiers reçus, politique de conservation, droits par lancement.
