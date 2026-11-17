# Sélecteurs de lancement au-delà de 100 choix

## Défaut confirmé et correction
Le serveur bornait déjà la liste générale et l'accueil métier à 100 lancements,
mais les sélecteurs ne proposaient ni recherche ni page suivante. Un lancement
ancien pourtant autorisé devenait introuvable. L'ancienne route administrative
`/api/partners/launch-options` chargeait inversement toute la collection.

- La route administrative conserve sa dépendance d'administration et sa réponse
  liste `{id,label}`, avec `q`, `offset` et `limit` (100 par défaut, maximum 100).
  Les permissions et le prédicat SQL canonique précèdent recherche et pagination.
- Les sélecteurs partenaires d'administration et de travail quotidien proposent
  une recherche par nom, client, référence de commande ou ORLI et des pages de
  100 choix. Ils réutilisent `/api/launches?page=true`, dont les compteurs et
  résultats excluent les lancements interdits avant pagination.
- Le rattachement historique depuis le Dossier Jaune dispose du même accès
  par recherche et pages. Une réponse ancienne ne remplace pas une recherche
  plus récente ; fermer le dialogue empêche toute mise à jour tardive.
- Aucun nouveau droit attribué. Les comptes achats non administrateurs ne peuvent
  toujours pas appeler l'ancienne route administrative. Les choix chargés dans
  l'accueil métier restent légers ; il n'est pas nécessaire de charger tout le
  corpus pour proposer les lancements suivants.
- L'intégration contient également les jetons de navigation centraux : une réponse
  dossier tardive n'écrase pas une page d'administration choisie entre-temps.

## Vérifications
- `FRAMATEX_DATA_DIR=$(mktemp -d /tmp/framatex-selectors-test.XXXXXX) PYTHONPATH=. python -m pytest -q tests/test_consolidation_selectors.py`
  → **1 réussi en 4,14 s**. Corpus de 123 lancements ; un lancement autorisé ancien
  absent de la première page et un résultat restreint portant le même préfixe.
  Vérifications nom/client/commande/ORLI, pagination, compteurs, limites de requête,
  absence d'identifiant/titre/client interdit et refus de l'API administrative.
- `FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium PYTHONPATH=. python tools/check_launch_selectors_browser.py`
  → **réussi** : recherche dans le dialogue historique, recherche achats non
  administrateur et deuxième page de 22 choix comprenant le lancement ancien.
  Aucune erreur JavaScript. Preuve : `artifacts/consolidation-selectors-browser.json`.
- `node --check static/orders.js`, `node --check static/partners.js` et
  `node tests/test_consolidation_navigation.cjs` : réussis.

Les données et identités sont synthétiques, en répertoire temporaire. Le test
Chromium est un contrôle ciblé de contrat ; les contrôles axe/mobile globaux du
parcours dossier/partenaires restent documentés séparément.
