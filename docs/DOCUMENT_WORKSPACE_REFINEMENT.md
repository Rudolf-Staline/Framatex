# FRAMATEX — Parcours documentaire du Dossier Jaune

Branche `feat/document-workspace-refinement`, créée depuis `design/landing-motion-wow` au commit `ae6b92602be15fce54e5a1e22cc7f43fee8e1131`.

Révision soumise à la recette de livraison `4013bc38ec46d5e8ccb91ed14f5c45748770b759`. Le commit suivant contient ce rapport et les captures. La commande `git rev-parse HEAD` ci-dessous donne le SHA exact de la version récupérée.

## Parcours livré

Depuis le tableau de bord général, sélectionnez une commande pour voir ses chiffres, ses alertes et son activité. Le tableau de bord individuel interroge `/api/launches/{id}/dashboard`. Il calcule les listes après contrôle des droits et à partir des seules pièces de la commande sélectionnée.

La liste des commandes et les demandes Client acceptées ouvrent la vue des quatre sous-dossiers. Chaque carte affiche sa couleur, sa fonction et sa progression. Le clic ouvre uniquement la checklist du sous-dossier. Le fil d’Ariane, le bouton de retour et les raccourcis entre sous-dossiers gardent la référence de commande accessible. Contrôles, Communication et Historique restent accessibles par onglets.

Les 22 règles standard couvrent les mêmes 19 pièces obligatoires et 3 facultatives. Les états distinguent absence, type à vérifier, type incompatible, présence conforme, validation métier, exception et non-applicabilité. Le signal de doublon exact s’ajoute à l’état de la pièce. Les quatre sous-dossiers se traitent en parallèle.

## Dépôt et lecture

Le dépôt depuis une ligne connaît la commande, le sous-dossier et le type attendu. Le dépôt général accepte plusieurs fichiers et traite leur classement successivement. Le navigateur affiche les octets transmis, puis l’analyse et le résultat de chaque fichier. Les versions, les liens de consultation, le SHA-256 et l’audit utilisent le stockage et les routes existants.

L’API conserve temporairement le fichier après réception et calcule une proposition à partir de son contenu. La commande, le sous-dossier initial et l’auteur sont liés au transfert. La confirmation rattache ces mêmes octets à la pièce. Un transfert publié ou annulé ne peut pas être réutilisé. Un transfert abandonné expire après deux heures et ses fichiers sont purgés au démarrage ou au prochain dépôt guidé. Un transfert réseau en cours peut être interrompu depuis l’interface.

Le lecteur distingue texte PDF natif, Word, cellules Excel et OCR sur les images et PDF scannés. Le nom du fichier reste un indice secondaire. Les propositions affichent les mots repérés, la rubrique et la référence de commande quand l’extraction le permet. Une reconnaissance incertaine peut être archivée avec le statut « Déposé — à vérifier ». En cas de conflit, le collaborateur peut corriger le classement, conserver le classement avec justification, ou annuler. Une version marquée à vérifier ou incompatible ne satisfait pas la pièce attendue.

Les classifications historiques restent exploitables après la migration additive `0010_document_intake`. L’API de dépôt direct historique conserve les classements fournis par les intégrations lorsque le lecteur n’établit pas de contradiction. La vérification des types inconnus s’applique au parcours guidé et aux nouvelles versions de pièces déjà identifiées. Cette compatibilité ne constitue pas une reclassification rétrospective des archives.

## Taille, analyses et cohérence

| Format interne | Limite par défaut | Variable d’environnement |
| --- | ---: | --- |
| PDF | 200 Mio | `FRAMATEX_UPLOAD_PDF_MIB` |
| Excel | 100 Mio | `FRAMATEX_UPLOAD_EXCEL_MIB` |
| Word | 100 Mio | `FRAMATEX_UPLOAD_WORD_MIB` |
| Images | 50 Mio | `FRAMATEX_UPLOAD_IMAGE_MIB` |
| Autres formats autorisés | 20 Mio | `FRAMATEX_UPLOAD_OTHER_MIB` |

Chaque variable accepte un entier de 1 à 200. Le plafond de 20 Mio sur les autres formats préserve la limite historique. La limite peut être relevée, par exemple avec `$env:FRAMATEX_UPLOAD_OTHER_MIB = '100'`. Le plafond du corps HTTP tient compte du format maximal configuré et d’un Mio d’enveloppe multipart. Si un proxy HTTP précède Uvicorn, sa limite de corps doit autoriser ce plafond et ses délais doivent couvrir le transfert et l’analyse.

La réception multipart utilise un fichier temporaire au-delà de son seuil mémoire. La copie vers le stockage et le calcul SHA-256 progressent par blocs. Le serveur vérifie les signatures, la structure ZIP Office, les tailles décompressées et les archives excessivement compressées. La lecture d’un document est bornée séparément à 12 Mio, trois pages PDF, trois feuilles Excel et des dimensions d’image limitées. Les analyseurs d’identification s’exécutent dans un processus à délai borné. L’inspection statique des formules garde son propre plafond de 5 Mio. Les classeurs s’ouvrent sans macros, sans liens externes et sans utiliser les résultats de formules mis en cache comme mesures métier. Les fichiers dépassant le budget d’analyse peuvent être archivés avec vérification manuelle.

Les valeurs confirmées depuis une version source alimentent les règles inter-documents configurées dans **Contrôles → Cohérence et Excel**. Les résultats indiquent les sources, versions, unités, extraits et écarts. La recette a comparé une commande client de 5 000 pièces et une fiche d’emploi de 4 500 pièces. Le second dossier est resté isolé. Les unités incompatibles et les sources ambiguës bloquent la comparaison. La décision et la justification restent humaines.

## Principaux fichiers

- `static/dossier.js`, `static/dashboard.js` et `static/brand/dossier.css` pour la navigation et les tableaux de bord.
- `static/document-upload.js`, `static/intake.js` et `static/quality.js` pour le transfert, l’identification et les sources de cohérence.
- `app/document_intake_routes.py`, `app/document_intake.py`, `app/intake.py`, `app/upload_limits.py` et `app/main.py` pour la réception et l’analyse.
- `app/completeness.py`, `app/internal_routes.py` et `app/quality.py` pour les états, les compteurs et les comparaisons.
- `app/document_intake_models.py` et `app/migrate.py` pour la migration additive.
- `tests/test_document_workspace.py` et `scripts/validate_document_workspace.py` pour les nouveaux scénarios. Les recettes existantes suivent les nouveaux points d’entrée avec les mêmes attentes métier.

## Recette et captures

Les suites utilisent Chromium et des bases temporaires. La recette dédiée couvre 1920, 1440, 1024, 820 et 390 px. Elle vérifie les transitions d’état après les clics, les réponses API, un vrai PDF de plus de 20 Mio, la progression intermédiaire du transfert, les anomalies de classement, le refus HTTP 413, le fichier invalide, l’interruption réseau et la comparaison de 500 pièces. Le scénario sans OCR utilise un répertoire Tesseract vide et vérifie que la pièce reste à contrôler. La recette complète couvre aussi l’inscription Client, l’acceptation FRAMATEX, la checklist, les versions, les partages, les doublons et le runtime.

| Vérification | Résultat |
| --- | --- |
| Pytest | 181 réussis, dont 6 nouveaux. Un avertissement Starlette/httpx de dépréciation. |
| JavaScript | 19 suites réussies |
| Recette documentaire Chromium | 9/9, cinq résolutions et 40 captures |
| Recette avec OCR indisponible | 5/5 |
| Recette globale API, Chromium et supervision | 133/133, avec stabilité vérifiée jusqu’à T+60 s et migration d’une copie de base |
| Espace FRAMATEX | 7 parcours, 52 captures, aucune erreur JavaScript |
| Parcours documentaire Client | 8 contrôles, cycle métier de 15 étapes |
| Landing | 25/25 contrôles Chromium |
| Préflight du lanceur | Vérifications du code Python et de l’import des dépendances réussies |

| Vue Chromium | Capture |
| --- | --- |
| Tableau de bord général | [1440 px](document-workspace-captures/1440-tableau-general.jpg) |
| Tableau de bord individuel | [1440 px](document-workspace-captures/1440-tableau-commande.jpg) |
| Quatre sous-dossiers | [1440 px](document-workspace-captures/1440-quatre-sous-dossiers.jpg), [390 px](document-workspace-captures/390-quatre-sous-dossiers.jpg) |
| Sous-dossiers | [Jaune](document-workspace-captures/1440-sous-dossier-jaune.jpg), [Rose](document-workspace-captures/1440-sous-dossier-rose.jpg), [Bleu](document-workspace-captures/1440-sous-dossier-bleu.jpg), [Vert](document-workspace-captures/1440-sous-dossier-vert.jpg) |
| Dépôt | [1440 px](document-workspace-captures/1440-depot.jpg), [390 px](document-workspace-captures/390-depot.jpg) |
| Transfert en cours | [Progression intermédiaire](document-workspace-captures/1440-transfert-en-cours.jpg) |
| Avertissement de classement | [Bon de livraison en Fiche de prix](document-workspace-captures/1440-avertissement-type.jpg) |
| Cohérence documentaire | [Écart et version source](document-workspace-captures/1440-coherence.jpg) |

Les captures de dépôt affichent un plafond PDF de 24 Mio configuré pour la recette du refus de taille. La valeur par défaut en exploitation est de 200 Mio.

Le profil PowerShell natif Windows n’a pas pu être exécuté dans l’environnement Linux. Les sondes, tests automatisés et la supervision du serveur ont été vérifiés sur Linux. L’OCR nécessite les données de langue Tesseract françaises et anglaises sur le poste qui exécute le serveur.

## Récupérer et lancer sous PowerShell

Depuis la racine du dépôt local, pour le premier checkout de la branche :

```powershell
git fetch origin refs/heads/feat/document-workspace-refinement:refs/remotes/origin/feat/document-workspace-refinement
git switch --track origin/feat/document-workspace-refinement
git rev-parse HEAD
.\scripts\start_windows.cmd
```

Pour mettre à jour un checkout existant :

```powershell
git switch feat/document-workspace-refinement
git pull --ff-only origin feat/document-workspace-refinement
git rev-parse HEAD
.\scripts\start_windows.cmd
```

Le lanceur initialise l’environnement Python et applique les migrations. Pour un essai avec un stockage distinct et le mode de démonstration existant :

```powershell
$env:FRAMATEX_DATA_DIR = Join-Path $PWD 'data-documentaire-recette'
.\scripts\start_windows.cmd -Demo
```

La documentation du démarrage et de la supervision figure dans [WINDOWS_LOCAL.md](WINDOWS_LOCAL.md).

## Commandes de recette

```bash
python -m pytest -q
for fichier in tests/*.cjs; do node "$fichier" || exit; done
python scripts/windows_preflight.py code
python scripts/windows_preflight.py deps
PYTHONPATH=. python scripts/validate_document_workspace.py --output data/recette-documentaire
PYTHONPATH=. python scripts/validate_document_workspace.py --without-ocr --output data/recette-sans-ocr
PYTHONPATH=. python scripts/demo_full_platform.py --output data/recette-complete
PYTHONPATH=. python scripts/validate_internal_ui.py --output data/recette-interne
PYTHONPATH=. python scripts/validate_client_workflow_ui.py --output data/recette-client
PYTHONPATH=. python scripts/validate_landing_motion.py --output data/recette-landing
```
