# Tasks

## 1. Responsive shared layout (`base.html`)

- [x] 1.1 Extend the ≤900px media query: nav links auto-width with `white-space: nowrap` in a horizontally scrollable bar, reduced `main` padding, single-column grid gap tightened; verify at 800px viewport that all nav links are visible and content uses the narrower padding
- [x] 1.2 Add a ≤600px media query: smaller `h1` and card `.value`, tighter `.panel` padding, 220px `.chart-box`, and `table { display: block; overflow-x: auto; }`; verify at 375px viewport that the coverage table scrolls inside its panel and the page has no horizontal overflow
- [x] 1.3 Verify the desktop layout (>900px) is visually unchanged: sidebar nav, two-column chart grid, original padding

## 2. Chart readability (`dashboard.html`)

- [x] 2.1 In `make()`, inject `maintainAspectRatio: false` and `interaction: { intersect: false }` before spreading per-chart options; verify each chart fills its `.chart-box` with no overflow at desktop and 375px widths
- [x] 2.2 Add a `truncate` helper (max 16 chars + ellipsis) and use it for the top-products y-axis labels with `autoSkip: false` on the y scale; verify at 375px that no axis label is clipped at the canvas edge
- [x] 2.3 Set the top-products tooltip `title` callback to the full untruncated product name via `dataIndex`, keeping the money `label`; verify tapping/hovering a truncated bar shows the complete name
- [x] 2.4 Sanity-check the other three charts (month, type, account) still render with correct tooltips and no console errors after the `make()` change

## 3. Verification

- [x] 3.1 Run `uv run pytest tests/test_webapp.py -q` and confirm all tests pass
- [x] 3.2 Run the app (`grocery webapp`) and walk dashboard, coverage, and admin at desktop, 800px, and 375px viewports, confirming the spec scenarios: nav visible and readable, tables scroll in-panel, no clipped chart labels, tooltips work by touch

## 4. Nav wrap fix (revision after mobile-view testing)

- [x] 4.1 At ≤900px, replace the nav's `overflow-x: auto` with `flex-wrap: wrap` plus a row gap, keeping brand and links `white-space: nowrap` so the bar reflows onto rows instead of scrolling; verify at 375px that Admin and Log out are visible with no horizontal menu scrolling
- [x] 4.2 At ≤600px, tighten nav link font-size and padding while keeping ≥40px-tall tap targets; verify at 375px the menu fits or wraps cleanly without crowding
- [x] 4.3 Re-verify: `uv run pytest tests/test_webapp.py -q` passes and a headless-Chrome screenshot at a true 375px viewport shows the full menu with no clipped labels

## 5. iPhone fixes (revision after device testing)

- [x] 5.1 Clamp `.chart-box canvas` to `max-width: 100%`; verify no page overflow at 320px (doc width equals viewport, was 350 vs 320)
- [x] 5.2 Restore phone font sizes: nav links back to 0.95rem (drop the 0.85rem shrink), h1 1.35rem, card values 1.5rem, keeping 40px tap targets; verify readability at 375px
- [x] 5.3 Re-verify: `uv run pytest tests/test_webapp.py -q` passes and headless-Chrome screenshots at 320/375/390px show no horizontal overflow and the full menu
