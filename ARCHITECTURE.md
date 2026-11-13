# Architecture — phase 3

L’entrée `app.main:app` assemble les routeurs, le cycle de vie et les protections HTTP. L’authentification employé, les permissions, l’audit, le stockage et les routes métier ont des propriétaires distincts ; les modules métier n’importent plus `app.main`. La complétude de l’interface sépare rendu et interactions. Voir [périmètre, contrats et vérifications du refactoring](docs/REFACTOR_APPLICATION_BOUNDARIES.md).

Framatex Guide ajoute un catalogue et un composant d’aide partagés, un registre fermé de navigation et la migration additive 0024 pour l’apprentissage personnel. Le moteur historique délègue à ce catalogue. Voir [architecture du guide](docs/FRAMATEX_GUIDE_ARCHITECTURE.md) et [rapport de livraison](docs/FRAMATEX_GUIDE_DELIVERY.md).

Le socle FastAPI, SQLAlchemy et SQLite est conservé. Les migrations 0021–0023 organisent les documents par commande, ajoutent les séquences de réouverture et la complétude de commande. Les blobs et identifiants documentaires sont conservés ; seuls les rattachements de rubrique évoluent après sauvegarde et contrôles. PostgreSQL, stockage objet et déploiement distant ne sont pas validés.

## Commandes et partenaires

`BusinessOrder` identifie une commande par client et référence. `BusinessOrderLaunch` rattache explicitement plusieurs lancements compatibles. Un `OrderDossier` unique par commande possède quatre rubriques `Folder`, et les documents ont une provenance facultative `Document.launch_id`. Tous les lancements d'une commande partagent ces rubriques canoniques. Les ACL historiques sont conservées sans élargissement et un lancement portant des documents ne peut pas être détaché implicitement. Les anciens dossiers de lancement convertis deviennent des alias d'archives, sans document concurrent. La décision remplace le modèle ancien : **une commande = un Dossier Jaune unique**. Voir [architecture détaillée](docs/ARCHITECTURE_COMMANDE.md) et [migration/restauration](docs/MIGRATION_PHASE3.md).

Les partenaires restent dans `partners` / `partner_accounts`, distincts des employés. Profils administratifs, domaines autorisés, contacts multiples et rôles configurables complètent ce référentiel. Une invitation nouvelle sans rôle explicite donne seulement la lecture ; la migration 0015 conserve les droits historiques des comptes antérieurs. L'administration partenaires et commandes demeure réservée aux administrateurs employés. Un partenaire ne peut pas s'attribuer un rôle.

## Documents et contrôles

Une transmission fournisseur approuvée peut être intégrée explicitement dans une `DocumentVersion`. `PartnerIntegration` conserve le lien vers la soumission, son auteur externe, son horodatage, son empreinte et sa décision. Le fichier est partagé sans copie du contenu. L'intégration est transactionnelle ; une version retirée reste dans l'historique mais cesse de justifier complétude, cohérence et publication.

Les règles de complétude combinent profil, type de commande, phase, type documentaire, rubrique, facultativité, délai et exception justifiée. Une publication requise doit être effectivement accessible à un client actif : le seul aperçu interne ne suffit pas. Une nouvelle version nécessite les validations correspondantes.

Les rapprochements comparent des valeurs relevées sur des versions exactes. Quantités, consommations, prix, montants, livraisons, réceptions et références disposent de contrôles explicites ; les unités incompatibles et sources multiples restent des états à résoudre. Le transfert d'un champ extrait exige une confirmation humaine et une correspondance autorisée ; l'identité du confirmateur reste liée à la donnée.

L'extraction utilise un processus Linux séparé : entrée 20 Mio, mémoire virtuelle 768 Mio, CPU 25 s, attente maximale 35 s, deux lectures simultanées par processus serveur. Les limites de pages, cellules et caractères restent visibles. L'OCR dépend des composants locaux disponibles. Excel fait l'objet d'une inspection statique bornée : structure, feuilles, formules et cellules critiques configurées. Aucun moteur de calcul Excel n'est revendiqué.

## Client, communications et quantités

Les commandes client sont des autorisations explicites, avec statut et échéance confirmés ; aucun pourcentage n'est inventé. Conversations, pièces jointes, historique et publications vérifient le destinataire à chaque accès. La révocation d'une commande masque aussi les publications liées, conversations et notifications correspondantes.

Les mouvements distinguent prévu, commandé, annoncé, déclaré, réceptionné, retourné et restant. Ils gardent leurs sources et annulations justifiées. Une livraison partielle ne constitue pas automatiquement une anomalie. Les lignes internes historiques et les lignes partenaires restent distinctes ; leur agrégation ne modifie pas les instantanés ORLI.

Les notifications sont internes, persistées et filtrées selon les droits actuels. Les rappels d'échéance sont générés par une commande planifiable et utilisent une clé stable. La file SMTP reste distincte et désactivée par défaut ; aucun email réel n'a été envoyé pendant la validation.

## ORLI, approbations et concurrence

Les imports ORLI gardent des instantanés immuables. Les profils de mapping sont persistants ; les lots sont comparés et une différence liée peut être conservée ou acceptée avec justification et contrôle de la version attendue. Une interface de résolution présente la source, ses candidats et les divergences ; confirmation ou rejet motivé et historisé, empreinte de source attendue, nouvelle évaluation à chaque import. Aucune API ORLI directe n'est simulée.

Les circuits d'approbation imposent l'ordre des rôles, la version exacte et des personnes distinctes. Une délégation temporaire concerne seulement l'étape courante et un employé déjà habilité ; elle est révocable et limitée à 30 jours. Le délai de chaque étape commence à son activation. Les décisions anciennes restent visibles ; une réouverture motivée crée une nouvelle séquence sur la version explicitement choisie, conserve les anciennes décisions et révoque les publications dépendantes. Les approbations d'une séquence antérieure ne sont pas reconduites.

SQLite impose les clés étrangères et sérialise ses écritures. Les migrations utilisent `BEGIN IMMEDIATE`, les demandes un contrôle de révision, les mouvements des clés d'opération et les connexions un budget partagé en base. Ces contrôles ont des tests de concurrence ; ils ne constituent pas une qualification de charge de production.
