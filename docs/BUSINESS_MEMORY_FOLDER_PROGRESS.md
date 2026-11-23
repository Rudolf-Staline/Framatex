# FRAMATEX — progression mémoire métier par sous-dossier

Branche : `feat/business-memory-folder-access`, issue de `feat/access-ux-refinement` à `0ccaa4a9244098ba32e534f94eff52a06fef481e`.

## Lot P0 terminé

- Migration additive `0014_business_memory_folder_access` : champ nullable `folder_slug` et index pour `internal_experience_notes`.
- Les anciens retours restent inchangés et non classés (`folder_slug = NULL`) ; ils restent réservés au chef jusqu'à une classification explicite.
- Pour un technicien, la lecture et la création nécessitent une commande et un sous-dossier précis avec `document.read` effectif. `document.write` n'est jamais requis pour la mémoire métier.
- Listes, recherche, compteurs, fiches partenaires, vigilances, accès direct et historique de décisions filtrent les retours par commande **et** sous-dossier.
- Le formulaire reçoit ses commandes/sous-dossiers autorisés du serveur ; les justificatifs sont limités au même sous-dossier.
- Le bouton depuis une commande est affiché après vérification serveur du sous-dossier courant.
- Le chef peut classer explicitement un ancien retour lié à une commande ; ce reclassement est audité. Un technicien ne peut pas déplacer un retour.

## Tests ciblés exécutés

- `tests/test_business_memory.py` + `tests/test_access_management.py` : 20 réussis.
- `tests/test_business_memory_folder_frontend.cjs` : 1 réussi.
- `scripts/validate_business_memory_ui.py` : 11/11 (chef, formulaire, persistance, 1920 à 390 px).
- Suites complètes avant le reclassement final : Python 209 réussis ; JavaScript 21/21.

## À faire avant livraison finale

- Rapport final, commit et vérification du push distant.
