# Lot 7 — Recette technique synthétique transversale

## Scénario exécuté
`tests/test_consolidation_journey.py` fournit **un parcours continu**, persistant et contrôlé via les vraies API locales. Il ne représente pas une recette officielle Framatex.

- Deux commandes d'un même client : une sans lancement, une avec deux lancements restreints. Pièces communes aux commandes et pièces avec provenance précise.
- Comptes achats, qualité et réception non administrateurs ; habilitations commande et lancement explicites. Refus de l'approbation pour les achats.
- Profil synthétique : facultatif, future exigibilité depuis l'événement explicitement configuré, pièce manquante et dérogation justifiée. Priorités de la commande sans lancement et recherche des deux commandes par client canonique.
- Circuit qualité par version : approbation, publication au bon client, retrait, remplacement de version, réouverture et nouvelle approbation ; conservation des deux décisions.
- Deux organisations fournisseurs et deux clients activés ; refus d'accès croisés aux demandes, publications et pièces internes.
- Demande documentaire créée par les achats, premier dépôt fournisseur rejeté, correction version 2, approbation qualité, intégration au Dossier Jaune canonique, double intégration refusée et clôture.
- Quantité commandée/prévue de 10,125 m ; annonce et déclaration de 4,125 m ; réception fractionnée 4,125 + 6 m, rejeu idempotent, retour de 0,125 m puis annulation motivée. Un état partiel normal ne devient pas automatiquement une anomalie. Navigation réception avec les vrais identifiants commande/lancement.
- Retrait d'habilitation achats : accès direct à l'ancienne version interdit, disparition des recherches/priorités et de la demande fournisseur ; maintien des accès qualité et à l'autre commande.
- Arrêt des clients HTTP, vraie sauvegarde SQLite et fichiers, restauration dans un **nouveau répertoire**. Vérification des identifiants, des versions, des approbations et liens de réouverture, du rejet fournisseur initial, de la provenance d'intégration, de la publication retirée, de l'annulation du retour, des empreintes SHA-256, de `integrity_check`, `foreign_key_check` et de la consommation des jetons partenaires.

## Isolation et sécurité d'exécution
- Données exclusivement synthétiques, adresse `sample.local`, stockage temporaire neuf à chaque commande.
- `FRAMATEX_EMAIL_ENABLED=0` et transport SMTP remplacé par un garde qui fait échouer le test si un envoi est tenté.
- Aucun navigateur public, service distant, donnée réelle ou email réel utilisés.

## Commande reproductible

```bash
FRAMATEX_DATA_DIR=$(mktemp -d /tmp/framat-journey-XXXXXX) /tmp/framatex-venv/bin/python -m pytest -q tests/test_consolidation_journey.py --tb=short
```

Le chemin Python correspond à l'environnement isolé de cette intervention ; le remplacer par celui de l'installation de revue.

## Résultat
**Dernière exécution : 1 passed en 13,29 s**, dans un répertoire temporaire neuf. Les premières exécutions ont corrigé deux erreurs de construction du scénario : obligation commande appliquée à une pièce de lancement (remplacée par une cardinalité lancement explicite), et réutilisation d'une clé d'opération entre annonce et réception (remplacée par une clé propre à chaque événement). Les contrôles métier ont refusé ces cas ; aucun droit ni contrôle n'a été affaibli.

## Limites de la preuve
Ce test démontre un parcours synthétique local et une restauration base/fichiers ; il ne mesure pas la charge de production, les ressources des serveurs Framatex, la qualité antivirus sur un corpus réel ou l'approbation officielle des règles métier. Les tests spécialisés complètent les fenêtres de panne, les accès désactivés, les dépôts concurrents et les scénarios de migration historiques.
