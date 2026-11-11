# Spec Delta: web-dashboard

## ADDED Requirements

### Requirement: Responsive layout on narrow viewports
The dashboard layout SHALL remain usable on narrow viewports: at tablet-and-below widths the navigation SHALL render as a compact bar that wraps so every navigation item remains visible without scrolling the menu, and the main content SHALL use reduced padding; at phone widths headings, summary-card values, and panel padding SHALL scale down. Tables SHALL scroll horizontally within their panel instead of overflowing the page, and these behaviors SHALL apply to every page sharing the layout.

#### Scenario: Navigating on a phone
- **WHEN** an authenticated user opens the dashboard at a phone-width viewport
- **THEN** all navigation items, including Admin and Log out, are visible and readable without scrolling the menu horizontally, and no horizontal page scrolling is caused by the navigation itself

#### Scenario: Viewing a wide table on a phone
- **WHEN** the coverage table is wider than a phone-width viewport
- **THEN** the table scrolls horizontally inside its panel instead of pushing the page wider

#### Scenario: Desktop layout unchanged
- **WHEN** the dashboard is opened at a desktop viewport wider than the tablet breakpoint
- **THEN** the layout renders as before, with the sidebar-style navigation and two-column chart grid

### Requirement: Chart label readability on narrow viewports
The dashboard charts SHALL keep axis labels readable on narrow viewports: long axis labels (such as product names on the top-products chart) SHALL be truncated with an ellipsis rather than clipped, the full label text SHALL be shown in the chart tooltip, charts SHALL fill their fixed-height chart containers across viewport widths, and chart tooltips SHALL be triggerable by touch without precise targeting.

#### Scenario: Long product name on the top-products chart
- **WHEN** the top-products chart renders a product whose name is longer than the space available for y-axis labels
- **THEN** the axis shows a truncated label ending in an ellipsis that is not clipped, and tapping or hovering that bar shows a tooltip containing the full product name

#### Scenario: Charts on a narrow viewport
- **WHEN** an authenticated user views the dashboard charts at a phone-width viewport
- **THEN** each chart fills its chart container without overflowing it, and a tooltip can be brought up by touching near a data point without touching it exactly
