# Parcours partenaires, réception et listes — consolidation

## Constats et corrections
- Confirmés : `staff()` admin-only pour achats/examen/réception ; contexte absent du contrat réceptions ; historique quadratique et annulations rechargées par mouvement ; listes documents/annuaires/validations non bornées ; impossibilité de réceptionner une pièce sans compte fournisseur.
- Déjà présents et préservés : CAS de demande et ligne matière, unicité version/intégration et clé d'opération, versions rejetées conservées, comptes partenaires distincts des employés, révocation compte/organisation et fichiers contrôlés.
- Droits explicites `supplier.read`, `supplier.request`, `supplier.review`, `receipt.read`, `receipt.write` + ACL et lecture des rubriques côté serveur. Aucun ajout de droits aux rôles historiques. Administration et accès clients restent administratifs. Les types client/fournisseur sont vérifiés même en présence d'une affectation historique incohérente.
- `received-versions` accepte les pièces hors portail avec auteur employé, canal et note ; ni compte fournisseur obligatoire ni identité usurpée. La version reste en attente d'une décision distincte. Publication/integration conserve cette provenance.
- Migration `0027_partner_received_sources` : reconstruction transactionnelle de `partner_submissions` rendant `account_id` facultatif et ajoutant `received_by`, `received_via`, `received_note`. Identifiants/contraintes/unicités/décisions et références entrantes restent intacts ; migration historique + répétition + FK vérifiées.
- Intégration cible : ACL documentaire également vérifiée ; retrait CAS pour empêcher doubles décisions concurrentes.
- Dépôts : contrôle long avant acquisition du verrou organisation/écriture métier ; recontrôle de révocation après fichier ; nettoyage par registre de stockage ; sérialisation avant commit pour ne jamais effacer un fichier déjà référencé à cause d'une erreur de réponse.
- Réception : réponse interne fournit `launch_id`, `order_id` réel ; portail ne diffuse pas ces identifiants internes. Contrat résumé distinct de l'historique ; résumés SQL groupés, annulations groupées et historique incrémental O(n log n). Contrats existants de mouvement conservent les quantités décimales, retours et idempotence.
- Annuaire, réceptions et file de validation : ACL SQL avant comptage/pagination, tris déterministes ; annuaire 10 enfants récents par organisation (total indiqué) ; file limitée aux derniers circuits des dernières versions, données d'autorisation chargées par lots. Frontend utilise pages serveur et historiques à la demande.

## Vérifications
- `python -m pytest -q tests/test_consolidation_partners.py` : 6 tests passés, 14,88 s (avant toute modification ultérieure signalée ci-dessous).
- Suite partenaires historique + nouveaux tests : 19 passés, 69,99 s (4 nouveaux tests à cette étape).
- `tests/test_order_documents_phase3.py` + nouveaux tests partenaires : 11 passés, 34,66 s.
- `tools/check_partner_browser.py`, Chromium local : parcours fournisseur/client complet, séparation, révocation, décisions, intégration, délégation et réouverture, dépôts lot, confirmation humaine, course d'administration ; contrôles axe WCAG A/AA et largeur 360/390/768/1440 réussis sur parcours initial. L'extension utilisateur achats non administrateur et dépôt hors portail a également réussi (journal /tmp/framatex-partners-browser.log et écran purchasing-nonadmin-offportal dans artifacts/phase3-partner-axe.json, quatre largeurs sans violation axe).
- Contrôles syntaxe `node --check static/partners.js`, `node --check static/orders.js`, fragments frontend : passés.
- Test volumétrie SQL réceptions : 50 lignes × 40 mouvements synthétiques, page 25, budget <20 instructions y compris authentification ; file validation : 31 documents ×3 versions dont un confidentiel, page5, budget<30, compteurs30 accessibles et versions courantes uniquement.

## Mesure isolée reproductible
`PYTHONPATH=. python tools/measure_delivery_history.py` compare la fonction du commit `origin/main` à la nouvelle et vérifie l'égalité de chaque événement. 3 répétitions en série, Decimal synthétique, machine partagée avec les autres tests :

| Corpus | Avant médiane | Après médiane |
|---|---:|---:|
| 500 mouvements +50 annulations | 69,09 ms | 4,89 ms |
| 2 000 mouvements +200 annulations | 788,20 ms | 87,44 ms |

Données brutes : `artifacts/consolidation-delivery-history.json`. Mesure de fonction, sans I/O ni concurrence HTTP ; aucune extrapolation de p95 ni qualification serveur Framatex.

## Limites précises
- Les règles de tolérance, délais, acteurs habilités à l'approbation et circuits officiels restent à valider par Framatex. Les droits proposés sont des mécanismes techniques, pas une politique officielle validée.
- Le portail fournisseur conserve pour compatibilité l'historique sur les lignes de sa page (50 lignes max) ; sa projection pourra encore être allégée. L'endpoint d'historique interne calcule linéairement les soldes antérieurs avant de renvoyer une page ; une très longue ligne pourra nécessiter une matérialisation validée.
- L'écran d'options employés limite les lancements à 100 ; un sélecteur de recherche supplémentaire sera nécessaire au-delà. La pagination par offset est déterministe mais ne constitue pas un instantané transactionnel entre deux consultations.
- Aucun test de charge de production, email réel ni validation du corpus Framatex.

Revue centrale et indépendante finale : sources et contrôles CAS examinés ; aucun défaut supplémentaire confirmé. Aucun résultat navigateur synthétique ne vaut recette Framatex.
