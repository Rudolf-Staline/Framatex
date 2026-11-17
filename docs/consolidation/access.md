# Lot 1B/C — Droits commande et contexte documentaire

## Constats confirmés
- `order_accessible` changeait de politique dès le premier rattachement : un lecteur sans OrderMember voyait toute commande dont tous les lancements étaient ouverts ; un lancement restreint cachait tout le dossier.
- Une pièce commune recevait artificiellement le premier lancement de la commande via `context_launch_id`.
- Les listes de documents de dossier, d'approbations et les détails commande supposaient que voir le dossier suffisait à voir toutes ses provenances.

## Corrections et décisions techniques
- ACL commande unique : compte actif et propriétaire, administrateur ou membre explicite. Les permissions d'action/rubrique restent indépendantes.
- Les restrictions historiques d'un lancement s'appliquent à sa provenance documentaire ; elles ne cachent plus les pièces communes et les autres lancements du dossier.
- Un nouveau rattachement n'ajoute aucun membre ; un retrait interdit l'accès direct aux anciennes versions, hors accès propre propriétaire/administrateur. La réponse de retrait indique l'accès effectif restant.
- Migration `0025_order_acl` : matérialisation idempotente, une seule fois, des utilisateurs actifs qui avaient réellement l'accès à tous les lancements d'une commande existante. Aucun droit d'action ajouté. Nouveaux rattachements exclus de cette migration.
- Les pièces communes ont `context_launch_id=None`, et `context_order_id` explicite. Les notifications existantes portent déjà order_id ; leurs contrôles exigent maintenant les deux périmètres lorsqu'une provenance lancement existe.
- Les impacts historiquement limités au lancement ne sont pas artificiellement attribués à un lancement : une pièce commune n'émet pas d'impact de lancement. Définir des règles d'impact commande serait une décision fonctionnelle supplémentaire.
- Prédicats SQL partagés : `order_access_clause`, `document_access_clause`, `source_launch_access_clause`, `launch_access_clause`. Ils permettent autorisation AVANT dénombrement et pagination. Test d'équivalence SQL/Python avec sources hétérogènes.
- Création de commande : permission `order.create`, réservée à l'administration sans attribution explicite à un rôle. Ajout des noms des permissions partenaires, sans subvention de droits.
- Dépôt commande : contrôles avant scan puis nouvelle lecture des droits après scan ; aucune transaction d'écriture durant copie/scan. Nettoyage stockage via son registre.

## Vérification
`/tmp/framatex-venv/bin/python -m pytest -q tests/test_consolidation_access.py tests/test_order_registry.py tests/test_document_search.py` : **5 passed**, 12,25 s, données synthétiques locales.

Les 3 nouveaux tests couvrent : sans lancement puis rattachement et retrait ; dossier à deux lancements dont un restreint ; pièce commune explicite ; accès direct ancienne version ; listes/détails/approbations sans titre ni identifiant interdit ; dépôt sur provenance interdite ; compte désactivé ; migration répétée sans doublon et sans ajout sur restriction non accessible. Un test a détecté un problème de corrélation SQL imbriquée qui a été corrigé avant validation.

## Limites
- La migration conserve la visibilité historique de commandes déjà liées à des lancements ouverts ; les opérateurs doivent réviser les habilitations de ces commandes. Elle n'accorde aucune nouvelle permission sensible.
- Les tests ne constituent pas une recette métier Framatex ; les politiques de rôle et de rétention nécessitent sa décision.

### Compléments d'intégration
- Les vérifications de provenance couvrent également les revues/valeurs/impacts, les exigences/ambiguïtés, les comparaisons qualité, les inspections Excel et le graphe/simulations. Les anciennes simulations sont relues avec leurs versions sources et masquées après retrait des droits.
- Un justificatif de matière doit être accessible à son utilisateur ; les lignes dont l'historique fait référence à une provenance désormais interdite sont masquées au lieu de révéler titres, identifiants et quantités dérivées.
- Les agrégats de demandes/réceptions dans le détail commande exigent les nouvelles permissions métier et les rubriques utiles ; les publications sont aussi filtrées par document.
- Les chemins liste/résumé commande et résumé dossier ont reçu la pagination/optimisation centrale pendant ce lot ; leurs requêtes utilisent les prédicats ACL partagés.
- Lecture de la dernière version d'approbation via requête bornée, sans chargement de toutes les versions.
- Vérification étendue : 31 tests ciblés avec schéma historique et restauration, **31 passed** en 94,58 s ; puis workflow/spec/qualité/matières/simulation et scénario source hétérogène enrichi, **24 passed** en 50,90 s. Les mises à jour concurrentes de migration ont temporairement empêché un lancement intermédiaire (modèle 0029 non encore importé) ; cette dépendance a été corrigée et la suite relancée.
