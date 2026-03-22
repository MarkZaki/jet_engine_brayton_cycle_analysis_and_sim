# Jet Engine Brayton Cycle Analysis and Simulation

Student-focused Brayton-cycle jet engine simulator with:

- a reusable gas model
- explicit static and total station tracking
- actual vs theoretical cycle tracking
- inlet, compressor, combustor, turbine, optional afterburner, and nozzle stages
- nozzle choking logic
- Plotly cycle plots, engine schematic, and operating-map exports
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
- explicit static vs total station properties and component delta tables
- combustor fuel-air ratio calculation from target turbine inlet temperature
- turbine work balance linked to compressor demand and fuel addition
- optional afterburner reheat stage with extra fuel addition and pressure loss
- nozzle choking detection with pressure-thrust and throat-area estimates
- config validation and infeasible operating-point warnings
- actual and theoretical `P-v`, `T-s`, `T-P`, and work plots
- geometry-linked engine thermal-flow schematic with Plotly
- Streamlit dashboard with controls, metrics, plots, station tables, component deltas, export tools, a pressure-ratio sweep, and a flight-envelope operating map
- CSV, JSON, HTML, and PNG export support

## Running The Project

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

### Script Mode

```bash
python main.py
```

Script mode writes Plotly HTML files to `outputs/`.
It also writes station/component CSV tables, summary metrics, and an HTML report.

## Validation

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Notes

- The solver is a 1D thermodynamic model, not CFD.
- Invalid configs are rejected before solving, and weak-cycle cases are flagged as infeasible instead of being hidden behind impossible geometry.
- The thermal-flow schematic is an engineering visualization built from station data and interpolation.
- Component geometry in the schematic is scaled from solved station areas, not arbitrary fixed heights.
- The ideal cycle is closed in the diagram layer for textbook comparison, while the actual engine path remains open.

## License

This project is licensed under the MIT License. See `LICENSE`.
