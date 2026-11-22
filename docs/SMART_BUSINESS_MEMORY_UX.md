# Mémoire métier et ergonomie FRAMATEX

Branche : `feat/smart-business-memory-ux`, créée depuis `feat/document-workspace-refinement` (`101b1811842336c2e9934aea797953d0352088cb`). Les modifications sont additives et ne touchent pas `main`.

## Fonctionnalités

- La page **Mémoire métier** permet d’ajouter un retour général ou relié à une commande, consulter les partenaires et filtrer les retours par texte, type, catégorie, importance, statut, période et date/importance.
- Le référentiel identifie clients, fournisseurs et ateliers. La recherche ignore casse, accents et espaces; les noms proches sont proposés pour revue humaine. Les doublons normalisés sont refusés, sans fusion automatique des entreprises similaires.
- Une fiche partenaire montre commandes accessibles, synthèse et chronologie. Un retour contient date, faits, importance, recommandation, statut et justificatif facultatif. Les corrections et clôtures demandent un motif et produisent une trace d’audit ainsi qu’un historique de décision.
- Les fiches partenaires peuvent être reliées aux commandes; le parcours d’acceptation d’une demande Client rattache ou crée la fiche correspondante. En cas de correspondance historique incertaine, aucune liaison automatique n’est faite; l’administrateur confirme depuis la demande.
- La sélection du fournisseur/atelier est disponible à la création et à la modification d’une commande, sur les demandes Client et dans le formulaire mémoire. Les vigilances affichées sont calculées sur les retours source, montrent date/commande, statut et recommandation, et ne bloquent aucune action.
- Les notes restent internes. La recherche des partenaires, fiches et retours n’inclut que les commandes visibles pour le collaborateur. Les routes métier restent sous session FRAMATEX et les droits du dossier jaune. L’espace Client ne reçoit aucun endpoint mémoire.
- Le commentaire documentaire est replié sous « + Ajouter une note facultative » et reste lié à la version par le mécanisme existant.
- Les modules de Contrôles sont groupés en Qualité documentaire, Suivi des modifications, Validation et suivi métier, sans changement de leurs moteurs.
- Un bouton QR apparaît dans l’en-tête. Il utilise le QR protégé existant, avec référence, client, article, téléchargement et impression. Le QR contient un pointeur, jamais un secret ni un droit d’accès.
- Chaque ligne de document donne accès au passeport de la version précise, via la vérification d’intégrité déjà existante.

## Données et migration

Modèles ajoutés : `BusinessPartner`, `PartnerAlias`, `LaunchPartner`, `ExperienceDecision`. `ExperienceNote` est enrichi avec partenaire, date d’événement, importance, statut, recommandation, justificatif et date de mise à jour. La colonne `launch_id` devient facultative afin de permettre les retours généraux.

La migration additive `0011_business_memory` crée les nouvelles tables et colonnes. Sur une ancienne table SQLite, elle copie les notes existantes avec leurs identifiants, textes, auteurs, dates et commandes, puis rend la commande facultative. Les lignes restent à vérifier lorsque le partenaire ne peut pas être rattaché sans ambiguïté. Migration sur base vierge et rejouabilité testées; une copie d’une base de recette existante a conservé les tables et lignes historiques.

## API

- `GET/POST /api/workspace/partners`
- `GET /api/workspace/partners/{partner_id}`
- `POST /api/workspace/partners/{partner_id}/client-account` (administrateur, rattachement explicite)
- `GET /api/workspace/partners/{partner_id}/vigilance`
- `GET/POST /api/launches/{launch_id}/partners`
- `GET/POST /api/workspace/business-memory`
- `GET/PATCH /api/workspace/business-memory/{note_id}`
- `GET /api/workspace/business-memory/{note_id}/decisions`
- Les routes existantes de commentaires documentaires, passeports et QR sont conservées et réutilisées.

## Captures navigateur

Captures réelles Chromium, données de recette jetables :

- [Mémoire métier à 1440 px](smart-business-memory-captures/1440-framatex-experience.png)
- [Mémoire métier mobile à 390 px](smart-business-memory-captures/390-memoire-metier.png)
- [Fiche partenaire et chronologie](smart-business-memory-captures/1440-fiche-partenaire.png)
- [Vigilance dans une nouvelle commande](smart-business-memory-captures/390-commande-memoire.png)
- [Groupes de Contrôles](smart-business-memory-captures/1440-categories-controles.png)
- [Note documentaire repliée](smart-business-memory-captures/1440-note-repliee.png)
- [QR de commande](smart-business-memory-captures/1440-qr-dossier.png)
- [Dossier Jaune intégré](smart-business-memory-captures/1440-framatex-dossier-jaune.png)

Les cinq formats 1920, 1440, 1024, 820 et 390 px ont été parcourus dans le runner mémoire; absence de débordement horizontal et d’erreur JS constatée. Les vues principales intégrées Client/FRAMATEX ont aussi été vérifiées dans la recette complète.

## Résultats vérifiés

- Python : **186 passed** (`.venv/bin/python -m pytest -q`).
- JavaScript : **19/19 suites passées** (`node --test tests/*.cjs`).
- Recette complète de la plateforme : **133/133**, notamment parcours Client A/B complet de 15 étapes, migration sur copie, stabilité du serveur et interfaces Chromium à 1440/1024/820/390 px.
- Recette dédiée mémoire : **11/11**, création/édition/clôture de retours, recherche accent/casse, commande et vigilances sourcées, QR téléchargeable, cinq largeurs, absence d’erreurs réseau/JS, redémarrage serveur et persistance, migration vierge/ancienne.
- Migration historique dédiée : note legacy gardée avec son identifiant et contenu, champ commande nullable après upgrade. Les tests de confidentialité vérifient qu’un collaborateur ne voit pas partenaire ou notes associés à une commande restreinte, et que les routes mémoire renvoient 401 sans session.
- Les recettes s’exécutent sur des répertoires temporaires; aucune base opérationnelle n’a été ouverte ou modifiée.

Les rapports JSON détaillés sont dans `/workspace/artifacts/business-memory/release-candidate` et `/workspace/artifacts/business-memory/specialized-final` dans l’environnement de recette. La recette Chromium globale comprend OCR et le parcours A/B; les captures intégrées principales sont archivées dans ce dépôt.

## Limites connues

- Les alias peuvent être conservés par la table dédiée, mais l’interface de gestion des alias n’est pas exposée dans cette passe. Les rapprochements automatiques de notes historiques sont faits uniquement sur nom normalisé exact; les autres restent à vérifier.
- Le rapprochement de deux noms similaires affiche des candidats et exige une action humaine; aucun algorithme de fusion avancé n’est introduit.
- Les justificatifs se rattachent à une version documentaire accessible de la commande associée; aucun nouveau mécanisme d’upload de preuve n’est ajouté.
- Les décisions et vigilances ne bloquent jamais les commandes et n’entraînent aucune décision commerciale automatique.
- Le lancement PowerShell natif n’a pas été exécuté dans l’environnement Linux utilisé pour cette recette.

## Récupération et lancement sous PowerShell

Depuis la racine du dépôt :

```powershell
git fetch origin
git switch feat/smart-business-memory-ux
if ($LASTEXITCODE -ne 0) { git switch --track origin/feat/smart-business-memory-ux }
git pull --ff-only origin feat/smart-business-memory-ux
git rev-parse HEAD
.\scripts\start_windows.cmd
```

La commande de démarrage applique les migrations locales existantes selon le lanceur Windows du projet. Sauvegarder le fichier de base avant un upgrade sur un poste opérationnel.

## Commit

SHA final : à inscrire après création du commit de livraison.
