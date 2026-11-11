# Audit initial archivé — 10 novembre 2026

Ce document conserve les constats antérieurs à la phase 1. Ils ne décrivent plus l’état courant. La phase 2 part de `e94e3c6` (PR #32 fusionnée) ; consulter `IMPLEMENTATION_STATUS.md`, `COUVERTURE_FONCTIONNELLE.md` et `docs/requirements.json` pour les réalisations et limites actuelles. Les hypothèses métier globales restent à confirmer.

Base : main 845d7de. Branche de travail : feat/framat-industrialization.
Audit statique initial, complété par les résultats exécutés dans IMPLEMENTATION_STATUS.md.

| Domaine / priorité | Fichiers | État initial et écart | Acceptation / tests nécessaires |
|---|---|---|---|
| Identités fournisseurs P0 | sharing_models/routes.py | absent : fournisseur = texte, aucun compte externe | invitation à usage unique, activation, révocation et isolation API |
| Transmission fournisseur P0 | sharing_* | partielle : employés enregistrent une réponse interne | dépôt externe, refus motivé, version suivante, approbation et clôture |
| Portail client P0 | sharing_* | simulé, external_access_enabled=False | version approuvée accessible uniquement au destinataire, retrait |
| Documents P0 | main.py, models.py, access.py | versions, stockage privé, signatures et ACL présents | régressions dépôt/téléchargement et URLs directes |
| Sessions P0 | core.py | Argon2, JWT, logout audité, limitation locale | sessions partenaires séparées, révocation persistante |
| Architecture P1 | models.py, migrate.py | par lancement ; modèles alternatifs non fusionnés | conserver IDs et ACL ; commande comme hypothèse sans conversion destructive |
| Complétude P1 | completeness*.py | règles persistantes, exceptions et validations existantes | paramètres commande et pièces partenaires non raccordés |
| Cohérence / Excel P1 | quality*.py, workflow*.py | comparaisons et inspection statique présentes | limites de calcul, nouvelles versions, provenance |
| Extraction P1 | intake*.py | PDF/DOCX/XLSX/OCR et confirmation humaine | contrôle ressources et raccordements à approfondir |
| ORLI P1 | orli*.py | import CSV/XLSX, mapping, snapshots, rapprochement humain | profils sauvegardés, réimport/conflits à compléter ; format réel indisponible |
| Matières P1 | material*.py | lignes, plans, mouvements et annulations | distinguer déclarations partenaires et réceptions officielles |
| Notifications P1 | internal_notifications.py, approval*.py | internes uniquement, filtrage droits | événements partenaires, file email persistante et transport autorisé |
| Approbations P1 | approval*.py | étapes et décisions par version | délégations/délais incomplets |
| Sauvegarde P0 | migrate.py | sauvegarde SQLite, migrations 0001–0003 | restauration DB + fichiers et conservation relations |
| Démo P1 | seed_* | scripts explicites, non appelés au démarrage | garde DEMO à renforcer |
| UX P1 | static/*.js | interface interne fonctionnelle, aucun parcours fournisseur | formulaires connectés, erreurs et états réels |

## Branches et dépendances

Références distantes récupérées et différences inspectées, sans fusion.
- PR 15 (82789cd) : stockage cloud et Vercel/Supabase, changements core/main, dépendances et nombreuses couches UI. Configuration et autorisation de déploiement absentes.
- PR 20 (b7a6ab7) : spécification Dossier Jaune unique, explicitement « à faire valider formellement ». Ne justifie pas une migration opérationnelle.
- PR 21 (cad32ec) : bibliothèque globale et migrations, dépend de branches cloud, mémoire métier et UI ; incompatibilité avec une simple reprise du schéma lancement.
- PR 29 (c3aba87) : client_routes.py, ClientContact et client_id sur lancements/publications, téléchargement soumis à pub_out. Principe de contrôle réutilisable ; création des contacts par mot de passe administrateur, absence d'invitation et dépendances cloud/globales empêchent une reprise isolée sans adaptation.
- PR 30 (3d6a52d) : logo uniquement ; PR 31 (8657cae) : landing et routes d'accueil, sans parcours fournisseur.
- Branches commande-identification, rôles simples, bibliothèque et UI inventoriées ; aucun cherry-pick automatique. Assistant/LLM hors périmètre.

## Hypothèse et registre externe

Conserver les lancements et quatre rubriques ; utiliser une référence commande explicite dans les échanges partenaires. Unification complète commande/lancements reste partielle, sans migration irréversible.
SMTP : aucune configuration autorisée, aucun envoi externe. ORLI : uniquement fichiers, aucun protocole direct connu. PostgreSQL/Supabase/stockage objet : non configurés, aucun accès distant. Antivirus : non disponible, validation structurelle ne garantit pas l'absence de malware. Validation métier des types publiables, règles et organisation documentaire : Framatex requise avant pilote externe.

La matrice détaillée de couverture conserve les exigences non réalisées ; ce document ne constitue pas une déclaration de conformité ni de disponibilité pour production.
