# Démonstration Framatex — Vercel + Supabase

## Périmètre et limites

Ce profil est **exclusivement destiné à des données fictives**. Les 55 tables
historiques du schéma `public` de Supabase sont préservées : la version actuelle
de Framatex utilise une nouvelle base logique dans le schéma PostgreSQL privé
`framatex_demo_v2`, contenant 94 tables. Le stockage des documents s'effectue
dans le bucket privé existant `framat-documents`.

- PostgreSQL est **persistant**; Vercel reste sans état.
- Les documents sont transférés vers **Supabase Storage** après validation.
  Un cache non fiable sous `/tmp` ne sert que pour les inspections et les téléchargements.
- Les autorisations métier demeurent appliquées par FastAPI, jamais par un lien
  public vers les objets. La clé Supabase secrète n'est accessible qu'au serveur.
- Les contrôles locaux de quota (`storage_budget.py`) sont transitoires et ne
  constituent **pas** un quota distribué. Le quota du bucket doit être surveillé.
- Les opérations de sauvegarde/restauration SQLite sont **incompatibles** avec
  PostgreSQL. Prévoir séparément les sauvegardes PostgreSQL et Storage.
- Le traitement SMTP et la maintenance utilisant des verrous SQLite ne doivent
  pas être activés en mode DEMO avant adaptation PostgreSQL.
- Aucun téléchargement, nom, contenu ou identifiant personnel réel ne doit être
  utilisé pour cette démo sans validation sécurité et conformité.

## Déploiement par étapes

1. Faire une sauvegarde vérifiée du projet Supabase existant et conserver
   l'ancienne configuration publique, **sans supprimer de tables**.
2. Lire `db/supabase_demo_bootstrap.sql`; exécuter ce fichier **une seule fois**
   via l'éditeur SQL du projet Supabase `Framatex Demo` (réf.
   `qwutrmdghvqntzruscvl`). La migration s'exécute en transaction et refuse
   de recréer un schéma existant.
3. Exécuter l'équivalent de `python -m app.postgres_schema verify` dans un
   environnement Python administrateur avec une connexion PostgreSQL au même
   projet. Aucune migration n'est exécutée dans une fonction HTTP.
4. Configurer sur Vercel les variables suivantes via le gestionnaire de secrets
   (jamais dans Git et jamais dans les logs) :

   ```env
   DATABASE_URL=postgresql+psycopg://<USER>:<PASSWORD>@<POOLER-HOST>:6543/postgres
   FRAMATEX_DB_SCHEMA=framatex_demo_v2
   FRAMATEX_MODE=DEMO
   FRAMATEX_STORAGE_BACKEND=supabase
   SUPABASE_URL=https://qwutrmdghvqntzruscvl.supabase.co
   SUPABASE_STORAGE_BUCKET=framat-documents
   SUPABASE_SECRET_KEY=<clé secrète côté serveur>
   FRAMATEX_SECRET_KEY=<clé aléatoire et stable de 32+ caractères>
   FRAMATEX_COOKIE_SECURE=1
   FRAMATEX_EMAIL_ENABLED=0
   FRAMATEX_GUIDE_AI_ENABLED=0
   ```

   La chaîne `DATABASE_URL` doit provenir de **Connect → Transaction pooler**
   du projet Supabase. Le serveur utilise psycopg avec requêtes préparées
   désactivées et des connexions de courte durée pour le mode serverless.
   Le schéma `public` reste inutilisé pour le stockage métier courant.
5. Après déploiement de la branche de recette, vérifier la réponse HTTP de
   `/api/health`, l'authentification, l'isolation des accès, la création des
   commandes, le dépôt/lecture/suppression des pièces, la reprise après un
   nouveau déploiement, et les journaux Vercel **à l'exécution**.
6. Ne promouvoir sur `main` qu'une version ayant réussi ces contrôles, avec
   une stratégie de restauration PostgreSQL + Storage adaptée.

## Sécurité

Le schéma de démo est privé. Aucune exposition Data API/RLS n'est nécessaire pour
ces tables, car seul FastAPI communique avec PostgreSQL. Le bucket reste privé,
et l'adaptateur conserve les données sur le serveur jusqu'à autorisation dans
les routes existantes. Pour les clés modernes `sb_secret_*`, l'en-tête HTTP
`apikey` est utilisé **sans** envoyer la clé dans un `Authorization: Bearer`.

> Ne configurez pas de production industrielle sur Vercel sans recette métier,
> analyse de volume, quotas distribués, antivirus réellement disponible et
> politique de sauvegarde indépendante.
