from __future__ import annotations

from performance.efficiency import (
    jet_power_efficiency,
    overall_efficiency,
    propulsive_efficiency,
    shaft_efficiency,
    specific_impulse,
    thermal_efficiency,
)
from performance.thrust import compute_thrust


def compute_bwr(state) -> float:
    if state.Wt == 0.0:
        return 0.0
    return state.Wc / state.Wt


def specific_work(state) -> float:
    return state.Wt - state.Wc


def specific_thrust(state, V0: float) -> float:
    if state.m_dot <= 0.0:
        return 0.0
    return compute_thrust(state, V0) / state.m_dot


def summarize_result(result, V0: float):
    final_state = result.final_state if hasattr(result, "final_state") else result[-1]
    initial_state = result[0] if hasattr(result, "__getitem__") else None
    fuel_flow = final_state.m_dot * final_state.fuel_air_ratio

    return {
        "thrust_N": compute_thrust(final_state, V0),
        "specific_thrust_N_per_kg_s": specific_thrust(final_state, V0),
        "fuel_air_ratio": final_state.fuel_air_ratio,
        "fuel_flow_kg_s": fuel_flow,
        "specific_impulse_s": specific_impulse(final_state, V0),
        "compressor_work_J_per_kg": final_state.Wc,
        "turbine_work_J_per_kg": final_state.Wt,
        "net_specific_work_J_per_kg": specific_work(final_state),
        "heat_input_J_per_kg": final_state.Qin,
        "bwr": compute_bwr(final_state),
        "shaft_efficiency": shaft_efficiency(final_state),
        "thermal_efficiency": thermal_efficiency(final_state, V0),
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
        "flight_speed_mps": initial_state.V if initial_state is not None else V0,
        "mass_flow_rate_kg_s": final_state.m_dot,
        "feasible": not final_state.infeasible,
        "warnings": list(final_state.warnings),
    }
