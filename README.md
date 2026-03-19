# Jet Engine Brayton Cycle Analysis and Simulation

Simple student-project scaffold for a Brayton-cycle jet engine simulator.

Repository: https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim

## Current Status

The project is still in scaffold stage.
The files exist, but the simulator logic and UI are not implemented yet.

## Simple Structure

```text
jet_engine_brayton_cycle_analysis_and_sim/
|-- .github/
|   `-- workflows/
|-- .streamlit/
|   `-- config.toml
|-- engine_sim/
|   |-- __init__.py
|   |-- atmosphere.py
|   |-- brayton_cycle.py
|   |-- engine.py
|   |-- performance.py
|   `-- visualization.py
|-- .gitattributes
|-- .gitignore
|-- app.py
|-- LICENSE
|-- README.md
`-- requirements.txt
```

## What Each File Will Do

- `app.py`: Streamlit app entrypoint
- `engine_sim/atmosphere.py`: ambient and flight-condition helpers
- `engine_sim/brayton_cycle.py`: cycle equations
- `engine_sim/engine.py`: engine-level calculation flow
- `engine_sim/performance.py`: thrust and efficiency metrics
- `engine_sim/visualization.py`: plots and diagrams

## UI Direction

The target look is still modern but scientific:

- clean light background
- blue-gray engineering palette
- warm accents for temperature and combustion
- clear units, labels, and readable plots

## Setup

```bash
git clone https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim.git
cd jet_engine_brayton_cycle_analysis_and_sim
pip install -r requirements.txt
streamlit run app.py
```

## License

This project is licensed under the MIT License. See `LICENSE`.
