# Lots 1A et 6 — migrations et exploitation

## Constats et corrections

- **Confirmé et reproduit** : sur les sources `33e7836`, une base au registre
  0023 échoue avec `UNIQUE constraint failed: schema_migrations.version`, tentative
  d'insérer à nouveau 0020. La garde teste désormais exactement 0020. Les autres
  gardes ont été examinées : elles nomment leur propre révision.
- **Corrigé et vérifié** : états 0020, 0021, 0022 et 0023, chacun issu des schémas
  Git historiques documentés dans `tests/fixtures/HISTORICAL_SCHEMAS.md`. Deux
  upgrades successifs, conservation utilisateur/audit/révocations, clés étrangères
  et sauvegarde. 0022 est reconstruit depuis 0023 en retirant son seul ajout,
  faute de commit isolé 0022 ; ce détail n'est pas masqué.
- **Corrigé et vérifié** : 0020 absent avec registre plus récent, révisions inconnues
  refusées sans suppression de registre. Aucun `INSERT OR IGNORE` ne masque une
  erreur de révision ; les protections existantes de schéma et backups restent.
- **Corrigé et vérifié** : réservations SMTP avec bail ; reprise avant transport,
  état incertain après démarrage transport ou acceptation avant commit ; aucune
  répétition automatique dans l'incertitude. Refus permanents séparés, cinq
  tentatives maximum, délais croissants. Les erreurs génériques de socket sont
  incertaines ; le test de retry historique utilise maintenant un refus SMTP
  de connexion explicite 421, et une régression couvre la socket ambiguë.
- **Corrigé et vérifié** : révocations et générations de session indépendantes de
  l'audit mutable, migration des révocations historiques. La purge synthétique
  de l'audit ne réactive pas un cookie révoqué. Outil d'export avec SHA/manifeste,
  purge sèche par défaut, vérification stricte des événements avant `--apply`,
  aucun délai officiel inventé, aucun historique réel supprimé.
- **Renforcé et vérifié** : barrière SQLite `BEGIN IMMEDIATE` pendant copie base et
  fichiers, estimation d'espace avant archive/restauration, permissions privées,
  manifeste et empreintes, restauration vers nouveau répertoire, révocations
  internes/externes. L'arrêt des écrivains reste requis pour les dépôts en cours.
- **Implémenté et testé localement** : liveness avec SHA réel ; readiness distincte
  sur révisions, stockage et scanner ; logs HTTP avec corrélation sans URL, corps,
  destinataire ni secret. ClamAV : présence exécutable et surveillance date du
  fichier daily, pas une preuve de qualité des signatures.
- **Documenté** : profil Linux/SQLite uniquement, secrets, HTTPS, quotas, scanner,
  signatures, SMTP, sauvegarde/restauration, rétention à décider. Nouveau guide
  actuel `docs/DEPLOIEMENT_INTERNE.md`, historique conservé. Les dépendances runtime
  utilisent maintenant les contraintes exactes déjà utilisées par la CI.

## Révisions intégrées (contrats fournis par chaque responsable)

0025 accès commande historiques conservateurs ; 0026 états opérationnels et
révocations durables ; 0027 provenance des réceptions hors portail ; 0028
identification/types/commentaires ; 0029 portée/échéance des obligations et
exceptions commande ; 0030 index de listes document/commande. Les helpers
respectifs sont livrés dans les commits des autres lots, et doivent être revus
ensemble. Les données historiques ne sont pas supprimées.

## Commandes et résultats

- Reproduction isolée depuis archive Git 33e7836, fixture schéma 0023 : exit 1,
  `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: schema_migrations.version`.
- `FRAMATEX_DATA_DIR=/tmp/framat-operations-final-isolated /tmp/framatex-venv/bin/python -m pytest -q tests/test_consolidation_operations.py tests/test_partner_migration_backup.py tests/test_backup_phase2.py tests/test_security_phase2.py tests/test_partners.py` :
  **25 passed in 70.10s** (avant ajout du dernier cas de registre 0020 manquant).
- Trois régressions ciblées (registre manquant/inconnu, barrière écrivains, socket
  incertaine) : **3 passed in 9.11s**.
- Export/purge audit synthétique après finalisation outil : **1 passed in 4.20s**.
- Revalidation finale du fichier de régression entier : résultat ajouté ci-dessous.
- Une première exécution simultanée non isolée a montré des collisions entre
  fixtures de plusieurs agents (table exists/locks/401). Elle n'est pas comptée
  comme preuve produit ; les runs ci-dessus ont des répertoires distincts.

## Mesure de restauration synthétique

Voir `backup_measurement.json` : une seule exécution Linux locale, une pièce,
deux versions de 512 Kio pseudorandom, 1 048 576 octets de fichiers ; archive
1 074 939 octets ; sauvegarde 0,125664 s, restauration 0,035100 s. Contrôles :
intégrité SQLite et FK, manifeste, deux SHA, versions, événement synthétique de
décision conservé, génération de restauration. Ce n'est ni un p95, ni un RPO/RTO,
ni un dimensionnement de production. Aucun avant/après comparable n'est revendiqué.

## Limites précises

- Les tests SMTP utilisent exclusivement un transport simulé ; aucune preuve de
  livraison réelle, aucun email réel envoyé. Les fenêtres incertaines nécessitent
  une décision opérateur explicite et peuvent produire un doublon si rejouées.
- Aucun serveur Framatex, ClamAV entretenu, distribution Linux finale, supervision,
  proxy ou accès réseau définitif n'est fourni : qualification sur cible restante.
- Les paramètres de signatures (48h), disque libre (100 Mio) et bail SMTP (120s)
  sont des défauts techniques configurables, pas des règles validées par Framatex.
- Les durées de conservation, RPO/RTO et autorisations de purge restent à décider.
  Le journal n'est pas déclaré immuable. Les exports/purges doivent être bornés
  pour la mémoire disponible et faits en maintenance.
- Corpus Framatex et schémas/données réels restent des dépendances externes ;
  aucun jeu synthétique ne constitue une recette officielle.

Revalidation finale : `FRAMATEX_DATA_DIR=/tmp/framat-operations-latest-whole /tmp/framatex-venv/bin/python -m pytest -q tests/test_consolidation_operations.py` : **13 passed in 21.50s**. Compilation Python des six modules opérationnels : succès. `git diff --check` : succès au contrôle.
