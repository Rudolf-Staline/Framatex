# Installation et validation locale

Aucun déploiement externe réalisé ni autorisé par ce guide. Utiliser une copie de test et SQLite.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest httpx
export FRAMATEX_DATA_DIR=/chemin/local/dedie
# Configurer FRAMATEX_SECRET_KEY (au moins 32 caractères) dans l'environnement, jamais dans Git.
.venv/bin/python -m app.migrate upgrade
.venv/bin/python -m app.bootstrap_admin
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Application interne : `/` ; portail : `/partners` ; documentation API : `/docs`.
`DATABASE_URL` doit désigner SQLite pour le migrateur actuel. Ne pas pointer vers une base distante. Voir `docs/MIGRATIONS_PARTENAIRES.md` pour sauvegarde/retour arrière.

```bash
.venv/bin/python -m pytest -q
for file in tests/*.cjs; do node "$file" || exit; done
for file in static/*.js; do node --check "$file" || exit; done
.venv/bin/pip install playwright
# Le script utilise Chromium déjà installé à /usr/bin/chromium.
.venv/bin/python tools/check_partner_browser.py
```

Le test navigateur crée sa propre base temporaire avec des données fictives ; il ne modifie pas les données configurées de l'installation. Capture : `artifacts/partner-browser.png`. Aucun transport email réel n'est lancé par les tests. La CI exécute les tests Python et JavaScript ; le navigateur reste une commande de validation dédiée.

## Démonstration

Créer une installation distincte, puis définir `FRAMATEX_MODE=DEMO` avant d'exécuter les modules `app.seed_demo`, `app.seed_completeness_demo`, `app.seed_workflow_demo`, `app.seed_quality_demo`. Sans cette variable, les scripts refusent toute écriture. Ne pas activer DEMO sur les données opérationnelles. Les jeux partenaires sont créés dans les tests, pas injectés au démarrage.

## Email (après autorisation)

Configurer `FRAMATEX_EMAIL_ENABLED=1`, `FRAMATEX_SMTP_HOST`, `FRAMATEX_SMTP_PORT` (587), `FRAMATEX_SMTP_FROM`, et si nécessaire `FRAMATEX_SMTP_USER`/`FRAMATEX_SMTP_PASSWORD`. Le serveur doit accepter STARTTLS avec certificat valide. Le worker explicite est `.venv/bin/python -m app.partner_mail`. Prévoir un ordonnanceur et la supervision ; aucune tâche automatique n'a été installée. Le worker traite au plus 50 messages par invocation, avec cinq tentatives maximum et délai exponentiel.

Avant un pilote : HTTPS et cookie Secure, domaines et SMTP approuvés, scan fichiers, sauvegarde/restauration complète, contrôles d'abus et validation des parcours métier. PostgreSQL, Supabase et Vercel restent non validés dans cette branche.
