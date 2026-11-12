# État courant — phase 3

Framatex Guide est développé sur `feat/framat-user-guide` : centre d’aide, manuel synchronisé, visites, progression et sélection Gemini facultative. Son [rapport de couverture et ses limites](docs/FRAMATEX_GUIDE_DELIVERY.md) sont séparés de la matrice historique ci-dessous. Aucun appel réel à Gemini ni gain mesuré n’est revendiqué.

**264 / 273 exigences terminées (96,7 %), 6 partielles et 3 bloquées.** Les identifiants et les anciens états sont conservés dans `docs/requirements.json`. Le modèle documentaire de référence est désormais le Dossier Jaune unique par commande.

Le [rapport phase 3](docs/RAPPORT_PHASE3.md) contient les commandes exécutées, leurs résultats, les limites et l'état de la PR. Les [procédures de migration/restauration](docs/MIGRATION_PHASE3.md) et le [rapport de sécurité](docs/SECURITE_PHASE3.md) s'appliquent à cette branche. Aucune validation de production ou conformité WCAG complète n'est revendiquée.

---

## Historique conservé : phase 2

# Livraison phase 2 — 11 novembre 2026

**248 / 273 exigences terminées et vérifiées en environnement contrôlé : 90,8 %. Le seuil demandé de 246 est atteint. Aucun accord de mise en production ou de pilote externe n'est revendiqué.**

Branche : `feat/framat-industrialization-phase2`, base `e94e3c6` après fusion de la PR #32. La reprise a confirmé 74 tests Python et les 76 exigences terminées de la phase 1. Aucun déploiement, aucune fusion, aucune donnée réelle et aucun transport SMTP réel pendant cette mission.

## Couverture et preuves

| État | Avant | Après |
|---|---:|---:|
| Terminé | 76 | 248 |
| Partiel | 158 | 22 |
| Absent | 36 | 0 |
| Bloqué | 3 | 3 |
| Couverture | 27,8 % | 90,8 % |
| P0 non terminées | 49 | 6 |

Les 273 identifiants et leur granularité sont conservés. Les 172 exigences supplémentaires validées comprennent les développements nouveaux et les fonctions existantes dont le parcours, la persistance et les droits ont été complétés ou vérifiés. Ce ne sont pas 172 modules nouveaux. Chaque ligne de `docs/requirements.json` cite son code, ses tests et la portée observée ; `COUVERTURE_FONCTIONNELLE.md` est généré par `tools/update_coverage.py`.

## Fonctionnalités livrées

- Référentiel partenaires enrichi : nom commercial, coordonnées, domaines email, contacts multiples, informations et pièces administratives versionnées, historique, rôles configurables. Les nouvelles invitations sans rôle explicite sont en lecture seule ; aucun partenaire ne peut s'accorder des droits.
- Intégration explicite des transmissions fournisseur approuvées dans les versions internes sans copie du blob. Provenance, empreintes, auteur, dates et décisions conservés ; réouverture des demandes et retrait des justificatifs, réévaluation de complétude/cohérence/publication.
- Commandes client autorisées, statuts et échéances confirmés, conversations avec pièces jointes, traitement et clôture, historique et notifications. Révocation de commande appliquée aux publications et échanges. Aucun avancement inventé.
- Matières partenaires : prévu, commandé, annoncé, déclaré, réceptionné, retourné et restant, sources obligatoires, annulations justifiées, historique des écarts et situations successives. Les réceptions partielles restent un état normal.
- Référentiel commande additif multi-lancements, synthèse documentaire/matières/publications/ORLI, contrôle des rattachements et détachements justifiés. Aucune migration globale du Dossier Jaune.
- Profils ORLI persistants, comparaison des lots, décisions conserver/accepter avec justification et contrôle du lien attendu ; instantanés préservés.
- Complétude conditionnelle par type de commande, phase, rubrique, document, facultativité et délai ; exceptions, version approuvée et publication client effectivement accessible.
- Comparaisons numériques et références exactes ; unités, sources multiples, tolérances et justifications explicites. Utilisation de champs extraits seulement après confirmation humaine, avec provenance conservée.
- Excel statique : structure, feuilles, formules et cellules critiques configurables. Lecture documentaire isolée et bornée, avertissements de lecture partielle, aucune formule recalculée ni OCR déclaré infaillible.
- Recherche documentaire filtrée par ACL avant comptage/pagination ; dépôt multiple par glisser-déposer, classement confirmé, état par fichier et reprise des échecs sans renvoi des succès déjà confirmés.
- Approbations : rôles séquentiels, séparation des personnes, délais par étape, délégation temporaire révocable et historique par version.
- Notifications internes persistantes, réponses/publications client et rappels d'échéance idempotents. Le transport SMTP reste distinct et désactivé.
- Sécurité : quotas, adaptateur scanner requis avec refus en cas d'indisponibilité, budget de connexion partagé, révocations employés/partenaires, protection du dernier administrateur, secrets atomiques, erreurs expurgées, clés étrangères et index, migrations concurrentes, sauvegarde/restauration complète avec invalidation des sessions.
- Démonstration reproductible : deux clients, deux fournisseurs, comptes distincts, commandes, documents, validations fictives, incohérence chiffrée et réception partielle. Relance idempotente et garde DEMO testées.

## Validation exécutée

- Régression complète : `.venv/bin/python -m pytest -q` — **105 tests réussis**, un avertissement de dépréciation Starlette/httpx, aucun échec.
- Les **13 scripts JavaScript** `tests/*.cjs` et `node --check` sur tous les fichiers `static/*.js` passent.
- Chromium réel : `.venv/bin/python tools/check_partner_browser.py` — **PASS**. Base temporaire, serveur loopback, fournisseur activation/dépôt/refus/version 2/approbation/intégration/clôture, pièces administratives et historique de livraison, client publication/téléchargement/question/pièce jointe/réponse/clôture/retrait, mobile 390 px, recherche, rattachement commande, conditions, délégation, dépôt multiple avec échec partiel et reprise, classement, confirmation humaine, modification d'accès employé. Pas d'erreur JavaScript observée. Captures dans `artifacts/`.
- Sécurité et concurrence : deux clients et deux fournisseurs, lecteurs et employés limités, accès directs, récupération et expiration, droits révoqués, comptes réactivés, cookies, CORS, scan requis indisponible, quota concurrent, erreurs sans secrets ; budget de connexion partagé entre processus, clé locale et migrations créées par processus concurrents.
- Reprise : migration synthétique 0003 → 0020 répétable ; identifiants, ACL, empreintes et fichiers conservés ; contraintes et rollback ; archives des documents internes, transmissions, pièces jointes et administratives ; restauration vers répertoire neuf et révocation des sessions.
- Démo : exécution réelle des cinq scripts concernés, refus hors DEMO, absence de doublons à la relance, intégrité des fichiers et consultations API des données générées.
- `git diff --check` : réussi.

Échecs intermédiaires corrigés : fixture dépendant de l'ordre des tests, course de migration SQLite, sélection d'une route documentaire inexistante, attentes navigateur trop précoces après actualisation et type documentaire de test non publiable. Aucun échec restant dans les validations ci-dessus. Les tests SMTP utilisent un transport contrôlé : ils ne prouvent aucun envoi réel. Les tests du scanner prouvent la politique de refus, pas l'efficacité d'un antivirus réel. Aucun essai de charge de production ni PostgreSQL réalisé.

## Limites restantes, sans exclusion du dénominateur

Trois exigences bloquées : synchronisation ORLI directe (N-05), SMTP réellement accepté par un service autorisé (N-06), recette et autorisation métier Framatex avant ouverture externe (N-07).

Les 22 exigences partielles concernent : modèle Dossier Jaune global et règles validées des quatre rubriques (R6-02, R6-05 à 08), robustesse d'extraction sur le corpus réel (R8.3-01), résolution complète des associations ORLI ambiguës (R9-11), réouverture d'un circuit sur la même version (R12-10), validation exhaustive des entrées (R13-09), qualification des uploads dangereux et scanner réel (R13-10, N-09), finitions transversales de navigation, recherche, états, mobile et accessibilité sur toutes les pages (R15-01 à 11). Les parcours mobiles testés ne valent pas conformité d'accessibilité générale.

Les simulations historiques `sharing` sont conservées et signalées ; elles n'ouvrent aucun accès externe tant qu'une publication approuvée n'a pas reçu une attribution partenaire explicite. Les règles, décisions et comptes DEMO restent fictifs. L'inspection Excel n'est pas un moteur de calcul, et aucun modèle de progression client n'est simulé.

Avant pilote : revue indépendante des droits et fichiers, scanner réel, limites réseau, charge, sauvegarde/restauration indépendante, configuration HTTPS et recette Framatex. La migration supporte SQLite ; PostgreSQL, Supabase et stockage objet ne sont pas qualifiés.

## Test local et suite

Commandes complètes dans `GUIDE_DEPLOIEMENT.md`. Pour le parcours reproductible : répertoire neuf, `FRAMATEX_MODE=DEMO`, mot de passe fourni dans `FRAMATEX_DEMO_PASSWORD`, puis `python -m app.seed_phase2_demo` et serveur local. Les comptes et résultats attendus sont décrits dans le guide.

La suite doit traiter les exceptions métier et le corpus réel, achever les associations ORLI ambiguës et la réouverture contrôlée, puis qualifier toutes les interfaces. Obtenir les paramètres et autorisations des services externes avant leurs essais réels. Aucun déploiement ni fusion automatique.

## Livraison Git

Commits de développement :

```text
0e1dd99 feat: extend supplier profiles and enforce organization-scoped roles
d487daf feat: integrate approved supplier versions with provenance and business controls
e688195 fix: serialize SQLite migrations and share login budgets across workers
59e2428 feat: complete client conversations and add private partner attachments and notifications
0259a32 feat: track announced deliveries planned quantities and justified cancellations
e59e8d2 feat: persist ORLI mappings and reconcile imported snapshots explicitly
a6a0484 feat: inspect Excel structure and configured critical cells with bounded analysis
feb4548 feat: add order registry conditional completeness and private administrative files
b202400 feat: add scoped approval delegation deadlines and partner notification center
76c7820 feat: seed reproducible isolated partner demonstrations and verify existing demo scripts
fdfd226 feat: bound document extraction and compare confirmed numeric and reference data
5b8ea1d fix: enforce database integrity and revoke sessions on access changes and restore
c1ac997 feat: expose historical delivery discrepancies with source and cancellation evidence
06b3215 feat: add batch drag-and-drop uploads and verify complete partner browser journeys
```

Documentation et matrice : commit `832a635`. La branche `origin/feat/framat-industrialization-phase2` a été poussée avec succès.

Création de PR en brouillon tentée avec `gh pr create --draft --base main --head feat/framat-industrialization-phase2 --body-file docs/PULL_REQUEST.md`. Refus de l'API GraphQL : `Post "https://api.github.com/graphql": Forbidden`. La vérification alternative par REST a également reçu `Forbidden`. **Aucune PR créée.** Ce refus provient de l'accès à l'API GitHub, pas d'un rejet de l'auto-approbation.

Lien de création : https://github.com/Rudolf-Staline/Framatex/pull/new/feat/framat-industrialization-phase2 . Description prête dans `docs/PULL_REQUEST.md`. Aucun déploiement ni merge effectué.
