from performance.efficiency import (
    jet_power_efficiency,
    overall_efficiency,
    propulsive_efficiency,
    shaft_efficiency,
)
from performance.thrust import compute_thrust


def compute_bwr(state):
    if state.Wt == 0:
        return 0.0
    return state.Wc / state.Wt


def specific_work(state):
    return state.Wt - state.Wc


def specific_thrust(state, V0):
    if state.m_dot <= 0:
        return 0.0
    return compute_thrust(state, V0) / state.m_dot


def summarize_result(result, V0):
    final_state = result.final_state if hasattr(result, "final_state") else result[-1]
    return {
        "thrust_N": compute_thrust(final_state, V0),
        "specific_thrust_N_per_kg_s": specific_thrust(final_state, V0),
        "fuel_air_ratio": final_state.fuel_air_ratio,
        "compressor_work_J_per_kg": final_state.Wc,
        "turbine_work_J_per_kg": final_state.Wt,
        "heat_input_J_per_kg": final_state.Qin,
        "bwr": compute_bwr(final_state),
        "shaft_efficiency": shaft_efficiency(final_state),
        "jet_power_efficiency": jet_power_efficiency(final_state, V0),
        "propulsive_efficiency": propulsive_efficiency(final_state, V0),
        "overall_efficiency": overall_efficiency(final_state, V0),
        "exit_velocity_mps": final_state.V,
        "exit_mach": final_state.M,
        "exit_static_temperature_K": final_state.T,
        "exit_total_temperature_K": final_state.Tt,
        "exit_static_pressure_Pa": final_state.P,
        "exit_total_pressure_Pa": final_state.Pt,
        "exit_area_m2": final_state.exit_area,
        "throat_area_m2": final_state.throat_area,
        "pressure_thrust_N": final_state.pressure_thrust,
        "nozzle_choked": final_state.nozzle_choked,
        "feasible": not final_state.infeasible,
        "warnings": list(final_state.warnings),
    }
