# FRAMATEX — Rapport d’audit fonctionnel et de stabilisation

Date de recette : 25 novembre 2026  
Branche : `fix/full-platform-stability`  
Base : `integration/cinematic-document-intelligence` à `04a2a7b499726181f030e10f5ee45113c2c14968`  
Commits du lot : `7dc7a89` (correctif), `1612753` (recettes reproductibles)  
Environnement : base SQLite temporaire, comptes et fichiers fictifs, Uvicorn réel, Chromium/Playwright headless Linux. `main` n’a pas été modifiée.

## Conclusion

Le défaut critique d’ouverture d’une nouvelle commande par un technicien a été reproduit sous la forme signalée : une requête secondaire refusée dans le `Promise.all` rendait l’ouverture entière dépendante de modules non essentiels. Le wrapper du Dossier Jaune imposait en plus le sous-dossier jaune, même pour un technicien uniquement habilité sur le bleu.

Le correctif sépare maintenant les données indispensables des modules facultatifs, recharge les habilitations courantes, sélectionne le premier sous-dossier réellement lisible et affiche une alerte explicite si un module secondaire échoue. Il ne transforme aucun refus en autorisation : les contrôles serveur restent inchangés et un lancement ou sous-dossier non attribué reste inaccessible.

Résultat des campagnes exécutées :

- **Réussi** — 221 tests Python (`python -m pytest -q`).
- **Réussi** — 21 suites JavaScript Node.
- **Réussi** — recette globale : 135/135 contrôles API, métier, runtime et Chromium.
- **Réussi** — scénario Costume : 7/7 étapes UI réelles.
- **Réussi** — habilitations : 15 contrôles, trois techniciens, 12 captures, persistance après redémarrage.
- **Réussi** — suppression/restauration : 5/5 contrôles UI réels.
- **Réussi** — sessions/navigation : 9/9 contrôles UI réels.
- **Réussi** — cinéma 3D : Dossier Jaune, tissu, carrousel et repli mobile.
- **Échec** — aucun échec final connu dans les scénarios exécutés.
- **Non testé** — les limites restantes sont listées explicitement en fin de rapport.

## Incident P0 — ouverture de « Costume » par un technicien

| Action testée | Profil | Résultat avant correction | Bug / cause technique | Correction apportée | Résultat après correction | Régression |
|---|---|---|---|---|---|---|
| Créer `Costume`, créer un technicien et affecter uniquement Bleu | Administrateur | Le cas nominal pouvait fonctionner, ce qui rendait le défaut intermittent | L’ouverture lançait environ 17 appels dans deux `Promise.all` indivisibles | Recette dédiée avec base temporaire et clics UI | **Réussi** | `scripts/validate_costume_technician.py` |
| Ouvrir Costume lorsqu’un module fournisseur renvoie 403 | Technicien Bleu / dépôt | Toute l’ouverture échouait avec le rejet secondaire | `supplier-requests`, publications, contrôles, etc. avaient le même caractère bloquant que le détail du lancement | Détail + complétude essentiels ; modules secondaires isolés avec valeurs de repli et alerte persistante | **Réussi** — commande ouverte, 403 signalé | Même recette, 403 réseau injecté |
| Choisir le dossier accessible | Technicien limité au Bleu | Le wrapper envoyait `folder || 'jaune'` | Jaune était forcé avant lecture des capacités | Sélection de la demande si lisible, sinon premier `folder.can_read` | **Réussi** — Bleu accessible, Jaune verrouillé | Costume + test statique `test_access_ux_frontend.cjs` |
| Modifier une habilitation pendant une session | Technicien connecté | L’interface pouvait conserver des capacités anciennes | `state.me` n’était pas rafraîchi lors de l’ouverture | `GET /api/auth/me` avant le chargement conditionnel | **Réussi** — effet immédiat | `validate_access_ui.py` + tests API |
| Ouvrir sans aucune affectation | Technicien C | Risque de données résiduelles dans l’UI | Aucune sélection sûre en l’absence de dossier lisible | Erreur 403 locale si aucun dossier lisible ; API continue de répondre 404 hors périmètre | **Réussi** — aucun contenu divulgué | `validate_access_ui.py` |

Les erreurs 500/réseau des modules secondaires ne sont pas masquées : elles sont consignées dans la console, stockées dans `state.launchLoadWarnings` et annoncées dans l’écran. Une erreur sur le détail, la complétude ou la session reste bloquante.

## Parcours Administrateur

| Écran / action | Profil | Avant / bug identifié | Cause / correction | Après | Test associé |
|---|---|---|---|---|---|
| Connexion, erreur d’identifiants, actualisation, déconnexion, retour navigateur | Admin | Aucun défaut final reproduit | Vérification sans changement métier | **Réussi** | recette globale + `validate_sessions_ui.py` |
| Accueil, commandes récentes, actions prioritaires, navigation vers une pièce | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale Chromium |
| Création et modification d’une commande ; quatre sous-dossiers | Admin | Ouverture dépendante des modules secondaires | Correctif `openLaunch` | **Réussi** | Costume + recette globale |
| Création de collaborateurs, mot de passe temporaire, activation/désactivation | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | `validate_access_ui.py` |
| Matrice d’accès, lecture/dépôt, affectations partielles et retrait actif | Admin | Jaune forcé et état de session potentiellement périmé | Sélection lisible + rafraîchissement des capacités | **Réussi** | `validate_access_ui.py` |
| Dépôt PDF, DOCX, XLSX, PNG, JPG, TXT, EML, CSV | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | `demo_full_platform.py` |
| OCR image/PDF scanné, propositions de type, confirmation humaine | Admin | Aucun défaut final reproduit | Aucun correctif requis ; aucune validation automatique | **Réussi** | recette globale OCR |
| Confirmation manuelle du type avec justification vide | Technicien Bleu | Aucun défaut final reproduit | La justification reste facultative lorsque la case de confirmation suffit | **Réussi** | scénario Costume |
| Doublon exact, notamment même email deux fois | Admin | Régression signalée antérieurement | Le correctif déjà présent à la base `04a2a7b` est conservé | **Réussi** — « Doublon détecté » puis décision motivée | recette globale Chromium |
| Consultation, téléchargement, V1/V2/V3, ancienne version, comparaison | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale API + Chromium |
| Commentaire et validation documentaire | Admin / valideur distinct | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale |
| Suppression document, double clic, fermeture modale, actualisation immédiate | Admin | Correctif récent à préserver | Recette existante convertie en parcours sans appel de fonctions métier JS | **Réussi** — un seul DELETE, aucun « Failed JSON » | `validate_document_deletion_ui.py` |
| Suppression V2, retour à V1 | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | même recette |
| Corbeille, motif, restauration et retour dans la checklist | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | même recette |
| Erreur 403 réelle pendant suppression | Admin | Risque de fausse réussite | Aucun masquage ; bouton réactivé et modale conservée | **Réussi** | même recette avec 403 injecté |
| Complétude et checklist de 22 pièces | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale Chromium |
| Cohérence, Excel et décision motivée | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale |
| Notifications et circuits de validation | Admin / valideur | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | tests Python/JS + recette globale API |
| Mémoire Client/Fournisseur/Atelier | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale UI/API |
| Recherche commande, client, modèle, référence, document, type, dossier | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale UI/API |
| Historique et audit filtré | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale Chromium |
| Passeport numérique et QR | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale API + tests Python/JS |
| Clients, demandes, acceptation et création d’un Dossier Jaune | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | recette globale Chromium |
| Publication autorisée et retrait | Admin | Aucun défaut final reproduit | Aucun correctif requis | **Réussi** | cycle Client A/B Chromium |

## Parcours Technicien et habilitations

| Action / profil | Résultat | Preuve / remarque |
|---|---|---|
| Aucun accès | **Réussi** | Accueil vide, commande absente, URL/API, téléchargement, passeport et QR refusés |
| Lecture seule | **Réussi** | Sous-dossiers attribués visibles ; sous-dossiers non attribués verrouillés sans titre ni document |
| Dépôt sans validation | **Réussi** | Dépôt permis, validation directe refusée 403 |
| Responsable | **Non testé** | Le niveau est présent dans la matrice et couvert par les tests de capacités, mais aucun parcours Chromium complet dédié n’a été exécuté sous ce profil exact |
| Personnalisé | **Non testé** | Affectations partielles Jaune/Rose et Bleu/Vert testées, mais pas chaque combinaison de cases du mode « Personnalisé » |
| Commande depuis Mes commandes | **Réussi** | Costume ouvert par clic réel |
| Commande depuis Mes sous-dossiers | **Réussi** | Deux commandes affectées rendues sans fuite |
| Commande depuis recherche | **Non testé** | Filtrage de l’API de recherche réussi ; ouverture par clic sous profil technicien non rejouée |
| Commande depuis notification | **Non testé** | Permissions et route couvertes par tests automatisés, pas de clic Chromium dédié sous technicien |
| Navigation entre dossiers autorisés | **Réussi** | Jaune+Rose et Bleu+Vert ; entrées interdites absentes/verrouillées |
| Dépôt et consultation Bleu | **Réussi** | Costume, fichier fictif conservé et visible sans F5 |
| Télécharger / nouvelle version / commentaire selon droits | **Réussi** | Backend de capacités + parcours versions global ; pas de fuite hors affectation |
| Suppression par responsable ou déposant autorisé | **Non testé** | Les refus et règles serveur sont couverts par pytest ; seul le parcours de suppression administrateur a été cliqué intégralement |
| Changement d’habilitation en session | **Réussi** | Retrait immédiat ; rafraîchissement de `state.me` à l’ouverture |
| Désactivation en session | **Réussi** | Requête suivante refusée 401 |
| Persistance après redémarrage | **Réussi** | Affectations ajoutées/retirées conservées |

## Dépôt documentaire, OCR et conservation

| Cas | Résultat | Vérification |
|---|---|---|
| PDF natif | **Réussi** | Dépôt, SHA-256 et téléchargement identique |
| PDF scanné | **Réussi** | OCR page par page, aucune validation automatique |
| PDF hybride | **Non testé** | Aucun fichier hybride dédié dans la campagne finale |
| PDF multipage natif | **Non testé** | Le scan multipage est couvert, pas un PDF natif multipage distinct documenté |
| Word / Excel | **Réussi** | Dépôt réel ; contrôle de formules Excel et `#REF!` |
| PNG / JPG | **Réussi** | Dépôt et OCR image |
| Email EML | **Réussi** | Sujet, expéditeur, date, engagement et doublon exact |
| CSV / TXT | **Réussi** | Dépôt et SHA-256 |
| Exécutable, faux PDF, fichier > 20 Mo, dossier invalide | **Réussi** | Refus 422/413 explicites |
| Fichier identique | **Réussi** | Doublon SHA-256 détecté, décision humaine requise |
| Fichier modifié / nouvelle version | **Réussi** | V1 à V3 conservées, anciennes versions téléchargeables |
| Fichier physique, métadonnées, SHA-256, version | **Réussi** | Octets de téléchargement comparés et base temporaire inspectée |
| Reconnexion / redémarrage | **Réussi** | Sessions, migrations et affectations persistantes ; conservation documentaire couverte par pytest |

## Parcours Client

| Action | Résultat | Test associé |
|---|---|---|
| Inscription, compte en attente, approbation, connexion | **Réussi** | recette globale Chromium |
| Brouillon, envoi, suivi, acceptation/rejet | **Réussi** | recette globale Chromium |
| Dépôt V1, correction demandée, V2, acceptation | **Réussi** | cycle Client A/B Chromium |
| Traitement FRAMATEX et création du Dossier Jaune | **Réussi** | recette globale Chromium |
| Partage, consultation, téléchargement et retrait | **Réussi** | cycle Client A/B Chromium |
| Isolation Client A / Client B et documents internes | **Réussi** | 404 et absence de contenu |
| Déconnexion, retour accueil et URL directe après sortie | **Réussi** | `validate_sessions_ui.py` |
| Notifications Client | **Non testé** | Aucun parcours Chromium final dédié à un centre de notifications Client |

## Navigation, boutons et robustesse

| Interaction / situation | Résultat | Détail |
|---|---|---|
| Menus latéraux, menu mobile, retour accueil | **Réussi** | 1440 et 390 px, admin/technicien/client |
| Modales, Annuler, Enregistrer, Confirmer | **Réussi** | Création, matrice, dépôt, suppression, restauration, lightbox |
| Filtres et recherche | **Réussi** | Formulaires réels, résultats métier vérifiés |
| Actualisation navigateur | **Réussi** | Session et écrans conservés |
| Retour navigateur après déconnexion | **Réussi** | Aucun contenu authentifié réaffiché |
| Ancien cookie réutilisé | **Réussi** | 401 côté serveur |
| Déconnexion interrompue | **Réussi** | Erreur lisible, session conservée, nouvel essai possible |
| Requête bloquée / API 500 | **Réussi** | Écran borné et bouton Réessayer |
| Réponses 204 / 400 / 401 / 403 / 404 / 500 | **Réussi** | Couverture pytest/API ; 401/403/404/500 également observées dans les recettes UI |
| Double clic | **Réussi** | Suppression : un seul DELETE |
| Navigation rapide entre commandes | **Réussi** | garde `djLoadToken` conservée ; campagne globale sans promesse non traitée |
| Plusieurs onglets simultanés | **Non testé** | Aucun scénario multi-onglets dédié dans cette campagne |
| Expiration temporelle réelle de session | **Non testé** | Révocation, désactivation et cookies périmés testés ; pas d’attente jusqu’au TTL naturel |

## Design et animations préservés

| Élément | Résultat | Vérification Chromium |
|---|---|---|
| Dossier Jaune Three.js | **Réussi** | Canvas WebGL visible ; deux états de défilement ont des rendus différents |
| Tissu textile 3D | **Réussi** | Variation temporelle et réaction au pointeur |
| Carrousel partenariat | **Réussi** | Suivant, indicateur, lightbox et fermeture |
| Repli mobile / mouvement réduit | **Réussi** | 390 px sans WebGL coûteux, capture statique visible |
| Direction artistique, couleurs, logos | **Réussi** | Aucun fichier CSS, image ou composant graphique modifié par ce lot |

## Captures livrées

Les preuves sélectionnées sont versionnées dans `docs/full-platform-stability-captures/` :

- `costume-01-admin-commande.png`, `costume-02-technicien-bleu.png`, `costume-03-technicien-document.png` ;
- `acces-06-matrice-commande.png`, `acces-07-technicien-dossier-partiel.png` ;
- `1440-parcours-dashboard.png`, `1440-parcours-mes-demandes.png` ;
- `390-framatex-dashboard.png`, `390-client-demandes.png` ;
- `suppression-document.png`, `corbeille.png` ;
- `cinematic-folder-progress.png`, `cinematic-fabric-progress.png`, `cinematic-carousel.png`, `cinematic-mobile-fallback.png`.

Les campagnes complètes produisent davantage de captures sous `data/`, répertoire volontairement ignoré par Git et recréable grâce aux scripts ci-dessous.

## Reproduction

```bash
python -m pytest -q
for test in tests/*.cjs; do node "$test" || exit 1; done
python scripts/validate_costume_technician.py --output data/stability-costume
python scripts/validate_access_ui.py --output data/full-platform-stability/access
python scripts/validate_document_deletion_ui.py --output data/full-platform-stability/deletion
python scripts/validate_sessions_ui.py --output data/full-platform-stability/sessions
python scripts/validate_cinematic_3d.py --output data/full-platform-stability/cinematic
python scripts/demo_full_platform.py --output data/full-platform-stability
```

## Limites et éléments non testés

Il serait incorrect d’affirmer que chaque combinaison possible de bouton et de permission a été épuisée. Restent **non testés** explicitement :

1. un parcours Chromium complet sous les profils exacts « Responsable » et « Personnalisé » pour toutes les actions ;
2. l’ouverture technicien depuis une notification et depuis un résultat de recherche par clic réel ;
3. la suppression/restauration par un responsable et par un déposant non administrateur en UI (les règles serveur sont testées) ;
4. un PDF hybride dédié et un PDF natif multipage dédié ;
5. un scénario multi-onglets concurrent et l’expiration naturelle par TTL ;
6. une exécution sur un hôte Windows natif — la compatibilité des chemins/runtime Windows est couverte par les tests, mais la campagne finale a tourné sous Linux ;
7. la durée au-delà de 60 secondes du test de stabilité du processus.

Aucune nouvelle fonctionnalité, dépendance ORLI obligatoire, refonte graphique, agent IA, chatbot ou automatisation n’a été ajoutée.
