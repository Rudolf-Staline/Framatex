# Version 0.4 — Deux innovations dans une livraison

**Livraison : 17 octobre 2026 · prototype local destiné aux essais, non à la production.**

## 1. Cohérence inter-documents

- Une règle administrateur spécifie deux **types documentaires** et leur **rubrique**, un champ métier et une tolérance numérique **absolue**.
- Un utilisateur habilité relève une valeur, son unité et la version exacte du document. Une valeur déjà enregistrée sur une version ne peut pas être écrasée ; il faut une nouvelle version du fichier.
- Le moteur compare les versions les plus récentes des deux sources et distingue : cohérent, écart, donnée manquante, unité incompatible, source ambiguë.
- Une différence reste un **point à examiner**, pas une erreur prouvée. La décision motivée (justifié / correction nécessaire) est attachée aux versions et valeurs comparées. Dès qu’une version change, l’ancienne décision ne vaut plus pour la nouvelle comparaison.
- Les données issues d’une rubrique interdite sont intégralement masquées par le serveur. La qualification nécessite le droit `quality.review` sur les deux rubriques.

**Exemple fictif** : « Lancement provisoire » = 1 500 pièces, « Lancement définitif » = 1 450 pièces. Le moteur montre l'écart, sans déclarer automatiquement le lancement définitif faux.

## 2. Système immunitaire Excel

- Lors d’un dépôt de classeur `.xlsx` dans l’application, une **inspection statique** est enregistrée automatiquement sur sa version.
- La première version sert de référence. Sur une nouvelle version du même document, l'inspecteur peut relever une cellule passée de formule à constante, une formule modifiée ou une référence `#REF!`.
- L'inspection n'exécute aucune formule, ne lance aucune macro et ne modifie aucun fichier. Les formules changées sont des avertissements à vérifier.
- Limites explicites : 5 Mo, 40 000 cellules et 200 signalements par inspection ; un classeur hors limites produit un état « analyse limitée ». Le fichier peut malgré tout être stocké selon les limites classiques de dépôt.

**Exemple fictif** : une cellule `=A1*A2` devient `2850` dans la version suivante. Le moteur signale une formule remplacée alors que le montant affiché peut sembler plausible.

## Interface

Dans le détail d’un lancement, rubrique **Fiabilité documentaire** :
1. « Relever une valeur » sur un document et sa version courante.
2. « Configurer une comparaison » (administrateur).
3. Affichage des paires de données et qualification des écarts.
4. Historique des inspections Excel avec cellules signalées.

## Démonstration et tests

Après `python -m app.seed_demo`, lancer `python -m app.seed_quality_demo` (idempotent), puis ouvrir « Chemises manches longues · pilote B ».

Tests prévus : `python -m pytest -q` et `node tests/test_quality_frontend.cjs`. Les tests couvrent les écarts, les tolérances, les décisions rendues obsolètes, les permissions, les formules remplacées et les références invalides.

## Précautions

- Les valeurs comparées sont **saisies après lecture humaine**, sans OCR ni rapprochement des contenus PDF. Une incohérence plausible n’est pas une preuve de non-conformité.
- Une règle qui désigne plusieurs documents de même type n’arbitre pas automatiquement entre eux.
- Le moteur Excel ne vérifie pas les erreurs de calcul financier et n’évalue pas les liens Excel externes.
- La sécurité de ce prototype (SQLite, analyse de fichiers sur le serveur local, absence de migrations versionnées) ne suffit pas à un déploiement Framatex sans revue spécialisée.
