# FRAMATEX — mémoire métier collaborative par sous-dossier

Branche : `feat/business-memory-folder-access`, issue de `feat/access-ux-refinement` (`0ccaa4a9244098ba32e534f94eff52a06fef481e`). Le SHA de livraison est vérifié sur `origin/feat/business-memory-folder-access` après le push.

| Fonctionnalité | État | Validation |
|---|---|---|
| Retours liés à une commande et un sous-dossier | Terminée | API et tests d’accès |
| Lecture/création avec `document.read`, sans `document.write` | Terminée | 4 profils techniciens |
| Filtrage listes, recherche, compteurs, partenaires et vigilances | Terminée | tests confidentialité |
| URL directe, modification d’autrui et révocation | Terminée | tests API |
| Retours historiques non classés chef-only | Terminée | migration et tests |
| Reclassement d’un ancien retour par le chef | Terminée | API, audit et test |
| Formulaire commande/sous-dossier filtré | Terminée | Chromium 11/11 |
| Dépôt uniquement sans lecture | Non réalisé | le modèle actuel impose `document.read` |

## Sécurité

- Un technicien doit fournir une commande et un `folder_slug` autorisé ; le serveur contrôle `document.read` dans cette commande précise.
- Les notes générales et historiques non classées ne sont jamais renvoyées aux techniciens.
- Le justificatif optionnel doit appartenir à la même commande et au même sous-dossier.
- La révocation est évaluée à chaque requête. Les modifications sont limitées à l’auteur ; le chef peut gérer et classer.

## Migration et fichiers

La migration additive `0014_business_memory_folder_access` ajoute `internal_experience_notes.folder_slug` et son index. Aucune donnée n’est supprimée ; les anciennes valeurs restent `NULL` jusqu’au classement explicite.

Fichiers principaux : `app/business_memory_routes.py`, `app/internal_models.py`, `app/migrate.py`, `static/business-memory.js`, les tests mémoire/accès et les scripts de recette.

## Résultats exécutés

- Tests mémoire et habilitations : 20 réussis, 1 avertissement externe Starlette.
- Test frontend dédié : 1/1.
- Recette Chromium Mémoire métier : 11/11, persistance après redémarrage et largeurs 1920, 1440, 1024, 820, 390 px.
- Suites complètes lors du lot P0 : Python 209 réussis ; JavaScript 21/21.

Captures : `artifacts/business-memory-folder-access/memory-ui-final/captures/1440-fiche-partenaire.png` et les captures responsive du même dossier.

## Windows

```powershell
git fetch origin
git switch feat/business-memory-folder-access
git pull --ff-only origin feat/business-memory-folder-access
.\scripts\start_windows.cmd
```

Le lanceur Windows n’a pas été exécuté dans cet environnement Linux.
