# Préparation Framatex Demo — Vercel + Supabase

**État : prêt pour une phase d'essai avec un nouveau projet Supabase VIDE, mais non déployé.**

## Blocage du 18 octobre 2026

La création de « Framatex Demo » dans l'organisation Supabase existante a été refusée : deux projets gratuits actifs sont déjà présents (**ECC Laundry** et **Horizon**). Aucune de ces bases n'a été modifiée ou suspendue. **Ne jamais lancer ces scripts contre un de ces deux projets.**

## Choix techniques

- App FastAPI inchangée (`index.py` est un point d'entrée pour Vercel) ; interface blanche et bleue conservée.
- Base PostgreSQL Supabase dédiée, connexion **transaction pooler** avec dialecte `postgresql+psycopg` et SQLAlchemy `NullPool`.
- Service de stockage Supabase **privé** `framat-documents`. La clé secrète reste dans les variables serveur Vercel. Toutes les opérations de fichier sont réalisées après les permissions FastAPI.
- Les fichiers temporaires sont enregistrés dans `/tmp/framat-data` sur Vercel. Aucune donnée persistante n'est stockée dans une fonction Vercel.
- Aucun accès public ni lien signé vers les documents ; les téléchargements passent par la route FastAPI existante.
- Les traitements OCR nécessitant des exécutables locaux doivent être désactivés ou vérifiés séparément sur Vercel ; ne pas considérer Tesseract comme opérationnel.

## Configuration après disponibilité d'un nouveau projet gratuit

1. Créer un **nouveau projet Supabase**, non utilisé par une autre application, et attendre sa mise en service.
2. Créer le bucket `framat-documents` en mode **PRIVATE** dans Storage ; garder les accès publics désactivés.
3. Configurer les variables d'environnement `DATABASE_URL`, `FRAMATEX_SECRET_KEY`, `FRAMATEX_STORAGE_BACKEND`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_STORAGE_BUCKET`, `FRAMATEX_COOKIE_SECURE=1`, `FRAMATEX_PUBLIC_BASE_URL` et `FRAMATEX_RESTRICT_NEW_LAUNCHES=1` (voir `.env.example`). **Ne jamais commiter ces secrets.**
4. Sur un poste de développement sécurisé, confirmer qu'il s'agit d'une base **neuve et vide** puis exécuter le bootstrap **une seule fois** :

   ```bash
   export FRAMATEX_CONFIRM_EMPTY_DEMO_DB=I_CONFIRM_NEW_EMPTY_FRAMATEX_DATABASE
   python -m app.demo_postgres init
   python -m app.demo_postgres status
   python -m app.bootstrap_admin --email admin@example.invalid
   ```

   Le bootstrap refuse une base contenant déjà des tables publiques. Il initialise le schéma et active RLS sur les tables Framatex, sans créer de politiques Data API accessibles aux clients. L'API FastAPI garde ses propres contrôles de droits ; la connexion PostgreSQL serveur est privilégiée et **ne doit jamais être exposée au navigateur**.
5. Connecter le dépôt GitHub à un projet Vercel **protégé** pour une prévisualisation. Les migrations et la création du compte doivent être effectuées **avant** d'ouvrir la démo ; Vercel ne les réalise pas à chaque requête.
6. Vérifier les téléchargements, le remplacement de versions, les permissions administrateur/collaborateur, le revocation des sessions, puis les journaux Vercel. N'utiliser **que des données fictives**.

## Contraintes et travaux restants

- Ce dépôt ne contient **aucune** URL réelle Supabase, aucune clé, ni aucun mot de passe. Il ne crée aucun projet payant.
- La base Supabase n'existe pas encore : l'intégration distant PostgreSQL et Storage n'est **pas testée en conditions réelles**. Les tests automatisés SQLite restent le filet de non-régression.
- Le bootstrap PostgreSQL convient à une nouvelle démo seulement ; il **ne remplace pas** un vrai système de migrations PostgreSQL pour les versions ultérieures.
- Les anciens scripts de données fictives peuvent écrire des fichiers localement sans les pousser dans le bucket. Pour un test en ligne, créer les dossiers depuis l'interface et téléverser les fichiers par l'API.
- Plusieurs modules Python dépendants de Tesseract/PyMuPDF/OpenPyXL doivent être évalués en conditions Vercel (ressources, durée, froid) avant de les considérer opérationnels.
- Avant un usage avec des données réelles Framatex : revue sécurité, isolation, audit des autorisations et validation de l'entreprise.
