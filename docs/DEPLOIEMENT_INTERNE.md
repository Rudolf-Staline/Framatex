# Installation interne vérifiée — consolidation du 17 novembre 2026

## Profil et décisions encore nécessaires

Le profil implémenté utilise Linux, Python 3.12, FastAPI/SQLAlchemy, SQLite et
un répertoire local privé. Le migrateur refuse les autres moteurs. Aucun
hébergement Supabase ou Vercel n'est requis, aucune installation distante
n'a été réalisée. Les capacités CPU, RAM, disques, concurrence, haute
disponibilité et engagements de sauvegarde de Framatex restent à déterminer.
Les mesures synthétiques de la livraison ne dimensionnent pas les serveurs.

Prérequis : volume local permettant les verrous POSIX et les transactions SQLite,
compte de service distinct, accès restreint au répertoire de données, disque
surveillé, reverse proxy HTTPS configuré par l'exploitant. Les téléchargements
restent servis par l'application après contrôle des droits. Tesseract et les
langues fra/eng sont nécessaires pour les parcours OCR concernés ; les limites
et avertissements d'extraction restent visibles et la confirmation humaine
reste obligatoire. Node et Playwright sont des dépendances de vérification,
pas du service HTTP.

## Installation reproductible

`requirements.txt` utilise les contraintes de `requirements-test-lock.txt` afin
que les versions transitives de l'installation et de la CI soient identiques.
Conserver ces deux fichiers ensemble. L'accès au dépôt de paquets ou à un miroir
interne est nécessaire à l'installation ; aucun accès Internet général n'est
requis pour la gestion documentaire locale. L'IA du guide est facultative et
désactivée par défaut.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export FRAMATEX_DATA_DIR=/chemin/prive/framatex
# Charger les secrets depuis le gestionnaire local de l'exploitant.
export FRAMATEX_MODE=OPERATIONAL
export FRAMATEX_COOKIE_SECURE=1
export FRAMATEX_UPLOAD_SCAN_MODE=required
export FRAMATEX_SCANNER_BACKEND=clamav
# Fournir FRAMATEX_SECRET_KEY : aléatoire, au moins 32 caractères.
.venv/bin/python -m app.migrate preflight
.venv/bin/python -m app.migrate upgrade
.venv/bin/python -m app.bootstrap_admin --email administrateur@example.local
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Avec un paquet livré sans `.git`, fournir `FRAMATEX_BUILD_COMMIT` avec le SHA
vérifié du code installé. `FRAMATEX_BUILD_VERSION` identifie la livraison (défaut
`consolidation-2026.11`), également utilisé par la documentation OpenAPI. `/api/health` indique processus vivant et commit ;
`/api/ready` retourne 503 tant que les révisions, l'espace de stockage ou les
prérequis du scanner ne sont pas prêts. Aucun secret ni chemin privé n'y figure.
Le seuil `FRAMATEX_MIN_FREE_BYTES` vaut 100 Mio par défaut : garde technique
configurable à adapter après dimensionnement. Ne pas ouvrir le service avant
la recette et les décisions d'exploitation requises.

## Migrations et contrôles d'accès

Arrêter HTTP, workers et imports avant la sauvegarde complète. Tester la
restauration et la migration sur une copie locale autorisée avant mise à niveau.
Ne pas effacer `schema_migrations`. Les révisions intermédiaires 0020 à 0023
sont couvertes par des schémas historiques synthétiques ; la migration refuse
les révisions inconnues et les relations historiques invalides.

- 0025 matérialise uniquement les accès effectifs historiques aux commandes
  déjà rattachées, sans attribuer de nouvelles permissions d'action. Les
  rattachements futurs ne créent plus d'habilitation implicite.
- 0026 conserve les révocations de sessions dans des tables indépendantes de
  l'audit ; les tokens précédemment révoqués restent refusés après export ou
  purge de l'audit. Les anciens emails `processing` deviennent `uncertain`.
- 0027 conserve l'auteur fournisseur ou l'employé qui enregistre une réception
  hors portail ; 0028 ajoute identification, types et commentaires sans écraser
  les originaux ; 0029 rend explicites portée et événement d'échéance ; 0030
  ajoute les index de liste.

Les nouvelles permissions métiers doivent être attribuées explicitement par
l'administration, selon les responsabilités approuvées. Aucune politique de
conservation Framatex n'est supposée connue. Ne purger ni les générations de
session ni les révocations pour gagner de la place. Le journal d'audit n'est
pas annoncé immuable ; les accès directs au fichier SQLite restent privilégiés.
L'outil `python -m app.audit_maintenance export ARCHIVE.jsonl --before DATE_ISO`
crée un export privé avec empreinte et nombre de lignes. Après copie et
vérification autorisées, `python -m app.audit_maintenance purge-export ARCHIVE.jsonl`
vérifie la correspondance exacte avec les événements encore présents, sans
suppression ; `--apply` effectue uniquement la purge explicitement demandée.
Il ne touche jamais aux états de révocation. La borne de date est obligatoire,
sans durée prédéfinie. Utiliser une fenêtre de maintenance, un export suffisamment
petit pour la mémoire disponible et une procédure approuvée précisant portée,
preuve de sauvegarde et durée ; cette livraison ne supprime aucun historique réel.

## Stockage, scanner et extraction

Configurer `FRAMATEX_STORAGE_QUOTA_BYTES`, `FRAMATEX_PARTNER_QUOTA_BYTES` et les
paramètres de concurrence documentés dans `.env.example`. La base de budget
locale et la quarantaine sont dérivables et ne sont pas des pièces métier.
Après arrêt des écritures, reconstruire le budget et rapporter les fichiers
orphelins avec `python -m app.storage_reconcile --storage DATA/files --database DATA/framat.db`.
L'outil ne supprime jamais les fichiers originaux orphelins. Les réservations
expirées sont récupérées ; le nombre de dépôts est borné par
`FRAMATEX_UPLOAD_CONCURRENCY` (4 par défaut, HTTP 429 et Retry-After à saturation),
le bail par `FRAMATEX_UPLOAD_LEASE_SECONDS` (900 secondes par défaut), et l'espace
libre par `FRAMATEX_STORAGE_MIN_FREE_BYTES` (0 par défaut, configurable). Un fichier n'est publié dans le stockage privé qu'après les
contrôles de format et le scan obligatoire. Ne pas remplacer `required` par
`disabled` pour contourner une indisponibilité du scanner.

Installer et maintenir ClamAV/freshclam selon la distribution et la politique
réseau retenue. `/api/ready` vérifie la présence de l'exécutable et, avec
l'adaptateur `clamav`, la date du fichier `daily.cvd`/`daily.cld` dans
`FRAMATEX_CLAMAV_DATABASE_DIR` (défaut `/var/lib/clamav`). Le seuil technique
`FRAMATEX_SCANNER_MAX_SIGNATURE_AGE_HOURS` vaut 48 heures ; ce n'est pas une
règle officielle Framatex. Cette surveillance par date de fichier ne prouve
ni le bon chargement ni l'exhaustivité des signatures. Qualifier le scanner et
son actualisation sur la machine retenue. Un résultat EICAR seul n'est pas une
qualification antivirus complète. Les fichiers malformés, chiffrés et les
limites de ressources sont refusés ou signalés selon les contrôles existants.
Le corpus réel Framatex reste à fournir pour la qualification documentaire.

## Sauvegarde, restauration et rétention

```bash
# Arrêter tous les processus qui écrivent puis utiliser un autre répertoire/volume.
.venv/bin/python -m app.backup backup /chemin/prive/framatex /sauvegardes/framatex-AAAAMMJJ.zip
# Restaurer seulement vers un répertoire inexistant.
.venv/bin/python -m app.backup restore /sauvegardes/framatex-AAAAMMJJ.zip /reprise/framatex
```

Le code prend en plus un verrou d'écriture SQLite pendant la copie base/fichiers,
vérifie l'intégrité, les relations, chaque empreinte et le manifeste ZIP. Une
écriture parallèle SQL est bloquée pendant cette copie. Le mode maintenance
reste requis : un dépôt peut avoir commencé son traitement avant transaction.
Les fichiers sont appendus, pas réécrits ; une pièce manquante provoque un refus
de sauvegarde, pas un succès silencieux.

L'espace temporaire estimé avant sauvegarde est deux fois la taille base/fichiers
plus 16 Mio (copie et archive, estimation conservatrice) sur le volume destination.
Les restaurations vérifient aussi l'espace libre avant extraction. Les archives
et fichiers restaurés sont privés ; les archives sont créées sans écraser une
destination existante. La restauration révoque sessions internes et invitations
externes. Elle exclut les secrets de session et la quarantaine/budget dérivable.

Destination et nom d'archive sont des arguments explicites : planifier la copie
hors machine et le chiffrement avec l'exploitant. Aucune suppression automatique
ni durée de rétention n'est activée. Framatex doit décider rétention, RPO et RTO.
Vérifier périodiquement une restauration sur un répertoire neuf : fichiers,
versions, décisions, contrôles d'accès, puis migration explicite. La réussite
d'un test synthétique ne garantit pas le temps de reprise d'une base réelle.

## Emails et reprise après interruption

Le worker est séparé de HTTP. SMTP reste désactivé tant que
`FRAMATEX_EMAIL_ENABLED=1` et une configuration explicitement approuvée ne sont
pas fournis. Aucun email réel n'a été envoyé pendant cette consolidation.

```bash
.venv/bin/python -m app.partner_mail
# Après examen manuel des logs du relais, décider explicitement du sort d'un envoi :
.venv/bin/python -m app.partner_mail --reconcile IDENTIFIANT --decision cancelled --reason 'Justification opérateur documentée'
```

Le bail `FRAMATEX_MAIL_LEASE_SECONDS` vaut 120 secondes (30–3600 configurables).
Une réservation expirée avant appel du transport est reprise ; après passage
à l'envoi, l'état devient `uncertain` sans renvoi automatique. Les erreurs SMTP
permanentes ne sont pas rejouées ; les refus temporaires connus ont au plus
cinq tentatives, avec délai croissant. Une rupture de socket reste incertaine.
`--decision accepted|retry|cancelled` exige une justification auditée ; `retry`
peut envoyer un doublon et reste limité au budget d'essais. Il n'y a aucune
promesse « exactement une fois » avec SMTP. Une acceptation SMTP ne prouve ni
livraison ni lecture.

Surveiller les états `failed`, `exhausted`, `permanent_failed`, `uncertain`, les
baux expirés et la saturation des quotas, ainsi que les réponses 503 de readiness.
Les journaux HTTP incluent un identifiant de corrélation renvoyé en `X-Request-ID`,
la méthode, le statut et la durée, sans requête, destinataire, corps ou secret.
Configurer collecte/rotation et alertes sur la machine retenue ; aucun service
de supervision distant n'est installé par cette livraison.
