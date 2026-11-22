# FRAMATEX — Collaborateurs et habilitations · rapport de livraison

Branche : `feat/access-management` · base : `feat/smart-business-memory-ux` (`6b0eafe`).
Commit final et vérification distante : voir § 11.
Suivi au fil de l'eau : [`ACCESS_MANAGEMENT_PROGRESS.md`](ACCESS_MANAGEMENT_PROGRESS.md).

> Règle appliquée partout : **accès = fonction du collaborateur × commande × sous-dossier × action**.
> Aucun technicien n'est lié à une couleur ; un compte unique sert sur toutes les commandes.

---

## 1. État de livraison

### Terminé et testé

| Domaine | Livré | Preuve |
|---|---|---|
| Comptes (P0) | Création, modification, fonction, activation/désactivation, un email unique par personne, une seule page de connexion | `test_01_04…`, recette navigateur §2 |
| Mots de passe (P0) | Argon2 ; mot de passe temporaire généré (`secrets`), affiché **une seule fois** ; changement imposé avant tout accès ; changement depuis « Mon compte » ; réinitialisation par le chef ; sessions antérieures révoquées ; jamais journalisé | `test_01_04…`, `test_password_chosen_by_chef…`, recette §3 |
| Écran Administration historique | Le mot de passe saisi par le chef y devient **temporaire** (changement imposé) : le chef ne connaît jamais un mot de passe permanent | `test_password_chosen_by_chef_in_legacy_screen_is_temporary` |
| Affectations dynamiques (P0) | Par commande et sous-dossier, ajout/retrait à tout moment, refus par défaut, commande « chef seul », un technicien sur 0, 1 ou n commandes, plusieurs techniciens sur un même sous-dossier, exemple A/B/C exact | `test_05_11_dynamic_assignments_example`, recette §5–11 |
| Actions détaillées (P0) | 10 actions par sous-dossier (tableau §3) ; validation distincte du dépôt ; téléchargement distinct de la consultation ; toute action implique la consultation | `test_12_16…`, `test_controls_require_controls_read…` |
| Isolation (P0) | Commandes, documents, versions, téléchargements, passeports, QR, recherche, tableaux de bord, activité, priorités, notifications, mémoire métier, contrôles croisés, inspections Excel, assistant ; URL directes et identifiants indirects refusés (404) | `test_12_16…`, `test_17…`, `test_18…`, recette §15–17 |
| Révocation (P0) | Retrait d'affectation, désactivation et réinitialisation effectifs **immédiatement**, y compris sur une session ouverte | `test_13_14…`, recette §13–14 |
| Écrans chef (P0) | « Collaborateurs et habilitations » : liste (nom, email, fonction, état, nb commandes, dernière activité), création, modification, (dés)activation, réinitialisation, historique ; bouton **Affecter des collaborateurs** dans l'en-tête de chaque commande (matrice Jaune/Rose/Bleu/Vert + éditeur d'actions) ; habilitations par collaborateur | captures 01–03, 06, 09, 11–12 |
| Écrans technicien (P0) | Mon tableau de bord, Mes commandes, Mes sous-dossiers, Mes actions, Mes notifications, recherche, Mon compte, Assistant ; sous-dossiers non affectés affichés « Accès restreint », sans titre de document, compteur ni contenu ; état vide explicite | captures 04–05, 07–08, 10 |
| Préréglages, copie, groupe (P0 option) | Préréglages (lecture, lecture + téléchargement, dépôt sans validation, responsable) = **propositions** ; copie depuis une autre commande = proposition ; affectation groupée | `test_bulk_copy_and_legacy_proposals_require_confirmation` |
| Migration (P0) | `0013_access_management` : aucun droit nouveau ; droits hérités présentés au chef (« Droits hérités à vérifier ») | `test_migration_0013…` |
| Audit | Création, modification, (dés)activation, affectation, modification et retrait de droits, réinitialisation (sans secret), décisions sur les droits hérités | `test_01_04…`, `test_13_14…` |
| Vue globale (P1) | Indicateurs : collaborateurs actifs, commandes affectées, commandes chef seul, sous-dossiers sans technicien (indicateur, pas erreur), validations en attente par responsable ; filtres | capture 09 |
| Notifications (P1) | Préférences (internes, emails futurs, rappels, modifications importantes, demandes de validation, nouvelles affectations) ; service `recipients()` ; notification interne « nouvelle affectation » | `test_19_notification_recipients` |
| Comptes de démonstration | `scripts/seed_access_demo.py` : base isolée uniquement, mots de passe générés à l'exécution | §8 |
| Persistance | Affectations, retraits et mots de passe conservés après redémarrage | `test_20…`, recette §20 |

### Partiel

- **Drapeau « commande restreinte / membres » (0.15)** : il ne s'applique plus qu'aux comptes
  *hérités* (sans profil, bases de test anciennes). Pour un compte en mode affectations, seule
  l'affectation ouvre une commande — plus strict, mais l'écran historique « Accès » d'une
  commande reste affiché ; il devrait renvoyer vers la matrice (P2).
- **`controls.read`** est appliqué au rapport de cohérence (`/quality`) et aux inspections Excel
  (`/excel-inspections`). Les autres modules de l'onglet Contrôles (OCR, simulation, ORLI…) restent
  gardés par `document.read` + l'action métier propre à chaque module. Les nouvelles routes de Codex
  devront appeler `controls.read` (voir §7).

### Non fait (volontairement, conformément à la mission)

- Aucun envoi d'email (pas de SMTP, Microsoft 365, n8n, Exchange) ; aucun mot de passe de
  messagerie demandé. Aucun lien de réinitialisation par email.
- Aucune protection contre la copie d'un contenu consulté (seul le téléchargement est contrôlé).
- Aucune fusion avec `feat/document-intelligence`, aucune modification de `main`.

### Travaux futurs (P2)

Modèles de fonction réutilisables ; expiration programmée d'une affectation ; délégation
d'administration limitée à un périmètre ; remplacement de l'écran « Accès » historique par la
matrice ; envoi effectif des emails une fois le canal choisi (le contrat `recipients()` est prêt).

---

## 2. Architecture des permissions

```
requête HTTP ──► middleware request_header_guard
                   │  access.guard_http_request : résout la commande depuis l'URL
                   │  (launches, documents, document-versions, approval-runs, impacts,
                   │   notifications, client-publications, supplier-requests) → 404 si non visible
                   ▼
                 request_context(launch_id)   ← ContextVar + cache propre à la requête
                   ▼
              endpoint ── must()/permitted() ──► access_control.can(user, action, folder, launch_id)
                                                     ├─ Administrateur → vrai
                                                     ├─ mode « affectations » → launch_assignments
                                                     └─ mode « hérité » → rôles 0.15 (tests historiques)
```

- **Point unique** : `app/access_control.py::can(user, action, folder=None, launch_id=None)`.
  `main.permitted()` et `access.accessible()` y délèguent : les ~200 appels existants passent
  tous par le nouveau contrôle sans réécriture.
- **Commande courante** : posée par le middleware pour toute URL directe ou indirecte, et par
  `launch_scope(id)` dans les vues multi-commandes (recherche, tableau de bord, activité,
  priorités, complétude, mémoire métier, notifications, assistant). **Sans commande connue,
  toute action de sous-dossier est refusée** : un oubli masque, il ne révèle jamais.
- **Refus par défaut** : un collaborateur ne voit une commande que s'il y possède au moins une
  affectation non vide (`launch_accessible`). Une nouvelle commande n'est visible que du chef.
- **Jamais d'élévation** : une affectation ne porte que des actions de sous-dossier ; une cible
  administrateur est refusée (422) ; les actions globales (`launch.create`, `launch.update`,
  `audit.read`) relèvent du rôle, que seul le chef attribue.
- **Révocation immédiate** : aucun droit n'est mis en cache au-delà de la requête ;
  `collaborator_profiles.sessions_valid_after` invalide les jetons émis avant une
  désactivation, une réinitialisation ou une révocation (`core.get_current_user`, comparaison
  avec `iat`).

## 3. Actions par sous-dossier

| Clé | Libellé | Remarque |
|---|---|---|
| `document.read` | Consulter les documents | impliquée par toute autre action |
| `document.download` | Télécharger | distincte de la consultation |
| `document.write` | Déposer de nouveaux fichiers | |
| `document.version` | Déposer une nouvelle version | |
| `document.comment` | Ajouter des commentaires | |
| `controls.read` | Consulter les contrôles | exigée sur **les deux** sous-dossiers d'un contrôle croisé |
| `impact.review` | Traiter les alertes | alias : `commitment.review` |
| `value.write` | Confirmer les informations extraites | |
| `quality.review` | Justifier un écart | alias : `requirement.review`, `ambiguity.review` |
| `document.review` | Valider les documents | distincte du dépôt ; alias : `completeness.review` |

Aucune suppression définitive n'est proposée. Les contrôles sont tous côté serveur ; l'interface
ne fait que masquer ce que l'API refuse déjà.

## 4. Modèles de données et migration

| Table | Rôle |
|---|---|
| `collaborator_profiles` | `user_id` (PK), `job_title`, `access_scope` (`assignments`), `must_change_password`, `sessions_valid_after`, `password_changed_at`, `notification_prefs` (JSON) |
| `launch_assignments` | `launch_id`, `user_id`, `folder_slug`, `actions` (JSON normalisé), `granted_by`, dates — unique (commande, collaborateur, sous-dossier) |
| `legacy_access_proposals` | droits hérités à vérifier : `origin` (role / member / creator), `folders` proposés, `status` (pending / applied / dismissed), décideur |

**Migration `0013_access_management`** (`app/access_migration.py`, appelée par `app/migrate.py`) :

1. crée les trois tables ;
2. crée un profil « affectations » pour chaque compte existant — **mots de passe inchangés**
   (`admin.test@framatex.com` conserve son hachage, vérifié par test) ;
3. **n'ouvre aucun droit** : aucune affectation créée ;
4. pour chaque collaborateur non administrateur, calcule ce que ses rôles 0.15 lui donnaient
   (commande non restreinte, membre, créateur) et l'enregistre comme **proposition** que le chef
   applique ou écarte dans « Droits hérités à vérifier ».

Conséquence documentée : après migration, un collaborateur existant ne voit plus aucune commande
tant que le chef n'a pas appliqué ses propositions ou affecté ses commandes. C'est voulu
(refus par défaut, aucun droit implicite) ; le chef voit la liste à traiter.

## 5. API

Toutes réservées au chef (`Administrateur`), sauf « Mon compte ».

| Méthode | Route | Objet |
|---|---|---|
| GET | `/api/admin/access/catalog` | actions, sous-dossiers, préréglages |
| GET / POST | `/api/admin/collaborators` | liste ; création → `{collaborator, temporary_password}` (une fois) |
| GET / PATCH | `/api/admin/collaborators/{id}` | détail ; nom, email, fonction, activation (pas soi-même, pas le dernier chef) |
| POST | `/api/admin/collaborators/{id}/reset-password` | nouveau mot de passe temporaire + révocation |
| POST | `/api/admin/collaborators/{id}/revoke-sessions` | déconnexion de toutes les sessions |
| GET | `/api/admin/collaborators/{id}/history` | journal des comptes et habilitations |
| GET | `/api/admin/collaborators/{id}/assignments` | habilitations par commande |
| PUT | `/api/admin/collaborators/{id}/assignments/{launch_id}` | `{folders: {slug: [actions]}}` (vide = retrait) |
| GET / PUT | `/api/admin/launches/{launch_id}/assignments` | matrice d'une commande |
| GET | `/api/admin/launches/{id}/assignments/copy-from/{source}` | proposition, rien n'est écrit |
| POST | `/api/admin/assignments/bulk` | affectation groupée (fusion) |
| GET | `/api/admin/access/overview` | vue globale, indicateurs, filtres |
| GET / POST | `/api/admin/access/legacy`, `…/legacy/{id}/{apply\|dismiss}` | droits hérités |
| GET | `/api/admin/access/recipients` | aperçu des destinataires d'un événement |
| GET | `/api/account` | mon compte |
| POST | `/api/account/password` | changement (ancien requis, ≥ 12 caractères, différent) |
| PUT | `/api/account/preferences` | préférences de notification |

`/api/auth/me` expose en plus `access_mode`, `job_title`, `must_change_password`,
`assigned_actions` (union, pour les menus) et `assigned_launches`. Tant que
`must_change_password` est vrai, toute route hors `/api/auth/me`, `/api/auth/logout` et
`/api/account/password` répond 403.

## 6. Règles de sécurité appliquées

- Aucun mot de passe en clair : ni base, ni journal, ni audit (« défini (non journalisé) »),
  ni rapport de recette, ni capture (le champ est masqué avant capture ; le script vérifie
  qu'aucun secret ne figure dans `results.json`).
- Le chef ne voit jamais un mot de passe permanent : il ne manipule que des mots de passe
  temporaires, remplacés obligatoirement.
- Contrôles croisés : un résultat n'est rendu que si les deux sous-dossiers sont lisibles **et**
  `controls.read` y est accordé — aucune fuite d'un sous-dossier non affecté.
- Mémoire métier : accès si `document.read` Jaune sur au moins une commande affectée ; une note
  liée à une commande n'est visible que sur une commande accessible ; **les notes générales
  (sans commande) sont visibles de tout compte ayant accès à la mémoire métier** (règle retenue
  et testée).
- Espace Client : comptes distincts (`ClientAccount`), non concernés par ces tables ; aucune
  note interne n'y est exposée (tests Espace Client inchangés et verts).
- Assistant : réponses prévalidées sans lecture de contenu ; l'indication de rubrique n'est
  donnée que pour un sous-dossier affecté (commande demandée, sinon au moins une commande).

## 7. Intégration avec Codex (`feat/document-intelligence`)

Aucun fichier algorithmique de Codex n'a été modifié. À l'intégration :

1. **Révision de migration** : `app/migrate.py` refuse toute révision inconnue. Ajouter
   l'identifiant de Codex à `REVISIONS` **après** `'0013_access_management'` (ou avant, s'il est
   déjà déployé) et conserver les deux blocs.
2. **Contrôle d'accès dans toute nouvelle route** :
   ```python
   from app.access_control import can, launch_scope
   from app.access import must_access            # 404 si la commande n'est pas visible
   launch = must_access(db, user, launch_id)
   must(user, "document.read", folder)           # délègue à can(), commande du contexte
   must(user, "controls.read", folder)           # pour tout résultat de contrôle / comparaison
   # vue multi-commandes :
   with launch_scope(launch.id):
       if can(user, "controls.read", folder): ...
   ```
   Les URL `/api/document-versions/{id}/…` et `/api/documents/{id}/…` sont déjà résolues par le
   middleware : la nouvelle route `compare-previous` de Codex est donc correctement bornée par
   `document.read`. Recommandation : y ajouter `must(user, "controls.read", folder)` puisqu'elle
   expose des constats d'inspection Excel.
3. **Destinataires d'un événement documentaire** :
   ```python
   from app.access_notifications import recipients
   rows = recipients(db, launch_id=..., folders=["jaune"], event_type="document.new_version",
                     exclude_user_id=auteur.id)
   # [{"user_id","name","email","folders","channels":{"internal","email"}}]
   ```
   Exemple : nouvelle version de la fiche d'emploi → passer le sous-dossier source et les
   sous-dossiers impactés ; seuls les collaborateurs affectés et habilités sont retournés.
4. **Fichiers partagés modifiés ici** (à fusionner avec attention) :
   - `app/main.py` : `permitted()` délègue à `can()` ; middleware sous `request_context` ;
     `/api/auth/me` enrichi ; `document.download` et `document.version` vérifiés ; drapeaux
     `can_version/can_download/can_comment/can_review` par sous-dossier ; profil créé (mot de
     passe temporaire) par `/api/admin/users` ; inclusion du routeur.
   - `app/migrate.py` : import des modèles, révision `0013`, trois tables.
   - `static/index.html` : `brand/access.css` et `access-admin.js` (`?v=access-2`).
   - `app/quality_routes.py` : filtre `controls.read` (2 lignes, aucun algorithme).
   - `app/workspace_routes.py` : boucle des priorités sous `launch_scope` (ré-indentation
     uniquement) et assistant borné.
   - Non modifiés : `app/models.py`, `static/dossier.js`, `static/app.js`.

## 8. Comptes de démonstration (base isolée)

```bash
python scripts/seed_access_demo.py --data-dir /chemin/vers/un/dossier/vide
FRAMATEX_DATA_DIR=/chemin/vers/un/dossier/vide python -m uvicorn app.main:app --port 8000
```

Refuse : le dossier `data/` par défaut, `DATABASE_URL`, un dossier non vide qu'il n'a pas créé,
toute base contenant un compte hors `example.test`. Crée `chef.demo@`, `technicien.a|b|c|d@example.test`,
quatre commandes, et affiche une fois des mots de passe temporaires générés à l'exécution
(changement imposé). Scénarios : une commande (D), plusieurs (A, B), aucune (C), lecture seule (D),
dépôt sans validation (A sur DEMO-001), quatre sous-dossiers (B sur DEMO-002), commande chef seul
(DEMO-004). Vérifié : refus de `data/`, d'un dossier étranger et d'une base à compte réel ; hachages Argon2.

## 9. Résultats des tests (exécutions réelles)

| Suite | Résultat |
|---|---|
| `pytest` (complet) | **198 réussis** — 186 existants + 12 habilitations |
| Tests JS `node tests/*.cjs` | **19/19** réussis |
| `scripts/validate_access_ui.py` (Uvicorn réel, Chromium, 1440 + 390 px, redémarrage) | **15/15**, 12 captures, aucune erreur JS, aucun défilement horizontal |
| `scripts/validate_internal_ui.py` | réussi — 52 captures, 7 parcours, aucune erreur JS |
| `scripts/validate_client_workflow_ui.py` | réussi — scénario complet |
| `scripts/validate_business_memory_ui.py` | **11/11** |
| `scripts/validate_document_workspace.py` | **9/9** |
| `scripts/qa_platform_review.py` | **96/96** (avec Tesseract installé ; sans Tesseract, seuls les 2 contrôles OCR échouent — environnement) |
| `scripts/demo_full_platform.py` | en cours d’exécution au moment de ce commit — résultat ajouté au commit suivant |

Tests existants ajustés sans affaiblissement : `test_business_memory` (tranche de révisions par
nom, plus par position), `test_pilot_feedback` et `test_internal_operations` (migration avant
création des comptes de test). `qa_platform_review.py` : le collaborateur de recette reçoit une
affectation explicite ; le contrôle « membre ajouté puis retiré » vérifie désormais qu'un membre
**sans affectation** n'a aucun accès, puis que l'affectation retirée/rétablie agit immédiatement ;
un contrôle « mot de passe défini par le chef : changement imposé » est ajouté.

Les 20 scénarios demandés → tests : 1 chef · 2 création · 3 première connexion · 4 sans affectation
(`test_01_04`) ; 5–11 (`test_05_11`) ; 12, 15, 16 (`test_12_16`) ; 13–14 (`test_13_14`) ;
17 recherche, QR, passeports, tableaux de bord, assistant, contrôles (`test_17`, `test_12_16`,
`test_controls…`) ; 18 mémoire métier (`test_18`) ; 19 destinataires (`test_19`) ; 20 persistance
(`test_20` + recette navigateur après redémarrage).

### Captures (`docs/access-management-captures/`)

| | |
|---|---|
| `acces-01-creation-collaborateur` | création d'un compte (sans commande) |
| `acces-02-mot-de-passe-temporaire` | affichage unique (valeur masquée pour la capture) |
| `acces-03-liste-collaborateurs` | liste chef |
| `acces-04-premiere-connexion` | changement imposé |
| `acces-05-technicien-sans-commande` | état vide |
| `acces-06-matrice-commande` | matrice d'une commande |
| `acces-07-technicien-dossier-partiel` | Jaune + Rose ouverts, Bleu/Vert verrouillés |
| `acces-08-mes-sous-dossiers` | vue technicien multi-commandes |
| `acces-09-vue-globale` | indicateurs et commande chef seul |
| `acces-10-mon-compte` | mot de passe et préférences |
| `acces-11/12-mobile-*` | 390 px : liste et matrice |

## 10. Reprise et lancement

```bash
git fetch origin feat/access-management && git checkout feat/access-management
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --port 8000      # la migration 0013 s'applique au démarrage
```

1. Se connecter avec le compte chef existant (inchangé).
2. **Collaborateurs et habilitations → Droits hérités à vérifier** : appliquer ou écarter les
   propositions des comptes existants.
3. Créer les techniciens (mot de passe temporaire à transmettre par un canal sûr).
4. Sur chaque commande : **Affecter des collaborateurs**.

Recettes : `pytest -q` · `for f in tests/*.cjs; do node "$f"; done` ·
`python scripts/validate_access_ui.py --output data/access-validation`.
Retour arrière : la migration ne modifie aucune table existante (trois tables ajoutées) ; une
sauvegarde de `data/framat.db` avant le premier démarrage suffit.

## 11. Commit et branche

SHA_FINAL
