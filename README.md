# Jet Engine Brayton Cycle Analysis and Simulation

Student-focused Brayton-cycle jet engine simulator with:

- a reusable gas model
- actual vs theoretical cycle tracking
- inlet, compressor, combustor, turbine, and nozzle stages
- nozzle choking logic
- Plotly cycle plots and thermal-flow schematic exports
- a Streamlit interface for interactive exploration

Repository: https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim

## Current Scope

The project now includes a working 1D engine-cycle core and a first interactive UI.
It is still a simplified model, but it is no longer just a scaffold.

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
|-- tests/
|   |-- test_solver.py
|   `-- test_visualization.py
|
|-- main.py
`-- requirements.txt
```

## Implemented Features

- reusable `IdealGas` model in `models/gas.py`
- ISA-based atmosphere helper in `models/atmosphere.py`
- structured engine run result with station table export
- combustor fuel-air ratio calculation from target turbine inlet temperature
- turbine work balance linked to compressor demand and fuel addition
- nozzle choking detection with pressure-thrust estimate
- actual and theoretical `P-v`, `T-s`, `T-P`, and work plots
- engine thermal-flow schematic with Plotly
- Streamlit dashboard with controls, metrics, plots, station table, and a pressure-ratio sweep

## Running The Project

### Streamlit UI

```bash
streamlit run ui/app.py
```

### Script Mode

```bash
python main.py
```

Script mode writes Plotly HTML files to `outputs/`.

## Validation

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Notes

- The solver is a 1D thermodynamic model, not CFD.
- The thermal-flow schematic is an engineering visualization built from station data and interpolation.
- The ideal cycle is closed in the diagram layer for textbook comparison, while the actual engine path remains open.

## License

This project is licensed under the MIT License. See `LICENSE`.
