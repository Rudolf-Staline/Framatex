# Bilan technique vérifié — Framatex MVP 0.17

Ce bilan distingue **constat technique** et **validation par Framatex**.

| Élément | Constat technique | Limite |
|---|---|---|
| Suite Python | 67 tests réussis en environnement isolé | N'établit pas la conformité métier |
| Scripts JavaScript | Tous les `tests/*.cjs` et contrôles `node --check` réussis | Ne remplace pas un test multi-navigateurs |
| Connexion et registre pilote | Parcours Chromium vers API FastAPI locale, sans erreur JavaScript | Jeu fictif, navigateur Chromium uniquement |
| Signalement puis triage | Signalement créé, rendu visible, clôturé avec justification | Utilisateur simulé, pas salarié Framatex |
| Vue mobile | Vérification d'une largeur de 390 px, sans débordement global | Test sur téléphone physique non réalisé |
| Déconnexion | Copie de jeton réutilisée après déconnexion : HTTP 401 | Test d'intrusion indépendant non réalisé |
| Droits de lancement | Requêtes par utilisateur non autorisé refusées, signalements masqués après retrait du droit | Rôles métier réels non validés |
| Migration v0.16 → v0.17 | Table ajoutée, données héritées conservées, sauvegarde produite, réexécution idempotente | Restauration indépendante non réalisée |

**À organiser avec Framatex :** une séance de recette sur poste autorisé, au moins deux profils métier, compte rendu de temps et d'erreurs par scénario, vérification des documents types et des workflows, essai de restauration, puis décision formelle d'autoriser ou non un pilote plus large.
