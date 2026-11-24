# FRAMATEX — Intégration finale des deux designs

Branche : `integration/final-premium-design` · base commune `feat/folder-color-naming` (`f0b064b`).
`main` n'est pas modifié.

## 1. Fusion

| Branche | Commit intégré | Contenu |
|---|---|---|
| `design/internal-premium-ux` (Claude) | `9f8adab` | espace interne : identité officielle, menu, accueils sans statistiques, commandes, documents, mémoire métier, habilitations |
| `design/landing-final-premium` (Codex) | `471f479` | landing : hero éditorial serif, navigation bleue, menu mobile, chaîne de valeur, partenariat |

- L'intégration part de `design/internal-premium-ux` et fusionne `design/landing-final-premium` par un
  commit de fusion (`699c994`, `--no-ff`) : les deux historiques sont conservés.
- Aucun conflit textuel : les fichiers modifiés sont distincts (Codex : `static/landing/`,
  `tests/test_landing.py`, `scripts/validate_landing_motion.py`, ses documents ; Claude : couche
  `static/internal-premium.*`, `static/index.html`, recettes internes, documents et captures).
- Conflits fonctionnels vérifiés : la landing (`/`) et l'espace interne (`/espace-framatex`) ne
  partagent que `static/brand/tokens.css`, que ni l'un ni l'autre ne modifie ; la couche interne est
  rattachée à `body.fx-pro`, absent de la landing et de l'Espace Client. Après fusion, avant toute
  correction : `pytest` 210 réussis, JS 21/21, recette Chromium de la landing 31/31.

## 2. Photographie « Notre solution »

- Fichier : la photographie de l'équipe autour d'une table, `https://framatex.net/wp-content/uploads/2022/08/banner-17.jpg`
  (1920 × 1005, publiée sur le site officiel FRAMATEX). La photographie jointe par l'utilisateur
  n'était pas disponible dans cette session : le fichier a été repris à l'adresse indiquée, sans
  retouche autre qu'un recadrage. Aucune image générée.
- Recadrage 4:3 centré sur la table (1340 × 1005 depuis x = 180), puis encodage local :
  `static/landing/notre-solution-equipe.{avif,webp,jpg}` (1200 × 900 : 96 Ko, 136 Ko, 210 Ko) et
  variantes `-640` (33 Ko, 50 Ko, 73 Ko), servies par `srcset`/`sizes` dans un `<picture>`.
- Le cadre de la section passe en 4:3 pour montrer la scène entière (poignée de main au centre) ;
  la section partenariat garde sa propre photographie (`partnership-meeting`).
- Droits : il s'agit d'une image publiée par FRAMATEX sur son site et désignée par l'utilisateur.
  Elle paraît provenir d'une banque d'images ; la licence d'origine est à confirmer par FRAMATEX
  avant mise en production publique.
- Test ajouté (`tests/test_landing.py`) : les trois formats sont référencés et servis (`200`, `image/*`).

## 3. Harmonisation graphique

| | Landing | Espace interne |
|---|---|---|
| Bleu | `#003B70` (navigation, boutons, en-tête au défilement, voiles du hero : anciennes teintes `rgba(10,31,68)` / `rgba(14,42,90)` remplacées par `#002C55` / `#003B70`) | `#003B70` (menu latéral, boutons) |
| Cyan | `#2DAAE1` (filets, accents), `#0A6F9E` lisible sur blanc | idem |
| Police | **Open Sans** locale (fichiers partagés `static/brand/fonts/open-sans-*`, OFL) pour la navigation, les textes et les éléments fonctionnels ; **titres h1–h3 en serif éditoriale** conservés | Open Sans partout |
| Couleur de thème | `#003b70` | — |

Les valeurs officielles sont redéfinies dans `landing.css` uniquement : `static/brand/tokens.css`
(partagé avec l'Espace Client) n'est pas modifié ; l'Espace Client garde son apparence. Aucune
refonte : la composition de Codex (hero, sections, animations) est intacte. Les accueils administrateur
et technicien restent **sans statistiques globales** (vérifié par les recettes : aucune carte KPI).

## 4. Doublons potentiels — `validate_document_workspace.py`

Diagnostic : les deux échecs historiques ne venaient pas d'un défaut de l'application. Lors du dépôt
d'une « version corrigée » dont le contenu est en réalité un bon de livraison, puis reclassée dans le
sous-dossier rose, le serveur signale un **doublon potentiel** avec la V1 mal classée ; l'interface
exige alors une décision explicite (« Choisissez comment traiter le rapprochement documentaire
proposé »). La recette, écrite avant cette règle, cliquait sur « Confirmer » sans décision et
attendait la publication (échec 1) ; la fenêtre restée ouverte bloquait le scénario suivant (échec 2).

Correction de la recette, en renforçant le contrôle : elle vérifie désormais que la confirmation sans
décision est **refusée** (message affiché, aucune requête `/publish`), puis choisit « Conserver comme
nouveau document indépendant » et vérifie la publication dans le sous-dossier rose. Résultat : 9/9.

## 5. Tests (exécutions réelles, base temporaire, Chromium)

Exécutées sur le commit `6ace861` (serveurs Uvicorn réels sur bases temporaires ; aucune donnée
opérationnelle touchée).

| Suite | Périmètre | Résultat |
|---|---|---|
| `pytest` complet | API, permissions, migrations, landing | **210 réussis** |
| `node tests/*.cjs` | rendus JS internes et Client | **21/21** |
| `validate_landing_motion.py` | landing 1920 → 390 px, menu mobile, liens des deux espaces, images locales, mouvement réduit | **31/31** |
| `validate_client_workflow_ui.py` | Espace Client : inscription, activation, demande, dépôt, partage, retrait, compte suspendu | **réussi** |
| `validate_internal_ui.py` | connexion chef, accueil sans KPI, commandes, quatre sous-dossiers, recherche, audit, 1440 → 390 px | **réussi** (52 captures, 7 parcours, 0 erreur JS) |
| `validate_access_ui.py` | création de techniciens, mot de passe temporaire, habilitations individuelles, isolation, révocation, désactivation, persistance | **15/15** |
| `validate_document_workspace.py` | dépôt PDF/Word/Excel, versions, doublons potentiels, OCR, cohérence | **9/9** |
| `validate_business_memory_ui.py` | mémoire métier par sous-dossier | **11/11** |
| `qa_platform_review.py` | revue globale (OCR, contrôles, notifications, historique, sécurité) | **96/96** |
| `demo_full_platform.py` | démonstration complète API + navigateurs Client et FRAMATEX | **135/135** |

## 6. Limites

- La photographie jointe par l'utilisateur n'était pas accessible dans cette session ; le fichier
  officiel de l'URL fournie a été utilisé. Licence d'origine à confirmer (voir § 2).
- L'Espace Client conserve DM Sans et ses couleurs (hors du périmètre demandé ; harmonisable par la
  même redéfinition locale si souhaité).
- La serif du hero reste une pile système (Iowan Old Style, Baskerville, Times New Roman), comme
  livrée par Codex : aucune police serif propriétaire n'a été ajoutée.

## 7. Commit et branche

Branche distante `origin/integration/final-premium-design`. Commits : fusion `699c994`, corrections
`6ace861`, puis le commit de ce rapport (SHA final communiqué dans le message de livraison, vérifiable
par `git ls-remote origin integration/final-premium-design`). `main` n'est pas modifié.
