## 2026-10-19 - Added ARIA label to the icon-only download button
**Learning:** Found an icon-only button (a download button) without an `aria-label`, representing an accessibility gap for screen-reader users in the application's document detail view. The button used a `title` attribute, but this does not reliably replace `aria-label` for screen reader users.
**Action:** Always ensure that icon-only interactive elements contain a clear and descriptive `aria-label` to provide proper context to assistive technologies.
