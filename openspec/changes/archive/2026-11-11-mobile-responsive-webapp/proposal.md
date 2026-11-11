# Proposal

## Why

The web dashboard is unusable on phones and narrow windows: the sidebar-style navigation squishes its full-width links into a single row, page padding wastes most of the viewport, and the data-coverage table overflows horizontally with no scroll. Additionally, on narrow screens the "Top products" chart clips the y-axis product names in half, so the most important labels on that chart are unreadable.

## What Changes

- Make the shared layout responsive: on tablet-width (≤900px) the navigation becomes a compact horizontal bar with auto-width links that wraps so every link stays visible, and page padding shrinks; on phone-width (≤600px) headings and card values scale down, panels tighten, and tables scroll horizontally instead of overflowing.
- Fix the "Top products" horizontal bar chart: y-axis product labels are truncated with an ellipsis so they never get clipped at the canvas edge, and the tooltip shows the full product name.
- Make all charts fill their fixed-height chart containers (`maintainAspectRatio: false`) so they scale correctly with viewport width instead of shrinking disproportionately or overflowing.
- Loosen chart tooltip hit-testing (`intersect: false`) so tooltips are easy to trigger by touch on small screens.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `web-dashboard`: Add requirements for a layout that renders usable on narrow/mobile viewports and for chart label readability on those viewports (truncated axis labels with the full text in the tooltip, charts filling their containers, touch-friendly tooltips).

## Impact

- `src/grocery_agent/webapp/templates/base.html`: responsive CSS media queries only; no markup restructure beyond what media queries need.
- `src/grocery_agent/webapp/templates/dashboard.html`: Chart.js options shared in `make()` (aspect ratio, interaction) and label/tooltip configuration for the top-products chart.
- No Python code, store, API, or dependency changes; existing webapp tests must continue to pass.
