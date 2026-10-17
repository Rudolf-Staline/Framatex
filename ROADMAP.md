## Livraison 0.9 — Pilotage et assistant de navigation

- [x] Vue « Mes actions » et synthèse en page d'accueil, filtres par urgence.
- [x] Agrégation des règles de complétude, impacts, exigences, ambiguïtés et engagements datés.
- [x] Calcul des priorités sans score caché et sans urgence fictive pour les dates absentes.
- [x] Assistant de navigation à procédures locales, accès contrôlé par les permissions.
- [x] Tests du cloisonnement documentaire, des priorités et de l'interface.
- [ ] Affectation nominative des tâches, préférences d'indicateurs et tableaux par service (hors 0.9).
- [ ] Procédures de navigation validées par Framatex ; assistant génératif non prévu sans cadrage.

## Livraison 0.8 — Emails et engagements

- [x] Archivage manuel de courriels `.eml` dans la rubrique Rose.
- [x] Suggestion locale d'engagements et confirmation humaine.
- [x] Suivi de statut et audit des décisions.
- [x] Autorisations par sous-dossier et tests.
- [ ] Intégration messagerie externe (validation Framatex requise).

# Suite du développement — proposition à discuter

Le MVP 0.6 comprend le **socle documentaire et une première implémentation de la complétude contextuelle** : il est démontrable mais ne prétend pas couvrir les 24 innovations décrites dans les fiches de cadrage. Il ne convient pas encore au déploiement opérationnel dans l'entreprise.

## Incrément 0.2 · Première réalisation (implémentée)

- Profils de complétude et exigences par sous-dossier, étape et type de document.
- Statuts **présent / manquant / en attente de validation / non encore exigible / exception documentée**.
- Validation humaine des versions, invalidée pour toute nouvelle version.
- Administration des règles, permissions et synthèse intégrée au tableau de bord.
- Scénarios fictifs testés ; **validation des règles métier de Framatex encore nécessaire**.

### Fonctions restant à ajouter à cette tranche

- Recherche documentaire transverse et filtres avancés.
- Circuits de validation personnalisés avec commentaires, remplaçants et échéances.
- Critère d'acceptation métier : comparer les alertes à une liste d'exigences validée avec Framatex, sans faux blocage.

## Incrément 0.3 · Données et modifications (prototype implémenté)

- [x] Valeurs métiers traçables : consommation, quantité de pièces, besoin matière, prix, unités et provenance du document.
- [x] Historique des révisions de valeurs avec provenance et justification ; comparaison ancienne/nouvelle valeur.
- [ ] Interprétation métier automatisée et conversion d’unités (non implémentées).
- [x] Règles configurables de dépendance entre valeurs ou nouvelles versions et sous-dossiers cibles.
- [ ] Graphe métier exhaustif et calcul des conséquences quantitatives (non implémentés).
- [x] Suivi motivé des alertes (pris en compte, action nécessaire, sans impact).
- [ ] Affectation à un responsable nominatif, relances et échéances (non implémentées).
- Scénario de test : quantité initiale de 1 500 pièces × 1,8 m = 2 700 m ; consommation révisée de 1,9 m × 1 500 = 2 850 m (+150 m). Lancement définitif de 1 450 pièces : 1,9 × 1 450 = 2 755 m, soit +55 m par rapport au besoin initial. **Ce scénario sert de démonstrateur, pas de règle de calcul des achats réelle.**

## Incrément 0.4 · Double livraison réalisée : cohérence et Excel

- [x] Comparaisons configurables entre deux types documentaires, avec valeurs issues de versions identifiées.
- [x] États : cohérent, écart, données absentes, source ambiguë, unités incompatibles.
- [x] Justification humaine d’un écart, invalidée en cas de nouvelle version.
- [x] Inspection XLSX statique automatique : formules supprimées/remplacées, changements de formules, références #REF!.
- [x] Filtrage serveur des données par droits d’accès aux sous-dossiers.
- [x] Extraction locale de champs candidats depuis PDF/Office/scans (0.5, confirmation humaine).
- [ ] Rapprochement automatique des champs OCR confirmés avec les valeurs métier suivies (étape suivante).

## Incrément 0.5 · Deux modules livrés : OCR et classement assisté

- [x] Prévisualisation avant dépôt avec proposition de classement et extraction de champs structurés.
- [x] OCR local des images et des PDF scannés quand Tesseract est disponible, avec limitation du nombre de pages.
- [x] Justificatif textuel par champ et validation explicite sur une version documentaire précise.
- [x] Refus de présenter comme disponibles les rubriques interdites à l'utilisateur.
- [ ] Évaluation du taux de reconnaissance sur un jeu d'essai anonymisé validé par Framatex.

## Incrément 0.6 · QR et passeports livrés

- [x] QR code imprimable par dossier, indépendamment du numéro ORLI et sans aucun secret.
- [x] Ouverture du lancement scanné après connexion et vérification des habilitations.
- [x] Étiquette imprimable, origine configurable sans faire confiance aux en-têtes Host.
- [x] Passeport par version : provenance, auteur, empreinte, historique et décisions.
- [x] Contrôle d’intégrité par comparaison avec les octets présents sur le disque.
- [ ] Test sur téléphone depuis un réseau **interne sécurisé** validé par Framatex.
- [ ] Registre externe et immuable des empreintes, à évaluer pour une valeur probante plus forte.

## Étape suivante · Deux innovations par incrément

- Capture photo mobile plus guidée et rattachement explicite des pièces scannées.
- Couverture des exigences client / détection des ambiguïtés (à choisir pour la prochaine paire).
- Liens explicites entre champs OCR confirmés, exigences client et règles de cohérence.
- Limites à traiter : traitements asynchrones, protection des uploads et qualité des scans.

## Préparation indispensable à un pilote Framatex

- Confirmer les sous-dossiers, les références, les étapes de fabrication, les véritables validations et les droits par service.
- Obtenir **des documents de test fictifs ou anonymisés** et des modèles Excel autorisés.
- Choisir et valider le serveur interne, le schéma de sauvegarde, le chiffrement, le certificat HTTPS, la rétention et les outils de sécurité.
- Faire passer les permissions de la granularité actuelle **rôle × sous-dossier** à **utilisateur/rôle × lancement × type de document × action**.
- Mettre en place les migrations versionnées, une base PostgreSQL si retenue, des tests de restauration, de charge et de sécurité ; formaliser la politique de conservation des données.

**À ne pas faire sans accord :** connecter ORLI en écriture, aspirer des boîtes email, utiliser des fournisseurs externes d'IA/OCR sur des fichiers internes, ouvrir le portail client, envoyer des notifications externes ou publier automatiquement un document.

## Incrément 0.7 · Exigences et ambiguïtés livré

- [x] Extraction locale de propositions d'exigences avec extrait et confirmation humaine.
- [x] Matrice traçable : exigence → version source → preuve → vérification par responsable.
- [x] Détection explicable de formulations imprécises ; suivi d'une clarification motivée.
- [x] Réexamen des exigences et ambiguïtés lorsque le document source est remplacé.
- [x] Permissions de lecture et de contrôle métier, refus des preuves issues d'un autre lancement.
- [x] Interface intégrée au détail du dossier et tests API / JavaScript.
- [ ] Extraire les exigences de l'intégralité des tableaux, schémas et images d'un tech pack complexe (non implémenté).
- [ ] Évaluer rappels, dates d'échéance et circuit de validation des clarifications avec Framatex.

**Prochain binôme possible :** archivage des emails sans impression + registre intelligent des engagements email. À ce stade, l'import manuel de `.eml` devra précéder toute interconnexion à une messagerie professionnelle ; aucune collecte automatique sans autorisation de Framatex.


## Livré dans le MVP 0.10 (17 octobre 2026)

- Graphe explicable des dépendances de calcul et circuits de vérification réellement configurés.
- Simulation de besoin et de coût matière, avec calcul exact Decimal, scénarios historiques facultatifs, sources et permissions.
- Aucune écriture dans les données validées ni dans ORLI.

À prévoir : validations des règles de consommation/pertes et des postes de coût avec Framatex ; adaptation du modèle aux tissus et lancements multi-composants ; règles d'accès plus fines par lancement ; migration versionnée des schémas avant une utilisation de production.


## Livré dans le MVP 0.11 (17 octobre 2026)

- [x] Lecture contrôlée CSV/XLSX avec correspondance des colonnes métier sans présumer du format réel ORLI.
- [x] Instantanés traçables, SHA-256, contrôle des doublons, valeurs manquantes, droits administrateur.
- [x] Rapprochement proposé par référence de lancement ou commande, jamais automatique.
- [x] Confirmation et justification obligatoires ; prévention des associations concurrentes ou incohérentes.
- [x] Interface d’import et de validation intégrée ; tests API + interface.
- [ ] Valider les colonnes de vrais exports anonymisés, la règle d’unicité et les modalités d’échanges avec l’ERP.
- [ ] Migrer la base via migrations SQL versionnées et tester restauration avant pilote réel.

## Livré dans le MVP 0.12 (17 octobre 2026)

- [x] Référentiel des matières lié à chaque lancement avec unité stable et pièce justificative Jaune.
- [x] Révisions de quantités prévues historisées sans écrasement.
- [x] Commandes et réceptions associées à des versions de documents Jaune/Rose, avec historique, annulation justifiée et auteur.
- [x] Rapprochement prévu / commandé / reçu, indicateurs explicables et alertes de vérification.
- [x] Contrôles de permissions sur Jaune et Rose et provenance d'une version appartenant au bon lancement.
- [x] Affichage des justificatifs et avertissement lorsque leur version a été remplacée.
- [ ] Vérifier les unités, taux de pertes, réceptions partielles et pièces probantes avec Framatex.
- [ ] Établir une correspondance contrôlée entre des champs d'exports ORLI validés et les lignes matière.

## Livré dans le MVP 0.13 (17 octobre 2026)

- [x] Circuits documentaires configurables (type exact et sous-dossier), de une à six étapes attribuées à des rôles.
- [x] Décisions séquentielles liées à la version, séparation auteur/valideur et historique des étapes.
- [x] Contrôles de non-contournement des approbations directes et des complétudes soumises à circuit.
- [x] Notifications internes destinées aux valideurs habilités et aux services impliqués par les alertes d'impact.
- [x] Vérification des permissions lors de la création et de la consultation des notifications ; disparition des notifications devenues inaccessibles.
- [x] Pages de validation par lancement, configuration des circuits et boîte de notifications.
- [x] 52 tests Python et contrôles JS réussis localement.
- [ ] Valider les circuits réels, le droit de délégation et la séparation des tâches avec Framatex.
- [ ] Prévoir des migrations de schéma versionnées, puis tests de montée en charge et audit de sécurité avant pilote métier.
