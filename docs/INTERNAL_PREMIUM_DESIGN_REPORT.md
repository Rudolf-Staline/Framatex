# FRAMATEX — Refonte premium de l'espace interne · rapport

Branche : `design/internal-premium-ux` (base `feat/folder-color-naming`, `f0b064b`), développée
dans un worktree séparé. Non modifiés : landing publique, Espace Client, ressources de Codex, `main`.
Suivi : [`INTERNAL_PREMIUM_PROGRESS.md`](INTERNAL_PREMIUM_PROGRESS.md).

## 1. Skills : provenance, installation, usage réel

| Skill | Source (commit cloné) | Licence | Installation | Usage réel dans cette mission |
|---|---|---|---|---|
| Frontend Design | `anthropics/skills` `e4bb5d9` | voir LICENSE.txt | copie de `skills/frontend-design` dans `~/.claude/skills` | plan de design (palette, typographie, un seul « geste » signature), liste des tics de pages générées : sur-titres en capitales partout, chaînes « A · B · C », cartes identiques à ombre grise, statistiques décoratives |
| UI UX Pro Max | `nextlevelbuilder/ui-ux-pro-max-skill` `e8b065f` | MIT | copie de `.claude/skills/ui-ux-pro-max` ; script `search.py` relu avant exécution (recherche locale dans des CSV, sans réseau ni commande système) | recherche « data table » (tableaux à défilement horizontal sur mobile, en-têtes), licence d'Open Sans dans sa base (`OFL`) |
| Impeccable | `pbakaus/impeccable` `b49177d` | Apache-2.0 | copie de `.claude/skills/impeccable` (scripts non exécutés) | mode « Operate » (l'identité n'apporte que typo, palette, densité et un geste signature ; jamais la structure ni les contrôles) ; grille d'audit (contraste, mouvement, cibles tactiles, débordement) appliquée au § 6 |
| Taste Skill | `Leonxlnx/taste-skill` `6c0b5c7` | MIT | copie de `skills/taste-skill` (scripts `shoot.mjs`/`consistency.mjs` non exécutés) | conçu pour des sites vitrines : seule la règle « vraies photographies, pas d'images générées » a été retenue |
| REA | `morluto/rea` | MIT | **non installé** | REA est un serveur MCP de rétro-ingénierie de binaires et d'applications, installé par `npx rea-agents setup` (configuration MCP et ponts natifs). Hors de proportion pour relever une identité web : le relevé a été fait directement dans Chromium avec `getComputedStyle` et `document.fonts` (§ 2). |

Aucun script externe n'a été exécuté à l'aveugle ; aucune autorisation supplémentaire n'a été requise.
Le domaine `framatex.net` était bloqué par la politique réseau : un environnement personnel
« Framatex » autorisant `framatex.net`, `www.framatex.net` et les hôtes Google Fonts a été créé
(approuvé dans la session) pour l'audit.

## 2. Relevé de l'identité officielle (framatex.net, Chromium 1440 et 390 px)

Méthode : `scripts` d'audit dans le bac à sable (Playwright), `getComputedStyle` sur `body`, `h1–h3`,
liens de navigation, boutons, en-tête et pied de page ; `document.fonts` ; requêtes de polices.

| Élément | Valeur relevée |
|---|---|
| Police | **Open Sans** (thème WordPress Avada, fichiers servis depuis `wp-content/uploads/fusion-gfonts/`) |
| Graisses | 400 (texte), 500–600 (navigation), 600 (titre principal), 700 (titres de section) |
| Corps | 15 px, interligne 25,5 px (1,7), couleur `#003B70` |
| Titre principal | 49,5 px / 54,45 px, 600, blanc sur bleu |
| Sur-titres | 15 px, capitales, **espacement 8 px**, cyan `#2DAAE1` ; variante « DEVENONS PARTENAIRES » bleu sur pavé blanc |
| Titres de section | 30 px / 36 px, 700, `#232323` |
| Couleurs dominantes | `#003B70` (626 occurrences), blanc, `#232323`, `#2DAAE1`, gris `#4F4F4F`, fond `#F9F9FB` ; logo sur `#00004C` |
| Boutons | contour blanc, capitales, 600, rayon ~10 px sur le héros |
| Composition | héros bleu plein avec grandes formes courbes grises, texte aligné à gauche, beaucoup d'air |
| Photographies | produits finis (costume, chemise, manteau…) et portraits d'équipe ; aucune illustration |

Les fichiers de police relevés (`memtYaGs126MiZpBA-UFUIcVXSCEkx2cmqvXlWqWuU6F.woff2`) portent le même
identifiant que ceux de Google Fonts : c'est la même Open Sans. Limite : en mode sans tête, certaines
images et polices du site ont répondu en erreur ; les valeurs ci-dessus proviennent des styles calculés,
pas de la capture.

## 3. Polices et licences

- **Open Sans** (Steve Matteson), police variable 300–800, normale et italique, sous-ensembles latin et
  latin étendu, **auto-hébergée** : `static/brand/fonts/open-sans-*.woff2`.
  Licence **SIL Open Font License 1.1** : `static/brand/fonts/OFL-Open-Sans.txt` (copie du dépôt
  officiel `googlefonts/opensans`). Aucune requête externe à l'exécution (compatible CSP).
- Les polices DM Sans et Manrope restent dans le dépôt pour la landing et l'Espace Client, qui ne sont
  pas modifiés.

## 4. Direction appliquée

« Corporate Editorial Workspace » : l'identité n'apporte que la typographie, la palette, la densité et
un seul geste signature ; la structure reste celle d'un logiciel métier.

- **Palette** : bleu FRAMATEX `#003B70` (menu, boutons principaux), cyan `#2DAAE1` réservé aux repères
  (état actif, focus, pastilles), titres `#232323`, surfaces `#F5F6F8`, séparateurs `#E1E5EA` ; quatre
  couleurs de sous-dossiers inchangées.
- **Typographie** : Open Sans partout ; 14 px de base, tableaux 13,5 px, titres de page 26 px / 700.
- **Geste signature** : sur les deux accueils seulement, un bandeau bleu reprenant le pavé « sur-titre
  espacé » et les courbes du héros officiel (dessinées en CSS, aucune image générée).
- **Rigueur** : rayons 4–6 px, bordures 1 px, ombres seulement sur les éléments flottants, aucun
  dégradé décoratif, aucune statistique décorative.
- **Logo** : fichier officiel `static/landing/logo-framatex.jpg`, jamais redessiné ni étiré ;
  `object-fit: cover` ne rogne que le fond uni du carré, sur un cadre de la même couleur.

## 5. Pages modernisées

Architecture : une couche finale `static/brand/internal-premium.css` + `static/internal-premium.js`,
chargée en dernier par `static/index.html` et rattachée à `body.fx-pro`. Les boutons existants (et
leurs gestionnaires) sont **déplacés**, jamais recréés ; aucune API, aucune permission, aucun contrôle
serveur n'a été modifié.

| Écran | Avant | Après |
|---|---|---|
| **Menu latéral** (P0) | fond blanc, libellés en capitales, carte « Framatex Assist », « Mon compte » mêlé aux outils | bleu FRAMATEX `#003B70`, logo officiel en bandeau, trois rubriques (*Travail quotidien*, *Ressources*, *Administration* / *Contrôle*), état actif à filet cyan, compteur de notifications non lues, **menu réductible** (icônes seules, infobulles, préférence mémorisée), profil, Mon compte et Déconnexion en pied ; tiroir mobile conservé |
| **Barre supérieure** (P0) | « WORKSPACE », pastille « Espace interne », bouton profil qui fait défiler le menu | fil d'Ariane français (« Espace FRAMATEX › Commandes › FR-DEMO… »), champ de recherche documentaire (Ctrl K / ⌘ K), cloche avec nombre de non-lues, profil qui ouvre Mon compte |
| **Accueil administrateur** (P0) | 10 cartes KPI, tableau de complétude en pourcentages, activité | **aucune statistique** : bandeau éditorial et raccourcis réels (nouvelle commande, recherche, collaborateurs, clients, mémoire métier) ; actions prioritaires ; documents à traiter (manquants, en validation, types à vérifier, doublons ; filtre par sous-dossier) ; commandes récentes avec l'avancement de chaque sous-dossier et choix du tableau de bord d'une commande ; demandes clients à traiter ; alertes ; notifications |
| **Accueil technicien** (P0) | même tableau de bord que le chef (KPI) ou carte vide | mes commandes attribuées avec un bouton par sous-dossier autorisé et son niveau (Lecture seule, Dépôt sans validation, Responsable, Personnalisé) ; mes actions prioritaires ; documents à traiter de mes sous-dossiers ; mes notifications ; accès rapides ; derniers retours de mémoire métier accessibles ; état vide explicite sans affectation |
| **Commandes** (P0) | 8 champs de filtre sur deux lignes | quatre filtres principaux, critères secondaires sous « Plus de filtres » (dépliés d'office si l'un d'eux est renseigné), tableau aux en-têtes lisibles, références en bleu |
| **Fiche commande** (P0) | 7 boutons sur deux lignes | actions principales visibles, « Suivi », « Modifier », « Gérer les accès » dans **Plus d'actions** (mêmes boutons, mêmes droits) |
| **Sous-dossiers** (P0) | grands aplats colorés | noms exacts conservés (*Sous-dossier jaune / rose / bleu / vert*), en-tête de la couleur sur fond pâle et filet supérieur, sous-dossier interdit grisé « Accès restreint » sans donnée ; sélecteur de sous-dossier coloré avec état courant |
| **Documents** (P1) | styles hérités | checklists, dépôt, consultation, versions, commentaires, OCR, cohérence, validations : tableaux, modales, champs et onglets harmonisés par la couche (aucune fonction modifiée) |
| **Mémoire métier** (P1) | 7 cartes chiffrées, 10 filtres plein écran | repères chiffrés en une ligne discrète, filtres secondaires repliés, **retours en chronologie** (fil vertical, pastilles), fiches partenaires sobres |
| **Collaborateurs et habilitations** (P1) | — | tableaux, onglets et matrice harmonisés ; niveaux Aucun accès / Lecture seule / Dépôt sans validation / Responsable / Personnalisé inchangés |
| **Autres écrans** (P1/P2) | en-têtes hétérogènes (point final coloré, sur-titres en capitales) | Mes actions, Notifications, Recherche, Clients et demandes, Historique et audit, Mon compte, Assistant : même titre de page ; connexion et changement de mot de passe : Open Sans, sur-titre officiel, logo officiel ; modales, formulaires, erreurs, états vides et chargements harmonisés |
| **Mouvement** (P2) | entrées multiples | ouverture des modales et menus, apparition courte du contenu (≤ 0,28 s), survols ; aucune animation permanente ; `prefers-reduced-motion` respecté |

## 6. Audit visuel (grille Impeccable)

| Critère | Constat | Action |
|---|---|---|
| Contraste | titres de rubrique du menu à 50 % de blanc sur `#003B70` = **4,0:1** (insuffisant) | portés à 62 % = **5,3:1** ; libellés 80 % = 7,8:1 ; texte secondaire `#636D7A` = 5,25:1 sur blanc ; cyan lisible `#0A6F9E` = 5,55:1 |
| Débordement horizontal | sélecteur de commande à 390 px : +14 px | corrigé (`min-width: 0`) ; mesure automatique sur les 71 captures : **0 débordement** |
| Clavier | focus visible cyan 2 px partout ; lignes de commandes activables à Entrée ; menu « Plus d'actions » natif (`details`) | — |
| Cibles tactiles | boutons ≥ 30 px, navigation 38 px | conforme au seuil WCAG 2.5.8 (24 px) |
| Mouvement | animations courtes, déclenchées par l'utilisateur | désactivées sous `prefers-reduced-motion` sans perte d'état |
| Identité | aucune image générée, logo officiel non déformé, une seule police (officielle) | — |
| Restant (P3) | les gros compteurs du module « Complétude » de l'onglet Contrôles et de la page Mes actions sont conservés : ce sont des compteurs fonctionnels de checklist, pas des statistiques d'accueil | à alléger lors d'une passe ultérieure |

## 7. Captures avant / après

`docs/internal-premium-captures/avant/` et `docs/internal-premium-captures/apres/` : mêmes données de
démonstration, mêmes comptes fictifs, mêmes largeurs (1920, 1440, 1024, 820, 390 px pour l'accueil,
les commandes, la fiche commande et le sous-dossier ; 1440 et 390 px pour les autres écrans).
Script : `python scripts/capture_internal_ui.py --output <dossier>` (base temporaire, mots de passe
aléatoires jamais écrits, défilement horizontal mesuré et attribué à l'élément fautif).

## 8. Tests réalisés

Exécutions réelles sur la branche (serveur Uvicorn sur base temporaire, Chromium) :

| Suite | Résultat |
|---|---|
| `pytest` complet | **209 réussis** |
| Tests JS `node tests/*.cjs` | **21/21** |
| `scripts/capture_internal_ui.py` (chef + 2 techniciens, 1920/1440/1024/820/390) | 71 captures, 0 échec, 0 erreur JS, 0 débordement |
| `scripts/validate_internal_ui.py` | réussi — 52 captures, 7 parcours, aucune erreur JS |
| `scripts/validate_access_ui.py` | **15/15** (création, mot de passe temporaire, matrice, isolation, révocation, persistance) |
| `scripts/validate_client_workflow_ui.py` | réussi — scénario complet |
| `scripts/validate_business_memory_ui.py` | **11/11** |
| `scripts/qa_platform_review.py` | **96/96** |
| `scripts/demo_full_platform.py` | **135/135** |
| `scripts/validate_document_workspace.py` | **7/9** — les 2 échecs existent à l'identique sur la base `f0b064b` (vérifié dans un worktree) : la recette ne traite pas la décision « doublon potentiel » désormais exigée au dépôt (comportement métier de la base) |

Recettes adaptées, sans affaiblir les vérifications : l'accueil attendu n'a plus de cartes KPI (le
nombre attendu passe de 10 à 0) ; les parcours qui cliquaient sur les KPI cliquent désormais sur les
listes de travail (actions, documents à traiter, alertes, commandes) et vérifient l'ouverture du bon
dossier ; le libellé attendu « Sous-dossier Jaune » est aligné sur le nom officiel « Sous-dossier jaune ».

## 9. Fonctionnalités préservées

Aucun fichier backend n'a été modifié (`app/` intact) : authentification, comptes et habilitations,
affectations, documents, versions, OCR, doublons, cohérence, validations, mémoire métier, recherche,
notifications, QR codes, passeports et audit fonctionnent comme avant — démontré par `pytest`,
`qa_platform_review` (96/96) et `demo_full_platform` (135/135). Côté interface, la couche finale
déplace les boutons existants avec leurs gestionnaires ; les écrans reçoivent les mêmes données des
mêmes API, toujours filtrées par le serveur. Les services de statistiques (`/api/workspace/dashboard`,
`kpis`) sont conservés : seule leur présentation en cartes a été retirée de l'accueil ; le tableau de
bord d'une commande reste accessible (fiche commande et sélecteur de l'accueil).

## 10. Limites restantes

- Référence éditoriale « Motives International » : la capture n'était pas disponible dans cette
  session ; la direction s'appuie sur le site officiel framatex.net.
- REA non installé (voir § 1) ; le relevé a été fait avec Chromium et `getComputedStyle`.
- Les écrans hérités sont harmonisés par la couche CSS, pas réécrits : quelques gabarits internes
  (module Complétude de l'onglet Contrôles, compteurs de Mes actions, page Administration « Rôles et
  checklists ») gardent leur structure d'origine.
- Aucune visionneuse documentaire nouvelle n'a été développée (hors priorité, comme demandé).
- `validate_document_workspace.py` : 2 échecs antérieurs à la refonte (décision « doublon potentiel »).
- Le thème sombre n'est pas prévu (l'application interne n'en avait pas).

## 11. Fichiers modifiés

Nouveaux : `static/brand/internal-premium.css`, `static/internal-premium.js`,
`static/brand/fonts/open-sans-latin-var-normal.woff2`, `open-sans-latin-ext-var-normal.woff2`,
`open-sans-latin-var-italic.woff2`, `OFL-Open-Sans.txt`, `scripts/capture_internal_ui.py`,
`docs/INTERNAL_PREMIUM_PROGRESS.md`, `docs/INTERNAL_PREMIUM_DESIGN_REPORT.md`,
`docs/internal-premium-captures/avant/` (63) et `apres/` (71).

Modifiés : `static/index.html` (2 lignes : la feuille et le script de la couche, chargés en dernier) ;
recettes `scripts/validate_internal_ui.py`, `validate_access_ui.py`, `validate_client_workflow_ui.py`,
`validate_document_workspace.py`, `demo_browser_full.py`, `demo_full_platform.py`, `windows_runtime.py`.

Non modifiés : `app/` (backend), `static/brand/tokens.css`, `static/landing/`, `static/client/`,
tous les modules JS existants.

## 12. Commit et branche

Branche distante `origin/design/internal-premium-ux`. Le SHA final est celui du commit qui contient
ce rapport ; il est communiqué dans le message de livraison et vérifiable par
`git ls-remote origin design/internal-premium-ux`. `main` n'est pas modifié ; aucune fusion.

Lancement : `pip install -r requirements-dev.txt` puis `python -m uvicorn app.main:app --port 8000`,
ouvrir `/espace-framatex`. Captures : `python scripts/capture_internal_ui.py --output <dossier>`.
