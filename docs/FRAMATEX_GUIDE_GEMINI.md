# Configuration et confidentialité de Gemini

Gemini est facultatif. Sans clé, si l’IA est désactivée, si le fournisseur est mal configuré, si les budgets sont atteints ou si une réponse est lente/invalide, le guide affiche les procédures locales vérifiées. Le centre d’aide, les raccourcis, visites et progressions restent disponibles.

```dotenv
FRAMATEX_GUIDE_AI_ENABLED=0
FRAMATEX_GUIDE_AI_PROVIDER=gemini
FRAMATEX_GUIDE_GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=
FRAMATEX_GUIDE_REQUESTS_PER_MINUTE=40
FRAMATEX_GUIDE_HTTP_REQUESTS_PER_MINUTE=300
FRAMATEX_GUIDE_AI_TIMEOUT_MS=5000
FRAMATEX_GUIDE_AI_MAX_OUTPUT_TOKENS=400
FRAMATEX_GUIDE_AI_USER_DAILY_LIMIT=30
FRAMATEX_GUIDE_AI_DAILY_LIMIT=100
```

Configurer la clé uniquement dans l’environnement serveur, jamais dans le navigateur, Git ou les journaux. L’activation exige explicitement `AI_ENABLED=1`, le fournisseur `gemini` et la clé. Le modèle demandé est configurable ; sa disponibilité réelle dépend du compte Google. Ne pas afficher ou partager la clé pour effectuer une vérification.

## SDK et requête

SDK officiel **`google-genai==3.2.0`**, installé et compatible avec les dépendances verrouillées. Référence officielle consultée : [Google Gen AI Python SDK](https://github.com/googleapis/python-genai). Les objets `genai.Client`, `types.HttpOptions`, `types.HttpRetryOptions`, `types.GenerateContentConfig` et le schéma Pydantic sont vérifiés avec la version installée. Le timeout est borné de 250 à 15 000 ms, les tentatives sont limitées à une et la sortie à un maximum configurable de jetons. Aucun outil ou fonction métier n’est donné au modèle.

Avant chaque appel, le serveur authentifie le profil, vérifie son contexte, recherche localement et filtre les procédures. **Au plus cinq procédures** sont transmises. Les budgets utilisateur et global sont réservés atomiquement dans SQLite et survivent aux workers et redémarrages. Ils bornent le nombre de requêtes et la taille de sortie, pas un montant monétaire dépendant des tarifs du fournisseur. Les fenêtres quotidiennes utilisent des périodes UTC fixes.

## Données transmises

Le texte brut de la question n’est pas transmis. La demande est réduite à des mots issus du vocabulaire public du catalogue ; les mots inconnus et les nombres sont exclus. Sont envoyés seulement ces termes pédagogiques, le type de profil, l’identifiant de page enregistré et les quelques procédures candidates (titres, étapes vérifiées, mots-clés et identifiants d’action).

Aucun contenu de document, nom de client lu en base, liste de clients, montant commercial, identifiant de commande/lancement/demande, mot de passe ou jeton de session n’est envoyé. Les recherches peuvent perdre une nuance non couverte par ce vocabulaire : une clarification est préférable à l’envoi d’un contexte commercial confidentiel. Les termes publics peuvent évidemment être reconnus lorsqu’ils figurent dans une question ; ils ne sont jamais enrichis avec des données métier.

Le modèle retourne uniquement des identifiants de procédures/actions, un niveau de confiance et un indicateur de clarification. Tout identifiant inconnu, action hors procédure, champ supplémentaire ou JSON invalide provoque un repli local. Le texte présenté provient du catalogue, ce qui empêche une sortie libre du modèle d’inventer une instruction ou un bouton.

## Évaluation et exploitation

La CI utilise un fournisseur simulé : succès, ambiguïté, refus d’action, JSON invalide, délai, quota et panne. Aucun appel réel à Google n’est effectué par défaut. Le banc d’essai exige `FRAMATEX_GUIDE_REAL_AI_TEST=1` et une clé distincte dans `FRAMATEX_GUIDE_EVAL_API_KEY`. Pour le corpus courant :

```bash
FRAMATEX_GUIDE_REAL_AI_TEST=1 python tools/evaluate_guide.py --gemini --ai-budget 112 --output artifacts/guide-evaluation-gemini.json
```

Le budget d’évaluation est propre au processus (défaut : 30 tentatives). Il ne remplace pas les limites de production et ne consomme pas leurs compteurs ; celles-ci restent à 30 par propriétaire/jour et 100 globales/jour par défaut. Le banc utilise les mêmes candidats, profils, permissions, payload minimal et validation structurée. Un quota fournisseur est identifié et interrompt les tentatives suivantes ; un timeout ou une réponse invalide donne un repli explicite. Une couverture partielle est affichée sans attribuer les résultats locaux au score des seules réponses Gemini.

Les scores locaux et enrichis sur le corpus complet ont chacun leur dénominateur. La comparaison appariée ne contient que les réponses Gemini validées et compte améliorations, dégradations et résultats inchangés. Chaque ligne conserve les deux résultats et précise si un appel a eu lieu. Un exemple sans réseau est généré avec `python tools/evaluate_guide.py --simulate --ai-budget 112 --output artifacts/guide-evaluation-simulated.json`. Voir [lecture du rapport et limites](FRAMATEX_GUIDE_FIXES.md).

Aucun test réel Gemini n’a été exécuté pendant cette livraison. La disponibilité effective de `gemini-3.5-flash-lite`, la latence distante et une amélioration quantitative par rapport au moteur local ne sont donc pas qualifiées. L’IA reste désactivée par défaut. L’exploitant doit autoriser l’accès à l’API Google dans sa politique réseau et vérifier les conditions de traitement des données applicables à son compte et à son offre.

La base ne conserve pas le texte des questions : seulement des événements minimaux et des retours catégorisés. Les statistiques sont agrégées et réservées aux administrateurs ; aucun détail d’organisation, texte de question ou secret ne doit être ajouté aux journaux. Les journaux de proxy/serveur doivent aussi éviter de conserver des questions passées manuellement en query string à l’API de recherche ; l’interface pose ses questions par POST.
