# Framatex — MVP 0.17 · Recette structurée et révocation des sessions

Cette version ne prétend **pas** valider le MVP auprès des équipes de Framatex. Elle prépare la collecte et la résolution de leurs retours dans un environnement d'essai contrôlé, sur des données fictives.

## Fonctionnalités livrées

1. **Retours de recette dans l'interface** : entrée « Recette pilote » dans la navigation. Tout utilisateur connecté peut enregistrer la fonctionnalité testée, les étapes de reproduction, le résultat attendu, le résultat observé et la gravité. Le signalement peut être lié à un lancement accessible, ou rester général.
2. **Suivi par l'administrateur** : consultation de l'ensemble des retours, changement d'état (à examiner, en cours, résolu, écarté), justification obligatoire lors de la résolution ou du classement. Les transitions sont auditées.
3. **Protection des observations** : un collaborateur voit uniquement ses propres retours ; si son habilitation à un lancement est retirée, il n'en voit plus les signalements associés. Aucun accès aux signalements d'autrui. Les textes affichés sont échappés contre les injections HTML.
4. **Déconnexion réelle** : les JWT de session comportent maintenant un identifiant unique `jti`. Une déconnexion crée une entrée de révocation dans le journal serveur ; un jeton copié et réutilisé est refusé, y compris après un redémarrage. Les sessions émises avant 0.17 nécessitent une nouvelle connexion.
5. **Migration non destructive** : révision `0003_pilot_reports` créant la table des retours, sans modification des dossiers ni des documents. Une sauvegarde SQLite est effectuée avant cette migration pour une base déjà versionnée.

## Installer ou mettre à jour

**Sauvegarder le dossier `data/` et s'assurer qu'aucun utilisateur ne modifie des documents durant la maintenance.** Puis :

```bash
python -m app.migrate status
python -m app.migrate upgrade
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Les anciens cookies sont invalidés par le nouveau format des jetons. Les collaborateurs doivent se reconnecter. Cette révocation ne remplace pas une architecture de sessions centralisée, nécessaire à un éventuel déploiement multi-instances.

## Comment effectuer la recette

1. Créer un lancement de démonstration sans numéro ORLI et y déposer un fichier fictif dans Rose.
2. Créer un compte de collaborateur de test avec droits restreints ; vérifier la consultation puis la révocation de son accès.
3. Depuis **Recette pilote**, créer un signalement en donnant les étapes précises de reproduction, et non une appréciation générale.
4. Depuis un compte administrateur, ouvrir le signalement, reproduire le cas, enregistrer une décision motivée, puis demander au collaborateur de confirmer le résultat.
5. Reporter les conclusions dans `RECETTE_PILOTE.md`. Aucun résultat utilisateur réel n'est présumé.

## Vérifications réalisées dans l'environnement de développement

- Tests FastAPI, base SQLite, sécurité et modules historiques (suites existantes plus tests de 0.17).
- Création, lecture, restriction et traitement de signalements au niveau API.
- Réutilisation refusée d'un cookie copié après déconnexion.
- Migration répétée sans perte de données ni duplication de la sauvegarde.
- Parcours Chromium avec pont local vers l'API de test : connexion, ouverture de la rubrique, création d'un signalement, résolution par l'administrateur, consultation mobile, déconnexion et refus du jeton rejoué.

**Non réalisé :** ateliers avec salariés Framatex, revue sur leurs postes et leur réseau, test d'intrusion, audit de code indépendant, homologation juridique ou technique des documents réels.
