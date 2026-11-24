# FRAMATEX — Landing page fashion editorial premium

## Périmètre livré

Branche : `design/landing-final-premium`, créée depuis `feat/folder-color-naming`.
Seule la landing publique et ses tests/documentations associés ont été modifiés :
aucun écran interne, portail Client, backend métier, token CSS partagé ou branche
`main` n’a été touché.

| Élément | État | Validation | Limites |
| --- | --- | --- | --- |
| Hero éditorial | Livré | Chromium 1920 → 390 px | La photo hero existante a été conservée. |
| Navigation bleu FRAMATEX | Livrée | Desktop + menu mobile | — |
| Typographie | Livrée | Chargement local, rendu Chromium | Police exacte de Motives non vérifiable ici. |
| Photo « Notre solution » | Livrée | AVIF/WebP/JPEG chargés localement | `banner-17.jpg` n’était pas joint. |
| Deux accès | Préservés | Liens Client et FRAMATEX réels | — |
| Chaîne de valeur / partenariat / footer | Préservés et harmonisés | Parcours de scroll Chromium | — |
| Animations et mouvement réduit | Préservés | 31/31 contrôles Chromium | — |

## Direction et ressources

- Hero éditorial : titre serif à fort contraste, zone de lecture à gauche,
  photographie immersive, CTA bleu FRAMATEX et indicateur discret.
- Navigation : bandeau bleu institutionnel, menu mobile utilisable au clavier et
  fermable avec `Escape`.
- Titres : pile serif système (`Iowan Old Style`, `Baskerville`, `Times New Roman`)
  uniquement sur la landing. Le texte conserve DM Sans locale sous OFL. Aucun token
  global n’a été modifié.
- « Notre solution » utilise la photographie d’équipe locale
  `partnership-meeting.avif`, avec repli WebP/JPEG, et non une image générée.

## Audit de référence et skills

Les skills externes demandés (REA, Anthropic Frontend Design, Taste, Impeccable et
UI UX Pro Max) ne sont pas disponibles dans cet environnement ; aucun script tiers
n’a été exécuté. Les accès publics à `framatex.net` et Motives International ont
été bloqués par le tunnel de l’environnement (HTTP 403). Aucune police, photo,
logo ou style propriétaire externe n’a donc été copié.

## Tests réellement exécutés

- `pytest -q tests/test_landing.py` : **6 réussis**.
- `node --test tests/test_landing_motion.cjs` : **1 réussi**.
- `pytest -q` sur une base temporaire : **210 réussis**, 1 avertissement de
  dépréciation Starlette/httpx.
- `node --test tests/*.cjs` : **21/21 réussis**.
- `python scripts/validate_landing_motion.py --output /workspace/artifacts/landing-premium/final` : **31/31 contrôles Chromium réussis**.
  - 1920, 1440, 1024, 820 et 390 px ;
  - assets locaux, cache `no-store`, images, liens des deux espaces ;
  - hero, cartes, chaîne de valeur, menu mobile et CTA ;
  - absence de débordement horizontal et d’erreur JavaScript ;
  - respect initial et dynamique de `prefers-reduced-motion`.

Captures : `/workspace/artifacts/landing-premium/final/`, notamment
`1920-hero-neutral.png`, `1440-hero-neutral.png`, `1024-hero-neutral.png`,
`820-hero-neutral.png` et `390-hero-neutral.png`.

## Fichiers modifiés

- `static/landing/index.html`
- `static/landing/landing.css`
- `scripts/validate_landing_motion.py`
- `tests/test_landing.py`
- `docs/LANDING_FINAL_PROGRESS.md`
- `docs/LANDING_FINAL_REPORT.md`

## Limite restante

Le brief mentionne une photographie distincte référencée sur le site officiel.
Elle n’était pas jointe et le réseau est refusé : la photographie d’équipe FRAMATEX
déjà locale est utilisée. Le fichier autorisé `banner-17.jpg` pourra la remplacer
sans changer l’architecture de la landing.
