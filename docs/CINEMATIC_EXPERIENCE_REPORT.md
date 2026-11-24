# FRAMATEX — Finalisation design, sessions et expérience cinématique

Branches : `integration/document-deletion-premium` (fusion) puis `design/cinematic-experience-final`.
`main` n'est pas modifié.

## Terminé

| Lot | Contenu | Commit |
|---|---|---|
| P0 Fusion | `integration/final-premium-design` + `feat/document-deletion-validation` (Codex, `2ea2b9b`) par commit de fusion, sans conflit ; migration `0015_document_soft_deletion` chaînée après `0014` ; suppression, corbeille, restauration et justification conservées | `8551e81` |
| P0 Sessions | « Quitter l'espace et retourner à l'accueil » (FRAMATEX : menu latéral + barre supérieure ; Client : menu + tiroir mobile) : API de déconnexion (jti révoqué côté serveur, cookie supprimé), état effacé en mémoire, `location.replace('/')` ; échec serveur → message, session conservée, nouvel essai ; retour navigateur depuis le cache → rechargement et revérification ; actualisation et navigation interne conservent la session ; pas de `beforeunload` | `b47e0bf` |
| P0 Connexions | FRAMATEX (et changement de mot de passe) : photographie textile authentique, logo officiel, titre serif, bouton « Retour à l'accueil », icônes Lucide, afficher/masquer, chargement, erreurs, notes sur les comptes, formulaire en premier sur mobile. Client (connexion, inscription) : même composition dans la structure existante, icônes Lucide dans les champs, un seul retour à l'accueil | `b47e0bf` |
| P1 Partenariat | 3 photographies officielles (framatex.net, 768 × 768 conservées ; ordre 2-1-3) en JPEG/WebP/AVIF locaux ; carrousel 5 s flou → net, zoom, perspective ; flèches, indicateurs, pause (bouton, survol, focus), clavier, glissement, agrandissement ; date « 11 février 2026 » ; inactif hors écran et sous mouvement réduit | `9578771`, `41e9bc2` |
| P1 Landing | moteur existant conservé ; ajout de 3 effets : flou → net des blocs, masque ascendant des titres, masque des photographies ; bandeau défilant infini (étapes de la chaîne de valeur) ; tout neutralisé sous `prefers-reduced-motion` | `e5ee5c3` |

## Reste à faire

- P1 icônes et finitions internes : non entrepris au-delà des icônes Lucide des connexions et de la
  sortie (l'espace interne utilisait déjà un jeu d'icônes homogène de même tracé).
- P2 Dossier Jaune 3D (Three.js), tissu 3D, effets supplémentaires (sticky stacking, GSAP
  ScrollTrigger) : **non commencés**, volontairement, pour livrer des lots stables dans le budget.

## Skills et outils réellement utilisés

- Frontend Design et Impeccable (déjà installés) : sobriété des effets (trois effets plutôt qu'une
  accumulation), contrôle du mouvement réduit et des performances.
- Lucide (ISC) : tracés SVG intégrés en ligne (mail, lock, eye, eye-off, arrow-left, log-in,
  log-out, loader, shield) ; aucune dépendance installée.
- Non installés : GOATED-UI-SKILL, MengTo/Skills, Playwright MCP (scripts Chromium existants
  utilisés), Blender MCP, Three.js et GSAP (non nécessaires aux lots livrés).

## Tests réellement exécutés

Sur `e5ee5c3` : `pytest` 211 ; JS 21/21 ; sessions 9/9 ; carrousel 7/7 ; landing 31/31 ; Espace Client
(workflow) réussi ; interne réussi ; habilitations 15/15 ; documents 9/9 ; mémoire métier 11/11 ;
`qa_platform_review` 96/96 ; `demo_full_platform` **134/135** (doublon d'email : voir limites).

## Captures disponibles

`docs/cinematic-captures/` : connexions FRAMATEX et Client (1440 et 390 px), carrousel (1440, 390,
détail, agrandissement), bandeau défilant de la landing.

## Limites

- Les photographies du partenariat et de « Notre solution » proviennent de framatex.net (pièces
  jointes non accessibles dans cette session) ; droits d'origine de `banner-17.jpg` à confirmer.
- `demo_full_platform.py` : le parcours « même email déposé deux fois → Doublon détecté » échoue depuis la
  fusion de `feat/document-deletion-validation` (moteur documentaire de Codex), non modifié ici.
- La déconnexion par la sortie volontaire est réelle ; quitter l'onglet sans cliquer laisse la
  session ouverte jusqu'à son expiration (8 h), comme demandé (pas de `beforeunload`).

## SHA final

Voir `docs/CINEMATIC_3D_REPORT.md` et le dernier commit de `design/cinematic-experience-final`.
