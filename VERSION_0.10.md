# Framatex — version 0.10 : dépendances et simulations d'impact

Deux innovations supplémentaires sont intégrées au socle de gestion par lancement de fabrication.

## 1. Graphe explicable de dépendances

Depuis chaque dossier, la section **Graphe des dépendances et simulation** présente les trois valeurs métier de référence (quantité du lancement, consommation matière par pièce, coût matière au mètre), les résultats calculés (besoin matière théorique et coût matière estimé) et les quatre arcs de calcul documentés. Les règles de propagation **actives et configurées par un administrateur** apparaissent également comme circuits de vérification, uniquement lorsque l’utilisateur dispose de l’accès aux sous-dossiers source et cible.

Ce graphe est volontairement borné : il ne déduit pas de chaîne causale à partir d'une simple association de documents ; aucune règle arbitraire n'est exécutée.

## 2. Simulation indicative des impacts

L'utilisateur habilité peut varier une ou plusieurs des trois valeurs **déjà enregistrées avec leur source documentaire** :

- `quantite_lancement` — pièce ;
- `consommation_matiere` — m/pièce ;
- `cout_matiere_unitaire` — MAD/m (champ ajouté en version 0.10).

Les calculs sont strictement :

- besoin matière (m) = quantité × consommation unitaire ;
- coût matière (MAD) = besoin matière × coût au mètre.

Un aperçu affiche la référence, le scénario et l'écart, sans sauvegarde automatique. Un utilisateur disposant aussi de `value.write:jaune` peut conserver un **instantané de simulation**, son auteur et sa date, avec audit. Les simulations antérieures ne sont jamais recalculées automatiquement et aucune donnée validée, commande, prix ou donnée ORLI n'est modifiée.

L'application refuse NaN, l'infini, les valeurs négatives, plus de quatre décimales, les clés inconnues, les unités inattendues et la variation d'un champ sans valeur source. Les données manquantes produisent des résultats « non calculables », pas des estimations inventées. Une source documentaire dépassée est signalée.

**Limites** : estimations partielles ne tenant pas compte des pertes, rendements, frais logistiques, taxes, marges ou conditions contractuelles. Les scénarios ne doivent pas être assimilés à des devis ni à des validations d'achats.

## API

- `GET /api/launches/{id}/dependency-graph` : nœuds, arcs et circuits actifs accessibles ;
- `POST /api/launches/{id}/impact-simulations` : aperçu, éventuellement `save: true` ;
- `GET /api/launches/{id}/impact-simulations` : les 30 derniers scénarios enregistrés ;
- `GET /api/business-value-fields` : inclut désormais `cout_matiere_unitaire` (MAD/m).

Les API de simulation sont réservées à l'accès au sous-dossier Jaune ; la sauvegarde requiert en plus le droit de consigner une valeur. Les permissions sont appliquées côté serveur.

## Mise à jour

Les nouvelles tables sont ajoutées au démarrage par SQLAlchemy (`create_all`) ; aucun remplacement des tables existantes n'est attendu dans ce prototype. Sauvegarder votre dossier `data/` avant d'installer une nouvelle version. Voir `README.md` pour la procédure d'installation et les variables d'environnement.

## Vérification

`python -m pytest -q` — 42 tests locaux réussis ; tous les tests Node `tests/*.cjs` réussis. L'ouverture interactive d'un navigateur connecté au serveur doit être vérifiée en environnement utilisateur avant mise en production.
