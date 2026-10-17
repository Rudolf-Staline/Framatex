# Framatex MVP 0.12 — Traçabilité matière et rapprochement des quantités

## Deux fonctionnalités livrées

**1. Traçabilité des matières par lancement de fabrication.** Chaque matière a une référence et une unité uniques à l'intérieur de son lancement (m, m², kg, g, pcs ou L). Un responsable crée une prévision de quantité associée à une **version précise d'une pièce du dossier Jaune**. Les révisions de cette prévision sont conservées : une nouvelle valeur ne supprime pas les précédentes.

**2. Rapprochement prévu / commandé / réceptionné.** Les commandes et réceptions sont consignées en **mouvements distincts et sourcés**, respectivement par une pièce du Jaune et une pièce du Rose. Un tableau présente : quantité prévue, quantité commandée, quantité réceptionnée, écart prévu–commandé et écart commandé–réceptionné. Les écarts au-delà du prévu et les réceptions supérieures aux commandes donnent lieu à une indication de vérification, sans être automatiquement qualifiés d'erreurs : les livraisons peuvent être partielles et le suivi incomplet.

Les mouvements sont conservés dans le journal ; en cas d'erreur de saisie, un responsable procède à une **annulation motivée**. L'entrée d'origine reste consultable et ne contribue plus aux totaux. Aucun mouvement n'est envoyé à ORLI ; aucun stock réel n'est modifié.

## Utilisation

1. Ouvrir un dossier de lancement, puis déposer au moins une fiche de besoin technique dans **Jaune** et, le cas échéant, une pièce de commande dans Jaune et un bon de réception dans **Rose**.
2. Dans « Traçabilité et rapprochement des matières », cliquer sur **Ajouter une matière**. Renseigner référence, désignation, unité, quantité prévue, version justificative et justification.
3. Utiliser **Enregistrer une commande** avec une pièce Jaune et **Enregistrer une réception** avec une pièce Rose. Chaque mouvement contient une quantité et une source documentaire.
4. Lire les totaux et écarts. Si une pièce a une nouvelle version, le justificatif précédent est signalé comme **à revérifier** ; l'historique demeure.
5. En cas de saisie incorrecte, utiliser **Annuler** et expliquer le motif. Une nouvelle entrée pourra être créée avec la valeur correcte.

## API

- `GET /api/launches/{id}/materials` — vue de synthèse et historique.
- `POST /api/launches/{id}/materials` — matière et première prévision.
- `POST /api/launches/{id}/materials/{line_id}/plans` — nouvelle prévision historisée.
- `POST /api/launches/{id}/materials/{line_id}/movements` — commande / réception sourcée.
- `POST /api/launches/{id}/materials/{line_id}/movements/{movement_id}/cancel` — annulation motivée.

Les quantités sont stockées en décimal (3 décimales maximum, pas de valeurs négatives pour les saisies) ; la cohérence des unités est assurée au niveau de chaque ligne matière. La lecture globale nécessite les droits `launch.read` et `document.read` sur **Jaune et Rose** pour éviter la divulgation indirecte des volumes de réception. Les écritures nécessitent `launch.update` et un droit `document.write` sur le sous-dossier de la pièce utilisée.

## Limites connues

- **Pas de contrôle de stock réel** : les quantités proviennent de saisies humaines, non d'une extraction fiable de l'ERP. Le module ne garantit ni la réception physique, ni l'état d'une commande fournisseur.
- **Pas de conversion d'unités** : une ligne garde une seule unité ; il faut vérifier la correspondance métier des quantités avant saisie.
- **Pas de validation de commande commerciale, de tolérance logistique ou de date d'arrivée** : les règles de gestion devront être confirmées avec Framatex.
- Les données d'ORLI importées en version 0.11 ne sont **pas** injectées automatiquement dans les quantités matières ; ce rapprochement nécessiterait un schéma d'export métier validé.
- Ce prototype conserve une base locale SQLite et la création de tables au démarrage. Une migration SQL versionnée, la sécurité du serveur, la validation des droits plus fins et une sauvegarde/restauration éprouvée sont indispensables avant un usage réel.

## Vérifications

`PYTHONPATH=. python -m pytest -q` : **48 tests Python réussis**.

`for file in tests/*.cjs; do node "$file"; done` puis `node --check static/*.js` : rendu des fragments et syntaxe JavaScript vérifiés.
