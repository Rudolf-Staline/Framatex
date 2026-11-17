# Livraison de consolidation Framatex — 17 novembre 2026

## Résultat et périmètre

Départ : `33e7836c1999db1b63331b626f5fa69d50bf193f`, récupéré depuis
`origin/main`. Branche : `consolidation/framatex-2026-11-17`.
L'arbre initial était propre, sans AGENTS.md applicable trouvé dans /workspace.
Aucune fusion de l'ancienne branche d'identification, aucun déploiement,
aucune modification de données réelles, aucun contact ou email réel.

Les défauts confirmés des parcours principaux ont reçu des corrections et des
régressions. La navigation canonique suit la commande, son dossier unique et
ses quatre rubriques. Les décisions techniques restent distinctes des règles
approuvées par Framatex. Cette livraison est révisable ; elle n'annonce ni une
recette métier ni une qualification des serveurs réels.

| Lot | État réel local | Preuves et limites |
|---|---|---|
| 1 Modèle, migrations, droits | Corrigé et vérifié | États historiques 0020–0023, ACL commande, provenances, versions et restrictions ; migration conservatrice 0025 |
| 2 Complétude, priorités, recherche | Corrigé et vérifié pour scopes existants | Noyau partagé, huit états, exceptions précises, publication effective, commandes sans lancement, client canonique ; obligations livraison/événement à définir si nécessaires |
| 3 Fournisseurs et réceptions | Corrigé et vérifié | Achats/qualité/réception non administrateurs, hors portail, séparation clients, intégration concurrente unique, Decimal, retours/annulations |
| 4 Gestion documentaire | Implémenté et vérifié localement | Identification, types stables, classement explicite, commentaires par version, guide et navigateur ; catalogue/champs provisoires à valider métier |
| 5 Volumétrie et concurrence | Corrigé et mesuré sur scénarios synthétiques ; optimisations restantes | Pages SQL canoniques, versions à la demande, quotas/réservations/quarantaine et historique incrémental ; anciennes projections complètes et agrégats globaux restent coûteux à très grand volume |
| 6 Exploitation | Implémenté et vérifié sur profil local SQLite | Migrations, restauration, état prêt/vivant, baux email et audit durable ; scanner réel/serveurs/relais et politiques de conservation à qualifier |
| 7 Validation et livraison | Validation technique locale terminée, publication PR bloquée | 208 tests réussis, trois parcours navigateur ; recette Framatex et CI distante non exécutées |

## Commits de revue

| Ensemble | Commits principaux |
|---|---|
| Stockage, interruption et mode exploitation | `6d8f7ea`, `bd8f00f`, `171f88e` |
| Droits et contextes | `43dd687`, `ca52054` |
| Complétude et priorités | `9c4c033` |
| Recherche, pages et threadpool | `314f66f`, `ab4e885` |
| Fournisseurs/réceptions | `9ab5a53` |
| Identification, guide et navigateur | `bcb3979`, `bf96907`, `bd4d59c` |
| Migrations, audit, sauvegarde et SMTP | `df0a0c7`, `7bf8953` |
| Parcours transversal et mesures | `26db3c6`, `0dcfe31` |
| Sélecteurs au-delà de100 | `734da38` |

## Diagnostic actuel et corrections

### Lot 1 — identité et droits

Le défaut de garde 0020 a été reproduit sur le commit initial : insertion
répétée et `UNIQUE constraint failed: schema_migrations.version`. Toutes les
gardes de révision ont été examinées ; chaque garde vérifie sa propre révision.
Les fixtures historiques proviennent de schémas réellement présents dans Git,
avec données synthétiques représentatives, pas d'un schéma actuel auquel on
retire seulement des numéros. Double migration, registre partiel, données et
relations conservées, schéma incompatible refusé.

La politique d'accès changeait dès l'ajout d'un lancement. Elle est désormais :
compte actif + propriétaire/administrateur/membre de commande, puis permissions
d'action/rubrique ; une provenance restreinte conserve en plus ses restrictions
historiques. Un rattachement futur n'accorde aucune habilitation. Une restriction
ne cache plus toutes les autres provenances et les pièces communes. Le retrait
d'un membre n'annule pas un accès propre au propriétaire ou à l'administrateur ;
la réponse indique l'accès effectif restant.

La permission de lecture de base s'applique aussi aux téléchargements, commentaires,
versions et reclassements directs, même si un droit de rubrique demeure.
Les filtres s'appliquent aux listes, compteurs, documents, versions, validations,
justificatifs, qualité, spécifications, simulations, notifications et recherche.
Les prédicats SQL partagent la politique avec les contrôles objet. La migration
0025 matérialise une seule fois les lecteurs qui avaient effectivement accès à
l'ensemble des lancements d'une commande historique, sans ajouter de permissions
d'action. L'exploitant doit ensuite revoir ces habilitations conservées.

Une pièce commune conserve `context_launch_id=None` et possède un contexte
commande explicite. Elle n'est plus affectée au premier lancement trié. Les
anciens identifiants et URLs restent résolubles. Les impacts historiquement
propres aux lancements ne sont pas inventés au niveau commande.

### Lot 2 — obligations et recherche

Le moteur commande historique était effectivement moins strict. Le noyau est
maintenant partagé : non applicable, facultatif, non encore exigible, manquant,
validation en attente, publication en attente, satisfait, exception. Une exception
n'est pas une pièce. Chaque décision vise sa version ; une version suivante ne
récupère pas l'approbation de la précédente. La disponibilité publiée réutilise
le contrôle du portail avec destinataire actif, droits, version courante et fichier.
Les anciennes exceptions restent limitées au lancement/règle d'origine.

Les portées commande et lancement sont explicites et dédupliquées par identifiant
d'obligation. Une pièce commune ne satisfait pas deux obligations propres à deux
lancements. L'événement d'échéance est explicite : `launch_created` conserve le
sens historique ; `order_created` doit être choisi. Sans événement de référence,
il n'est pas remplacé silencieusement par la création de commande. L'attestation
officielle inconnue devient `business_rules_confirmed=null` et
`business_rules_status=not_recorded`, sans inventer de validation.

Les priorités et compteurs incluent les commandes sans lancement, les exceptions,
la clôture des lancements et la visibilité partielle. Le client de recherche vient
de BusinessOrder, avec repli historique ; `client_id` distingue les homonymes.
Les obligations livraison/événement n'ont pas été inventées en l'absence d'un
référentiel documentaire approuvé pour ces événements.

### Lot 3 — fournisseurs et réception

Le portail et les transitions existaient déjà : CAS, unicité de version,
intégration et clé d'opération ont été préservés et renforcés, sans réimplémentation
globale. Les opérations quotidiennes utilisent `supplier.read`, `supplier.request`,
`supplier.review`, `receipt.read`, `receipt.write` et `order.create`, attribuées
explicitement. Aucun rôle existant ne reçoit automatiquement ces permissions.

Une pièce reçue par email, papier ou remise directe est enregistrée par le vrai
collaborateur avec canal/note ; aucun compte fournisseur artificiel. Rejet,
correction, nouvelle version, approbation, intégration, double appel concurrent,
révocation et séparation des deux portails sont vérifiés.

Le contrat de réception expose les vrais identifiants commande/lancement pour
l'interne. Les projections distinguent commandé, prévu, annoncé, déclaré, reçu,
retourné et restant ; décimales et unités sont conservées. Une réception partielle
normale n'est plus présentée implicitement comme une anomalie. Les seuils et dates
restent configurables. Les résumés sont séparés des mouvements et de l'historique.

### Lot 4 — gestion quotidienne

Les éléments utiles de `feat/commande-identification` (371c259) ont été lus et
adaptés, sans fusion de branche. Informations commande et atelier de lancement
sont séparés, valeurs décimales et conflits optimistes vérifiés, anciennes clés
JSON préservées. Référence/client restent canoniques.

Le catalogue provisoire porte des identifiants stables, libellés et alias uniques.
L'inconnu reste « À classer ». Migration sans fusion ambiguë ni écrasement des
libellés d'origine ; sélection par rubrique, reclassement explicite, classement
assisté et complétude utilisent ce vocabulaire. Les commentaires internes restent
liés à une version avec auteur/date, distincts des corrections et approbations.
Le guide existant et le manuel ont été mis à jour, avec parcours non administrateur.

### Lot 5 — données, fichiers et traitements

Recherche, commandes, annuaires, réceptions et file de validation filtrent les
autorisations avant COUNT/OFFSET/LIMIT. Les tris utilisent un identifiant stable
en départage. Le dossier canonique charge une page de pièces, leur dernière
version et leurs validations ; historiques sur demande. Les versions courantes,
décisions et annulations sont chargées en groupe dans les parcours optimisés.
Les plans SQLite confirment les index des pages et versions :
`docs/consolidation/query-plans.json`.

En exploitation, le dépôt refuse une configuration antivirus désactivée, pas
seulement un scanner configuré mais indisponible. Le verrou couvrant copie/scan a été remplacé par des réservations atomiques dans
un sidecar SQLite dérivable : quota global, concurrence configurable, bail,
reprise, libération et espace libre. Les fichiers restent en quarantaine avant
format/antivirus, puis publication atomique. Les fichiers orphelins sont signalés
et restent comptés, sans suppression automatique des originaux. Les réconciliations
se font en maintenance. Les droits sont relus après le scan. Les traitements de
validation et l'accès SQL du garde HTTP passent hors boucle asynchrone ; aucune
infrastructure distribuée obligatoire n'a été ajoutée.

### Lot 6 — exploitation

Le profil vérifié est Linux/Python 3.12/FastAPI/SQLAlchemy/SQLite avec stockage
local POSIX ; la présence de DATABASE_URL ne vaut pas support PostgreSQL.
Chemins, secrets, quotas, concurrence, scanner et seuils sont configurables.
`/api/health` identifie processus/version/commit ; `/api/ready` vérifie schéma,
écriture/espace et prérequis scanner sans exposer de secrets. Les requêtes sont
corrélées dans les journaux, sans contenu documentaire.

La sauvegarde prend un verrou d'écriture SQLite pendant la copie base/fichiers,
vérifie empreintes, intégrité et manifeste, contrôle l'espace temporaire et ne
restaure que vers un répertoire neuf. Le mode maintenance reste nécessaire.
Les révocations de session sont conservées hors audit mutable ; export et purge
sont explicites, vérifiés, sans délai officiel prédéfini ni journal déclaré immuable.

La file email a des baux, reprises et retries bornés. Une fenêtre d'acceptation SMTP
incertaine devient `uncertain`, avec rapprochement opérateur explicite ; aucun
« exactement une fois » annoncé. Une revue indépendante a reproduit et corrigé
les courses de bail expiré, ancien worker et écrasement de décision. Un QUIT en
échec après acceptation ne transforme plus une acceptation connue en échec.
Tous les transports d'essai sont simulés ; aucun email réel.

## Mesures et conditions

Linux x86_64 partagé, Python 3.12.14, dépendances verrouillées pour l'installation
et la CI. Node local 24.22.1 ; CI déclarée Node 22, non exécutée à distance ici.
Pas de charge sur démonstration publique, base réelle ou serveur Framatex.

| Scénario synthétique | Avant | Après | Conditions |
|---|---:|---:|---|
| Recherche 100 documents, 300 versions, page 25 | 379 SQL ; médiane 556,05 ms | 5 SQL ; médiane 83,69 ms | Même fixture, lecteur non administrateur, fonction API, 3 échantillons, tracemalloc |
| Recherche 1 000 documents, 3 000 versions, page 25 | 3 079 SQL ; médiane 5 782,29 ms | 5 SQL ; médiane 83,86 ms | Même fixture ; pas de HTTP ; mesures locales non exclusives |
| Recherche concurrente, corpus 100/1 000 | Non mesuré | 36 appels, 0 erreur, 5 SQL/appel | 2 puis 4 threads, sessions distinctes, 3 vagues, pas de p95 |
| Complétude, 10 puis 200 pièces ×2 versions | Pas de mesure avant comparable | 18 puis 18 SQL | 1 règle avec validation, requête HTTP complète ; preuves JSON plafonnées à 20 |
| Historique 500 mouvements, 50 annulations | Médiane 69,09 ms | 4,89 ms | Fonction pure Decimal, 3 répétitions, égalité de chaque événement vérifiée |
| Historique 2 000 mouvements, 200 annulations | Médiane 788,20 ms | 87,44 ms | Même protocole ; aucune extrapolation production |
| Sauvegarde/restauration 1 Mio en 2 versions | Non mesuré | 0,126 s / 0,035 s ; ZIP 1 074 939 octets | Une exécution isolée, hashes/FK/décisions vérifiés ; ni RPO ni RTO promis |

JSON bruts et commandes reproductibles : `docs/consolidation/queries.md`,
`search-before.json`, `search-after.json`, `search-concurrent.json`,
`backup_measurement.json`, `artifacts/consolidation-delivery-history.json`.
La mémoire Python après recherche de 1 000 pièces était de 690 048 à 695 853 octets
sur les échantillons hors échauffement, contre environ 3,9 Mio avant. Le JSON de
page passe de 9 852 à 10 202 octets car le client canonique est désormais renseigné.

## Migrations et contrats à relire

1. Sauvegarde complète avec arrêt des écrivains, restauration de contrôle puis
   `python -m app.migrate preflight` et `python -m app.migrate upgrade`.
2. 0025 : matérialisation conservatrice de visibilité historique ; revoir les
   OrderMember préservés. Les nouveaux rattachements ne créent aucun membre.
3. 0026 : états de révocation durables et baux email ; les anciens `processing`
   sans preuve deviennent incertains. 0027 : source fournisseur ou employé réel.
4. 0028 : identification/types/commentaires ; reprise contrôlée de JSON historique.
   0029 : portée/référence d'échéance explicites et exceptions commande. 0030 : index.
5. Les nouvelles permissions doivent être attribuées par l'administration selon
   les responsabilités approuvées. Aucun compte ne devient administrateur.
6. `/api/orders` et `/api/launches` conservent la représentation liste sans
   `page=true`, désormais bornée par limit (100 maximum) avec X-Total-Count ;
   parcourir offset/limit pour la collection complète. Annuaires/réceptions :
   mode page explicite ; validation-queue : total/pending globaux visibles et page.
7. Les sélecteurs de lancement ont recherche et pages serveur ; les formulaires
   conservent un bouton d'envoi distinct de la pagination (régression et Chromium).
   `dossier?summary=true`, `document-page` et `documents/{id}/history` sont utilisés
   par le nouvel écran ; les anciennes routes complètes restent compatibles.
8. Complétude : huit états ; `ready/items` reste l'adaptateur commande de
   `present/rows`. Une échéance sans événement de référence devient non exigible,
   pas calculée depuis un autre événement. Lire la notice de configuration.

## Commandes et résultats de validation

- Référence initiale isolée : `PYTHONPATH=. python -m pytest -q` → **156 réussis,
  2 ignorés**, 352,38 s sous charge de vérifications concurrentes.
- Passage intégré intermédiaire : **194 réussis, 2 ignorés**, 404,30 s ; il
  précède les derniers correctifs de revue et ne vaut pas résultat final.
- Passage complet après intégration : **206 réussis, 2 ignorés**, 285,94 s ;
  ClamAV réel absent et test IA réel non activé.
- Résultat final après sélecteurs et derniers gardes : **208 réussis, 2 ignorés,
  1 avertissement**, 300,33 s. Journal conservé : `docs/consolidation/final-validation.txt`.
  Avertissement : adaptateur datetime SQLite Python3.12 déprécié dans la fixture
  historique ; aucun test supprimé ni erreur masquée.
- 18 fichiers `tests/*.cjs` exécutés et 27 scripts `static/*.js` vérifiés avec
  `node --check` : réussis ; compilation Python et `pip check` : réussis.
- Trois outils navigateur Chromium local : partenaires, dossier, guide réussis.
  Parcours achats non administrateur/hors portail compris ; clavier/focus/mobile
  et axe sans violation rapportée sur les surfaces/largeurs testées. Cela ne vaut
  pas audit WCAG exhaustif. Preuves dans `artifacts/phase3-browser.json`,
  `phase3-partner-axe.json`, `guide-browser.json` et captures synthétiques.
- Catalogue guide : 57 procédures, 61 visites, 171 actions ; manuel synchronisé.
  Évaluation locale : 122 questions du corpus de test, sans appel externe ;
  simulation de panne disponible séparément, jamais présentée comme validation IA réelle.
- Un seul parcours transversal combine les modules et la restauration réelle :
  `tests/test_consolidation_journey.py`, réussi aussi isolément en 13,29 s.
- Les fixtures MVP ont été isolées pour permettre l'exécution après d'autres
  modules ; les tests d'origine restent présents. Le test de verrou ancien
  conserve le contrôle de quota tout en vérifiant la suppression du conflit global.

## Limites et décisions restantes

- Corpus documentaire Framatex, règles, rôles, tolérances, échéances et recette
  des collaborateurs restent externes. Les champs/types sont provisoires.
- Aucun référentiel d'obligations par livraison/événement ni clôture autonome de
  commande n'a été inventé. Les impacts commande demandent une définition métier.
- Les anciennes routes de détail/aperçu complet peuvent encore produire de gros
  historiques ; le portail fournisseur conserve des historiques complets sur une
  page de lignes bornée. L'historique d'une longue ligne parcourt ses événements
  antérieurs. Les agrégats globaux restent proportionnels aux obligations visibles.
  Ces limites ne sont pas masquées par les mesures de page fixe.
- Les sélecteurs de rattachement historique et de demandes métier offrent une
  recherche serveur et des pages pour retrouver les lancements au-delà des 100
  premiers. La pagination offset ne fournit pas un instantané multi-requêtes
  en présence d'insertions concurrentes.
- ClamAV absent localement : tentative portable sans installation système avec
  `APT_CONFIG=/tmp/framatex-clamav/apt.conf /usr/bin/apt-get update` bloquée par
  **HTTP 403 Forbidden** du proxy, sur miroir interne et sources originales.
  Conséquence : test `tests/test_clamav_phase3.py` ignoré, preuve moteur réel
  manquante localement ; EICAR seul ne vaudrait pas qualification complète.
- Scanner réel, signatures, relais SMTP, CPU/RAM/disques, volume autorisé,
  chiffrement d'infrastructure, sauvegarde hors site, rétention/RPO/RTO et
  supervision doivent être configurés/qualifiés sur les serveurs retenus.
- Le test du fournisseur IA optionnel reste volontairement désactivé ; il n'est
  nécessaire ni à la GED ni à la qualification de cette livraison.
- Publication GitHub : branche et tous les commits poussés. SHA distant du rapport
  vérifié : `be0e9a982bf88e1bf4e9eeecdb65e58b93e6fdb0` avant l'ultime compte rendu
  de publication. Tentative réelle `gh pr create --draft --base main --head
  consolidation/framatex-2026-11-17 --title "Consolidation Framatex : droits,
  documents, fournisseurs et exploitation" --body-file docs/PULL_REQUEST_CONSOLIDATION.md`
  → **`Post "https://api.github.com/graphql": Forbidden`**, code1.
  Aucune PR n'existe à l'issue de cette tentative ; aucune URL de PR annoncée.
  Il reste à exécuter la même commande après rétablissement de l'accès API, puis
  vérifier la CI distante. Rien ne reste à pousser. Aucun déploiement ni fusion dans main.

## Vérification courte pour le relecteur

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
npm ci
FRAMATEX_DATA_DIR="$(mktemp -d)" FRAMATEX_GUIDE_AI_ENABLED=0 FRAMATEX_EMAIL_ENABLED=0 \
  PYTHONPATH=. .venv/bin/python -m pytest -q -rs
for f in tests/*.cjs; do node "$f"; done
for f in static/*.js; do node --check "$f"; done
.venv/bin/python tools/build_guide_manual.py --check
# Installer Chromium de test, puis exécuter les trois parcours synthétiques.
.venv/bin/python -m playwright install chromium
.venv/bin/python tools/check_phase3_browser.py
.venv/bin/python tools/check_partner_browser.py
.venv/bin/python tools/check_guide_browser.py
```

Installation et reprise : `docs/DEPLOIEMENT_INTERNE.md`. Grille métier préremplie :
`docs/RECETTE_CONSOLIDATION.md`. État de reprise et détails :
`docs/CONSOLIDATION_PROGRESS.md`, `docs/consolidation/*.md`.
