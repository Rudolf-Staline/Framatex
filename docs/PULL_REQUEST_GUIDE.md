## Problème et comportement livré

L’ancien assistant proposait quelques procédures par mots-clés et conservait des descriptions liées au dossier par lancement. Framatex Guide partage désormais un catalogue vérifié entre espace interne, fournisseurs, clients et recherche, selon le modèle courant : une commande = un Dossier Jaune unique.

Le centre d’aide permanent et `/help` offrent 56 procédures, recherche, catégories, récents, raccourcis et retours. Les 60 visites Driver.js locales présentent les vrais écrans, demandent explicitement le choix d’un objet autorisé et enregistrent une progression personnelle versionnée. Elles ne déposent, ne valident et n’envoient aucune donnée métier. L’endpoint historique délègue au même moteur.

Gemini est facultatif et désactivé par défaut. Le SDK officiel sélectionne uniquement des identifiants parmi les procédures déjà autorisées. Le texte brut des questions, les documents et les identifiants métier ne sont pas envoyés. Sorties invalides, budgets, absence de clé et indisponibilité conduisent au catalogue local.

## Migration et risques

Migration additive `0024_user_guide`, six tables indépendantes des données métier ; séparation des propriétaires employés/partenaires. Sauvegarde cohérente et arrêt des écritures selon la procédure habituelle avant toute installation ultérieure. Le retour complet utilise la sauvegarde et le code correspondants. Aucun déploiement ni fusion automatique.

Les cibles conditionnelles absentes suspendent explicitement une visite. Les 43 contrats de source sont contrôlés, tandis que Chromium couvre les parcours critiques. Disponibilité du modèle demandé et gain réel de Gemini non qualifiés : aucun appel Google réel n’a été effectué. Le manuel est français ; des exemples métier de complétude, circuits et ORLI restent à approfondir avec Framatex.

## Validation

- Suite complète Python : 138 réussites, un test Gemini réel ignoré ; groupe ciblé Guide : 18 réussites et un test réel ignoré ; migration/restauration : deux réussites.
- 122 questions annotées : 100 % sur le jeu local fini, refus et raccourcis contrôlés ; aucune généralisation ni amélioration Gemini présumée.
- Tests JavaScript, catalogue, routes, cibles, manuel synchronisé et ressources Driver locales.
- Trois parcours Chromium : fournisseurs/clients existants, dossiers/versions existants, nouveau Guide avec quatre profils, sélection d’objet, multi-écrans, reprise, cible absente et absence d’envoi métier.
- Axe sans violation sur le panneau aux quatre largeurs testées ; résultat limité aux écrans exercés.

Voir [rapport de livraison](https://github.com/Rudolf-Staline/Framatex/blob/feat/framat-user-guide/docs/FRAMATEX_GUIDE_DELIVERY.md), [tests](https://github.com/Rudolf-Staline/Framatex/blob/feat/framat-user-guide/docs/FRAMATEX_GUIDE_TESTS.md), [configuration Gemini](https://github.com/Rudolf-Staline/Framatex/blob/feat/framat-user-guide/docs/FRAMATEX_GUIDE_GEMINI.md) et [manuel](https://github.com/Rudolf-Staline/Framatex/blob/feat/framat-user-guide/GUIDE_UTILISATEUR_FRAMATEX.md). Preuves et captures synthétiques dans `artifacts/guide-*`.
