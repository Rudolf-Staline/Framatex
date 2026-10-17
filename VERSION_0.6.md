# MVP 0.6 — QR papier et passeports numériques

**Livraison du 17 octobre 2026** — Deux innovations complémentaires ajoutées au socle existant, sans perte des versions 0.1–0.5.

## 1. Passerelle papier-numérique

- Chaque lancement de fabrication dispose d'un QR généré depuis **l'UUID interne**, indépendamment du numéro ORLI.
- L'interface propose une étiquette imprimable (nom du lancement, identifiant interne, QR).
- Le QR pointe vers `/#/launch/<UUID>`. Après connexion, le navigateur ouvre le lancement. Une personne habilitée peut ensuite choisir son sous-dossier et déposer une photo, un PDF ou un scan ; les modules de classement/OCR de 0.5 restent accessibles.
- Les contrôles d'accès **ne dépendent jamais du QR** : celui-ci n'est pas un jeton de session. Les pages de génération, d'étiquette et de consultation de documents exigent une authentification.
- L'adresse encodée provient exclusivement de `FRAMATEX_PUBLIC_BASE_URL`, **jamais** des en-têtes Host ou Forwarded envoyés par le navigateur.

**Configuration** : définir `FRAMATEX_PUBLIC_BASE_URL=https://mon-serveur-interne.example` seulement après validation de l'hébergement interne et de TLS. Par défaut, le QR pointe vers `http://127.0.0.1:8000`, utilisable sur le PC hébergeur mais **pas depuis un téléphone**. Ne pas exposer l'application sur Internet pour corriger ce problème.

API : `GET /api/launches/{id}/paper-link`, `GET /api/launches/{id}/paper-qr.png`, `GET /api/launches/{id}/paper-label`.

## 2. Passeport de traçabilité documentaire

- Chaque version de document possède son passeport (nom, type, sous-dossier, numéro, taille, auteur, date, SHA-256 enregistré).
- Le passeport rappelle la version immédiatement précédente et son empreinte enregistrée.
- Les décisions approuver/refuser/demander une reprise restent associées à la version précise sur laquelle elles ont été prises.
- À la consultation, le serveur recalcule l'empreinte **sur les octets réellement stockés** et compare également la taille enregistrée. Résultats possibles : `intact`, `mismatch`, `missing` ou `unavailable`.
- Une personne n'a accès au passeport que si elle possède `launch.read` et `document.read` pour le sous-dossier correspondant ; les documents d'autres rubriques ne sont pas divulgués.

API : `GET /api/document-versions/{id}/passport`.

### Ce que le passeport ne certifie pas

Un hash SHA-256 enregistré dans **la même base modifiable** que les documents n'est **pas** un journal immuable ni une signature électronique. Un attaquant ayant accès simultanément à la base et aux fichiers peut remplacer les deux valeurs. Un registre externe d'empreintes, les sauvegardes et la politique de conservation restent à définir avec Framatex avant un pilote réel.

## Vérification

`PYTHONPATH=. python -m pytest -q` : 26 tests Python. Les scripts `tests/*.cjs` et `node --check static/*.js` passent également.

Les tests couvrent l'authentification à l'étiquette QR, l'impossibilité d'imposer une URL par un en-tête Host malveillant, le filtrage des passeports par permissions, et la détection de fichier modifié ou manquant. Aucun essai terrain de scan avec réseau interne Framatex n'a été réalisé.

## Mise à niveau

1. Arrêter le serveur et **sauvegarder le dossier `data/`**.
2. Remplacer seulement les sources (les scripts, `app/`, `static/`, tests et docs), **sans supprimer `data/`**.
3. Installer la dépendance ajoutée : `python -m pip install -r requirements.txt`.
4. Configurer `FRAMATEX_PUBLIC_BASE_URL` seulement pour une origine interne appropriée, sinon conserver la valeur locale par défaut.
5. Redémarrer le serveur et vérifier `/api/health` (version `0.6.0`).

Aucune nouvelle table ni migration de base n'est introduite par 0.6.
