## Problème et correction

L’entrée Administration pouvait disparaître au démarrage malgré une session valide : `app.js` appelait un module différé encore absent. Après un classement, un ancien rechargement de lancement pouvait aussi remplacer l’administration et faire disparaître le collaborateur ciblé. Le démarrage attend maintenant les modules et les résultats d’un rechargement ancien sont ignorés après une nouvelle navigation.

La recette partenaires provoque les deux courses, vérifie le compte, la liste puis la conservation de l’administration, et désactive le collaborateur avec confirmation API des rôles et du motif d’audit. Diagnostics et traces excluent les secrets. Le workflow compte trois passages indépendants (tout échec reste bloquant) et exécute aussi Commandes et Guide après un échec précédent. Commandes attend l’onglet réellement actif avant de paginer.

## Validation

- Partenaires : 3/3 sessions propres réussies ; Commandes et Guide réussis.
- Python : suite existante 156 réussis, 1 Gemini réel ignoré ; nouveau test de nettoyage des traces réussi ; ClamAV réel.
- 15 scripts JavaScript, syntaxe, catalogue, manuel et évaluations locale/simulée réussis.
- Deux reproductions avant correction avec traces nettoyées ; détail dans `docs/BROWSER_ADMIN_CI.md` et `artifacts/admin-browser-validation.json`.

Limite : Playwright 1.65.0 installé, mais le téléchargement de Chromium 158.0.8127.18 est refusé (403 réseau). Validation locale avec Chromium système 156.0.8078.79. La réussite des trois recettes avec le navigateur exact en GitHub Actions reste à vérifier avant fusion. Aucun déploiement ni fusion.
