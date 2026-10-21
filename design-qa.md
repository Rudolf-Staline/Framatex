# Framatex · textile direction and PDF annotations

final result: passed

Reference: user-supplied `Tableau de bord Framatex – Commandes(1).png`, 1672 × 941.
The selected image governs the cream navigation rail, serif heading, textile image,
compact folder tabs, pale missing-document banner and document register.

The running FastAPI application was opened in the cloud browser. A local-only QA
harness embedded the actual app at a 1672 × 941 CSS viewport, then scaled the whole
frame to fit the browser capture. The reference was scaled by the same factor.
Reference and implementation were viewed together in a composite, with separate
header and document-register comparisons. [Implementation capture](docs/qa/textile-direction.jpg).
All fixture data and the QA session harness are excluded from source control.

P0/P1/P2 findings resolved: header actions clipped by inherited overflow; excess
card shadows; active navigation background inconsistent between folders; version
labels with inherited decorations; assistant overlapping the PDF save action;
annotation coordinates on rotated pages; protection against closing unsaved notes.

Verified in the cloud browser:

- Four folder tabs, documentary expectations and real document statuses.
- PDF modal above the dossier; page navigation, zoom and fit-to-width.
- Text annotation saved into version 2, then reopened and visibly retained.
- Warning on closing unsaved annotations, with continue/discard actions.
- Historical version 1 read-only, without a save button.
- 320, 390, 768, 1024 and 1440 px layouts: no document-level horizontal overflow; PDF save
  control inside the modal bounds. Horizontal scrolling stays within the register.
- No application console errors observed; unrelated browser-extension errors excluded.

Server validation: 113 tests passed, including actual PDF annotation bytes,
original preservation, version conflict, rotated pages, invalid coordinates,
read-only permissions, client isolation and login-space validation.
Frontend validation: 32 Node suites passed, including updated space-choice/login assertions.

Preserved product behavior: actual permissions, dossier data and workflow statuses;
existing publications and immutable versions. Notifications were previously removed
at the user's request and are not reintroduced from the reference image.

P3 follow-up: retain the established Phosphor outline icon set rather than mixing
it with the reference's filled folder icons. Long real filenames may occupy two
lines; sample reference file types and validation outcomes are not fabricated.
