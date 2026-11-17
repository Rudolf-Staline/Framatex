# Lot 4 — gestion documentaire

Départ : 33e7836. Ancienne branche `feat/commande-identification` lue au commit 371c259 (fichier order_fields et interface), sans fusion globale.

## Réalisé
- Fiche facultative commune à la commande : programme/collection, article/modèle, quantité décimale et unité, livraison prévue, observations. Client/référence affichés depuis BusinessOrder ; ORLI depuis le lancement.
- Fiche distincte par lancement, avec son atelier : aucun atelier unique imposé à la commande. Clés stables, validation des longueurs/dates/décimales, mises à jour partielles conservant les clés anciennes ; révision optimiste et verrou court sur le propriétaire. Les changements sont conservés dans l'audit avec l'état antérieur.
- Migration additive 0028 : quatre tables sans suppression ; reprise conditionnelle de l'ancienne colonne launches.identification_json, en conservant les clés retirées. Une valeur historique malformée interrompt la migration, sans remise à zéro.
- Référentiel technique provisoire avec IDs stables, libellés et alias non ambigus. Les catégories initiales viennent des exemples et du classement assisté existants : elles ne définissent pas des obligations métier officielles. Les libellés d'origine sont conservés dans document_type_assignments. Les textes inconnus ou dans la mauvaise rubrique restent « À classer ». Aucun regroupement de documents ni réécriture automatique de libellés historiques.
- Sélection du type par rubrique, reclassement explicite depuis Versions et historique ; conflit signalé si le classement a changé. Le classement assisté retourne aussi le type_id sans retirer l'obligation de confirmation humaine.
- Commentaires internes ajoutés sur une version précise avec auteur et date, append-only, pagination serveur, lecture/écriture de rubrique et contrôle canonique du dossier. Réutilisation du circuit existant pour les demandes de correction et décisions : les commentaires ne modifient pas l'approbation.
- Interface existante conservée, nouvelles fiches en dialogues, labels explicites, erreurs conservant la saisie. Les procédures concernées du guide sont mises à jour.

## Vérifications
- `python -m pytest -q tests/test_consolidation_documents.py tests/test_intake.py` : 8 réussis.
- `node tests/test_consolidation_documents_frontend.cjs` : réussi (labels, échappement, contrats de montage).
- `node --check static/order-identification.js` et `node --check static/orders.js` : réussis.
- Une première commande guide catalog/evaluation/API sans FRAMATEX_DATA_DIR explicite a utilisé le répertoire data/ partagé par plusieurs processus de test : 13 échecs de concurrence (401 compte absent, tables supprimées pendant accès). Relance isolée nécessaire et en cours ; aucun contournement des droits.
- Relance isolée `FRAMATEX_DATA_DIR=$(mktemp -d /tmp/framatex-docs-guide.XXXXXX) python -m pytest -q tests/test_guide_catalog.py tests/test_guide_evaluation.py tests/test_guide_api.py tests/test_consolidation_documents.py tests/test_intake.py` : 38 réussis en 66,63 s. Le défaut initial était un partage de base entre processus de test ; aucun contournement fonctionnel.
- `node tests/test_guide_frontend.cjs` : réussi après installation npm des dépendances épinglées.
- Test supplémentaire : reprise idempotente de identification_json (ancienne branche), avec clé retirée conservée.
- Navigateur : nouveaux parcours identification décimale, atelier par lancement, commentaire v1 conservé et absent v2, reclassement explicite, nouvelle version et téléchargement vérifiés ; 4 contrôles axe/mobile du dossier réussis. Contrôle transverse complet en cours après correction centrale de l'import ApprovalStageAssignment dans la file de validation.
- Suite globale : intégration centrale à suivre.

## Limites et décisions restantes
- Référentiel et clés facultatives sont des propositions techniques réversibles, à compléter/valider par Framatex, sans exigences sensibles automatiques.
- Pas de lecture/édition graphique PDF ; l'original reste conservé.
- Pas de preuve sur un corpus métier réel. Les tests portent exclusivement sur des données synthétiques.
- main.py et orders.js sont des fichiers d'intégration partagés : leurs hooks sont présents, mais leur commit est centralisé par l'agent principal.
