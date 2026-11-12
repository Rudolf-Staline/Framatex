# Catalogue et inventaire Framatex Guide

Le catalogue comprend **56 procédures, 60 visites dont quatre découvertes par profil, 168 actions enregistrées et 43 contrats de cibles**. Ces nombres sont contrôlés automatiquement, ils ne désignent pas autant de nouvelles fonctions métier.

L’inventaire confronte les fonctions réelles de `app.js`, `orders.js`, `partners.js`, les modules métier et leurs routes. Il couvre tableau de bord, commandes, dossier canonique, rubriques, lancements, dépôts, versions, recherche, contrôles, complétude, cohérence, extraction à confirmer, réceptions/matières, validations, réouverture, historique, notifications, priorités, annuaires, administration, droits, ORLI, fournisseurs et clients. Les parcours d’activation, correction, messages, pièces administratives, livraisons, publications et clarifications sont séparés par profil.

Les sources de vérité sont :

- `app/guide_data/catalog.fr.json` : identifiant, version, langue, titre, catégorie, profils, mots-clés, prérequis, étapes permanentes, résultat, problèmes fréquents, limites, actions, visite et sources.
- `app/guide_data/navigation.json` : destinations, rendu réel, surface, contexte et permissions.
- `app/guide_data/targets.json` : contrat entre cible stable et composant source.
- `GUIDE_UTILISATEUR_FRAMATEX.md` : manuel généré, lisible sans IA.

`tools/check_guide_catalog.py` vérifie les identifiants, références, permissions déclarées, actions fermées, sources, routes réelles et marqueurs. Le parcours Chromium complète ces contrôles sur les éléments effectivement rendus. Les marqueurs ne sont pas des sélecteurs CSS décoratifs et ne donnent aucun droit supplémentaire.

Les rubriques et procédures affichent les limites connues : règles obligatoires à valider par Framatex, corpus réel d’extraction non qualifié, transport SMTP et synchronisation ORLI directe indisponibles sans leurs dépendances. Le guide ne les présente pas comme des services actifs.

## Mise à jour

1. Vérifier le parcours et ses permissions dans le code et le navigateur.
2. Modifier la procédure, son action et sa cible enregistrée ; conserver son identifiant.
3. Incrémenter la version d’une visite si son déroulement change.
4. Ajouter ou adapter les questions de référence, sans dériver les réponses attendues du moteur de recherche.
5. Régénérer le manuel puis exécuter les contrôles de cohérence et de navigation.

Le catalogue ne comporte aucune URL libre envoyée à Gemini. Un bouton de procédure est résolu par l’application et vérifié à nouveau côté serveur. Les procédures liées à une création ou un envoi ne constituent jamais une autorisation d’effectuer cette opération à la place de l’utilisateur.
