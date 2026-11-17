## Problème et résultat

Les rattachements de lancements changeaient les droits de commande, les pièces
communes recevaient une provenance artificielle et les moteurs de complétude
produisaient des résultats différents. Les listes et dépôts sérialisaient ou
chargeaient des collections entières ; des migrations intermédiaires et reprises
SMTP échouaient.

Cette consolidation conserve FastAPI, SQLAlchemy, SQLite et l'interface existante.
Le parcours principal part désormais de la commande et de son dossier unique,
avec permissions explicites, versions/provenances conservées et opérations
fournisseur accessibles à des rôles métier non administrateurs.

## Lots de revue

1. **Modèle/migrations/droits** : ACL commande stable, restrictions par provenance,
   contexte explicite, migration conservatrice des lecteurs historiques,
   schémas 0020–0023/idempotence et refus des incompatibilités.
2. **Complétude/priorités/recherche** : noyau partagé, huit états, exceptions
   précises, publication réellement accessible, cardinalités commande/lancement,
   délais explicites et client canonique.
3. **Fournisseurs/réception** : permissions métier explicites, réception hors
   portail avec auteur réel, intégration CAS/idempotence, Decimal, retours et
   annulations, navigation et listes serveur.
4. **Documents** : identification commande/lancement, catalogue provisoire avec
   alias uniques, classement explicite, commentaires par version et guide actualisé.
5. **Volume/concurrence** : ACL SQL avant pagination/comptage, versions courantes
   et historique à la demande, réservations de quota, quarantaine, reprise et
   historique incrémental ; absence de scan obligatoire refusée en exploitation.
6. **Exploitation** : profil interne configurable, sauvegarde/restauration,
   révocations durables hors audit, baux SMTP avec état incertain, readiness et
   corrélation de requêtes, dépendances alignées avec la CI.
7. **Validation** : tests de régression, parcours transversal avec restauration,
   contrôles navigateur/mobile/axe et mesures synthétiques reproductibles.

## Validation

Résultats définitifs : [rapport de consolidation](docs/CONSOLIDATION_REPORT.md)
et [état de reprise](docs/CONSOLIDATION_PROGRESS.md).

- Suite complète finale : **208 tests réussis, 2 ignorés**, 300,33 s. Les deux
  ignorés sont ClamAV réel absent et le fournisseur IA optionnel non activé.
  18 tests JavaScript et 27 scripts syntaxe vérifiés. Les derniers ajustements
  de sélection, permissions indirectes et mode exploitation sont inclus.
- Tests JavaScript et syntaxe, trois parcours Chromium fournisseur/client,
  dossier et guide réussis ; navigation clavier, focus et axe/mobile vérifiés.
- Migration de schémas Git historiques, double upgrade et restauration réelle
  avec vérification des fichiers/versions/décisions/empreintes.
- Recherche, page 25, lecteur non administrateur, 100/1 000 pièces ×3 versions :
  **379/3 079 → 5/5 instructions SQL**. 36 appels concurrents synthétiques sans
  erreur. Complétude : **18 SQL pour 10 comme pour 200 pièces**. Les latences et
  leurs limites sont documentées ; aucune mesure de production ni p95 inventé.

## Migration et limites

Les révisions 0025–0030 sont additives/conservatrices. Lire
[installation interne](docs/DEPLOIEMENT_INTERNE.md), sauvegarder en maintenance,
tester la restauration sur une copie puis lancer preflight/upgrade. Revoir les
habilitations historiques matérialisées et attribuer les nouvelles permissions
explicitement ; aucun rôle ne reçoit automatiquement de droits sensibles.

Le catalogue et les champs sont provisoires. Les règles officielles, le corpus
Framatex, les obligations par livraison/événement, le dimensionnement des serveurs,
les seuils et la conservation/RPO/RTO restent à valider. Certaines anciennes
projections complètes restent coûteuses à grand volume ; les nouveaux parcours
paginés sont à utiliser. Le test du moteur ClamAV réel reste bloqué localement
(absence du binaire et HTTP 403 des sources de paquets) ; le contrôle obligatoire
indisponible reste refusé. Aucun test IA réel, email réel, donnée réelle,
déploiement ni fusion.

[Grille de recette préremplie](docs/RECETTE_CONSOLIDATION.md).
