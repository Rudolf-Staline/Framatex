# MVP 0.3 — Décisions, valeurs et propagation ciblée

Cette version reprend **intégralement le code et les données 0.2**. Trois fonctionnalités distinctes ont été ajoutées :

## 1. Décisions documentaires motivées

- Validation **approuvée**, **refusée** ou **à reprendre**, chaque décision horodatée, attribuée à un utilisateur et rattachée à **une version précise**.
- Historique des décisions conservé sans écrasement ; commentaire requis pour les refus et demandes de reprise.
- Le remplacement d'une pièce crée une nouvelle version **à examiner**, sans hériter de la validation précédente.
- **Lien avec la complétude 0.2** : si une règle exige une validation, la dernière décision 0.3 prime sur la validation 0.2 pour la version courante. Une approbation 0.3 satisfait cette exigence ; un refus ou une reprise empêche de la considérer comme validée.

## 2. Traçabilité des valeurs métier

- Saisie contrôlée d'une consommation matière, quantité de lancement, besoin matière total ou prix unitaire (catalogue démonstratif).
- Valeur décimale exacte, unité, **version de document source**, auteur, date et justification de la modification.
- Historique de toutes les révisions : **une nouvelle valeur n'efface jamais l'ancienne**.
- L'unité d'un même champ doit rester stable : aucune conversion automatique n'est appliquée.
- Les valeurs sont **saisies et contrôlées par une personne** : pas encore d'extraction automatique, d'OCR ni de formule métier recalculée.

## 3. Premières dépendances / alertes ciblées

- L'administrateur configure des règles : source = *champ métier modifié* ou *nouvelle version d'un type documentaire* ; destination = sous-dossier concerné ; instruction de vérification explicite.
- Les modifications déclenchent des alertes liées au lancement, avec ancien/nouveau chiffre quand il s'agit d'une valeur.
- Un habilité peut enregistrer *pris en compte*, *action nécessaire* ou *sans impact*, avec une justification.
- Les alertes ne sont visibles que si l'utilisateur possède les droits **sur les sous-dossiers source et cible**, pour ne pas divulguer des valeurs sensibles.
- **Aucun envoi d'email**, aucune correction automatique de la fiche de prix, aucune écriture ORLI.

## Essai sur données inventées

À partir d'un environnement de démonstration propre :

```bash
python -m app.bootstrap_admin --email admin@exemple.local
python -m app.seed_demo
python -m app.seed_completeness_demo
python -m app.seed_workflow_demo
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Puis ouvrir le dossier *Chemises manches longues · pilote B*.

**Scénario pédagogique** : 1 500 pièces × 1,8 m = 2 700 m, puis 1 500 × 1,9 m = 2 850 m : variation de +150 m. Si la quantité définitive passe à 1 450 pièces, le besoin indicatif devient 1 450 × 1,9 m = 2 755 m, soit +55 m par rapport à la base initiale. Ces opérations ne sont **pas** automatiquement exécutées par le moteur 0.3 ; elles illustrent les vérifications possibles.

## API ajoutée

- `GET /api/launches/{id}/reviews`, `POST /api/documents/{id}/reviews`
- `GET /api/business-value-fields`, `GET|POST /api/launches/{id}/values`
- `GET|POST /api/admin/impact-rules`, `PATCH /api/admin/impact-rules/{id}`
- `GET /api/launches/{id}/impacts`, `POST /api/impacts/{id}/decision`
- `GET /api/launches/{id}/workflow-summary`

Nouvelles habilitations : `document.review`, `value.write`, `impact.review`, chacune susceptible d'être limitée au sous-dossier. L'administrateur possède les permissions par défaut ; les autres rôles doivent les recevoir explicitement.

## Limites avant pilote interne

Cette livraison est un **prototype local** : elle ne remplace ni ORLI ni les validations réelles de Framatex. Les valeurs suivies et les liens de dépendance restent **déclaratifs**, et les destinataires sont matérialisés par des sous-dossiers plutôt que des responsables désignés. Les workflows, rôles, étapes, sources faisant foi et unités doivent être validés avec Framatex. La gestion fine des droits par lancement, la base PostgreSQL, les migrations formelles, la sauvegarde/restauration, le stockage chiffré, les tests de charge et une revue de sécurité restent nécessaires avant tout déploiement opérationnel.
