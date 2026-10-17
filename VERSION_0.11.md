# Framatex MVP 0.11 — Imports ORLI et rapprochement contrôlé

## Deux fonctionnalités

**1. Importer un instantané ORLI (CSV / XLSX).** Un administrateur peut importer un export limité à 3 Mo / 1 000 lignes avec une correspondance *explicite* des en-têtes. `orli_ref` correspond à une **référence de lancement de fabrication**, pas à un simple numéro de commande. Les champs facultatifs sont `order_ref`, `client_name`, `designation`, `quantity` et `status`. Les valeurs sont conservées telles que lues, avec les limites de taille ; les références doublonnées dans un même import, absentes ou comportant des erreurs sont signalées et exclues du rapprochement. La somme de contrôle SHA-256 empêche d'importer deux fois exactement le même fichier. Chaque import est historisé. Aucun lancement ni document n'est créé à l'import.

**2. Rapprocher un lancement avec une ligne importée.** Dans chaque dossier, le système propose les lignes pour lesquelles la référence de lancement ORLI **ou** la référence de commande correspond exactement (espaces superflus et casse ignorés uniquement). Le rapprochement est manuel, nécessite le droit `launch.update`, une confirmation explicite et une justification. En cas de divergence de client ou commande, une dérogation motivée est exigée. Les références déjà utilisées par un autre lancement, les lignes invalides, les lignes déjà associées et les lancements clôturés sont refusés. Après confirmation, la référence ORLI du dossier est renseignée uniquement si elle était auparavant vide ; **aucune autre donnée du dossier n'est écrasée**. Un dossier rapproché ne peut pas changer arbitrairement de référence ORLI.

## Comment l'essayer

1. Créer le premier administrateur et lancer l'application selon le `README.md`.
2. Créer un dossier, par exemple « Vestes pilote », avec la référence de commande `CMD-42` **sans ORLI**.
3. Ouvrir **Imports ORLI** dans la navigation. Importer le fichier `examples/orli_export_fictif.csv` (données fictives) avec le mapping proposé par défaut.
4. Ouvrir le dossier « Vestes pilote » et consulter les candidats sous **Rapprochement ORLI**. Vérifier les références puis confirmer avec une justification.
5. Vérifier que le dossier porte la référence importée. L'export d'origine n'est ni réécrit ni envoyé à ORLI.

## Limites et sécurité

- **Aucune connexion ni écriture à ORLI**. Le format réel, les colonnes et l'unicité des identifiants restent à valider avec Framatex.
- L'application ne tente pas de deviner des correspondances floues ; aucune association n'est automatique.
- Les imports sont réservés à l'administrateur ; les suggestions sont affichées aux personnes pouvant modifier le lancement, tandis que les lecteurs ne voient que l'état de liaison courant.
- L'import est une photographie à une date donnée, **pas une synchronisation**. Le module ne déduit pas la validité actuelle des valeurs, et n'interprète pas les coûts métiers.
- L'original de l'export n'est pas enregistré intégralement : seuls son empreinte, ses informations descriptives et les valeurs mappées sont conservés pour limiter l'exposition des données inutiles.
- Le prototype utilise une création de tables automatique : **prévoir une migration versionnée** avant tout déploiement sur une base existante et sauvegarder le dossier `data/` avant mise à jour.

## Tests

`PYTHONPATH=. python -m pytest -q` : 45 tests Python réussis localement.

`for file in tests/*.cjs; do node "$file"; done` : tests JavaScript de toutes les versions réussis localement.
