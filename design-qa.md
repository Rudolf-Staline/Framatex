# Tableau de fichiers — contrôle visuel du 20 octobre 2026

Périmètre : nouvelle demande de retirer le panneau droit « À vérifier » et de reprendre le style de la capture du tableau. Ce contrôle remplace le rapport de blocage visuel initial pour ce composant de bureau ; il ne constitue pas une recette complète de tous les modules.

final result: passed

## Référence et rendu inspectés

- Source : `/workspace/scratch/53cc5695024c/upload/image(20261020-065003).png`, 478 × 205 pixels. Taille CSS et densité source inconnues ; capture partielle du tableau, quatre fichiers fictifs.
- Production inspectée avec une session authentifiée via le formulaire sécurisé : `https://framat-demo.vercel.app/`.
- Version applicative : `3064663da27df67fc9ae1110fce44dbb53029cb9`.
- Capture plein viewport : `/workspace/scratch/53cc5695024c/framatex-fichiers-20261020.jpg`, 1363 × 936 pixels, viewport CSS 1363 × 936, densité 1.
- Capture du composant : `/workspace/scratch/53cc5695024c/framatex-liste-fichiers.jpg`, 1072 × 126 pixels, recadrage de la même capture navigateur.
- Comparaison dans une seule image : `/workspace/scratch/53cc5695024c/framatex-table-comparison.png`.
- Normalisation : source agrandie uniformément 2× pour sa lisibilité, composant de production conservé à 1×. Aucune densité CSS source n’est inventée. Les différences de largeur du viewport et de contenu ne sont pas traitées comme des défauts de style.
- État : sous-dossier Jaune, recherche vide, aucun fichier sélectionné. La production comporte un fichier réel avec trois versions ; les quatre exemples de la référence n’ont pas été ajoutés à la base.

## Constats corrigés et preuves

1. [P1, corrigé] Le panneau droit conservait une colonne entière et une bordure, absentes de la demande. Suppression du panneau et de son appel API ; dépôt déplacé dans l’en-tête. Vérifié dans le DOM authentifié : aucune `.saffron-context`, tableau de 1072 px.
2. [P2, corrigé] Le tableau précédent utilisait une ligne jaune sélectionnée par défaut et débordait de 2 px sur un conteneur de 802 px. Lignes blanches, sélection explicite par cases, colonnes réparties sur toute la largeur. Après correction : `clientWidth = scrollWidth = 1072`, largeur de page 1363 px pour un viewport de 1363 px.
3. [P2, corrigé] Les métadonnées sous le nom et l’icône générique ne reprenaient pas la capture. La taille se trouve désormais sous le nom ; ORLI et historique sont accessibles dans la boîte du document. Icônes officielles Untitled UI File Icons, dont PDF avec symbole Acrobat, rendues mécaniquement sans redessiner les tracés. Image chargée vérifiée : largeur naturelle 40 px.

## Surfaces de fidélité

| Surface | Résultat du contrôle |
| --- | --- |
| Typographie | Inter sur le tableau, nom 14 px/600, données 14 px/400, en-têtes 12 px/500. Famille calculée contrôlée et `document.fonts.check('600 14px Inter')` vrai. |
| Espacement et structure | Six colonnes, cases à gauche, fichier et taille sur deux lignes ; lignes mesurées à 80 px. Suppression de la colonne de contrôle, séparateurs horizontaux fins, absence de débordement bureau. |
| Couleurs et surfaces | Fond blanc, texte principal `#101828`, secondaire `#667085`, séparateurs `#eaecf0`, en-tête `#fcfcfd`. Suppression de la bande jaune sur la première ligne. |
| Images et icônes | Famille officielle de fichiers, PDF Acrobat chargé. Les auteurs réels utilisent leurs initiales ; les portraits et personnes fictives de la référence ne sont pas injectés dans les comptes de production. |
| Texte et contenu | Libellés français, taille et dates réelles, dernier déposant et version réelle. Les adresses email de démonstration de la référence ne sont pas reproduites. |
| Accessibilité et interactions | Cases natives nommées, sélection globale et individuelle, état du nombre sélectionné, liens de fichier accessibles au clavier, onglets testés avec les flèches et focus transféré à l’onglet actif. |

## Interactions réellement vérifiées

- Sélection de tous les fichiers affichés : case et ligne cochées, barre « 1 fichier sélectionné » affichée ; désélection rétablit l’état initial.
- Clic sur le fichier : ouverture des actions, affichage de la référence ORLI et de la version, historique des trois versions et accès au REX contextualisé conservés.
- Recherche sans correspondance : état « Aucun résultat » ; effacement restaure le fichier.
- Filtre Word : aucun résultat pour le document PDF ; remise sur Tous les types.
- Passage à Rose : état vide sans panneau droit ; retour à Jaune avec les flèches du clavier.
- Aucun dépôt ni changement de données métier effectué pendant ces contrôles.

## Vérifications techniques et limites

- GitHub Actions de la PR #25 : réussi, avec 92 tests Python et 30 scripts JavaScript.
- Ajustement d’icônes : syntaxe JavaScript, test du registre, chargement réel des images et comparaison visuelle après déploiement.
- Aucun journal d’erreur/fatal Vercel trouvé pour le déploiement applicatif contrôlé.
- La lecture de l’historique console navigateur a été interrompue par la protection de rétention après connexion sécurisée. Aucune affirmation « sans erreur console » n’est faite.
- Les largeurs mobile/tablette ne sont pas déclarées visuellement vérifiées : l’API navigateur n’a pas permis de changer le viewport. Le tableau conserve ses colonnes dans une zone de défilement interne sur ces largeurs.

## Historique de comparaison

- Capture initiale authentifiée : panneau droit, ligne jaune et débordement constatés.
- Premier déploiement : panneau supprimé, mesures de largeur et sélection vérifiées ; icône PDF encore différente.
- Ajustement : adoption des icônes officielles de fichiers.
- Dernière capture et comparaison commune : corrections visibles, image chargée, aucune anomalie P0/P1/P2 restante sur le composant bureau demandé.

## Contrôles restants hors périmètre de cette capture

- Recette visuelle à 390 et 768 px et zoom 200 %.
- Relecture complète de la console dans une session de diagnostic sans historique de connexion protégé.
- Les portraits réels des utilisateurs demanderaient des images de profil fournies par leurs comptes ; les initiales restent la représentation actuelle.
