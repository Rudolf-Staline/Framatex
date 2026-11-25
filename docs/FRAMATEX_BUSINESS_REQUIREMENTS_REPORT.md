# FRAMATEX — Exigences métier de la tutrice · rapport

Branche : `feat/framatex-business-requirements`, créée depuis `fix/full-platform-stability`
(`1e5e981`, correctifs de Codex conservés, dont l'ouverture des commandes par les techniciens).
`main` n'est pas modifié. Design premium existant conservé ; landing, 3D, partenariat et connexions
non modifiés.

> Les photographies du modèle de la tutrice n'étaient pas visibles dans cette session : la fiche
> suit la liste des 14 champs fournie dans la demande.

## 1. Exigences réalisées

| Lot | Réalisé | Commit |
|---|---|---|
| **1. Fiche commande et transfert Client** | 14 champs ; seul le nom est obligatoire ; NULL = « Non renseigné » (jamais 0) ; références en texte (zéros initiaux conservés : `000417`, `0042`) ; création complète en une transaction (`POST /api/order-sheets`) ; panneau « Fiche commande » en tête du Dossier Jaune (replié dans la vue d'un sous-dossier) ; « Modifier la fiche » réservé à `launch.update` ; historique avant/après ; lecture technicien selon l'affectation, sans droit ajouté. Demande Client : nom du projet, description, couleur, référence de commande, N° client issu du compte ; transfert intégral à l'acceptation | `c8b365c` |
| **2. Recherche** | N° client (`client_code` existant, jamais dupliqué), client, projet, N° commande FRAMATEX, N° de demande Client, référence de commande Client, article, atelier, couleur, N° OF, facture, document, type ; casse et accents ignorés ; résultats « commandes » et « documents » cliquables ; pagination ; aucune commande ni document non autorisé ; recherche dans « Mes demandes » côté Client | `1b4ceae` |
| **3 et 5. Visionneuse** | PDF (pages rendues côté serveur, navigation, zoom, plein écran, recherche surlignée) ; Excel (feuilles, cellules, formules, grands tableaux par 200 lignes, 60 colonnes) ; Word (titres, texte, tableaux ; limite de fidélité signalée) ; PNG/JPG ; TXT/CSV ; EML (objet, expéditeur, destinataires, date, texte, pièces jointes listées) ; format non prévisualisable expliqué ; actions existantes conservées à droite ; version historique affichée avec son propre contenu | `24c331d` |
| **4. Historique** | Sur l'audit existant (aucun système concurrent) : global (filtres commande, auteur, action, document, dates), par commande (onglet Historique), par document (visionneuse) ; date et heure, auteur, action, commande, sous-dossier, type, fichier, version, avant/après, motif ; « Ouvrir Vn » ouvre la visionneuse sur la version ; document supprimé → corbeille (administrateur), jamais rouvert ; habilitations détaillées aux administrateurs ; « Information non enregistrée » pour les anciens événements incomplets | `2e6fbee` |
| **6. Performance** | SQLite : `busy_timeout` 15 s (une écriture concurrente attend au lieu d'échouer) ; **WAL évalué puis écarté** (aucun gain mesuré ; une copie brute de `framat.db` aurait pu omettre les écritures récentes, risque réel pour les sauvegardes manuelles) ; recherche : détails calculés pour la seule page renvoyée ; test de charge progressif reproductible | `932871c`, commit final |
| **Compatibilité** | Référence ORLI conservée dans la fiche ; formulaire de création avec les identifiants historiques (`#new-launch-form`, `#l-name`…) ; association d'un fournisseur à la création (mémoire métier) conservée et désormais enregistrée avec la fiche complète ; historique du document non demandé sans droit d'audit (aucune requête refusée) | commit final |

## 2. Migrations

`0016_order_sheet` (additive, idempotente, compatible avec les anciennes bases) :
- `launch_operations` : `description`, `workshop`, `color`, `of_number`, `quantity_launched`,
  `quantity_delivered`, `invoice_ref`, `desired_date`, `client_order_ref`, `client_account_id`
  (référence `client_accounts`) ;
- `client_order_requests` : `project_name`, `description`, `color` ;
- index : atelier, couleur, N° OF, facture, référence Client, compte Client, `launches.order_ref`,
  `launches.client_name`.

Champs réutilisés sans doublon : nom (`launches.name`), N° commande FRAMATEX (`launches.order_ref`),
client (`launches.client_name`), article et quantité commandée (`launch_operations`), N° client
(`client_accounts.client_code`). Pour une commande historique sans compte Client, le N° client reste
« Non rattaché » jusqu'à un rattachement explicite à un compte existant (aucune identité inventée).

## 3. Sécurité de la visionneuse

Aperçus rendus par le serveur (PyMuPDF, openpyxl, python-docx, Pillow, module `email`) ; droits
revérifiés à chaque requête (accès à la commande + `document.read`) ; le fichier original reste
réservé à `document.download` (consultation sans téléchargement testée) ; versions et documents
supprimés inaccessibles ; formules et macros jamais exécutées ; scripts HTML des emails retirés ;
images ré-encodées sans métadonnées ; tailles bornées (40 Mo, 2 400 px, 300 Ko de texte) ; aucun
service externe. Les captures d'écran ne peuvent pas être empêchées.

## 4. Performances mesurées

Serveur Uvicorn unique, 4 CPU, base temporaire. Scénario par utilisateur : connexion, création,
ouverture, recherche, dépôts PDF et Excel, aperçus PDF et Excel, fiche, suppression, restauration
(11 requêtes). Trois campagnes : initiale, avec WAL, configuration finale (`busy_timeout` sans WAL) —
`docs/load-test/avant-wal.json`, `apres-wal.json`, `final-sans-wal.json`.

| Utilisateurs simultanés | Requêtes | Débit | Erreurs | Verrous SQLite | Recherche (médiane) | Création (médiane) |
|---|---|---|---|---|---|---|
| 1 | 11 | 31–36 req/s | 0 | 0 | 9–11 ms | 91–92 ms |
| 5 | 55 | 60–65 req/s | 0 | 0 | 67–76 ms | 40–49 ms |
| 10 | 110 | 52–56 req/s | 0 | 0 | 290–369 ms | 74–77 ms |
| 20 | 220 | 47–54 req/s | 0 | 0 | 665–966 ms | 172–178 ms |

Intégrité : toutes les commandes créées (36/36 puis 30/30), aucun doublon. Le plafond observé
(≈ 50–65 req/s) est celui du processus unique (hachage Argon2 à la connexion, rendu PDF, recherche
en Python) ; aucune campagne n'a produit de verrou SQLite ; WAL n'a pas changé le débit et a été
écarté (voir § 1). Pistes mesurables ensuite : plusieurs
processus Uvicorn, index de recherche plein texte. Les limites anti-abus (tentatives de connexion)
ne sont pas modifiées.

## 5. Tests réellement exécutés

Bases temporaires, données fictives (`example.test`), serveurs Uvicorn réels, Chromium avec clics réels.

| Suite | Résultat final |
|---|---|
| `pytest` (dont `test_order_sheet.py`, `test_document_preview.py`) | **226 réussis** |
| Tests JS `node tests/*.cjs` | **21/21** |
| `validate_business_requirements_ui.py` — demande Client enrichie, acceptation et transfert, création complète, « Modifier la fiche », recherche par N° client, lecture technicien | **6/6** |
| `validate_document_viewer_ui.py` — PDF (page, zoom, recherche), V1 depuis l'historique, Excel (feuilles, formules, 399 lignes), Word, historique global/commande/document, corbeille | **8/8** |
| `validate_costume_technician.py` (scénario Costume de Codex) | **réussi** |
| `validate_document_deletion_ui.py` | **5/5** |
| `validate_document_workspace.py` | **9/9** |
| `validate_business_memory_ui.py` (dont persistance après redémarrage) | **11/11** |
| `validate_sessions_ui.py` · `validate_access_ui.py` | **9/9** · **15/15** |
| `validate_client_workflow_ui.py` · `validate_internal_ui.py` | réussis (52 captures, 7 parcours) |
| `validate_landing_motion.py` · `validate_partnership_carousel.py` · `validate_cinematic_3d.py` | 31/31 · 7/7 · réussi |
| `qa_platform_review.py` · `demo_full_platform.py` | **96/96** · **135/135** |
| `load_test_platform.py` (1, 5, 10, 20 utilisateurs) | 0 erreur, 0 verrou SQLite, 0 doublon |

Préparation par l'API dans certaines recettes (création des fichiers PDF/Excel/Word de test, V2) ;
toutes les consultations, ouvertures, modifications, recherches et navigations sont faites par clics.
Le dépôt par l'interface est couvert par `validate_document_workspace.py` et le scénario Costume.

## 6. Captures

`docs/business-requirements-captures/` : nouvelle demande Client, fiche transférée, création de
fiche, fiche modifiée, recherche par N° client, visionneuse PDF / Excel / Word, historique global.

## 7. Restant à développer

- Publication sélective, côté Client, des informations gérées par FRAMATEX (atelier, N° OF,
  quantités lancée et livrée, facture) : aujourd'hui elles ne sont **jamais** visibles du Client.
- Pièces jointes des emails : listées, non ouvrables depuis l'email (à déposer comme documents).
- PDF scannés sans texte : la recherche dans la visionneuse ne trouve rien (l'OCR existant reste
  disponible dans « OCR / extraction »).
- Historique par commande et par document : réservé aux rôles disposant de `audit.read`.
- Performances au-delà de 20 utilisateurs simultanés et documents très volumineux : non mesurés
  (aperçus refusés au-delà de 40 Mo, message explicite).

## 8. Commit et branche

Branche distante `origin/feat/framatex-business-requirements` (commits `c8b365c`, `1b4ceae`, `24c331d`,
`2e6fbee`, `932871c`, puis le commit de ce rapport — SHA final donné dans le message de livraison,
vérifiable par `git ls-remote origin feat/framatex-business-requirements`). `main` non modifié.
