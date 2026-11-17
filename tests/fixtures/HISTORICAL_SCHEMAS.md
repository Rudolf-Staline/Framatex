# Schémas SQLite synthétiques historiques

Ces dumps compressés sont générés par `python -m app.migrate upgrade` à partir
des sources Git historiques de Framatex, dans un répertoire neuf, sans donnée réelle.

| Fixture | Sources | Ajustement |
|---|---|---|
| schema_0020.sql.gz | 5b8ea1d | Aucun |
| schema_0021.sql.gz | 0024706 | Aucun |
| schema_0022.sql.gz | 5bd1d02 | Retrait de la table et de la révision 0023, seul ajout de cette étape ; aucun commit isolé 0022 dans cet historique |
| schema_0023.sql.gz | 5bd1d02 | Aucun |

Les tests ajoutent un utilisateur et des révocations synthétiques, exécutent deux
mises à niveau et vérifient registre, données, clés étrangères et sauvegarde.
Ces fixtures contrôlent la compatibilité des schémas ; elles ne remplacent pas
un test de mise à niveau sur une copie autorisée de la base Framatex.
