# Jet Engine Brayton Cycle Analysis and Simulation

Student-focused Brayton-cycle jet engine simulator with:

- a reusable gas model with optional temperature-dependent properties
- explicit static and total station tracking
- actual vs theoretical cycle tracking
- turbojet and turbofan architectures
- optional afterburner, dual-stream nozzle support, and simple component maps
- nozzle choking logic and fixed-geometry nozzle constraints
- Plotly cycle plots, engine schematic, compare mode, and operating-map exports
- a Streamlit interface for interactive exploration, presets, JSON save/load, and reporting

Repository: https://github.com/MarkZaki/jet_engine_brayton_cycle_analysis_and_sim

## Current Scope

The project now includes a working 1D engine-cycle core, optional dual-stream turbofan support,
simple off-design component maps, richer reporting metrics, and a more capable interactive UI.
It is still a simplified model, but it is now much closer to a compact design-study tool than a scaffold.

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
- typed `EngineConfig` model and preset library in `configs/default.py`
- ISA-based atmosphere helper in `models/atmosphere.py`
- structured engine run result with station table export, assumptions, and equations
- explicit static vs total station properties and component delta tables
- speed-based and Mach-based flight input
- combustor fuel-air ratio calculation from target turbine inlet temperature
- dual-spool turbofan work balance with separate fan / HP compressor loads
- optional afterburner reheat stage with extra fuel addition and pressure loss
- core and bypass nozzle handling with choking, fixed-geometry constraints, and pressure-thrust estimates
- simple off-design compressor and turbine map penalties
- config validation and infeasible operating-point warnings
- thrust, TSFC, specific impulse, fuel flow, core/bypass thrust split, and sizing outputs
- actual and theoretical `P-v`, `T-s`, `T-P`, and work plots
- geometry-linked engine thermal-flow schematic with a bypass overlay for turbofan cases
- Streamlit dashboard with presets, compare mode, save/load config JSON, generalized sweeps, operating maps, report/assumptions view, and export tools
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
# or
pytest -q
```

## Notes

- The solver is a 1D thermodynamic model, not CFD.
- The turbofan and component-map features use simplified engineering approximations intended for design studies, not certified engine prediction.
- Invalid configs are rejected before solving, and weak-cycle cases are flagged as infeasible instead of being hidden behind impossible geometry.
- The thermal-flow schematic is an engineering visualization built from station data and interpolation.
- Component geometry in the schematic is scaled from solved station areas, not arbitrary fixed heights.
- The ideal cycle is closed in the diagram layer for textbook comparison, while the actual engine path remains open.

## License

This project is licensed under the MIT License. See `LICENSE`.
