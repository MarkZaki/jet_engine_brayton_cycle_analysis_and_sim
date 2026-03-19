# Architecture Notes

## Layout

- `app/` is reserved for the Streamlit application shell and user navigation.
- `src/jet_engine_sim/core/` will contain thermodynamic and engine-cycle logic.
- `src/jet_engine_sim/models/` will hold structured inputs, states, and outputs.
- `src/jet_engine_sim/visualization/` will generate plots and schematic views.
- `src/jet_engine_sim/utils/` will keep constants and shared unit helpers.
- `tests/` mirrors the package layout for validation and regression coverage.

## Planned Flow

1. User inputs are collected in the Streamlit app.
2. Inputs are validated into structured models.
3. Core cycle functions compute stage states and performance outputs.
4. Visualization modules transform results into diagrams and scientific plots.
5. The app presents metrics, charts, and sensitivity studies.

## Boundary Between UI And Physics

- UI code should stay in `app/`.
- Simulation code should stay in `src/jet_engine_sim/`.
- Plot builders may live in `src/jet_engine_sim/visualization/` and be reused by the app.
- Tests should target the physics layer first, then visualization behavior, then page-level workflows.
