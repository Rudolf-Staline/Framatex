# Lot 5 — Dépôts, quotas et traitements

## Constats confirmés
- Le verrou exclusif historique `.upload-budget.lock` couvrait copie, contrôle de format et antivirus. Un deuxième dépôt obtenait 409 même si le quota était disponible.
- La consommation était recalculée par parcours de tous les fichiers à chaque dépôt.
- Le fichier était écrit directement dans `files/` avant sa vérification.
- Les routes historiques de dépôt conservaient leur session de lecture et ne revérifiaient pas les accès après le scan.

## Corrections
- Réservations SQLite dans `.storage-budget.sqlite3`, distinct de la base métier. `BEGIN IMMEDIATE` couvre seulement les écritures de comptabilité. Aucune transaction/verrou global ne couvre le scan.
- Nombre de réservations actives borné et configurable. Saturation : 429 avec `Retry-After: 1`, message permettant de reprendre. Dépassement de quota : 413.
- Taille connue réservée avant copie ; taille inconnue réservée avant chaque écriture. Taille maximale 20 Mio, SHA-256, contrôles de format isolés et refus du scan obligatoire indisponible conservés.
- Écriture en quarantaine privée `.upload-quarantine/`, permission 0600. Publication par lien atomique sans écrasement après les contrôles ; le contenu est synchronisé sur disque avant publication.
- Compteur d'octets et registre des blobs finalisés. Aucun parcours des fichiers après l'initialisation, hors réconciliation explicite.
- Libération de réservation et fichier en cas d'erreur/cancellation ; libération du compteur lors des échecs métier et après aperçu d'extraction via `document_storage.remove_blob()`.
- Bail expiré repris au dépôt suivant ou à la réconciliation ; les octets éventuellement liés avant un arrêt brutal sont comptés et préservés.
- Dépôts historiques commande/lancement/nouvelle version : transaction de lecture interrompue avant copie/scan ; nouvelle vérification du compte et de la portée après scan. La route historique sérialise sa réponse avant commit afin qu'une erreur de sérialisation ne supprime pas un fichier déjà référencé.
- Le test de verrou global a été adapté au nouveau contrat : un ancien verrou ne bloque plus le dépôt ; le quota reste appliqué. La couverture est complétée par un vrai test de concurrence entre deux scans et un test de réservation entre processus.

## Configuration
| Variable | Défaut | Règle |
|---|---|---|
| `FRAMATEX_STORAGE_QUOTA_BYTES` | 1073741824 | entier positif ; valeur historique conservée, à dimensionner |
| `FRAMATEX_UPLOAD_CONCURRENCY` | 4 | 1 à 64 réservations actives par installation |
| `FRAMATEX_UPLOAD_LEASE_SECONDS` | 900 | 180 à 86400 secondes ; minimum supérieur aux limites de contrôle/scan |
| `FRAMATEX_STORAGE_MIN_FREE_BYTES` | 0 | réserve disque locale configurable ; refus 507 sous le seuil |

Le nombre de dépôts et le quota sont communs aux workers utilisant le même répertoire de stockage local. Le profil vérifié reste Linux/SQLite sur disque local ; aucun partage réseau ou multi-serveur n'est qualifié.

## Réconciliation et restauration
Arrêter les écritures pour comparer avec les références métier :

```sh
python -m app.storage_reconcile --storage /chemin/data/files --database /chemin/data/framat.db
```

La commande reconstruit les compteurs, libère les quarantaines expirées, et rapporte les fichiers originaux non référencés ainsi que les références manquantes. Elle **ne supprime aucun fichier original**. Les fichiers non référencés restent comptés dans le quota ; leur traitement nécessite une décision opérateur après investigation. Le sidecar est dérivable et ne fait pas partie de l'archive métier : après restauration dans un répertoire neuf, le premier dépôt reconstruit la comptabilité depuis les fichiers présents. La quarantaine n'est jamais incluse comme document sauvegardé.

## Validation locale synthétique
- Première régression : `python -m pytest -q tests/test_consolidation_storage.py tests/test_document_storage.py tests/test_file_security_phase3.py` → 13 tests réussis.
- Suite étendue après ajout des contrôles post-scan : `python -m pytest -q tests/test_consolidation_storage.py tests/test_document_storage.py tests/test_file_security_phase3.py tests/test_security_phase2.py tests/test_clamav_phase3.py` → **23 réussis, 1 ignoré** (ClamAV externe), **48,92 s** après ajout des cas de taille inconnue et de réserve disque.
- Scénarios : deux scans simultanés avec barrière, quota atomique entre processus, saturation du nombre de réservations, scan obligatoire indisponible, libération après échec métier, reprise de bail et arrêt entre lien et commit comptable, reconstruction initiale, conservation des originaux, compte désactivé pendant scan, collision de nom, taille inconnue, réserve disque et absence de parcours répété du corpus.
- Le budget de parcours du corpus est vérifié fonctionnellement : trois dépôts successifs déclenchent un seul parcours initial, puis utilisent le compteur.

## Limites explicites
- Pas de file de traitement persistante ajoutée : les contrôles sont exécutés hors boucle HTTP dans le pool de threads et bornés par les réservations et délais des sous-processus. Leur fin reste attendue par la requête HTTP.
- La quarantaine et les fichiers finaux doivent rester sur le même système de fichiers, condition nécessaire au lien atomique.
- Les créations/suppressions manuelles dans `files/` nécessitent une réconciliation. Le code applicatif utilise le propriétaire de stockage pour libérer son quota.
- L'espace temporaire des extracteurs et du scanner dépend de leurs outils et du serveur ; la réserve disque configurable n'est pas une qualification du dimensionnement réel.
- Le scanner réel, sa fraîcheur de signatures et le corpus documentaire Framatex restent à qualifier par l'exploitation. Aucun email ni fichier réel utilisé.
