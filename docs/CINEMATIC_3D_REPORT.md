# FRAMATEX — Visuels 3D de la landing et des connexions

Branche : `design/cinematic-experience-final`. Backend, OCR, authentification, habilitations,
fonctionnalités documentaires, carrousel, espaces de travail et `main` : non modifiés.

## Visuels réalisés

| Visuel | Contenu | Commit |
|---|---|---|
| **Dossier Jaune en 3D** (section « Le Dossier Jaune, devenu numérique », entre « Notre solution » et les deux espaces) | Scène Three.js synchronisée au défilement (section collante 430 vh, progression amortie) : chemise à onglet **extrudée** (épaisseur, biseaux), couverture **articulée** qui s'ouvre comme un livre, cinq **feuilles** qui se déploient en éventail, **quatre sous-dossiers** jaune, rose, bleu, vert qui sortent et se rangent, puis un **écran** qui s'élève avec une capture réelle anonymisée de l'accueil de la plateforme. Ombres douces (PCF), lumière clé + contre-jour cyan, textures procédurales papier/kraft, légère réaction au pointeur, étapes textuelles synchronisées | `572efa1` |
| **Tissu bleu FRAMATEX en 3D** | Maillage 160 × 100 déformé à chaque image (grands plis, ondulations, froissé), matériau physique *sheen* (reflet velouté des textiles), relief de tissage procédural, réaction douce au pointeur. Intégré à l'appel à l'action de la landing et en bas du panneau décoratif des connexions FRAMATEX et Client (fondu dans la photographie authentique, formulaires inchangés) | `e491744`, commit final |

Performances et accessibilité : Three.js chargé **à la demande** (import dynamique à l'approche de la
section) ; rendu uniquement quand la scène est visible et en mouvement ; densité de pixels plafonnée
(1,75 / 1,5). **Alternative statique** — capture de la plateforme, sous-dossiers et étapes — sur écran
étroit (< 820 px), sous `prefers-reduced-motion`, sans WebGL ou en cas d'échec de chargement ; le
tissu n'est alors pas chargé (fond bleu ou photographie conservés).

## Outils réellement utilisés

- **Three.js 0.169.0** (MIT) : récupéré depuis le registre npm officiel (`npm pack three`), hébergé
  dans `static/landing/vendor/` avec sa licence (la CSP n'autorise que les scripts locaux).
- Skills déjà installés : Frontend Design et Impeccable (une scène maîtrisée plutôt qu'une
  accumulation, mouvement réduit, coût GPU).
- **Non utilisés** : GSAP ScrollTrigger (la synchronisation au défilement est assurée par une
  progression amortie en JavaScript natif, sans dépendance supplémentaire), Blender MCP (objets
  modélisés directement en Three.js), GOATED UI et MengTo Skills (non nécessaires).

## Tests exécutés

- `pytest` : 212 réussis (dont `test_landing_folder_3d_scene_is_local_lazy_and_has_static_fallback`).
- Tests JS : 21/21 (ordre des sections de la landing mis à jour avec la section 3D).
- `validate_landing_motion.py` : 31/31 ; `validate_partnership_carousel.py` : 7/7.
- `validate_sessions_ui.py` 9/9, `validate_access_ui.py` 15/15, `validate_client_workflow_ui.py`
  et `validate_internal_ui.py` réussis (connexions avec tissu).
- Chromium (WebGL logiciel SwiftShader) : six étapes de la scène capturées à 1440 px, alternative
  statique vérifiée à 390 px (aucun débordement, aucune erreur JavaScript).

Captures : `docs/cinematic-captures/1440-dossier-3d-etape-*.png`, `390-dossier-3d-statique.png`,
`1440-tissu-3d-cta.png`.

## Fonctionnalités restantes

- P2 non réalisé : écrans 3D multiples de la plateforme, fils textiles entrelacés, transitions
  supplémentaires entre scènes.
- Hors périmètre, signalé : `demo_full_platform.py` 134/135 — le parcours « même email déposé deux
  fois → Doublon détecté » échoue depuis la fusion du moteur documentaire de Codex
  (`feat/document-deletion-validation`) ; non modifié ici (fichiers de Codex).
