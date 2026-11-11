# Design

## Context

The webapp is a FastAPI + Jinja2 app whose styling lives entirely in an inline `<style>` block in `base.html`; charts are rendered client-side by a vendored Chart.js (`chart.umd.js`) configured in an inline script in `dashboard.html`. There is no build step and no external CSS framework. The existing ≤900px media query already collapses the chart grid to one column and stacks the nav, but nav links keep `width: 100%` in a row (squished), `main` keeps its 2rem/2.5rem padding, and tables have no overflow handling. The top-products chart passes raw product names as y-axis labels; Chart.js does not truncate them, so long names are drawn past the canvas edge and clipped.

## Goals / Non-Goals

**Goals:**
- Pure-CSS responsiveness for the shared layout at two breakpoints (≤900px, ≤600px), with no markup restructuring beyond class-friendly hooks that already exist.
- Readable top-products chart: truncated y-axis labels, full name in the tooltip.
- Charts that fill their fixed-height `.chart-box` containers at any width, and touch-friendly tooltips.

**Non-Goals:**
- Rewriting templates into separate mobile layouts, introducing a CSS framework, or splitting CSS into files.
- Changing any Python route, query, or store behavior; changing chart data or aggregation.
- Touch/gesture interactions beyond tooltip triggering (no pinch-zoom or swipe features).

## Decisions

- **Media queries in `base.html` instead of a framework or separate stylesheet.** The app has no build pipeline; inline styles are the established pattern. Two breakpoints: ≤900px (nav compaction, reduced `main` padding, single-column grid — extends the existing query) and ≤600px (typography/card/panel scaling, 220px chart boxes, `table { display: block; overflow-x: auto; }`).
  - *Alternative considered:* one breakpoint only — rejected because card values and 280px chart boxes still waste space on phones; a second query costs a few lines.
- **Navigation wraps instead of horizontally scrolling.** Headless-Chrome testing at a true 375px viewport measured the nav content at 522px; the original `overflow-x: auto` approach made Admin and Log out disappear behind hidden scrolling with no affordance. At ≤900px the nav row uses `flex-wrap: wrap` (brand and links keep `white-space: nowrap`; the bar reflows onto extra rows), and at ≤600px links keep the 0.95rem font with ≥40px-tall tap targets. On iPhone widths the menu wraps to two rows — accepted for visibility.
  - *Alternative considered:* keeping horizontal scroll with visible scrollbar styling — rejected because iOS overlays/hides scrollbars and cut-off items read as a broken page; a burger menu is overkill for four links.
- **Charts clamped to their container.** A canvas has an intrinsic 300px default width; at phone widths (≤~365px of available content) it overflowed its `.panel` and pushed the whole page ~30px wider than the viewport, which read as the view being cut off. `.chart-box canvas { max-width: 100%; }` lets Chart.js size the canvas to the box at any width.
  - *Alternative considered:* fixed pixel canvas sizing or disabling responsiveness — rejected; the clamp keeps charts fluid at every breakpoint.
- **Phone typography stays near desktop sizes.** Shrinking the ≤600px font sizes (0.85rem nav links, 1.25rem h1) read as too small on iPhones; the phone breakpoint now only tightens spacing and chart height, keeping the 0.95rem nav font and 1.35rem/1.5rem headings and card values.
- **Truncate axis labels in JS at the data boundary, not via CSS/Chart.js ticks.** A small `truncate(text, max = 16)` helper maps `product_name` to the label array; the tooltip `title` callback looks up the untruncated name from `data.top_products` by `dataIndex`. Sixteen characters keeps labels inside the canvas at 320px widths with the default Chart.js tick font.
  - *Alternative considered:* Chart.js `ticks.callback` truncation — rejected because it duplicates the lookup and the tooltip title still needs the raw name anyway.
- **Chart-wide defaults in `make()`.** The existing `make(id, config)` helper injects `maintainAspectRatio: false` (charts fill `.chart-box` exactly, which already has `position: relative`) and `interaction: { intersect: false }` before spreading per-chart `options`, so per-chart values still win. This fixes all four charts in one place.
  - *Alternative considered:* repeating the options in each of the four chart configs — rejected as drift-prone.
- **`autoSkip: false` on the top-products y-axis.** Bars are the data rows; skipping ticks would hide products. With truncation, every row's label fits.

## Risks / Trade-offs

- [Truncation hides part of a product name on the axis] → The full name is one tap/hover away in the tooltip; 16 chars is enough to disambiguate in practice, and the list is sorted by spend.
- [`maintainAspectRatio: false` changes chart sizing on desktop] → Charts now exactly fill the existing 280px `.chart-box` on all screens; this is the intended Chart.js pattern for fixed-height relative containers and visually only removes dead space.
- [`interaction.intersect: false` can show tooltips when the pointer is between points] → This is the desired touch behavior; mode stays `nearest` (default), so the shown tooltip is the closest data point.
- [Inline CSS grows] → Still one file, ~20 added lines; splitting stylesheets is out of scope.
- [Menu may occupy two rows on narrow phones] → Accepted: visibility of all items beats a single-row bar; four short links keep the second row short.

## Migration Plan

Template-only change; no data, config, or dependency migration. Deploy by restarting `grocery webapp`. Roll back by restoring the two template files.
