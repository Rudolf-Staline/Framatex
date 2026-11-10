# Architecture et décisions

Le socle FastAPI/SQLAlchemy/SQLite reste en place. Les versions, dossiers, ACL, lancements, contrôles, notifications internes et Framatex Assist sont conservés. Aucun service distant n'est initialisé.

## Partenaires

`partner_models.py` ajoute organisations typées fournisseur/client, comptes, jetons opaques hachés, demandes, versions, événements, affectations de publications, lignes de commande, mouvements et file email. Les comptes partenaires ne figurent pas dans `users` : leur cookie séparé ne peut authentifier aucune route interne. Le seul accès externe à une pièce interne passe par une publication explicitement attribuée et revalidée au téléchargement.

`partner_routes.py` porte le parcours documentaire et les identités ; `partner_delivery_routes.py` porte les déclarations et confirmations ; `partner_mail.py` est un worker explicite. Les opérations internes nouvelles sont réservées aux administrateurs, choix conservateur en attendant des délégations métier validées. L'interface `/partners` fournit les formulaires correspondants. L'OpenAPI est disponible à `/docs` et `/openapi.json`.

Une demande appartient à un fournisseur et référence un lancement et une commande. Les tables historiques de demandes simulées sont conservées, sans conversion implicite des noms en organisations. Les pièces externes réutilisent le stockage privé et sa validation structurelle ; elles ne deviennent pas automatiquement des documents internes ni des données de complétude. Cette intégration reste à faire.

Les demandes passent par requested → pending → rejected → pending → approved → closed. Chaque version possède une empreinte, un auteur et un horodatage. Une décision exige la dernière version en attente. Un compare-and-swap sur la révision protège contre les modifications simultanées ; les contraintes d'unicité empêchent les numéros de version dupliqués. Une demande approuvée ne peut recevoir une nouvelle version sans un futur mécanisme de réouverture explicite.

## Commandes et quantités

Hypothèse de travail : échanges par référence commande, plusieurs matières et lancements possibles. Pas encore de référentiel commande unifié. Les lignes partenaires sont séparées du journal historique matières : aucun rapprochement automatique ORLI ni modification de ses instantanés. Les déclarations fournisseurs ne changent jamais les réceptions. Les réceptions/retours exigent une pièce approuvée de la même commande, organisation et lancement. Les quantités sont décimales, strictement positives ; les retours diminuent le reçu net. Une clé d'opération empêche une seconde écriture lors d'une reprise réseau. Une livraison partielle est un état normal ; un excédent est affiché.

## Communications

Le fil d'événements est persistant. Les dépôts créent une notification interne pour le créateur habilité. Les événements employés créent des emails uniquement pour les contacts ayant activé cette préférence. Aucun envoi depuis une requête HTTP. Le worker SMTP exige configuration et activation explicites, TLS et vérification du certificat. SMTP accepté ne prouve ni livraison ni lecture. Un crash entre l'acceptation SMTP et le commit laisse `processing` : vérifier le fournisseur de messagerie avant toute reprise manuelle (pas de promesse d'exactement une livraison).

## Limites

SQLite seulement pour les migrations. Pas d'unification documentaire globale, de multi-worker certifié, de moteur Excel de calcul, de scan antivirus, ni de pilote externe validé. Les choix de rubriques et types publiables restent ceux du socle, à faire confirmer par Framatex.
