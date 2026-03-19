# Design Direction

## Visual Intent

The simulator should feel like a compact engineering workstation:

- modern layout
- restrained motion
- high information density without clutter
- scientific credibility over decorative dashboard styling

## Recommended Palette

- primary blue: `#0F6CBD`
- deep navy text: `#102A43`
- cool panel gray: `#E8EEF5`
- hot-section amber: `#FF8A00`
- combustion red: `#C44536`
- success green: `#2D6A4F`

## UI Principles

- Use a light canvas for readability in long analysis sessions.
- Keep controls in a stable sidebar and analysis outputs in a wide main panel.
- Surface top-line metrics first: thrust, thermal efficiency, specific fuel consumption, and exit conditions.
- Use consistent units everywhere and annotate symbols with engineering notation.
- Reserve animation for transitions that explain flow or state changes.

## Plot Principles

- Prefer Plotly for interactive exploration.
- Use clean gridlines and direct annotations instead of heavy legends where possible.
- Keep temperature-related traces in warm colors and pressure-related traces in cool colors.
- Build T-s and P-v style views to look like lab or textbook figures, not marketing charts.
- Support export-friendly figures with clear axis titles and units.

## Planned App Pages

1. Overview dashboard
2. Cycle explorer
3. Parametric study
4. Engine schematic and flow view
