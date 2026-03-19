# Jet Engine Brayton Cycle Analysis and Simulation

Student-project scaffold for a Brayton-cycle jet engine simulator.

Repository: https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim

## Current Status

This repository currently contains only the project layout and placeholder modules.
The physics, UI, and visualization logic still need to be implemented.

## Folder Structure

```text
project_root/
|
|-- solver/
|   |-- __init__.py
|   |-- base.py
|   |-- engine.py
|   |-- cycle.py
|   `-- stages/
|       |-- compressor.py
|       |-- combustor.py
|       |-- turbine.py
|       |-- nozzle.py
|       |-- inlet.py
|       `-- afterburner.py
|
|-- models/
|   |-- atmosphere.py
|   `-- gas.py
|
|-- performance/
|   |-- thrust.py
|   |-- efficiency.py
|   `-- metrics.py
|
|-- visualization/
|   |-- plots.py
|   |-- diagrams.py
|   `-- flow.py
|
|-- ui/
|   `-- app.py
|
|-- configs/
|   `-- default.py
|
|-- main.py
`-- requirements.txt
```

## Module Responsibilities

- `solver/`: thermodynamics and engine-stage execution flow
- `models/`: atmosphere and gas-property helpers
- `performance/`: thrust, efficiencies, and derived metrics
- `visualization/`: scientific plots, schematics, and flow visuals
- `ui/`: Streamlit interface
- `configs/`: default inputs and presets

## UI Direction

The intended look remains modern but scientific:

- light engineering-style layout
- restrained blue-gray palette
- warm thermal accents for hot sections
- clear units and plot labels

## Setup

```bash
git clone https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim.git
cd jet_engine_brayton_cycle_analysis_and_sim
pip install -r requirements.txt
streamlit run ui/app.py
```

## License

This project is licensed under the MIT License. See `LICENSE`.
