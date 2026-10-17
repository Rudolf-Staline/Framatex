# Framatex — MVP 0.13 · Circuits de validation et notifications ciblées

## Fonctionnalité 1 — Circuits de validation configurables

L'administrateur peut créer un **circuit par sous-dossier et par type documentaire exact**. Chaque circuit comporte de une à six étapes ordonnées ; chaque étape est affectée à un rôle déjà configuré, doté des permissions `launch.read`, `document.read` et `document.review` pour le sous-dossier concerné.

Depuis le lancement, un utilisateur habilité dépose un document et **soumet sa version courante** au circuit. Les personnes appartenant au rôle de la première étape peuvent approuver, demander des corrections ou refuser. La prochaine étape ne s'ouvre qu'après validation de la précédente. Les décisions conservent le commentaire, le décideur, l'étape et la version exacte.

Garde-fous :
- aucune approbation automatique, aucun saut d'étape ;
- l'auteur du dépôt ne peut pas valider sa propre version ; un même utilisateur ne peut pas valider deux étapes du même circuit ;
- le rôle de validation effectif est obligatoire, **même pour l'administrateur** ;
- un refus et une demande de correction exigent un commentaire motivé ;
- une version remplacée rend son ancien circuit **obsolète** sans réécrire ses décisions ;
- une nouvelle version doit être soumise à un nouveau circuit ;
- pour un type soumis à un circuit, une validation simple ne peut pas contourner ce dernier.

**Limites actuelles** : les circuits sont séquentiels, sans délégation ni relance programmée ; les circuits déjà commencés continuent selon leur paramétrage même si le modèle est désactivé. Un circuit refusé nécessite une nouvelle version. La base conserve les anciens historiques.

## Fonctionnalité 2 — Notifications internes ciblées

La nouvelle page **Notifications** affiche uniquement les alertes destinées au compte connecté :

- demande d'approbation à l'étape actuellement ouverte ;
- décision finale transmise au demandeur, si ses droits sont conservés ;
- alerte d'impact transmise aux collaborateurs autorisés à voir à la fois le sous-dossier source et le sous-dossier cible, et autorisés à traiter l'impact.

La consultation, la lecture et la navigation vers le dossier sont protégées côté serveur. Les notifications disparaissent de la réponse API si un droit de lecture a été retiré. Une clé d'événement empêche les duplications pour la même personne.

**Aucun message externe** n'est envoyé : pas de SMTP, webhook, SMS ou connexion automatique aux boîtes professionnelles.

## Utilisation

1. Dans **Administration → Circuits de validation**, créer un circuit, par exemple `Fiche d’emploi` dans **Jaune**, deux étapes `Bureau technique → Contrôle qualité`. Prévoir **des comptes distincts** ayant ces rôles et leurs permissions.
2. Déposer une fiche dans le dossier Jaune d'un lancement ; ouvrir **Circuits de validation**, puis **Soumettre la version**.
3. Se connecter avec le premier valideur. Ouvrir **Notifications**, accéder au dossier et décider.
4. Se connecter avec le second valideur et conclure le circuit.
5. Ajouter une nouvelle version : l'ancien circuit apparaît obsolète. La nouvelle version n'est pas approuvée automatiquement.

## Routes ajoutées

| Méthode | Route | Fonction |
|---|---|---|
| GET / POST | `/api/admin/approval-templates` | Lister / créer des circuits, administrateur |
| PATCH | `/api/admin/approval-templates/{id}` | Activer / désactiver un circuit |
| GET | `/api/launches/{id}/approval-overview` | Documents visibles, circuit, étapes et décisions |
| POST | `/api/documents/{id}/approval-runs` | Soumettre la version courante |
| POST | `/api/approval-runs/{id}/decisions` | Décider de l'étape attribuée |
| GET | `/api/notifications` | Boîte de réception du compte |
| POST | `/api/notifications/{id}/read` | Marquer une notification comme lue |

## Tests

`PYTHONPATH=. python -m pytest -q` : **52 tests Python** réussis, y compris 4 tests ajoutés pour la version 0.13.

`for file in tests/*frontend.cjs; do node "$file"; done` : tous les scripts JavaScript réussissent ; `node --check static/*.js` à appliquer fichier par fichier.

## Mise à niveau et limites de sécurité

**Sauvegarder le répertoire `data/` et arrêter l'application avant mise à niveau.** Quatre nouvelles tables de circuits et une table de notifications sont créées par SQLAlchemy au démarrage ; ce mécanisme est une facilité de prototype, **pas une migration contrôlée de production**. Aucun changement ne doit être introduit sur une installation réelle sans migrations versionnées, tests de restauration et audit de sécurité.

Les règles Framatex de séparation des tâches, signatures réglementaires, périmètres des sous-dossiers, responsabilités des valideurs et éventuelles échéances devront être confirmées. Une décision de workflow constitue une approbation interne traçable, **pas** une signature électronique légalement qualifiée.
