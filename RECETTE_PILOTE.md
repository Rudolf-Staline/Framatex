# Framatex — Plan de recette du pilote

**Périmètre :** MVP 0.16 local, données entièrement fictives. Un dossier = un lancement. Le résultat d'un test automatique ne vaut pas validation métier par Framatex.

| Parcours | Résultat vérifié ici | Validation Framatex |
|---|---|---|
| Connexion administrateur / refus mot de passe incorrect | Oui, tests HTTP | À réaliser sur poste cible |
| Cinq échecs consécutifs / blocage temporaire | Oui, test automatisé | À confirmer derrière proxy réel |
| Création d'un lancement sans ORLI et quatre sous-dossiers | Oui, API et interface Chromium pontée | À confirmer |
| Dépôt puis nouvelle version d'une pièce dans Rose | Oui, API intégrée | À tester depuis l'interface réelle |
| Consultation et téléchargement des deux versions | Oui, recette API | À confirmer |
| Restriction d'un lancement, affectation puis retrait de droits | Oui, recette API | À confirmer avec rôles métier |
| Navigation longue fiche et sélecteur de rubrique | Oui, Chromium ponté | À confirmer |
| Déconnexion à largeur mobile 390 px | Oui, Chromium ponté | À confirmer sur téléphone |
| Absence de débordement horizontal global à 390 px | Oui, Chromium ponté | À confirmer sur navigateurs mobiles |
| Conservation de données après migration 0.14/0.15 | Tests de migration existants | Test de restauration indépendant |
| Exploitation avec de vrais documents clients / ORLI | **Non autorisée à ce stade** | Approbation de Framatex requise |
| Résistance aux fichiers hostiles, tests de charge, test d'intrusion | Non réalisés | À planifier |

## Parcours manuel conseillé

1. Sur un poste de recette, créer un administrateur avec un mot de passe distinct de tout mot de passe réel utilisé ailleurs.
2. Se connecter et créer « Chemises de démonstration — lancement A », sans ORLI. Vérifier les quatre sous-dossiers.
3. Dans Rose, déposer un bon de réception fictif TXT/PDF ; ajouter une nouvelle version et vérifier l'accès aux deux versions.
4. Créer un rôle limité à `launch.read` + `document.read` sur Rose et un collaborateur fictif.
5. Restreindre le lancement : vérifier que le collaborateur ne le voit pas ; l'autoriser, puis retirer son accès ; vérifier que les anciens liens directs renvoient une erreur.
6. Sur mobile ou émulation mobile, ouvrir le lancement, parcourir les rubriques via le sélecteur, faire défiler le tableau de documents et se déconnecter.
7. Tester le QR sur un téléphone **du réseau autorisé**, avec une URL de base réellement joignable, sans exposer l'application à Internet.
8. Vérifier sauvegarde/restauration et absence de documents sensibles dans les journaux applicatifs.

## Critères de décision

Le pilote peut être étudié après validation des propriétaires métier, du périmètre réseau, de la politique de stockage, des habilitations nominales et des procédures de restauration. Les règles de complétude, références ORLI et workflows fictifs doivent être validés avant tout usage opérationnel.
