# Landing finale premium — progression

Branche : `design/landing-final-premium` (depuis `feat/folder-color-naming`).

## Terminé

- Audit ciblé des fichiers de landing, des assets locaux, des tests et du comportement animé existant.
- Navigation institutionnelle bleu FRAMATEX, avec menu mobile cohérent.
- Direction typographique éditoriale limitée à la landing : serif système à fort contraste pour les titres, DM Sans conservée pour le texte fonctionnel.
- Section « Notre solution » raccordée à la photographie réelle d’équipe disponible localement, en AVIF/WebP/JPEG, sans génération d’image.

## En cours

- Rapport de livraison et vérification distante du commit final.

## Tests déjà exécutés

- `pytest -q tests/test_landing.py` : 6 réussis.
- `node --test tests/test_landing_motion.cjs` : 1 réussi.
- `python scripts/validate_landing_motion.py` : 31/31 contrôles Chromium réussis aux largeurs 1920, 1440, 1024, 820 et 390 px, dont le menu, les deux accès, les animations, l’absence de débordement et `prefers-reduced-motion`.
- `pytest -q` sur une base temporaire : 210 réussis, 1 avertissement de dépréciation Starlette/httpx.
- `node --test tests/*.cjs` : 21/21 réussis.

## Dernier état récupérable

- `66cba11` — hero, navigation bleue et photographie de solution, poussé sur GitHub.
- Prochaine action : exécuter les suites complètes, publier la documentation finale et vérifier le SHA distant.

## Limites connues

- L’environnement bloque l’accès public à `framatex.net` et à Motives International (erreur de tunnel 403) : aucune police ni ressource externe n’a été copiée.
- Aucun fichier distinct correspondant à `banner-17.jpg` n’était joint. La photographie d’équipe déjà présente dans les assets FRAMATEX est utilisée à la place.
