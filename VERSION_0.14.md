# MVP Framatex 0.14 — Publication client simulée et demandes documentaires fournisseurs

Cette livraison ajoute **deux modules fonctionnels**. Ils s'exécutent uniquement dans l'application interne : **aucun compte client ou fournisseur, URL publique, email sortant ni interface exposée sur Internet** n'est créé. Toute ouverture externe exige une validation de Framatex et une conception de sécurité distincte.

## 1. Publication client contrôlée

Dans un lancement associé à un client renseigné, l'administrateur peut sélectionner une **version documentaire exacte** et justifier sa publication interne simulée. Pour être recevable, la pièce doit :

- figurer dans **Jaune** ou **Rose**, et appartenir à une **liste fermée de types admissibles** (fiche technique, dossier technique client, rapport de contrôle, certificat qualité, bon de livraison, fiche qualité) ;
- ne comporter aucun terme sensible explicite dans son titre, son type ou son nom de fichier (prix, coûts, marges, factures, budget, interne, ORLI, etc.) ;
- être la version courante ;
- disposer d'une **approbation sur cette version** : circuit complet si un circuit est configuré, sinon dernière revue documentaire approuvée.

L'administrateur peut afficher l'**aperçu client local** et retirer une publication en précisant un motif. Le retrait reste tracé. Une version remplacée, un client modifié ou une approbation devenue invalide enlève automatiquement la pièce de l'aperçu, sans supprimer l'historique. L'aperçu n'affiche que des métadonnées de publication et **ne télécharge pas les fichiers**.

> Une liste fermée et un contrôle du nom ne suffisent pas à déterminer si **le contenu** d'un fichier est communicable. L'approbation humaine reste indispensable ; ce module n'est pas une garantie de confidentialité ou de conformité.

## 2. Échanges documentaires avec les fournisseurs (simulation interne)

Un collaborateur habilité peut enregistrer une demande de document fournisseur liée à un lancement et au sous-dossier **Jaune** ou **Rose** : fournisseur, pièce attendue, type documentaire, date cible optionnelle et précisions. Cette demande est une ligne de suivi interne, **non une invitation envoyée au fournisseur**.

Un document reçu est déposé par un utilisateur Framatex à l'aide du mécanisme existant. La demande peut ensuite être clôturée comme **reçue** en associant la **version courante d'un document du même lancement et du même sous-dossier**, avec type concordant et commentaire motivé. Elle peut aussi être **annulée avec justification**. Une version de justificatif remplacée apparaît comme telle dans le suivi, sans altérer la décision antérieure. Les demandes sont filtrées par les permissions de lecture du sous-dossier ; les écritures nécessitent en plus le droit de dépôt.

## Navigation

Ouvrez un lancement et descendez jusqu'à la section **Échanges documentaires** :

1. Pour un aperçu client, faire approuver une fiche autorisée (ou achever son circuit), puis utiliser **Publier une version** et **Aperçu client** depuis la session administrateur.
2. Pour une demande fournisseur, cliquer sur **Demander une pièce**, puis déposer un document dans le sous-dossier approprié et choisir **Traiter** afin de rattacher le justificatif.

## Tests

`PYTHONPATH=. python -m pytest -q tests/test_sharing.py`

`node tests/test_sharing_frontend.cjs`

Suite complète : `PYTHONPATH=. python -m pytest -q` ; puis `for file in tests/*.cjs; do node "$file"; done`.

## Limites avant pilote

- Aucun accès externe, aucun service d'email ni portail de dépôt fournisseur.
- Aucune analyse automatique fiable de la confidentialité du **contenu** des pièces : contrôle juridique et métier requis.
- Les nouveaux schémas sont ajoutés par `create_all` pour les **bases vierges** ou mises à jour additives simples. Une vraie exploitation requiert des migrations versionnées, des tests de reprise, et un durcissement réseau / sécurité.
- Les règles d'éligibilité des documents, de confidentialité, de publication, de traitement des demandes et de conservation doivent être validées par Framatex.
