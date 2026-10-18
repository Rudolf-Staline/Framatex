# Version 0.19 — Interface blanche et accents bleus

## Objectif

Reprendre le langage visuel validé pour Framatex : **fond global blanc**, textes anthracite, cartes à bordures gris clair et **bleu** pour les actions principales et éléments actifs. La maquette de référence inspire la composition sans être recopiée comme une image figée.

## Modifications livrées

- **Tableau de bord** : nouveau bandeau d'accueil avec illustration CSS, accès rapides à la création et aux dossiers, quatre indicateurs et lancements récents. Une colonne dédiée à **Framatex Assist** permet de poser une question sans quitter la vue générale.
- **Navigation** : barre latérale blanche, sélection bleu clair, icônes homogènes, raccourci direct vers l'assistant et barre supérieure allégée.
- **Assistant** : espace conversationnel dédié avec fil de discussion de la session, questions fréquentes, accès aux dossiers autorisés et liens vers les rubriques. Le panneau de l'accueil continue d'utiliser exactement le même service de réponses.
- **Dossiers jaunes et modules métier** : harmonisation des fonds, tableaux, boutons, étiquettes, boîtes de dialogue et champs. Les sous-dossiers Jaune, Rose, Bleu et Vert conservent leurs couleurs de repérage métier.
- **Responsive** : affichage en une colonne sur les écrans étroits ; la décoration du bandeau est masquée sur téléphone pour préserver la lisibilité. Navigation horizontale défilante ; déconnexion toujours accessible.
- **Accessibilité** : étiquettes de champs, états de focus visibles, région conversationnelle annoncée (`aria-live`) et prise en compte de `prefers-reduced-motion`.

## Périmètre et sécurité

Aucun modèle d'IA externe n'a été ajouté. L'assistant interroge toujours uniquement `POST /api/assistant/guide` ; les réponses restent fondées sur les procédures locales et respectent les contrôles d'accès côté serveur. Il ne télécharge pas les fichiers du lancement pour en inférer le contenu. La mémoire de conversation est **locale à la page**, non enregistrée en base.

Aucun schéma de données ou endpoint métier n'a été modifié. **Aucune migration supplémentaire n'est nécessaire** pour passer de la version 0.18 à la version 0.19.

## Vérifications

- `python -m pytest -q` — **67 tests réussis**.
- `for file in tests/*.cjs; do node "$file"; done` — tests JavaScript réussis.
- `for file in static/*.js; do node --check "$file"; done` — syntaxe validée.
- Chromium piloté en local avec une passerelle de test vers l'API : dashboard, question en ligne, espace assistant, ouverture d'un dossier, écran large (1672 px), laptop (1280 px), mobile (390 px). Pas d'erreur JavaScript ni de débordement horizontal relevé.

Les scénarios ont été vérifiés sur des **données fictives**. Les essais ne remplacent pas une recette en entreprise ou un audit indépendant de sécurité.

## Installation

Depuis le répertoire du projet, après sauvegarde d'une éventuelle installation existante :

```bash
python -m pip install -r requirements.txt
python -m app.migrate upgrade
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Se reporter au `README.md` pour la création du premier administrateur et les consignes de sécurité.
