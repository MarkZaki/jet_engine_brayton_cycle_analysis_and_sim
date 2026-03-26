# MATLAB Version

This folder contains a MATLAB translation of the core Python Brayton-cycle solver.

Included:

- ambient ISA preprocessing
- inlet, compressor, combustor, turbine, and nozzle stages
- actual and ideal state tracking
- summary performance metrics
- station and component tables
- one-at-a-time parameter sweep support
- basic MATLAB plots for `P-v`, `T-s`, `T-P`, performance, and engine flow

Not included:

- the Streamlit UI
- HTML report generation

## Quick Start

From the project root in MATLAB:

```matlab
addpath("matlab");
[result, summary] = EngineSim.main();
```

For a non-interactive solve:

```matlab
addpath("matlab");
result = EngineSim.run_engine_case(struct("verbose", false));
summary = EngineSim.summarize_result(result, result.config.flight_speed);
disp(summary.thrust_N)
disp(result.station_table)
```

For a parameter sweep:

```matlab
addpath("matlab");
sweep = EngineSim.sweep_parameter( ...
    struct("verbose", false), ...
    "compressor_pressure_ratio", ...
    [4, 8, 12] ...
);
disp(sweep)
```
