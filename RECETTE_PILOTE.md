# Framatex — Protocole de recette métier (MVP 0.17)

**Statut : préparation technique uniquement.** Aucun collaborateur Framatex n'a encore participé à une recette attestée dans ce dossier. Les exemples et comptes de démonstration doivent rester fictifs. Le prototype ne doit pas héberger de données clients réelles sans autorisation formelle.

## Participants et conditions de départ

Prévoir au minimum un administrateur et deux profils métier de Framatex, choisis par l'entreprise (par exemple technique et réception). Un animateur observe sans guider le participant avant qu'il ne rencontre une difficulté. Les scénarios doivent être basés sur le flux réel validé par Framatex : les profils et les étapes fictifs du prototype ne sont pas une référence métier.

Avant la séance : confirmer le périmètre réseau, créer les comptes de test, sauvegarder `data/`, documenter le navigateur et la résolution de l'écran, préparer un dossier de démonstration sans ORLI, un dossier restreint et trois documents **entièrement fictifs** dont un Excel. Informer les participants qu'aucune donnée sensible ne doit être copiée dans un signalement.

## Scénarios à faire réaliser sans assistance

| ID | Parcours demandé | Critère vérifiable | Résultat réel |
|---|---|---|---|
| R01 | Ouvrir un dossier pour un lancement sans référence ORLI | Quatre sous-dossiers créés, état « À compléter » | Non réalisé chez Framatex |
| R02 | Déposer et retrouver une pièce dans Rose | Catégorie et nom corrects, fichier téléchargeable | Non réalisé |
| R03 | Remplacer une pièce sans effacer sa version initiale | Deux versions accessibles, historique inchangé | Non réalisé |
| R04 | Identifier une pièce attendue à l'étape courante | Non exigible ≠ manquante, justification visible | Non réalisé |
| R05 | Faire approuver une version puis déposer une nouvelle version | L'approbation antérieure ne valide pas la nouvelle | Non réalisé |
| R06 | Identifier une incohérence documentaire ou Excel | Alerte explicable, aucune correction automatique | Non réalisé |
| R07 | Ouvrir le dossier depuis un QR papier | Connexion obligatoire, permissions conservées | Non réalisé |
| R08 | Restreindre l'accès à un lancement puis retirer un membre | Le dossier et les liens directs deviennent inaccessibles | Non réalisé |
| R09 | Consulter les actions prioritaires et retrouver leur source | Pas de fausse échéance, pas de fuite d'information | Non réalisé |
| R10 | Retrouver une fonctionnalité via l'assistant d'aide | Parcours guidé et respect des droits | Non réalisé |
| R11 | Signaler une difficulté dans « Recette pilote » | Étapes, résultat attendu et observé enregistrés | Non réalisé |
| R12 | Administrateur : traiter le retour puis faire rejouer la tâche | Justification tracée, problème revérifié | Non réalisé |
| R13 | Se déconnecter puis essayer un ancien jeton/cookie | Accès refusé | Non réalisé chez Framatex |
| R14 | Tester une restauration d'une sauvegarde en environnement isolé | Documents et historique retrouvés | Non réalisé |

## Modèle de compte rendu par participant

- **Scénario / date / rôle** : …
- **Réussite autonome** : oui / partielle / non / non applicable.
- **Durée chronométrée** : … (à relever, non estimée par l'équipe technique).
- **Étapes où la personne hésite** : …
- **Erreur ou incompréhension observée** : …
- **Attente formulée par la personne** : …
- **Identifiant du signalement saisi dans l'application** : …
- **Après correction, retest par une autre personne** : …

Conserver un signalement par difficulté reproductible, en évitant des commentaires vagues tels que « l'application n'est pas intuitive ». Ne jamais enregistrer de mot de passe, nom de client, adresse email réelle ou autre information confidentielle dans le texte libre.

## Priorisation proposée pour le traitement

- **Bloquant** : impossibilité de continuer le scénario ou violation avérée d'un accès. Corriger avant un essai élargi.
- **Majeur** : tâche terminable uniquement avec une procédure de contournement importante.
- **Mineur** : la tâche reste réalisable mais comporte une difficulté mesurable.
- **Suggestion** : amélioration à étudier sans anomalie avérée.

Un signalement ne passe à « Résolu » que lorsque la correction est testée sur un scénario reproductible. Le statut ne prouve pas à lui seul la validation par l'utilisateur métier.

## Conditions de passage à un pilote élargi

Documenter explicitement : validation du périmètre métier et des règles documentaires par Framatex ; absence de défaut bloquant connu ; reprise réussie de tous les scénarios critiques ; contrôle des permissions sur les vrais rôles ; sauvegarde/restauration testée ; validation du réseau et du stockage ; accord écrit avant accès à des informations réelles. En cas d'échec, ajourner le pilote et ouvrir les actions correspondantes.

## Ce qui a effectivement été vérifié par l'équipe de développement

Les essais automatiques et Chromium sur **données fictives** sont rapportés dans `VERSION_0.17.md`. Ils contrôlent le comportement du logiciel dans un environnement isolé, sans se substituer aux ateliers utilisateurs ou à un audit de sécurité indépendant.
