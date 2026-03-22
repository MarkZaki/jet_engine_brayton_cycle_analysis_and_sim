# Brayton Cycle Thermodynamics Project

This project analyzes a turbojet Brayton cycle using a clean, course-focused thermodynamics model.

It is built around the main components students usually discuss in an introductory analysis:

- inlet
- compressor
- combustor
- turbine
- nozzle

The project tracks actual and theoretical cycle behavior, plots the common thermodynamic diagrams,
shows station-by-station properties, and provides an interactive Streamlit interface for studying
how design choices affect thrust, fuel use, and efficiency.

## Features

- constant-property ideal-gas model
- ISA atmosphere support for altitude studies
- actual vs theoretical cycle tracking
- station-by-station static and total properties
- thrust, fuel-air ratio, fuel flow, specific impulse, efficiencies, and back work ratio
- `T-s`, `P-v`, `T-P`, and stage-work plots
- labeled engine schematic with useful state information
- compare mode for two input cases
- parameter sweep tools
- CSV and HTML report export

## Project Structure

```text
project_root/
|
|-- configs/
|   `-- default.py
|
|-- models/
|   |-- atmosphere.py
|   `-- gas.py
|
|-- performance/
|   |-- efficiency.py
|   |-- metrics.py
|   |-- reporting.py
|   `-- thrust.py
|
|-- solver/
|   |-- base.py
|   |-- cycle.py
|   `-- engine.py
|
|-- tests/
|   |-- test_solver.py
|   `-- test_visualization.py
|
|-- ui/
|   `-- app.py
|
|-- visualization/
|   |-- diagrams.py
|   |-- flow.py
|   `-- plots.py
|
|-- main.py
|-- requirements.txt
`-- streamlit_app.py
```

## Running The Project

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

### Script Mode

```bash
python main.py
```

## Using The Sweep Tab

The Sweep tab performs a one-at-a-time parameter study.

How to use it:

1. Set your baseline case in the sidebar.
2. Open the Sweep tab and choose one variable to study.
3. Enter the `Start`, `End`, and `Points` values.
4. Read the plot and table to see how thrust and overall efficiency change across the selected range.

How it works:

- The app creates evenly spaced values between the chosen start and end points.
- For each value, it builds a fresh case with only that one parameter changed.
- It then reruns the full Brayton-cycle solver for that case.
- This means every plotted point is a real solved operating point, not an interpolation.

In mathematical form, the sweep values are generated as:

```text
x_i = x_min + i(x_max - x_min)/(N - 1)
```

For each `x_i`, the solver evaluates a new case and recomputes the full cycle, including:

- inlet total conditions
- compressor temperature rise and work
- combustor heat addition and fuel-air ratio
- turbine work balance
- nozzle exit state and thrust

Important notes:

- Only one parameter is varied at a time.
- All other inputs stay fixed at the current baseline settings.
- If altitude is swept, ambient temperature and pressure are recalculated from the ISA atmosphere model at each point.
- If flight speed is swept, the sweep is solved in direct speed mode so the selected speed values are used exactly.

## Validation

```bash
python -m unittest discover -s tests -v
```

## Notes

- This is a one-dimensional steady-flow thermodynamic model, not CFD.
- The report and interface focus on thermodynamic interpretation, not detailed engine manufacturing design.

## License

This project is licensed under the MIT License. See `LICENSE`.
