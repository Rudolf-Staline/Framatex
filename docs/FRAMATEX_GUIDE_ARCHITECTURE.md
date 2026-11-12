# Architecture de Framatex Guide

Base de travail : `main`, fusion de la PR #34 (`d6cde69`). Branche : `feat/framat-user-guide`. Le guide conserve le modèle métier **une commande = un Dossier Jaune unique**, quatre rubriques, plusieurs lancements. Il ne lit aucun fichier et n’exécute aucune opération métier.

## Une seule chaîne d’aide

`guide_data/catalog.fr.json` contient les procédures françaises, actions et visites versionnées. `navigation.json` ferme la liste des destinations et de leurs permissions. `targets.json` associe les cibles stables aux composants réels. Le backend partage ces registres avec l’espace interne, les fournisseurs, les clients et la recherche. L’ancien `POST /api/assistant/guide` reste un adaptateur local de compatibilité ; son ancien moteur et les anciens rendus conversationnels ont été retirés. `assistant.js` et `workspace.js` délèguent au même composant `guide.js`.

Le composant partagé fournit panneau, centre d’aide `/help`, catégories, recherche locale, procédures détaillées, raccourcis, aide contextuelle, visites Driver.js et retours utilisateurs. Le manuel hors ligne est généré à partir du même catalogue. Les textes de procédure sont toujours ceux du catalogue ; aucun texte libre produit par Gemini n’est affiché comme une instruction vérifiée.

## Permissions et contexte

L’identité provient exclusivement de la session validée. L’en-tête `X-Framatex-Guide-Surface: internal|partner` choisit explicitement la famille de session, ce qui évite de confondre les cookies lorsqu’un navigateur utilise les deux espaces. Il ne confère aucun droit.

Les procédures, visites, destinations et actions sont filtrées à chaque requête. Le serveur vérifie les commandes/lancements via leurs ACL existantes, les demandes via l’organisation du fournisseur et les commandes client via leurs autorisations actives. Une cible sans objet sélectionné déclenche un sélecteur d’objets autorisés ; aucun objet n’est choisi arbitrairement. Les identifiants de ressource ne sont jamais transmis à Google.

Les seules actions exécutables sont la navigation, la consultation d’une procédure et le démarrage d’une visite. La visite peut ouvrir une rubrique ou un formulaire, mais ne déclenche ni dépôt, ni approbation, ni téléchargement, ni message. Les actions issues d’une réponse ne peuvent pas fournir une URL ou un nom de fonction libre.

## Visites et synchronisation

Driver.js 1.12.1, ses styles et sa licence MIT sont livrés localement dans `static/vendor`. Aucun CDN n’est utilisé. Les cibles `data-guide-target` appartiennent aux composants réels. Les visites attendent le rendu, gèrent les changements de page, le clavier, la fermeture et la reprise. Si un formulaire conditionnel n’est pas ouvert ou si une cible disparaît, la visite est suspendue explicitement, son étape est enregistrée et l’utilisateur peut réessayer ou consulter le manuel.

Le contexte de reprise transite seulement dans `sessionStorage`, associé à une empreinte de profil. La session et les droits sont revérifiés à la reprise. Le texte des questions n’y est pas conservé. Les changements de profil ou de session réinitialisent le contexte en mémoire.

## Persistance et migration

Migration additive `0024_user_guide` : `guide_progress`, `guide_preferences`, `guide_visits`, `guide_feedback`, `guide_events`, `guide_budgets`. Aucun objet métier existant n’est modifié.

La clé personnelle utilise deux espaces distincts : `employee:<id>` et `partner:<id>`. Le client ne fournit jamais le propriétaire. La progression est indexée par propriétaire, identifiant de visite et version. Les anciennes versions de progression restent conservées. Les événements minimaux gardent les démarrages, interruptions et fins ; recommencer une visite met à jour son état courant sans supprimer les anciennes versions ou les événements.

`Plus tard` évite une nouvelle sollicitation dans la même session et permet une proposition à une connexion ultérieure. `Ne plus proposer automatiquement` reste persistant. Les visites restent disponibles à la demande. Un utilisateur sans permission métier conserve l’accès à l’aide, mais aucune liste d’objets ni visite interdite ne lui est retournée.

## Maintenance

Exécuter `tools/check_guide_catalog.py`, `tools/build_guide_manual.py --check`, les tests et le parcours navigateur à chaque changement de navigation. Une modification fonctionnelle d’une visite nécessite d’incrémenter sa version, sans réécrire les progressions précédentes. Ajouter une langue consiste à ajouter un catalogue localisé avec les mêmes identifiants et les libellés d’interface correspondants ; le schéma de données et les permissions n’ont pas à être reconstruits. La version livrée est uniquement en français.
