# Brief addendum: design and accessibility

*The repository owner sent this to the Claude Code cloud session that built the site on 2026-10-30, while
it was working from [BRIEF.md](BRIEF.md). It is kept verbatim below. The description of
[PR #1](https://github.com/mpuchstein/MandelbrotXR/pull/1) says how each point was handled, under "How each
addendum point was handled".*

Design and accessibility addendum to site/BRIEF.md, from the repo owner. Treat it as part of the brief; where it is more specific than the brief, follow the addendum. Don't edit BRIEF.md itself. Note in the PR how each point was handled.

## Visual direction
- **Feel:** a well-typeset research report, like Distill.pub or Our World in Data. Not a SaaS landing page.
- **Avoid:** glassmorphism, neon glow, gradient text, emoji icons, decorative animation.
- **Tokens:** define every color, the spacing scale (4px steps), radii and type sizes as CSS custom properties on `:root`, with one set for dark and one for light.
- **Color:** neutral surfaces. One accent taken from the classic Mandelbrot palette (deep blue → gold), used only for emphasis and focus.
- **Type:**
  - `system-ui` for text, `ui-monospace` for code;
  - 16–17px body text with 1.5–1.6 line height;
  - prose and transcripts capped at about 70ch;
  - `font-variant-numeric: tabular-nums` in every column of numbers.
- **Candidate labels:** add a short `label` per candidate in `site/candidates.toml` (e.g. "Opus 5.5 · v1") and use it in tables and charts. Full folder names appear only on detail pages.
- **Charts:**
  - Give each candidate one fixed, colorblind-safe color, the same in every chart. Use Okabe–Ito; past 8 candidates, extend deterministically, e.g. by adding a dash pattern or marker shape.
  - Always pair color with a direct label. Never rely on color alone.
- **Heatmap:** a single-hue sequential scale, with the rank number printed in each cell and a legend that says "1 = best".
- **Mobile:** matrix tables get a sticky header and a sticky first column, and scroll inside their own container.

## Accessibility checks (add these to "Done when")
- **axe-core:** run it (pinned `axe-core` npm package, injected through Playwright in `site/check_site.py`) on every page type in both light and dark themes. It must report zero serious or critical violations.
- **Keyboard-only pass:**
  - Must work without a mouse: sorting, filters, the heatmap and Blind/Reveal toggles, search, compare, and the theme toggle.
  - Toggles are `<button>` elements with `aria-pressed`.
  - Focus is visible everywhere.
  - Every page has a skip link, landmarks, and exactly one h1.
- **Announcements:** search results and sort changes are announced through an `aria-live="polite"` region.
- **Charts:** every SVG chart has `role="img"`, a `<title>` and a `<desc>`, and a table equivalent.

## Visual QA loop
- After producing the screenshots (390 and 1440 px, light and dark), have an agent with fresh context critique them for hierarchy, spacing, alignment, overflow, truncation, contrast and chart legibility.
- Fix what it finds, and put before/after screenshots in the PR.
