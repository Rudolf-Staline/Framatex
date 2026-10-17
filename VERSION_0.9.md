# Framatex MVP 0.9 — Tableau de bord métier et guide de navigation

## 1. Tableau de bord métier

Nouvel endpoint `GET /api/workspace/priorities`. Il agrège par lancement actif les documents manquants ou à valider selon la complétude contextuelle, les impacts en attente de vérification, les exigences client non vérifiées, les ambiguïtés ouvertes et les engagements confirmés arrivés à échéance ou exigibles dans 7 jours.

La priorité est **déterministe** : échéance dépassée (`urgent`), vérification documentaire ou métier (`high`), engagement daté à suivre sous 7 jours (`normal`). Les échéances absentes n'entraînent pas d'alerte de retard. Les dossiers clos sont exclus. Les résultats sont triés, leur nombre est retourné et l'interface affiche les 100 premiers éléments au plus avec indication de troncature.

Le backend filtre chaque source documentaire par les droits `document.read` de ses sous-dossiers (pour un impact, source **et** destination). Il contrôle aussi `launch.read`. Le tableau n'ouvre aucune permission nouvelle. Les liens servent à ouvrir la rubrique concernée du lancement ; ils ne réalisent aucune action métier.

## 2. Guide de navigation

Nouvel endpoint `POST /api/assistant/guide`, avec une question de 2 à 500 caractères et, facultativement, l'ID du lancement courant. Le moteur reconnaît un ensemble **limité** de mots-clés normalisés puis choisit une réponse procédurale, parmi un guide intégré. Il ne récupère ni fichiers ni emails, n'utilise pas d'IA générative et n'appelle pas de service externe. Un résultat a un écran autorisé à ouvrir ou aucun écran si la question n'est pas reconnue.

Les réponses sont filtrées par habilitation ; « Où déposer une facture ? » ne propose pas un accès au sous-dossier Vert lorsque celui-ci est interdit. Les fonctions d'administration ne sont présentées qu'à un administrateur. Les demandes ambiguës invitent à reformuler.

## Vérification

- 40 tests Python réussis localement, y compris les cas de cloisonnement Rose/Jaune.
- Tests JavaScript des modules existants et du tableau 0.9, avec échappement HTML.
- Aucun essai avec données confidentielles de Framatex.

## Limites

Ce n'est pas encore un centre de tâches affectées individuellement : les données exposées proviennent des alertes et statuts existants. Il n'y a ni notifications push, ni tâches programmées, ni automatisation, ni IA générative. Les règles documentaires et guides doivent encore être confrontés aux véritables pratiques de Framatex.
