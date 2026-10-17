# Suite du développement — proposition à discuter

Le MVP 0.2 comprend le **socle documentaire et une première implémentation de la complétude contextuelle** : il est démontrable mais ne prétend pas couvrir les 24 innovations décrites dans les fiches de cadrage. Il ne convient pas encore au déploiement opérationnel dans l'entreprise.

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
- [ ] Extraction OCR et rapprochement automatique des valeurs brutes (étape suivante).

## Étape suivante · Acquisition intelligente

- OCR de quelques documents-types anonymisés, restitution de la zone source, niveau de confiance et validation humaine.
- Comparaison de deux fichiers Excel de même famille, inspection des formules et des cellules clés, sans réparation automatique.
- Classement documentaire assisté (type et sous-dossier), puis QR pour rattachement à l'UUID du dossier.
- Critère d'acceptation : aucune valeur incertaine ne modifie une fiche métier sans confirmation humaine.

## Préparation indispensable à un pilote Framatex

- Confirmer les sous-dossiers, les références, les étapes de fabrication, les véritables validations et les droits par service.
- Obtenir **des documents de test fictifs ou anonymisés** et des modèles Excel autorisés.
- Choisir et valider le serveur interne, le schéma de sauvegarde, le chiffrement, le certificat HTTPS, la rétention et les outils de sécurité.
- Faire passer les permissions de la granularité actuelle **rôle × sous-dossier** à **utilisateur/rôle × lancement × type de document × action**.
- Mettre en place les migrations versionnées, une base PostgreSQL si retenue, des tests de restauration, de charge et de sécurité ; formaliser la politique de conservation des données.

**À ne pas faire sans accord :** connecter ORLI en écriture, aspirer des boîtes email, utiliser des fournisseurs externes d'IA/OCR sur des fichiers internes, ouvrir le portail client, envoyer des notifications externes ou publier automatiquement un document.
