> **Phase 3 :** avant toute mise à niveau, suivre le [guide de migration et restauration](docs/MIGRATION_PHASE3.md), sur une copie, avec arrêt des écritures. Aucun déploiement n'a été autorisé dans cette mission. Pour reproduire les contrôles : `pip install -r requirements-test.txt`, `npm ci`, `python -m playwright install --with-deps chromium`, puis les deux scripts navigateur référencés dans [le rapport](docs/RAPPORT_PHASE3.md). Installer ClamAV et configurer le mode `required` avec une base de signatures maintenue avant une exploitation protégée.

# Installation et validation locale — phase 2

Utiliser une installation locale dédiée et SQLite. Aucun déploiement externe n'est autorisé par cette mission.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest httpx
export FRAMATEX_DATA_DIR=/chemin/local/dedie
# Fournir FRAMATEX_SECRET_KEY (au moins 32 caractères) par l'environnement.
.venv/bin/python -m app.migrate upgrade
.venv/bin/python -m app.bootstrap_admin --email admin@example.local
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Espaces : `/` interne, `/partners` partenaires, `/search` recherche documentaire, `/docs` API. Le migrateur prend en charge SQLite uniquement. Voir `docs/MIGRATIONS_PARTENAIRES.md` avant toute mise à niveau. Extraction bornée prévue pour Linux ; OCR selon disponibilité de Tesseract et des langues fra/eng. Les limites et indisponibilités sont affichées.

```bash
.venv/bin/python -m pytest -q
for file in tests/*.cjs; do node "$file" || exit; done
for file in static/*.js; do node --check "$file" || exit; done
.venv/bin/pip install playwright
.venv/bin/python tools/check_partner_browser.py
```

Le script navigateur utilise Chromium à `/usr/bin/chromium`, une base temporaire et un serveur loopback. Il couvre fournisseur, client, pièces jointes et administratives, intégration, recherche, commandes, conditions, délégation, dépôt multiple et champs confirmés. Captures : `artifacts/partner-browser.png` et `artifacts/client-browser.png`. Aucun transport SMTP réel n'est déclenché.

## Démonstration reproductible

Sur un répertoire neuf distinct de toute donnée opérationnelle :

```bash
export FRAMATEX_DATA_DIR=/chemin/local/demo-framat-phase2
export FRAMATEX_MODE=DEMO
# Définir FRAMATEX_DEMO_PASSWORD dans l'environnement (12–256 caractères).
.venv/bin/python -m app.seed_phase2_demo
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Le script réutilise `seed_demo`, `seed_completeness_demo`, `seed_workflow_demo`, `seed_quality_demo` et ajoute les partenaires. Comptes : `demo-admin@example.local`, `demo-client-a@example.local`, `demo-client-b@example.local`, `demo-supplier-a@example.local`, `demo-supplier-b@example.local`. Tous utilisent le mot de passe fourni ; aucune valeur de mot de passe n'est imprimée. Une relance ne réécrit pas les comptes ni les données. Les règles et validations de démonstration sont fictives.

## Exploitation locale et intégrations

- Quota : `FRAMATEX_PARTNER_QUOTA_BYTES`, 104857600 par défaut.
- Scan : `FRAMATEX_UPLOAD_SCAN_MODE=disabled|required`. En mode required, `FRAMATEX_SCANNER_COMMAND` doit désigner le scanner autorisé ; son argument final est le fichier. Exécution sans shell. Tester les codes 0, 1 et erreur avec le service réel avant ouverture. Aucun service n'a été installé ici.
- HTTPS : activer `FRAMATEX_COOKIE_SECURE=1`. Pour un pilote restreint, `FRAMATEX_RESTRICT_NEW_LAUNCHES=1`.
- Rappels internes : bouton administration partenaires ou `.venv/bin/python -m app.partner_notice_routes`. Cette commande est idempotente pour une échéance donnée, ne transmet aucun email et peut être planifiée après configuration locale. Aucun ordonnanceur n'a été installé.
- ORLI : importer CSV/XLSX, sauvegarder un mapping, comparer les lots et décider explicitement d'une mise à jour. Le format réel et la synchronisation directe restent à fournir/autoriser.
- SMTP désactivé par défaut. Après autorisation seulement : `FRAMATEX_EMAIL_ENABLED=1`, paramètres SMTP/TLS dans l'environnement, puis `.venv/bin/python -m app.partner_mail`. Le worker traite au plus 50 messages, avec cinq tentatives maximum. « Accepté SMTP » ne prouve ni livraison ni lecture. Ne pas rejouer automatiquement un état processing ambigu.

Avant tout pilote externe : recette Framatex, revue de sécurité, scanner réel, limites réseau, sauvegarde/restauration indépendante et qualification de charge. PostgreSQL, Supabase, stockage objet et Vercel ne sont pas validés par cette branche.
