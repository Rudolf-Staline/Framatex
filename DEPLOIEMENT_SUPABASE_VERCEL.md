# Préparation Framatex Demo — Vercel + Supabase

**État : base et stockage Supabase provisionnés, projet Vercel lié à GitHub ; déploiement non effectué faute des secrets serveur.**

## Provisionnement effectue le 18 octobre 2026

- Supabase « Framatex Demo » cree en `eu-west-1`, projet `qwutrmdghvqntzruscvl` (organisation personnelle existante).
- ECC Laundry temporairement suspendu pour liberer un emplacement gratuit ; Horizon reste actif.
- Bucket `framat-documents` cree en mode **private**, limite 20 Mo par objet.
- Les **43 tables** metier de la demo ont ete creees en PostgreSQL ; chacune possede RLS active et aucun acces `anon` / `authenticated` direct. Les tables sont **actuellement vides**.
- Projet Vercel `framat-demo` cree, GitHub `Rudolf-Staline/Framatex` associe, authentification Vercel active pour tous les deploiements. **Pas de deploiement fonctionnel a cette date.**
- La connexion effective Vercel -> Supabase n'est PAS etablie : les identifiants secrets et l'hote exact du pooler manquent. L'API Vercel refuse la creation de variables d'environnement (HTTP 403). Les secrets doivent etre ajoutes par le proprietaire depuis son tableau de bord.

**IMPORTANT : ne pas executer `python -m app.demo_postgres init` sur ce projet deja initialise.** La commande refuse toute base qui contient deja des tables. Verifier le schema avec `python -m app.demo_postgres status` une fois la connexion configuree.

## Variables a ajouter manuellement dans Vercel

Dans `framat-demo` > Settings > Environment Variables, enregistrer **Production et Preview** :

1. `DATABASE_URL` : copier la chaine exacte **Transaction pooler** depuis `Supabase > Connect`, remplacer le placeholder du mot de passe, convertir `postgresql://` en `postgresql+psycopg://` et conserver le port `6543`. Ajouter `?sslmode=require` si absent. Ne jamais inventer le sous-domaine du pooler.
2. `SUPABASE_SECRET_KEY` : cle serveur moderne `sb_secret_...` depuis `Supabase > Project Settings > API Keys`. Ne la placer ni dans le navigateur, ni dans GitHub, ni dans les messages de discussion.
3. `FRAMATEX_SECRET_KEY` : secret genere aleatoirement de plus de 32 caracteres pour signer les sessions Framatex.
4. `FRAMATEX_PUBLIC_BASE_URL` : definir avec l'URL Vercel definitive apres attribution du domaine pour les QR codes.

Deja preconfigures sur Vercel : `FRAMATEX_STORAGE_BACKEND=supabase`, `SUPABASE_URL=https://qwutrmdghvqntzruscvl.supabase.co`, `SUPABASE_STORAGE_BUCKET=framat-documents`, `FRAMATEX_COOKIE_SECURE=1`, `FRAMATEX_RESTRICT_NEW_LAUNCHES=1`.

Le secret Supabase moderne `sb_secret_...` est transmis **uniquement dans l'en-tete HTTP `apikey`**. L'en-tete `Authorization: Bearer` ne s'utilise que pour les anciennes cles JWT `service_role`.

## Choix techniques

- App FastAPI inchangée (`index.py` est un point d'entrée pour Vercel) ; interface blanche et bleue conservée.
- Base PostgreSQL Supabase dédiée, connexion **transaction pooler** avec dialecte `postgresql+psycopg` et SQLAlchemy `NullPool`.
- Service de stockage Supabase **privé** `framat-documents`. La clé secrète reste dans les variables serveur Vercel. Toutes les opérations de fichier sont réalisées après les permissions FastAPI.
- Les fichiers temporaires sont enregistrés dans `/tmp/framat-data` sur Vercel. Aucune donnée persistante n'est stockée dans une fonction Vercel.
- Aucun accès public ni lien signé vers les documents ; les téléchargements passent par la route FastAPI existante.
- Les traitements OCR nécessitant des exécutables locaux doivent être désactivés ou vérifiés séparément sur Vercel ; ne pas considérer Tesseract comme opérationnel.

## Validation avant le premier déploiement

- Confirmer `python -m app.demo_postgres status` ; **ne pas** recréer les tables déjà présentes.
- Créer un compte administrateur fictif avec un mot de passe fort (sans partager ce mot de passe dans le dépôt), puis alimenter des dossiers d'essai avec des documents fictifs.
- Terminer la revue de la PR #15 et les tests CI, puis déployer une prévisualisation Vercel protégée.
- Tester la connexion, les téléversements, les téléchargements, les habilitations et la révocation des sessions sur le vrai serveur.
- Garder à l'esprit la fenêtre de restauration simplifiée de 90 jours pour ECC Laundry suspendu.

## Contraintes et travaux restants

- Ce dépôt peut mentionner l’URL publique du projet Supabase, mais ne doit contenir **aucune clé secrète ni aucun mot de passe**. Le nouveau projet est annoncé à 0 $/mois.
- La base Supabase est initialisée, mais l’intégration PostgreSQL/Storage depuis Vercel n’est **pas encore testée en conditions réelles**, faute de secrets serveur. Les tests SQLite restent le filet de non-régression.
- Le bootstrap PostgreSQL convient à une nouvelle démo seulement ; il **ne remplace pas** un vrai système de migrations PostgreSQL pour les versions ultérieures.
- Les anciens scripts de données fictives peuvent écrire des fichiers localement sans les pousser dans le bucket. Pour un test en ligne, créer les dossiers depuis l'interface et téléverser les fichiers par l'API.
- Plusieurs modules Python dépendants de Tesseract/PyMuPDF/OpenPyXL doivent être évalués en conditions Vercel (ressources, durée, froid) avant de les considérer opérationnels.
- Avant un usage avec des données réelles Framatex : revue sécurité, isolation, audit des autorisations et validation de l'entreprise.