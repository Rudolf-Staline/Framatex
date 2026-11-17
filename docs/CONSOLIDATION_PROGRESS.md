# Consolidation Framatex — état de reprise, 17 novembre 2026

## Branche, référence et contraintes
- Départ : `33e7836c1999db1b63331b626f5fa69d50bf193f`, origin/main récupéré et revérifié inchangé.
- Branche : `consolidation/framatex-2026-11-17` ; arbre initial propre, aucun AGENTS.md applicable trouvé dans /workspace.
- Code stabilisé : `50b68ae` (inclut `734da38` sélecteurs, `171f88e` antivirus exploitation, `ca52054` permissions indirectes).
- Tous les commits et le rapport ont été poussés ; SHA local/distant `be0e9a9` identiques avant ce dernier compte rendu. Arbre propre vérifié avant mise à jour de publication.
- Aucun déploiement, fusion, contact, email réel ou modification de données réelles.
- Profil de revue : Linux x86_64, Python3.12.14 isolé `/tmp/framatex-venv`, SQLite ; Node local24.22.1, CI déclarée Node22. Aucune qualification des serveurs Framatex.

## Dépendances et ordre suivi
1. ACL commande/contexte et migration conservatrice → filtres SQL et provenance.
2. Noyau complétude → priorités, agrégats et contrats UI.
3. Permissions métier → fournisseurs, réception hors portail et intégration.
4. Identification/types/commentaires → parcours documentaire et guide.
5. Réservations, pagination et mouvements → mesures et concurrence.
6. Migrations, restauration, sessions/audit, baux SMTP → exploitation.
7. Parcours transversal, navigateur, contrôles globaux, rapport et publication.

## Lots et décisions
| Lot | État actuel | Preuve / limite |
|---|---|---|
| 1 Modèle/migrations/droits | Corrigé et vérifié localement | Gardes0020, schémas historiques0020–0023, double upgrade, ACL/contexte, sources et anciennes versions ; revue des membres historiques à faire par exploitation |
| 2 Complétude/priorités/recherche | Corrigé et vérifié sur scopes existants | Huit états, exception précise, publication effective, sans lancement, client canonique ; règles officielles non attestées |
| 3 Fournisseurs/réceptions | Corrigé et vérifié localement | Nonadmins, hors portail, CAS/intégration concurrente, Decimal/retours/annulations ; politiques métier à valider |
| 4 Documents/identification/guide | Implémenté et vérifié localement | IDs/types/alias, JSON ancien conservé, version/commentaire, clavier/mobile/axe ; catalogue et champs provisoires |
| 5 Volumétrie/concurrence | Corrigé et mesuré sur scénarios synthétiques ; limites restantes explicites | SQL pages constant, quota/quarantaine/reprise, incrémental ; anciennes projections complètes et agrégats globaux encore coûteux à très grand volume |
| 6 Exploitation | Implémenté et vérifié sur profil SQLite | Sauvegarde/restauration, audit durable, readiness, baux SMTP ; ClamAV réel/serveurs/relais externes non qualifiés |
| 7 Validation/livraison | Validation locale terminée, branche publiée ; PR bloquée | 208 tests réussis ; tentative GraphQL Forbidden, aucune PR créée |

Choix explicites : aucun rôle sensible accordé implicitement ; owner/admin restent des accès propres après retrait de membre ; source restreinte indépendante de l'accès commande ; pas de lancement artificiel ; règles/portées/échéances configurables sans attestation inventée ; pas de portage PostgreSQL partiel.

## Vérifications exécutées
- Référence33e7836 isolée : **156 réussis,2 ignorés**,352,38s. Le premier essai dans l'arbre partagé fut contaminé par des modifications pendant exécution : il n'est pas utilisé comme référence.
- Intégration intermédiaire : **194 réussis,2 ignorés**,404,30s.
- Passage complet après revue : **206 réussis,2 ignorés**,285,94s (`/tmp/framatex-global-final.log`).
- Passage final après sélecteurs/antivirus/permissions : **208 réussis,2 ignorés,1 avertissement**,300,33s ; journal `docs/consolidation/final-validation.txt`. Le changement JS ultérieur au lancement de cette suite a sa régression Node et son parcours navigateur complet réussis.
- Permissions indirectes+documents+MVP : **9 réussis**,10,36s ; stockage final : **13 réussis**,6,39s ; sélecteur>100 : **1 réussi**,4,14s.
- Parcours transversal unique : **1 réussi**,13,29s, incluant huit clients HTTP, deux commandes, fournisseurs/clients, décisions/réouverture, réceptions/idempotence, révocation et vraie restauration avec hashes/FK/versions/décisions.
- Trois parcours navigateur sur code stabilisé : dossier **PASS** (`/tmp/framatex-dossier-delivery.log`), partenaires **PASS** (`/tmp/framatex-partners-delivery.log`), guide **PASS** (`/tmp/framatex-guide-delivery.log`). Sélecteurs historiques et achats nonadmin>100 également **PASS**, aucune erreur JS.
- 18 tests JavaScript et27 scripts syntaxe : réussis. Compilation Python, pip check, catalogue57 procédures/61 visites/171 actions et manuel synchronisé : réussis.
- Les tests d'origine sont conservés. Fixture MVP désormais isolée ; contrôle de quota conservé lors du remplacement du verrou global. Le navigateur choisit explicitement le bouton d'envoi depuis l'ajout de pagination aux formulaires.

## Mesures inspectables
- Recherche, page25,3versions/pièce, lecteur nonadmin : **379→5 SQL à100 pièces**, **3079→5 à1000**. Médianes locales556,05→83,69ms et5782,29→83,86ms ; JSON et mémoire dans `docs/consolidation/search-*.json`.
- Concurrence2/4 :36 recherches synthétiques,0erreur,5SQL/appel. Aucun p95 de production revendiqué.
- Complétude :18SQL avec10 puis200pièces×2versions ; preuves JSON plafonnées20.
- Historique :500mouvements69,09→4,89ms ;2000mouvements788,20→87,44ms,3échantillons et égalité événementielle.
- Sauvegarde/restauration synthétique1Mio :0,126s/0,035s, une exécution, ZIP1074939octets ; pas de RPO/RTO promis.

## Revue et corrections additionnelles
- Une revue a trouvé des corrélations EXISTS incorrectes : test SQL/Python de sources hétérogènes ajouté et corrigé.
- Source de justificatifs/qualité/spécifications/simulations et engagements filtrée.
- Historique asynchrone ne rouvre plus un dialogue fermé ; réponse initiale de dossier ne remplace plus une navigation ultérieure.
- Baux SMTP : anciennes réservations et anciens workers clôturant tardivement reproduits et corrigés ; acceptation SMTP connue préservée après erreur QUIT. Aucun envoi réel.
- Antivirus désactivé refuse maintenant le dépôt en OPERATIONAL ; quarantaine/quota libérés.
- Nouveaux sélecteurs serveur dépassent100 lancements ; formulaire désactive le vrai bouton d'envoi, pas celui de pagination.

## Blocages et preuves manquantes
- ClamAV absent. Tentative portable uniquement/tmp : `APT_CONFIG=/tmp/framatex-clamav/apt.conf /usr/bin/apt-get update` → **HTTP403Forbidden** du proxy, miroir interne et sources originales. Test moteur réel ignoré ; refus du scan indisponible vérifié avec transport/processus simulés. EICAR seul ne serait pas une qualification complète.
- IA réelle optionnelle volontairement non activée ; aucune dépendance de la GED locale.
- API GitHub : `gh api user --jq .login` → **Forbidden** ; git fetch/push fonctionnent. Aucune PR annoncée sans URL vérifiée.
- Corpus réel, règles et acteurs officiels, paramètres serveurs/scanner/SMTP, conservation/RPO/RTO et recette Framatex restent externes.
- Anciens endpoints complets et agrégats globaux : limites exposées dans le rapport ; pas de promesse de volume illimité ni de snapshot entre pages offset.

## Publication finale et reprise
- Push réussi jusqu'au rapport `be0e9a9`, égalité SHA local/distant vérifiée ; le présent compte rendu est également commité et poussé. Rien ne reste à pousser.
- Tentative réelle de PR : `gh pr create --draft --base main --head consolidation/framatex-2026-11-17 --title "Consolidation Framatex : droits, documents, fournisseurs et exploitation" --body-file docs/PULL_REQUEST_CONSOLIDATION.md` → `Post "https://api.github.com/graphql": Forbidden`, code1. Aucune PR créée, aucune URL de PR annoncée.
- À la reprise : rétablir l'accès API GitHub puis exécuter cette commande et vérifier la CI distante. Ne pas fusionner ni déployer sans instruction.
- Poursuivre la recette et le dimensionnement avec Framatex : corpus réel, règles/acteurs/délais, scanner et signatures, SMTP, conservation/RPO/RTO. Les limites des anciennes projections complètes restent documentées.

Détails par lot dans `docs/consolidation/*.md`. Rapport : `docs/CONSOLIDATION_REPORT.md`. Installation : `docs/DEPLOIEMENT_INTERNE.md`. Grille métier : `docs/RECETTE_CONSOLIDATION.md`.
