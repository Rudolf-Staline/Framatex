# Installation web (nouvelle instance uniquement)

La page `/setup` est fermée par défaut. Elle n'est pas une procédure de récupération de compte.
Elle refuse une base contenant un utilisateur interne (même désactivé), un client ou un événement
d'audit. Elle ne modifie aucun compte existant. Une installation réussie écrit un événement d'audit
et ferme immédiatement l'endpoint. Les autres comptes sont gérés par les interfaces existantes.

Sur une **nouvelle instance de développement isolée**, après configuration et migrations habituelles,
définir côté serveur `FRAMATEX_SETUP_SECRET` avec un secret aléatoire d'au moins 32 caractères,
distinct des mots de passe et clés de session. Ne jamais le placer dans les fichiers statiques, le
dépôt Git ou une variable publique. Ouvrir `/setup` en HTTPS, saisir le secret et les informations
du premier administrateur. Retirer ensuite la variable d'environnement et redéployer pour la
désactiver également au niveau de la configuration. Aucune configuration de l'instance existante
n'est changée par ce code.

Les tests utilisent une base SQLite temporaire dédiée et vérifient le refus par défaut, le secret,
le hachage, la fermeture après installation, le refus d'un compte existant et la concurrence.
Le verrou PostgreSQL bloque également les insertions concurrentes sur les tables concernées.
