# Figure Style Guide

## Goal
Provide a unified visual style for all generated figures to ensure consistency across sources.

## Global Defaults
- Canvas: white background, no outer border.
- Font: `Source Sans 3` (fallback: `Arial`).
- Base font size: 9–10 pt for labels, 11–12 pt for titles.
- Line width: 0.8–1.2 pt.
- Axis style: thin ticks, minimal gridlines.

## Color System
- Primary palette (categorical, 6–10 colors): muted, colorblind-safe.
- Sequential palette: light to dark for intensity/heatmaps.
- Diverging palette: symmetric around zero.
- Avoid pure red/green pairs unless supplemented with shape or annotation.

## Themes
Available themes (set via `PFC_STYLE_THEME`):
- `classic` (default)
- `mono_ink`
- `ocean`
- `forest`
- `solar`

Example:
```
PFC_STYLE_THEME=ocean python scripts/run_with_style.py path/to/script.py
```

## Layout Rules
- Multi-panel figures use consistent margins and aligned axes.
- Panel labels: uppercase letters, top-left corner, bold.
- Legends: outside plot area when possible.

## File Output
- Vector first: `PDF` or `SVG`.
- Raster: `PNG` at 300 dpi minimum.
- Naming: `paperid_figX_panelY.ext` (example: `n2024_001_fig2_B.pdf`).

## Compliance Checklist
- Colors follow the palette.
- Fonts and sizes follow defaults.
- Axes and legends follow layout rules.
- Output includes reproducible script and exact command.
