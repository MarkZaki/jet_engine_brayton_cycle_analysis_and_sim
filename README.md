# Jet Engine Brayton Cycle Analysis and Simulation

Interactive project scaffold for a modern, scientific simulator focused on Brayton-cycle jet engine analysis.

Repository: https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim

## Current Status

This branch contains the repository layout, documentation, and project metadata only.
No simulator logic or UI implementation has been written yet.

## Project Goals

- Model the Brayton cycle for gas turbine and turbojet analysis.
- Extend the cycle with practical engine elements such as diffuser, combustor, nozzle, and afterburner.
- Present results through a modern interface that still reads like an engineering tool rather than a generic dashboard.
- Support both quick interactive exploration and more formal scientific plotting.

## Suggested Repository Structure

```text
jet_engine_brayton_cycle_analysis_and_sim/
|-- .github/
|   |-- ISSUE_TEMPLATE/
|   |-- workflows/
|   `-- PULL_REQUEST_TEMPLATE.md
|-- .streamlit/
|   `-- config.toml
|-- app/
|   |-- pages/
|   `-- streamlit_app.py
|-- assets/
|   |-- figures/
|   `-- icons/
|-- docs/
|   |-- architecture.md
|   |-- design-direction.md
|   `-- roadmap.md
|-- notebooks/
|-- src/
|   `-- jet_engine_sim/
|       |-- core/
|       |-- models/
|       |-- utils/
|       `-- visualization/
|-- tests/
|   |-- core/
|   `-- visualization/
|-- .gitattributes
|-- .gitignore
|-- LICENSE
|-- README.md
`-- requirements.txt
```

## Why This Structure

- `app/` keeps the Streamlit entrypoint and user-facing pages separate from the simulation engine.
- `src/jet_engine_sim/` holds domain logic so the thermodynamics model remains reusable outside the UI.
- `docs/` keeps architecture, design direction, and planning decisions visible before implementation starts.
- `tests/` is ready for physics validation and regression checks once the model exists.
- `.github/` provides basic issue, PR, and CI scaffolding from the start.

## UI and Plot Direction

The intended visual direction is modern but scientific:

- light background with disciplined contrast
- restrained blue-steel palette with thermal accents for hot sections
- engineering-style labels, units, and annotations
- interactive plots for exploration, with room for publication-style exports later

Detailed direction lives in [docs/design-direction.md](docs/design-direction.md).

## Planned Modules

- `core/`: atmosphere, cycle logic, engine assembly, and performance calculations
- `models/`: structured inputs, station states, and result containers
- `visualization/`: T-s diagrams, pressure/temperature plots, and engine-view graphics
- `utils/`: constants and unit helpers

## Setup

```bash
git clone https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim.git
cd jet_engine_brayton_cycle_analysis_and_sim
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Next Build Phases

1. Implement the thermodynamic core in `src/jet_engine_sim/core/`.
2. Build scientific data models and validation.
3. Add the Streamlit interface and interactive plots.
4. Add tests for cycle equations, station states, and UI-driven scenarios.

## License

This project is licensed under the MIT License. See `LICENSE`.
