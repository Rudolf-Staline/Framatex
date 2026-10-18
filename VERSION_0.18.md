# Framatex MVP 0.18 — Refonte de l'interface

## Objectif

Repenser l'expérience visuelle du **MVP 0.17** en s'inspirant des principes d'organisation du projet Dribbble **AI Document Management Dashboard UI** de VALMAX, sans recopier son interface ni utiliser ses visuels. Le projet garde son architecture (FastAPI, interface JavaScript, SQLite) et l'ensemble des fonctionnalités métier existantes.

## Changements

- **Système visuel sombre** : anthracite, vert profond, touches menthe, typographie plus affirmée, surfaces et états visuels cohérents ; illustration abstraite créée en CSS, sans image tierce.
- **Tableau de bord reconstruit** : zone de bienvenue opérationnelle, indicateurs métiers, lancements récents, assistant contextuel, état du prototype et actions à traiter.
- **Navigation restructurée** : sections Travail et Gestion & contrôle, nouvelle barre supérieure et recherche qui ouvre la bibliothèque avec le champ de recherche actif.
- **Dossiers jaunes** : sous-dossiers et tableaux harmonisés avec le nouveau thème ; rubriques fonctionnelles conservées (complétude, décisions, Excel, OCR, ORLI, matières, clients/fournisseurs, recette pilote, etc.).
- **Assistant de navigation** : remplacement de l'ancienne fenêtre par un panneau conversationnel avec messages successifs, suggestions rapides, réponses de l'API existante et liens internes. Le serveur continue d'appliquer les droits.
- **Mobile** : grilles et tableau de bord adaptatifs, barre de navigation horizontale, panneau assistant pleine largeur et boutons accessibles.
- **Accessibilité** : états de focus visibles, labels, rôles de dialogue, réduction des animations selon les préférences du système.

## Portée réelle du chatbot

Le chatbot **n'utilise pas de modèle génératif** ; il appelle `/api/assistant/guide`, fondé sur des procédures locales. La présentation conversationnelle n'implique pas de compréhension libre des documents ni de réponse aux questions métier complexes. Les demandes hors périmètre donnent lieu à une reformulation. Les informations sont filtrées par les autorisations.

## Vérification

`python -m pytest -q` et `for file in tests/*.cjs; do node "$file"; done`. Les parcours sur navigateur sont testés avec une API locale de démonstration, exposée aux pages de test par un pont interne (le navigateur de cet environnement bloque les connexions directes aux ports locaux). Des captures sont disponibles dans la livraison, avec des données fictives.

## Mise à jour

La 0.18 n'ajoute **aucune migration de base de données** : elle modifie la présentation et les tests frontaux. Sauvegarder le dossier `data/` avant tout remplacement du code. Ne pas utiliser de données confidentielles avant validation de Framatex.

## Référence de conception

VALMAX, [AI Document Management Dashboard UI](https://dribbble.com/shots/27150848-AI-Document-Management-Dashboard-UI). Inspiration : hiérarchie, densité, thème sombre et place de l'assistant. Toutes les interfaces et l'illustration de Framatex ont été recréées indépendamment.
