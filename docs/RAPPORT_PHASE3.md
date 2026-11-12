# Rapport phase 3 — Framatex

La règle **une commande = un Dossier Jaune unique**, avec quatre rubriques et plusieurs lancements, est implémentée comme source de vérité documentaire. Les anciennes données sont converties par rattachements explicites, sans déplacement de fichiers ni suppression des versions, décisions, publications ou audits.

Branche : `feat/framat-industrialization-phase3`. Base : PR #33, `17eefa893e33cb3f52121449b5f0a636872971c1`. Environnement local uniquement, données synthétiques et bases temporaires. Aucun déploiement, aucune fusion dans `main`, aucune base de production modifiée, aucun email réel envoyé, aucune fonctionnalité d'IA ou de chatbot ajoutée.

## Résultat de couverture

| État | Phase 2 | Phase 3 |
|---|---:|---:|
| Terminé, vérifié en environnement contrôlé | 248 | 264 |
| Partiel | 22 | 6 |
| Bloqué | 3 | 3 |
| Total d'identifiants | 273 | 273 |
| Couverture | 90,8 % | 96,7 % |

Les 273 identifiants sont conservés. Les 22 anciennes lignes partielles possèdent un historique d'état, leur nouveau comportement, les fichiers, les tests et les dépendances dans `requirements.json`. R6-02 conserve son identifiant et l'ancienne décision « Dossier Jaune global », désormais remplacée par « Dossier Jaune unique par commande ». Le pourcentage théorique 270/273 n'est pas revendiqué.

## Incréments livrés

1. Architecture : dossier canonique unique, quatre rubriques, provenance facultative, ACL conservatrices, alias historiques, contraintes et tests d'isolation/concurrence.
2. Intégration : dépôts, versions, intégration fournisseur, emails, contrôles de sources/cohérence/matières, complétude par commande, recherche, partage, notifications et QR.
3. Contrôles : séquences de réouverture, résolution ORLI, vérification/extraction isolées, quota interworkers, refus des fichiers dangereux, scanner requis et gestion des collisions sans perte.
4. Interface : navigation métier, dossier et lancement clairement distingués, filtres et pagination, confirmations et états, réseau, doubles soumissions, clavier, contrastes et contrôles mobiles.
5. Validation : migration réelle de schéma phase 2 sur copie, sauvegarde complète avant conversion, répétition, restauration, régression, matrice et rapports.

## Commandes réellement exécutées et résultats

Dossier de travail : `/workspace/Framatex`.

```sh
python -m venv .venv
.venv/bin/pip install -q -r requirements.txt pytest httpx playwright
.venv/bin/pip install -r requirements-test.txt
npm install --save-dev --save-exact axe-core
npm ci
```

Installation réussie. L'installation finale utilise le verrou Python complet `requirements-test-lock.txt`, Playwright 1.65.0, pytest 9.2.0, httpx 0.28.1 et le verrou npm avec axe-core 4.14.0.

```sh
PATH=/tmp/framat-clamav/runtime/usr/bin:$PATH \
LD_LIBRARY_PATH=/tmp/framat-clamav/runtime/usr/lib/x86_64-linux-gnu \
.venv/bin/python -m pytest -q --tb=short
```

**119 passed, 2 warnings, 150,21 s**, sans test antivirus ignoré. Les avertissements concernent la dépréciation du TestClient httpx et l'adaptateur datetime SQLite, pas des échecs métier. Le moteur ClamAV 1.4.3 est réel ; sa base de test est synthétique et limitée à EICAR.

```sh
for file in tests/*.cjs; do node "$file" || exit 1; done
for file in static/*.js; do node --check "$file" || exit 1; done
```

**13 scripts de tests JavaScript réussis ; 21 sources JavaScript valides.** Les anciens tests sont conservés. Le test historique de détachement attend maintenant 409 lorsqu'un lancement porte des documents : ce changement explicite empêche de rompre leur appartenance canonique ; le téléchargement historique reste vérifié.

```sh
FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium \
.venv/bin/python tools/check_phase3_browser.py

FRAMATEX_BROWSER_EXECUTABLE=/usr/bin/chromium \
.venv/bin/python tools/check_partner_browser.py
```

**Deux parcours Chromium réussis**, chacun sur sa propre base temporaire :

- Commandes du même client séparées, dossier partagé entre lancements, dépôt, filtre d'origine, version, historique et téléchargement ; Tab/Maj+Tab/Echap dans le dialogue ; panne réseau et reprise manuelle ; pagination réelle de 30 lancements ; rejet puis confirmation d'une association ORLI ambiguë.
- Fournisseur et client : activation, droits et révocation, versions/correction/approbation, intégration, fichiers administratifs, mouvements de réception, recherche, publications, clarification et pièce jointe, synthèse de commande, complétude, délégation, approbation puis réouverture motivée dans le navigateur, dépôt multiple avec échec partiel, confirmation d'extraction et révocation d'un collaborateur.

**76 contrôles axe/mobile sans violation sur les vues testées** : 64 contrôles sur dossier, accueil, commandes, annuaires, réceptions, validations, lancements, détail de lancement, actions, notifications, ORLI, administration, audit, recherche et connexion partenaire ; 12 sur fournisseur connecté, client connecté et administration partenaire. Largeurs : 360, 390, 768 et 1440 px. Cette preuve ne constitue pas un audit WCAG complet ou une certification d'accessibilité.

```sh
.venv/bin/python -m pytest -q \
  tests/test_order_documents_phase3.py::test_full_versioned_migrator_on_copy_and_automatic_archive_restore \
  --tb=short
```

**1 passed**. Ce test exécute effectivement, dans des sous-processus isolés, `python -m app.migrate preflight`, puis `python -m app.migrate upgrade` deux fois, sur une copie restaurée du schéma exact de phase 2. L'archive automatique est restaurée vers un nouveau répertoire et les empreintes, relations et anciennes références sont vérifiées. D'autres tests conservent les tuples complets de versions, les décisions, les publications et les notifications ; les liens incompatibles interrompent la conversion sans écriture partielle.

```sh
.venv/bin/python tools/update_coverage.py
git diff --check
```

Matrice régénérée : **264 terminé, 6 partiel, 3 bloqué** ; pas d'erreur d'espacement. Comparaison automatique des identifiants avec le commit de référence : ensemble identique de 273 identifiants.

## Limites restantes : six exigences partielles

| ID | Fonction disponible | Dépendance précise restante |
|---|---|---|
| R6-05 | Jaune canonique, fichiers, versions, droits, décisions, recherche et complétude configurée | Catégories obligatoires et règles techniques/commerciales validées par Framatex non fournies |
| R6-06 | Rose canonique et mêmes contrôles, intégration des pièces de réception | Règles de réception, pièces obligatoires et échéances métier Framatex non fournies |
| R6-07 | Bleu canonique et mêmes contrôles | Catégories et règles douanières Framatex validées non fournies |
| R6-08 | Vert canonique et mêmes contrôles | Règles de facturation et pièces obligatoires Framatex validées non fournies |
| R8.3-01 | Extraction déterministe isolée, bornée et sourcée ; corpus synthétique PDF/DOCX/XLSX/images, documents protégés/corrompus et OCR indisponible | Aucun corpus réel fourni pour mesurer les erreurs et la robustesse sur les documents Framatex |
| N-09 | Adaptateur ClamAV réel, mode requis, EICAR, délai/erreur/base absente refusés et nettoyage | Base complète de signatures et mise à jour non vérifiées ; service officiel bloqué par le réseau de cet environnement |

N-05 (ORLI direct), N-06 (SMTP réellement autorisé et accepté) et N-07 (pilotage/validation métier Framatex) demeurent bloquées par leurs dépendances externes. Aucun statut n'est promu pour compenser ces dépendances.

## CI, restrictions réseau et revue distante

`.github/workflows/tests.yml` couvre les PR et les pushes sur `main`. Il installe ClamAV, les dépendances verrouillées, Chromium Playwright avec ses dépendances système et exécute les deux parcours critiques. Les preuves JSON et captures sont conservées comme artifacts. Les scripts utilisent `sys.executable` et le navigateur installé par Playwright par défaut ; aucun chemin vers Chromium préinstallé n'est imposé en CI.

Dans cet environnement, `python -m playwright install chromium` a échoué sur `cdn.playwright.dev` avec 403 « Domain forbidden » ; le Chromium local a permis les tests réels. `curl -I --max-time 20 https://database.clamav.net/daily.cvd` a échoué sur CONNECT 403. Aucune restriction réseau ni protection n'a été désactivée.

L'exécution distante de GitHub Actions n'est pas revendiquée sans observation d'un retour GitHub. L'état final de la branche et de la PR est consigné ci-dessous après tentative de publication Git autorisée par la mission.

## Documents et preuves

- [Architecture](ARCHITECTURE_COMMANDE.md), [migration/restauration](MIGRATION_PHASE3.md), [sécurité](SECURITE_PHASE3.md), [description de PR](PULL_REQUEST.md).
- `artifacts/phase3-controls.txt`, `artifacts/phase3-validation.txt`, `artifacts/phase3-browser.json`, `artifacts/phase3-partner-axe.json`, captures synthétiques.
- Source de vérité : `docs/requirements.json` ; synthèse générée : `COUVERTURE_FONCTIONNELLE.md`.

## État Git distant final

La branche `feat/framat-industrialization-phase3` a été poussée avec succès par :

```sh
git push -u origin feat/framat-industrialization-phase3
```

La tentative de création de PR a réellement été exécutée :

```sh
gh pr create --repo Rudolf-Staline/Framatex --base main \
  --head feat/framat-industrialization-phase3 \
  --title 'Dossier Jaune unique par commande et consolidation phase 3' \
  --body-file docs/PULL_REQUEST.md
```

**Échec, code 1 : `Post "https://api.github.com/graphql": Forbidden`.** `gh auth status` signalait également que l'identité GitHub API n'était pas utilisable dans cet environnement. Aucun numéro de PR n'est donc revendiqué et aucune exécution distante de CI n'a été observée. L'accès Git autorisait le push mais ne prouve pas l'accès à l'API de création de PR.

La description prête à utiliser est dans `docs/PULL_REQUEST.md`. [Ouvrir la PR depuis la branche poussée](https://github.com/Rudolf-Staline/Framatex/pull/new/feat/framat-industrialization-phase3). Aucun contournement de politique, aucune fusion et aucun déploiement n'ont été réalisés.
