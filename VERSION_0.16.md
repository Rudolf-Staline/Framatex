# MVP 0.16 — Recette de stabilisation (17 octobre 2026)

Cette version ne rajoute pas deux nouvelles innovations : elle stabilise les parcours existants avant un pilote métier. Les simulations et les données de tests restent fictives.

## Corrections ergonomiques

- **Mobile** : le bouton « Se déconnecter » n'est plus masqué sous 760 px ; son parcours revient bien à l'écran de connexion.
- **Écran de dossier** : un sélecteur « Aller à une rubrique » donne accès directement aux sections disponibles (pièces, complétude, alertes, Excel, OCR, QR, exigences, emails, matières, etc.). Un bouton ramène en haut de la page.
- **Tableaux sur écran étroit** : la zone documentaire ne force plus l'ensemble du document à dépasser la largeur de l'écran ; les tableaux conservent, eux, un défilement horizontal local.

## Renforcement HTTP et connexion

- Les réponses ajoutent `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` et une `Permissions-Policy` restrictive, **y compris pour les erreurs d'autorisation**.
- La page d'accueil utilise une politique de sécurité du contenu (CSP) interdisant notamment les scripts tiers, les `iframe` et les objets embarqués. La politique spécifique de l'étiquette QR est conservée.
- Les réponses API et la page principale reçoivent `Cache-Control: no-store` ; les téléchargements documentaires avaient déjà un cache désactivé.
- Après cinq échecs de connexion sur un même couple IP/adresse email en cinq minutes, les nouvelles tentatives reçoivent temporairement une réponse `429`. Les comptes sont traités uniformément, qu'ils existent ou non.

**Limite de sécurité :** le compteur de tentatives est conservé en mémoire **par processus Python** ; cette protection ne suffit pas en environnement multi-instance/multi-worker. Pour une production : magasin partagé (p. ex. Redis), configuration d'un proxy de confiance et tests de résilience. La portée des accès par lancement reste celle de la 0.15 : les anciens dossiers ne sont pas convertis automatiquement en mode restreint.

## Validation exécutée

- Suite Python complète : **63 tests réussis**, dont la recette d'un lancement fictif (sans ORLI), ses quatre rubriques, le dépôt et la révision d'un document, le téléchargement de deux versions, l'autorisation puis la révocation d'un collaborateur.
- Tests JavaScript existants et vérification syntaxique de tous les modules JS : réussite locale.
- Chromium headless : connexion, liste des dossiers, création via interface, ouverture d'un dossier, navigation rapide, consultation d'un document déposé via l'API, vue étroite, déconnexion mobile, aucune exception JavaScript dans ce parcours.
- **Précision sur le navigateur :** les connexions directes Chromium → `127.0.0.1` sont bloquées par le conteneur ; le test a donc utilisé un pont de requêtes local vers l'API réelle. C'est une vérification fonctionnelle significative, **pas** une preuve d'un parcours navigateur-réseau réel de bout en bout. Une recette manuelle sur un poste Framatex reste nécessaire.

## Installation / migration

1. Sauvegarder le dossier `data/`, incluant la base SQLite et les documents.
2. Arrêter le processus de la version précédente.
3. Remplacer le code en conservant `data/` ; réinstaller les dépendances si nécessaire.
4. Exécuter `python -m app.migrate upgrade` et vérifier `python -m app.migrate status`.
5. Exécuter `python -m pytest -q`, puis redémarrer l'application localement.
6. Suivre la checklist dans `RECETTE_PILOTE.md` avant toute introduction de données réelles.

**Non couvert :** audit de sécurité indépendant, authentification centralisée, stockage chiffré, tests antivirus/charge/sauvegarde et restauration sur infrastructure Framatex, vérification de la conformité métier avec les équipes, et véritable portail extranet.
