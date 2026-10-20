# Bibliothèque safran — validation du design 1

Date : 20 octobre 2026.

## Résultat

final result: blocked

La transposition et les tests techniques sont terminés. Le rendu navigateur n’a pas pu être capturé : l’ouverture de `http://terminal.local:4173/` a renvoyé `net::ERR_BLOCKED_BY_CLIENT`, puis le navigateur a explicitement refusé l’observation au titre de sa politique d’accès aux URL. Aucun autre mécanisme de navigateur ni autre adresse locale n’a été utilisé pour contourner ce refus. Une réponse HTTP ou le démarrage du service ne constitue pas une validation visuelle.

Après ce constat initial, l’utilisateur a explicitement demandé le déploiement, effectué le 20 octobre 2026. La comparaison visuelle reste à reprendre. Ce rapport ne valide ni la fidélité graphique ni l’absence de régression responsive.

## Cible et preuves

- Source visuelle : proposition 1 « Bibliothèque safran », image générée choisie par l’utilisateur.
- Chemin de la source dans la session : `/workspace/scratch/53cc5695024c/generated_images/exec-ad57eefd-5a8c-4a80-a01b-f04fa5dcd602.png`.
- Dimensions source : 1487 × 1058 pixels, interface bureau sans cadre ; densité CSS non spécifiée par l’image.
- État cible : utilisateur connecté, Dossier Jaune ouvert, rubrique Technique/Jaune, six documents, première ligne sélectionnée, deux vérifications à droite.
- Implémentation : `static/app.js`, `static/global-library.js`, `static/design-safran.css`, dernière feuille chargée dans `static/index.html`.
- Capture de l’implémentation : indisponible, accès navigateur refusé.
- Viewport/CSS/densité de l’implémentation : non mesurés ; normalisation non réalisée.
- Comparaison plein écran côte à côte : bloquée, capture de l’implémentation manquante.
- Comparaisons de détail : bloquées pour le même motif ; devront couvrir navigation, onglets, tableau, panneau et boîte d’actions.

L’aperçu temporaire est distinct du dépôt. Il utilise les fichiers frontend du dépôt et des réponses synthétiques exportées depuis les véritables routes FastAPI sur une base SQLite jetable. Aucun jeu de données, session ou mécanisme d’authentification de cet aperçu n’est inclus dans la branche.

## Surfaces à vérifier visuellement

| Surface | Implémentation préparée | Validation restante |
| --- | --- | --- |
| Polices et typographie | DM Sans et Plus Jakarta Sans conservées ; titre 40 px, texte de document 14 px | Chargement réel, poids, coupures, hiérarchie et rendu aux autres largeurs |
| Espacement et structure | Barre latérale ivoire, onglets plats, tableau, panneau séparé par un filet | Proportions, densité, hauteur des lignes et alignements avec la source |
| Couleurs et jetons | Safran pour Jaune ; thèmes Rose/Bleu/Vert conservés ; texte secondaire et focus assombris pour le contraste | Contraste calculé réel après cascade, états actifs et focus dans le navigateur |
| Images et icônes | Aucune image de contenu dans la cible ; icônes Phosphor officielles vendues avec licence MIT | Chargement du sprite externe, taille et alignement des icônes |
| Texte et contenu | Libellés français ; contrôles calculés et contexte ORLI ; aucune anomalie de démonstration codée en dur | Coupures et lisibilité avec les données réelles, libellés longs |
| Responsive et accessibilité | Menu mobile, onglets clavier, filtrage, focus visible, réduction des animations | Captures à 1487, 1024, 768, 390 et 320 px ; zoom 200 %, parcours Tab/Escape, absence de débordement |

## Vérifications techniques effectuées

- API et logique métier : 85 tests Python réussis.
- Frontend : 29 scripts de contrôle Node réussis, dont un nouveau contrôle de contexte Safran.
- Syntaxe de tous les fichiers JavaScript et `git diff --check` : réussis.
- Contrôles de contexte testés : ORLI et droits de lecture, unités incompatibles sans conversion, états indisponibles distincts d’un résultat vide, filtrage, tri sans mutation de l’archive, historique et téléchargement courant, préremplissage du REX et réponse tardive après navigation.
- Les tests frontend utilisent un environnement VM avec stubs DOM. Ils ne remplacent pas les interactions dans un navigateur.
- Interactions primaires dans le navigateur : non exécutées, accès refusé avant le rendu.
- Console navigateur : non inspectable sur l’aperçu bloqué ; aucune conclusion « sans erreur ».

## Historique de comparaison

1. Source choisie ouverte et inspectée ; transposition dans l’application existante.
2. Service d’aperçu démarré ; ouverture via le navigateur sélectionné refusée. Capture et comparaison bloquées avant le premier passage visuel.
3. Aucune itération de fidélité déclarée. Les corrections de logique et tests techniques ne sont pas comptées comme des passages de QA visuelle.

## Liste de reprise

1. Ouvrir une prévisualisation autorisée de la branche avec une session de test.
2. Capturer l’état cible et comparer la source et le rendu dans une même image normalisée.
3. Vérifier dépôt, recherche, filtres, changement de rubrique, tri, historique/téléchargement, lien vers les vérifications et création/consultation/interrogation d’un REX.
4. Contrôler les largeurs indiquées, le clavier et les erreurs console.
5. Corriger les défauts P0/P1/P2 éventuels, recapturer et comparer ; passer ce rapport à `final result: passed` uniquement après cette vérification.
6. Fusionner et déployer après validation visuelle.


## Itération suivante — rôles simples et registre de fichiers

La demande du 20 octobre à 06:50 remplace la création de rôle détaillée par une matrice Accès / Modification pour Jaune, Rose, Bleu et Vert. Les nouveaux booléens sont traduits côté serveur vers les droits existants ; modification sans accès est rejetée, les rôles existants restent inchangés et aucun accès global aux anciens lancements n’est accordé implicitement.

Le tableau reprend la capture fournie : nom du fichier avec métadonnées discrètes, taille réelle de la dernière version, date d’ajout du document, mise à jour et auteur réel du dernier dépôt. Les auteurs sont résolus après application des droits de lecture ; aucune adresse email n’est ajoutée à la réponse documentaire.

Référence : `/workspace/scratch/53cc5695024c/upload/image(20261020-065003).png`, 478 × 205 pixels. Validation de cette itération : tests API de refus/autorisation, compatibilité des rôles, attribution de la dernière version, et tests frontend de la matrice, des métadonnées et de l’échappement HTML. Aucun nouveau rendu de l’espace connecté n’a été capturé ; les limites de validation visuelle restent inchangées.
