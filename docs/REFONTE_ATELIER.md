# Framatex — refonte Atelier

La refonte est implémentée sur la branche `feat/atelier-interface-20261021`, à partir de la dernière version `feat/clients-portal-ux-20261020` (`c3aba87`). Elle conserve FastAPI, les données, les API et les contrôles d’accès existants.

## Interface et parcours

- Espace clair, jaune franc, icônes Phosphor cohérentes, typographie DM Sans hébergée avec l’application.
- Navigation latérale simplifiée, recherche de commande par `Ctrl K` / `⌘ K`, assistant flottant conservé.
- Commandes : filtres par statut, recherche sans accents, tri par mise à jour, livraison ou nom, vues liste et grille, pagination.
- Le filtre client repose sur son identifiant : deux sociétés homonymes ne mélangent pas leurs dossiers.
- Création progressive : le nom suffit. Les informations de production et le rattachement au portail restent facultatifs. Les quatre sous-dossiers sont créés par le serveur.
- Dossier : identité et informations principales, quatre rubriques colorées, documents et outils distincts, recherche documentaire.
- Dépôt : glisser-déposer, contrôle du format et de la taille, titre proposé depuis le fichier, retour d’erreur et protection contre les doubles soumissions.
- Dialogues : navigation clavier et fermeture existantes conservées, arrière-plan inactif et défilement bloqué pendant la saisie.
- Animations discrètes, désactivées selon la préférence de réduction des mouvements.

## Cohérence métier

Les dates de livraison sans heure ne changent plus de jour selon le fuseau du navigateur. La validation affichée tient compte des revues de la version courante lorsque aucun circuit n’est présent. Les textes de publication décrivent le portail client réel et le rattachement à un client du répertoire est requis dans l’interface. Les demandes fournisseurs restent internes.

Les contrôles de publication, permissions, versions, approbations et isolation entre clients restent exécutés par le serveur.

## Maintenance

Le navigateur charge deux feuilles de style : `legacy-ui.css` et `atelier.css`. Les anciens styles de modules restent isolés dans la couche CSS `legacy`. Le fichier de compatibilité est généré avec :

```sh
python scripts/build_legacy_css.py
```

Les règles du nouveau produit se trouvent dans `static/atelier.css`. La licence des polices est conservée dans `static/fonts/OFL.txt`.

## Vérifications effectuées

- 105 tests Python réussis, couvrant notamment les API, droits, clients, documents, validations et publications.
- 32 scripts de vérification JavaScript réussis, avec ajout de cas pour les sociétés homonymes, les accents, la pagination, le tri sans date et les fuseaux horaires.
- Syntaxe de tous les fichiers JavaScript contrôlée.
- Parcours dans Chromium sur une base locale de démonstration : connexion, recherche, création, dépôt et accès aux douze outils du dossier.
- Dossier vérifié aux largeurs 320, 390, 768, 1024 et 1440 pixels ; liste et clients vérifiés sur mobile. Les grands tableaux défilent dans leur zone, sans élargir la page.

## Livraison

L’utilisateur a autorisé l’envoi de la branche `feat/atelier-interface-20261021` vers `Rudolf-Staline/Framatex` et le déploiement d’une prévisualisation Vercel du projet `framat-demo`. Les données de test locales et les captures de vérification ne font pas partie de la livraison.
